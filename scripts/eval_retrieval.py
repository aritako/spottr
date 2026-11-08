"""Run the retrieval calibration sweep against the local database.

The sweep is the manual, local half of the retrieval evaluation: it embeds the authored
golden-set questions with the real embedding client, then queries the corpus directly for
every candidate cutoff and every candidate top-k. It is deliberately not part of the test
suite because it calls the OpenAI API and needs a seeded, ingested database.

The scoring and lock rules live in ``app.eval`` and stay pure and offline. This script only
owns the database session, the embedding call, and the report.

Usage (from the repository root, with the corpus already ingested):

    DATABASE_URL=postgresql+psycopg://coach:coach@localhost:5432/coach \\
        python scripts/eval_retrieval.py

See README.md for when a re-run is expected and what to do with the recommendation.
"""

import argparse
import math
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from openai import OpenAIError
from sqlalchemy import create_engine, make_url
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

# Make `app` importable when the script is run directly from the repo root, matching
# scripts/seed.py, instead of silently importing an installed copy from elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.repository.docs import DocsRepository  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.models import Chunk  # noqa: E402
from app.engine.rag import EMBEDDING_DIMENSIONS, get_embeddings  # noqa: E402
from app.eval.golden_set import (  # noqa: E402
    DEFAULT_GOLDEN_SET_PATH,
    GoldenSet,
    GoldenSetError,
    load_golden_set,
)
from app.eval.metrics import (  # noqa: E402
    QuestionResult,
    RetrievedPassage,
    ScoringReport,
    relevant_passages,
    score,
    select_passages,
)
from app.eval.sweep import (  # noqa: E402
    COSINE_DISTANCE_CEILING,
    CUTOFF_K,
    MAX_SWEEP_K,
    MIN_SWEEP_K,
    NO_MATCH_BAR,
    RECALL_BAR,
    CutoffLock,
    TopKLock,
    lock_cutoff,
    lock_top_k,
    sweep_cutoffs,
)

Embedder = Callable[[list[str]], list[list[float]]]
Retriever = Callable[[list[float], int, float], Sequence[RetrievedPassage]]

# Retrieval now asks for the widest supported window so one query reveals the distances that
# the cutoff sweep ranks. The sweep itself never asks for more than MAX_SWEEP_K passages.
DISCOVERY_TOP_K = MAX_SWEEP_K

# Cosine distance is bounded to [0, 2]; the repository applies a strict ``distance < cutoff``.
# Nudge past the ceiling so opposite vectors are observed too, instead of silently dropped.
DISCOVERY_CUTOFF = COSINE_DISTANCE_CEILING + 1e-6

EMPTY_CORPUS_MESSAGE = (
    "The database has no corpus chunks, so there is nothing to evaluate. "
    "Ingest the coaching corpus first (scripts/ingest_corpus.py), then re-run the sweep. "
    "No questions were embedded and no metrics were printed."
)


class RunnerError(RuntimeError):
    """The sweep cannot start or its input is unusable, with an actionable message."""


@dataclass(frozen=True)
class FailurePair:
    """The ``(cutoff, k)`` pair whose per-entry failures are printed."""

    cutoff: float
    k: int
    label: str


@dataclass(frozen=True)
class EntryFailure:
    """One question that retrieval got wrong at the reported pair."""

    question: str
    kind: Literal["recall", "no_match"]
    expected_document: str | None
    selected: tuple[RetrievedPassage, ...]
    expected_passages: tuple[RetrievedPassage, ...]


@dataclass(frozen=True)
class SweepEvaluation:
    """Everything the report needs from the pure sweep core."""

    discovery_results: tuple[QuestionResult, ...]
    cutoff_reports: tuple[ScoringReport, ...]
    cutoff_lock: CutoffLock
    locked_cutoff_report: ScoringReport | None
    top_k_reports: tuple[ScoringReport, ...]
    top_k_lock: TopKLock | None

    @property
    def recommended(self) -> tuple[float, int] | None:
        """The locked ``(cutoff, k)`` pair, or ``None`` when the bars are not met."""
        if self.cutoff_lock.qualifies and self.top_k_lock is not None:
            if self.top_k_lock.qualifies and self.top_k_lock.k is not None:
                cutoff = self.top_k_lock.cutoff
                return cutoff, self.top_k_lock.k
        return None


def cosine_distance(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine distance between two vectors, matching pgvector's ``<=>`` operator."""
    if len(left) != len(right):
        raise ValueError(f"vector dimension mismatch: {len(left)} != {len(right)}")

    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        raise ValueError("cosine distance is undefined for a zero vector")

    similarity = max(-1.0, min(1.0, dot / (left_norm * right_norm)))
    return 1.0 - similarity


def make_repository_retriever(repository: DocsRepository) -> Retriever:
    """Adapt ``DocsRepository.retrieve`` to the plain passages the eval core consumes."""

    def retrieve(
        query_embedding: list[float], k: int, max_distance: float
    ) -> list[RetrievedPassage]:
        chunks = repository.retrieve(query_embedding, k, max_distance)
        return [_to_retrieved_passage(chunk, query_embedding) for chunk in chunks]

    return retrieve


def _to_retrieved_passage(chunk: Chunk, query_embedding: Sequence[float]) -> RetrievedPassage:
    source = chunk.document.source if chunk.document is not None else None
    if not source:
        raise RunnerError(
            f"Chunk {chunk.id} of Document {chunk.document_id} has no source filename. "
            "Re-ingest the corpus with scripts/ingest_corpus.py, which records the corpus "
            "filename as the source, then re-run the sweep."
        )
    try:
        distance = cosine_distance(query_embedding, chunk.embedding)
    except ValueError as error:
        raise RunnerError(
            f"Chunk {chunk.id} of Document {chunk.document_id} has an unusable embedding "
            f"({error}). Re-ingest the corpus with scripts/ingest_corpus.py."
        ) from error
    return RetrievedPassage(
        document_source=source,
        chunk_index=chunk.chunk_index,
        distance=distance,
    )


def build_question_results(
    golden_set: GoldenSet,
    embeddings: Sequence[Sequence[float]],
    retrieve: Retriever,
    *,
    k: int,
    cutoff: float,
) -> tuple[QuestionResult, ...]:
    """Turn the golden set and its query embeddings into the eval core's input."""
    entries = golden_set.entries
    if len(embeddings) != len(entries):
        raise RunnerError(
            f"Embedding count mismatch: {len(embeddings)} vectors for {len(entries)} questions. "
            "The embedding client must return exactly one vector per golden-set question."
        )

    results: list[QuestionResult] = []
    for entry, embedding in zip(entries, embeddings, strict=True):
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise RunnerError(
                f"The embedding for {entry.question!r} has {len(embedding)} dimensions, but the "
                f"corpus uses {EMBEDDING_DIMENSIONS}. Check EMBEDDING_MODEL: the ingest and query "
                "models must match."
            )
        passages = retrieve(list(embedding), k, cutoff)
        results.append(
            QuestionResult(
                question=entry.question,
                expected_document=entry.expected_document,
                passages=tuple(sorted(passages, key=lambda passage: passage.distance)),
            )
        )
    return tuple(results)


def evaluate_results(
    golden_set: GoldenSet,
    embeddings: Sequence[Sequence[float]],
    retrieve: Retriever,
) -> SweepEvaluation:
    """Score every candidate configuration through the repository's cutoff path.

    A wide discovery retrieval supplies the distances that define the candidate cutoffs. Each
    candidate is then re-retrieved with that cutoff and ``k = 5`` so the report exercises the
    same SQL ``distance < cutoff`` path the coach uses. The lock rule itself only needs the
    distances, so it runs on the discovery results; its metrics are re-checked against the
    repository-scored reports at the final pair.
    """
    discovery = build_question_results(
        golden_set,
        embeddings,
        retrieve,
        k=DISCOVERY_TOP_K,
        cutoff=DISCOVERY_CUTOFF,
    )

    candidate_cutoffs = [report.cutoff for report in sweep_cutoffs(discovery, k=CUTOFF_K)]
    cutoff_reports = tuple(
        score(
            build_question_results(golden_set, embeddings, retrieve, k=CUTOFF_K, cutoff=candidate),
            k=CUTOFF_K,
            cutoff=candidate,
        )
        for candidate in candidate_cutoffs
    )
    cutoff_lock = lock_cutoff(discovery, k=CUTOFF_K)

    locked_cutoff_report: ScoringReport | None = None
    top_k_reports: tuple[ScoringReport, ...] = ()
    top_k_lock: TopKLock | None = None
    if cutoff_lock.qualifies and cutoff_lock.cutoff is not None:
        cutoff = cutoff_lock.cutoff
        locked_cutoff_report = score(
            build_question_results(golden_set, embeddings, retrieve, k=CUTOFF_K, cutoff=cutoff),
            k=CUTOFF_K,
            cutoff=cutoff,
        )
        top_k_reports = tuple(
            score(
                build_question_results(golden_set, embeddings, retrieve, k=k, cutoff=cutoff),
                k=k,
                cutoff=cutoff,
            )
            for k in range(MIN_SWEEP_K, MAX_SWEEP_K + 1)
        )
        top_k_lock = lock_top_k(discovery, cutoff=cutoff)

    return SweepEvaluation(
        discovery_results=discovery,
        cutoff_reports=cutoff_reports,
        cutoff_lock=cutoff_lock,
        locked_cutoff_report=locked_cutoff_report,
        top_k_reports=top_k_reports,
        top_k_lock=top_k_lock,
    )


def run_sweep(
    golden_set: GoldenSet,
    repository: DocsRepository,
    *,
    embed: Embedder = get_embeddings,
) -> SweepEvaluation:
    """Embed the questions, retrieve their candidates, and score the sweep.

    The caller owns the session; this function only uses the repository it is handed.
    """
    if not repository.has_chunks():
        raise RunnerError(EMPTY_CORPUS_MESSAGE)

    questions = [entry.question for entry in golden_set.entries]
    embeddings = embed(questions)
    return evaluate_results(golden_set, embeddings, make_repository_retriever(repository))


def failure_pair(evaluation: SweepEvaluation) -> FailurePair:
    """Choose the pair whose failures are most useful to a human.

    Prefer the final recommendation. If the cutoff locked but no k satisfies both bars, show
    the failing k. If no cutoff qualifies, show the most permissive candidate: a miss there is
    a real miss rather than a threshold artefact.
    """
    if evaluation.top_k_lock is not None:
        if evaluation.top_k_lock.qualifies and evaluation.top_k_lock.k is not None:
            return FailurePair(
                cutoff=evaluation.top_k_lock.cutoff,
                k=evaluation.top_k_lock.k,
                label="recommended pair",
            )
        report = evaluation.top_k_lock.report
        return FailurePair(
            cutoff=evaluation.top_k_lock.cutoff,
            k=report.k if report is not None else CUTOFF_K,
            label="locked cutoff with a failing top-k sweep",
        )

    most_permissive = max(evaluation.cutoff_reports, key=lambda report: report.cutoff)
    return FailurePair(
        cutoff=most_permissive.cutoff,
        k=CUTOFF_K,
        label="most permissive candidate cutoff (no cutoff met both bars)",
    )


def entry_failures(
    results: Sequence[QuestionResult], *, k: int, cutoff: float
) -> tuple[EntryFailure, ...]:
    """The questions retrieval got wrong at one ``(cutoff, k)`` pair."""
    failures: list[EntryFailure] = []
    for result in results:
        selected = select_passages(result.passages, k=k, cutoff=cutoff)
        if result.is_negative:
            if selected:
                failures.append(
                    EntryFailure(
                        question=result.question,
                        kind="no_match",
                        expected_document=None,
                        selected=selected,
                        expected_passages=(),
                    )
                )
            continue

        if not relevant_passages(selected, result.expected_document):
            expected_passages = relevant_passages(result.passages, result.expected_document)
            failures.append(
                EntryFailure(
                    question=result.question,
                    kind="recall",
                    expected_document=result.expected_document,
                    selected=selected,
                    expected_passages=tuple(
                        sorted(expected_passages, key=lambda passage: passage.distance)
                    ),
                )
            )
    return tuple(failures)


def unexpected_documents(
    results: Sequence[QuestionResult], *, k: int, cutoff: float
) -> tuple[tuple[str, int, int], ...]:
    """Count selected passages outside the expected Document, per Document.

    Returns ``(source, passages, questions)`` rows sorted by passage count. A Document with a
    high count across many questions is the drift signal the precision report exists for.
    """
    passages_by_source: dict[str, int] = {}
    questions_by_source: dict[str, set[str]] = {}
    for result in results:
        selected = select_passages(result.passages, k=k, cutoff=cutoff)
        for passage in selected:
            if passage.document_source == result.expected_document:
                continue
            source = passage.document_source
            passages_by_source[source] = passages_by_source.get(source, 0) + 1
            questions_by_source.setdefault(source, set()).add(result.question)

    rows = [
        (source, count, len(questions_by_source[source]))
        for source, count in passages_by_source.items()
    ]
    return tuple(sorted(rows, key=lambda row: (-row[1], row[0])))


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _distance(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _margin_bounds(
    results: Sequence[QuestionResult], report: ScoringReport
) -> tuple[float | None, float | None, float | None]:
    """Worst selected positive hit, best Negative-question passage, and their gap."""
    worst_positive = max(
        (
            margin.worst_positive_distance
            for margin in report.margins
            if margin.worst_positive_distance is not None
        ),
        default=None,
    )
    best_negative = min(
        (
            passage.distance
            for result in results
            if result.is_negative
            for passage in result.passages
        ),
        default=None,
    )
    margin = (
        best_negative - worst_positive
        if worst_positive is not None and best_negative is not None
        else None
    )
    return worst_positive, best_negative, margin


def _passage_list(passages: Sequence[RetrievedPassage]) -> str:
    if not passages:
        return "(no Passage above the cutoff)"
    return ", ".join(
        f"{passage.document_source} #{passage.chunk_index} at {passage.distance:.3f}"
        for passage in passages
    )


def format_report(evaluation: SweepEvaluation) -> str:
    """Render the human-actionable sweep report."""
    lines: list[str] = []
    first_report = evaluation.cutoff_reports[0]
    lines.append("RETRIEVAL CALIBRATION SWEEP")
    lines.append(
        f"Golden entries: {len(evaluation.discovery_results)} "
        f"({first_report.positives} positive, {first_report.negatives} Negative questions)"
    )
    lines.append("")

    lines.extend(_format_recommendation(evaluation))
    lines.append("")

    lines.append(
        f"CUTOFF SWEEP AT k={CUTOFF_K} "
        f"(bars: recall >= {RECALL_BAR:.0%}, Negative no_match >= {NO_MATCH_BAR:.0%})"
    )
    lines.append(
        "      cutoff   recall@5   no_match   precision   worst+ hit   best- passage   margin"
    )
    recommended_cutoff = evaluation.recommended[0] if evaluation.recommended else None
    for report in evaluation.cutoff_reports:
        worst_positive, best_negative, margin = _margin_bounds(evaluation.discovery_results, report)
        marker = (
            "  <- locked"
            if recommended_cutoff is not None
            and math.isclose(report.cutoff, recommended_cutoff, abs_tol=1e-12)
            else ""
        )
        lines.append(
            f"  {report.cutoff:>10.4f}   {_percent(report.recall):>8}   "
            f"{_percent(report.no_match_rate):>8}   {_percent(report.precision):>9}   "
            f"{_distance(worst_positive):>11}   {_distance(best_negative):>13}   "
            f"{_distance(margin):>7}{marker}"
        )
    lines.append(
        "  Note: margin = best Negative-question passage distance - worst selected positive hit."
    )
    lines.append(
        "  The best Negative passage is shown even when it is below the cutoff, because that "
        "separation is what the lock rule measures."
    )
    if recommended_cutoff is not None and not any(
        math.isclose(report.cutoff, recommended_cutoff, abs_tol=1e-12)
        for report in evaluation.cutoff_reports
    ):
        lines.append(
            "  The locked cutoff is centred between candidate cutoffs; its own metrics are in "
            "RECOMMENDATION."
        )
    lines.append("")

    lines.extend(_format_top_k(evaluation))
    lines.append("")

    pair = failure_pair(evaluation)
    lines.append(f"PER-ENTRY FAILURES AT cutoff={pair.cutoff:.4f}, k={pair.k} ({pair.label})")
    failures = entry_failures(evaluation.discovery_results, k=pair.k, cutoff=pair.cutoff)
    if not failures:
        lines.append(
            "  None. Every positive question retrieved its expected Document and every "
            "Negative question reported no match."
        )
    for failure in failures:
        if failure.kind == "recall":
            lines.append(f'  [recall]   "{failure.question}"')
            lines.append(f"    expected   {failure.expected_document}")
            lines.append(f"    retrieved  {_passage_list(failure.selected)}")
            if failure.expected_passages:
                nearest = failure.expected_passages[0]
                lines.append(
                    "    expected Document nearest: "
                    f"{nearest.document_source} #{nearest.chunk_index} at "
                    f"{nearest.distance:.3f} ({_not_selected_reason(nearest.distance, pair)})"
                )
            else:
                lines.append(
                    "    expected Document nearest: not in the retrieved candidates "
                    f"(top {DISCOVERY_TOP_K} at the discovery cutoff)"
                )
        else:
            lines.append(f'  [no_match] "{failure.question}"')
            lines.append("    expected   no match")
            lines.append(f"    retrieved  {_passage_list(failure.selected)}")
    lines.append("")

    hijacking_documents = unexpected_documents(
        evaluation.discovery_results, k=pair.k, cutoff=pair.cutoff
    )
    lines.append(
        f"UNEXPECTED DOCUMENTS AT cutoff={pair.cutoff:.4f}, k={pair.k} "
        "(selected passages outside the expected Document)"
    )
    if not hijacking_documents:
        lines.append("  None.")
    for source, passage_count, question_count in hijacking_documents:
        passages_label = "passage" if passage_count == 1 else "passages"
        questions_label = "question" if question_count == 1 else "questions"
        lines.append(
            f"  {source}: {passage_count} {passages_label} across "
            f"{question_count} {questions_label}"
        )

    return "\n".join(lines)


def _format_recommendation(evaluation: SweepEvaluation) -> list[str]:
    lines = ["RECOMMENDATION"]
    if evaluation.cutoff_lock.qualifies and evaluation.top_k_lock is not None:
        top_k_lock = evaluation.top_k_lock
        if top_k_lock.qualifies and top_k_lock.k is not None:
            cutoffs = evaluation.recommended
            assert cutoffs is not None
            cutoff, k = cutoffs
            cutoff_report = evaluation.locked_cutoff_report
            final_report = next(
                (report for report in evaluation.top_k_reports if report.k == k), None
            )

            lines.append(f"  MAX_COSINE_DISTANCE = {cutoff:.4f}")
            lines.append(f"  DEFAULT_TOP_K = {k}")
            lines.append("  Evidence:")
            if cutoff_report is not None:
                worst_positive, best_negative, margin = _margin_bounds(
                    evaluation.discovery_results, cutoff_report
                )
                lines.append(
                    f"    cutoff at k={CUTOFF_K}: recall@{CUTOFF_K} = "
                    f"{_percent(cutoff_report.recall)} (bar >= {RECALL_BAR:.0%}), no_match = "
                    f"{_percent(cutoff_report.no_match_rate)} (bar >= {NO_MATCH_BAR:.0%}), "
                    f"precision = {_percent(cutoff_report.precision)}"
                )
                lines.append(
                    f"    separation: worst positive hit {_distance(worst_positive)}, "
                    f"best Negative passage {_distance(best_negative)}, "
                    f"margin {_distance(margin)}"
                )
            if final_report is not None:
                lines.append(
                    f"    final pair (cutoff={cutoff:.4f}, k={k}): recall@{k} = "
                    f"{_percent(final_report.recall)}, no_match = "
                    f"{_percent(final_report.no_match_rate)}, precision = "
                    f"{_percent(final_report.precision)}"
                )
            lines.append(
                "  The bars are satisfied; update app/engine/rag.py with these values in the "
                "same reviewed change as the calibration evidence."
            )
            return lines

        lines.append("  None. The cutoff locked, but the top-k lock failed.")
        if evaluation.locked_cutoff_report is not None:
            cutoff_report = evaluation.locked_cutoff_report
            lines.append(
                f"  Locked cutoff at k={CUTOFF_K}: recall@{CUTOFF_K} = "
                f"{_percent(cutoff_report.recall)}, no_match = "
                f"{_percent(cutoff_report.no_match_rate)}, precision = "
                f"{_percent(cutoff_report.precision)}"
            )
        lines.append(f"  Why: {top_k_lock.reason}")
        lines.append(
            "  The bars cannot be met at a supported top-k, so a human must choose an "
            "explicit fallback; no constants should be changed silently."
        )
        return lines

    lines.append("  None. No candidate cutoff satisfies the lock rule.")
    lines.append(f"  Why: {evaluation.cutoff_lock.reason}")
    lines.append(
        "  The bars cannot be met simultaneously with the authored golden set and the current "
        "corpus, so a human must choose an explicit fallback; this report does not prove a "
        "safe pair."
    )
    return lines


def _format_top_k(evaluation: SweepEvaluation) -> list[str]:
    if evaluation.top_k_lock is None or evaluation.cutoff_lock.cutoff is None:
        return [
            f"TOP-K SWEEP AT THE LOCKED CUTOFF: Skipped because no cutoff locked at k={CUTOFF_K}."
        ]

    cutoff = evaluation.cutoff_lock.cutoff
    lines = [f"TOP-K SWEEP AT LOCKED CUTOFF {cutoff:.4f}"]
    lines.append("       k   recall@k   no_match   precision   worst+ hit   best- passage   margin")
    recommended_k = evaluation.top_k_lock.k if evaluation.top_k_lock.qualifies else None
    for report in evaluation.top_k_reports:
        worst_positive, best_negative, margin = _margin_bounds(evaluation.discovery_results, report)
        marker = "  <- locked" if recommended_k == report.k else ""
        lines.append(
            f"  {report.k:>6}   {_percent(report.recall):>8}   "
            f"{_percent(report.no_match_rate):>8}   {_percent(report.precision):>9}   "
            f"{_distance(worst_positive):>11}   {_distance(best_negative):>13}   "
            f"{_distance(margin):>7}{marker}"
        )
    return lines


def _not_selected_reason(distance: float, pair: FailurePair) -> str:
    if distance >= pair.cutoff:
        return "at or above the cutoff"
    return "outside the selected top-k"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=DEFAULT_GOLDEN_SET_PATH,
        help="Golden-set YAML file (default: %(default)s)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL (default: DATABASE_URL from settings)",
    )
    return parser.parse_args(argv)


@contextmanager
def _open_session(database_url: str) -> Iterator[Session]:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)() as session:
            yield session
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not settings.openai_api_key:
        print(
            "error: OPENAI_API_KEY is not set. The sweep embeds the golden-set questions with "
            "the real embedding client, so a dummy key cannot run it.",
            file=sys.stderr,
        )
        return 1

    try:
        golden_set = load_golden_set(args.golden_set)
    except GoldenSetError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    database_url = args.database_url or settings.database_url
    display_url = make_url(database_url).render_as_string(hide_password=True)

    try:
        with _open_session(database_url) as session:
            evaluation = run_sweep(golden_set, DocsRepository(session))
    except OperationalError as error:
        print(
            f"error: cannot reach the database at {display_url}. Start the database and apply "
            f"migrations, then retry. Details: {error.orig}",
            file=sys.stderr,
        )
        return 1
    except SQLAlchemyError as error:
        print(
            f"error: the database query failed at {display_url}. Check that the migrations are "
            "applied and that the corpus was ingested with the configured EMBEDDING_MODEL. "
            f"Details: {error}",
            file=sys.stderr,
        )
        return 1
    except OpenAIError as error:
        print(
            "error: the embedding call failed. Check that OPENAI_API_KEY is a real key and that "
            f"the API is reachable. Details: {error}",
            file=sys.stderr,
        )
        return 1
    except RunnerError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Golden set: {args.golden_set}")
    print(f"Database:   {display_url}")
    print()
    print(format_report(evaluation))
    return 0 if evaluation.recommended is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
