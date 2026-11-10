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
from dataclasses import dataclass, field
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
    GoldenEntry,
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
    wilson_interval,
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
    margin_bounds,
    negative_distance,
    positive_distance,
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
    ranking_ceiling: tuple[ScoringReport, ...] = ()
    true_ranks: dict[str, tuple[int, float] | None] = field(default_factory=dict)
    routing_results: tuple[QuestionResult, ...] = ()

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


def true_ranks(
    results: Sequence[QuestionResult],
    embeddings: Sequence[Sequence[float]],
    corpus: Sequence[tuple[str, Sequence[float]]],
) -> dict[str, tuple[int, float] | None]:
    """For each positive question, the 1-based rank and distance of the nearest chunk of its
    expected Document among all chunks, or None when that Document has no chunk.
    ``corpus`` is (document source, embedding) per chunk. Ranks use cosine_distance."""
    ranks: dict[str, tuple[int, float] | None] = {}
    for result, embedding in zip(results, embeddings, strict=True):
        if result.is_negative:
            continue

        distances = [cosine_distance(embedding, chunk_embedding) for _, chunk_embedding in corpus]
        expected = [
            distance
            for (source, _), distance in zip(corpus, distances, strict=True)
            if source == result.expected_document
        ]
        if not expected:
            ranks[result.question] = None
            continue

        nearest = min(expected)
        rank = 1 + sum(1 for distance in distances if distance < nearest)
        ranks[result.question] = (rank, nearest)

    return ranks


def make_repository_retriever(repository: DocsRepository) -> Retriever:
    """Adapt ``DocsRepository.retrieve`` to the plain passages the eval core consumes."""

    def retrieve(
        query_embedding: list[float], k: int, max_distance: float
    ) -> list[RetrievedPassage]:
        chunks = repository.retrieve(query_embedding, k, max_distance)
        return [_to_retrieved_passage(chunk, query_embedding) for chunk in chunks]

    return retrieve


def _chunk_source(chunk: Chunk) -> str:
    source = chunk.document.source if chunk.document is not None else None
    if not source:
        raise RunnerError(
            f"Chunk {chunk.id} of Document {chunk.document_id} has no source filename. "
            "Re-ingest the corpus with scripts/ingest_corpus.py, which records the corpus "
            "filename as the source, then re-run the sweep."
        )
    return source


def _to_retrieved_passage(chunk: Chunk, query_embedding: Sequence[float]) -> RetrievedPassage:
    source = _chunk_source(chunk)
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
    *,
    corpus: Sequence[tuple[str, Sequence[float]]] | None = None,
) -> SweepEvaluation:
    """Score every candidate configuration through the repository's cutoff path.

    A wide discovery retrieval supplies the distances that define the candidate cutoffs. Each
    candidate is then re-retrieved with that cutoff and ``k = 5`` so the report exercises the
    same SQL ``distance < cutoff`` path the coach uses. The lock rule itself only needs the
    distances, so it runs on the discovery results; its metrics are re-checked against the
    repository-scored reports at the final pair.

    Routing negatives are retrieved for the report but excluded from every gated computation:
    the coach routes them to the data tools, so they are the agent eval's subject, not the
    relevance cutoff's.
    """
    entries = golden_set.entries
    if len(embeddings) != len(entries):
        raise RunnerError(
            f"Embedding count mismatch: {len(embeddings)} vectors for {len(entries)} questions. "
            "The embedding client must return exactly one vector per golden-set question."
        )

    gated_entries: list[GoldenEntry] = []
    gated_embeddings: list[Sequence[float]] = []
    routing_entries: list[GoldenEntry] = []
    routing_embeddings: list[Sequence[float]] = []
    for entry, embedding in zip(entries, embeddings, strict=True):
        if entry.no_match and entry.negative_kind == "routing":
            routing_entries.append(entry)
            routing_embeddings.append(embedding)
        else:
            gated_entries.append(entry)
            gated_embeddings.append(embedding)

    gated_set = GoldenSet(entries=gated_entries)
    discovery = build_question_results(
        gated_set,
        gated_embeddings,
        retrieve,
        k=DISCOVERY_TOP_K,
        cutoff=DISCOVERY_CUTOFF,
    )
    ranking_ceiling = tuple(
        score(discovery, k=k, cutoff=DISCOVERY_CUTOFF) for k in range(MIN_SWEEP_K, MAX_SWEEP_K + 1)
    )

    candidate_cutoffs = [report.cutoff for report in sweep_cutoffs(discovery, k=CUTOFF_K)]
    cutoff_reports = tuple(
        score(
            build_question_results(
                gated_set, gated_embeddings, retrieve, k=CUTOFF_K, cutoff=candidate
            ),
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
            build_question_results(
                gated_set, gated_embeddings, retrieve, k=CUTOFF_K, cutoff=cutoff
            ),
            k=CUTOFF_K,
            cutoff=cutoff,
        )
        top_k_reports = tuple(
            score(
                build_question_results(gated_set, gated_embeddings, retrieve, k=k, cutoff=cutoff),
                k=k,
                cutoff=cutoff,
            )
            for k in range(MIN_SWEEP_K, MAX_SWEEP_K + 1)
        )
        top_k_lock = lock_top_k(discovery, cutoff=cutoff)

    routing_results: tuple[QuestionResult, ...] = ()
    if routing_entries:
        routing_results = build_question_results(
            GoldenSet(entries=routing_entries),
            routing_embeddings,
            retrieve,
            k=DISCOVERY_TOP_K,
            cutoff=DISCOVERY_CUTOFF,
        )

    return SweepEvaluation(
        discovery_results=discovery,
        cutoff_reports=cutoff_reports,
        cutoff_lock=cutoff_lock,
        locked_cutoff_report=locked_cutoff_report,
        top_k_reports=top_k_reports,
        top_k_lock=top_k_lock,
        ranking_ceiling=ranking_ceiling,
        true_ranks=(true_ranks(discovery, gated_embeddings, corpus) if corpus is not None else {}),
        routing_results=routing_results,
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

    corpus = [(_chunk_source(chunk), chunk.embedding) for chunk in repository.list_chunks()]
    questions = [entry.question for entry in golden_set.entries]
    embeddings = embed(questions)
    return evaluate_results(
        golden_set,
        embeddings,
        make_repository_retriever(repository),
        corpus=corpus,
    )


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


def _rate_with_interval(successes: int, total: int) -> str:
    if total == 0:
        return "n/a"
    low, high = wilson_interval(successes, total)
    return f"{successes / total * 100:.1f}% [{low * 100:.1f}-{high * 100:.1f}]"


def _distance(value: float | None) -> str:
    if value is None or math.isinf(value):
        return "none"
    return f"{value:.4f}"


def _passage_list(passages: Sequence[RetrievedPassage]) -> str:
    if not passages:
        return "(no Passage above the cutoff)"
    return ", ".join(
        f"{passage.document_source} #{passage.chunk_index} at {passage.distance:.4f}"
        for passage in passages
    )


def format_report(evaluation: SweepEvaluation) -> str:
    """Render the human-actionable sweep report."""
    lines: list[str] = []
    first_report = evaluation.cutoff_reports[0]
    lines.append("RETRIEVAL CALIBRATION SWEEP")
    lines.append(
        f"Golden entries: "
        f"{len(evaluation.discovery_results) + len(evaluation.routing_results)} "
        f"({first_report.positives} positive, {first_report.negatives} retrieval Negative, "
        f"{len(evaluation.routing_results)} routing Negative questions)"
    )
    lines.append("")

    lines.extend(_format_recommendation(evaluation))
    lines.append("")

    lines.append(
        f"CUTOFF SWEEP AT k={CUTOFF_K} "
        f"(bars: recall >= {RECALL_BAR:.0%}, Negative no_match >= {NO_MATCH_BAR:.0%})"
    )
    if first_report.positives and first_report.negatives:
        p_bound, d_bound = margin_bounds(evaluation.discovery_results, k=CUTOFF_K)
        lines.append(
            f"Recall bound P={_distance(p_bound)}, negative bound D={_distance(d_bound)}, "
            f"margin D-P={_distance(d_bound - p_bound)} "
            "(cutoffs in (P, D] meet both bars)"
        )
    lines.append(
        "      cutoff   recall@5 [95% CI]      no_match [95% CI]   doc precision   "
        "passage precision"
    )
    recommended_cutoff = evaluation.recommended[0] if evaluation.recommended else None
    for report in evaluation.cutoff_reports:
        marker = (
            "  <- locked"
            if recommended_cutoff is not None
            and math.isclose(report.cutoff, recommended_cutoff, abs_tol=1e-12)
            else ""
        )
        lines.append(
            f"  {report.cutoff:>10.4f}   "
            f"{_rate_with_interval(report.recalled, report.positives):>20}   "
            f"{_rate_with_interval(report.no_matches, report.negatives):>19}   "
            f"{_percent(report.document_precision):>13}   "
            f"{_percent(report.precision):>17}{marker}"
        )
    if recommended_cutoff is not None and not any(
        math.isclose(report.cutoff, recommended_cutoff, abs_tol=1e-12)
        for report in evaluation.cutoff_reports
    ):
        lines.append(
            "  The locked cutoff is not a candidate cutoff; its own metrics are in RECOMMENDATION."
        )
    lines.append("")

    lines.extend(_format_top_k(evaluation))
    lines.append("")

    lines.extend(_format_ranking_ceiling(evaluation))
    lines.append("")

    lines.extend(_format_distances(evaluation))
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
                    f"{nearest.distance:.4f} ({_not_selected_reason(nearest.distance, pair)})"
                )
            else:
                lines.append(
                    "    expected Document nearest: not in the retrieved candidates "
                    f"(top {DISCOVERY_TOP_K} at the discovery cutoff)"
                )
            if failure.question in evaluation.true_ranks:
                true_rank = evaluation.true_ranks[failure.question]
                if true_rank is None:
                    lines.append("    expected Document has no chunks")
                else:
                    rank, distance = true_rank
                    lines.append(f"    true rank {rank} at distance {_distance(distance)}")
        else:
            lines.append(f'  [no_match] "{failure.question}"')
            lines.append("    expected   no match")
            lines.append(f"    retrieved  {_passage_list(failure.selected)}")
    lines.append("")

    routing_lines = _format_routing_negatives(evaluation)
    if routing_lines:
        lines.extend(routing_lines)
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
                p_bound, d_bound = margin_bounds(evaluation.discovery_results, k=k)
                lines.append(
                    f"    cutoff at k={CUTOFF_K}: recall@{CUTOFF_K} = "
                    f"{_rate_with_interval(cutoff_report.recalled, cutoff_report.positives)} "
                    f"(bar >= {RECALL_BAR:.0%}), no_match = "
                    f"{_rate_with_interval(cutoff_report.no_matches, cutoff_report.negatives)} "
                    f"(bar >= {NO_MATCH_BAR:.0%}), doc precision = "
                    f"{_percent(cutoff_report.document_precision)}, passage precision = "
                    f"{_percent(cutoff_report.precision)}"
                )
                lines.append(
                    f"    separation: recall bound P={_distance(p_bound)}, "
                    f"negative bound D={_distance(d_bound)}, "
                    f"margin D-P={_distance(d_bound - p_bound)}"
                )
            if final_report is not None:
                lines.append(
                    f"    final pair (cutoff={cutoff:.4f}, k={k}): recall@{k} = "
                    f"{_rate_with_interval(final_report.recalled, final_report.positives)}, "
                    f"no_match = "
                    f"{_rate_with_interval(final_report.no_matches, final_report.negatives)}, "
                    f"doc precision = {_percent(final_report.document_precision)}, "
                    f"passage precision = {_percent(final_report.precision)}"
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
    _, d_bound = margin_bounds(evaluation.discovery_results, k=CUTOFF_K)
    lines = [f"TOP-K SWEEP AT LOCKED CUTOFF {cutoff:.4f}"]
    lines.append(f"Negative bound D={_distance(d_bound)}")
    lines.append(
        "  k   recall@k [95% CI]   no_match [95% CI]   doc precision   passage precision   P"
    )
    recommended_k = evaluation.top_k_lock.k if evaluation.top_k_lock.qualifies else None
    for report in evaluation.top_k_reports:
        p_bound, _ = margin_bounds(evaluation.discovery_results, k=report.k)
        marker = "  <- locked" if recommended_k == report.k else ""
        lines.append(
            f"  {report.k:>2}   "
            f"{_rate_with_interval(report.recalled, report.positives):>20}   "
            f"{_rate_with_interval(report.no_matches, report.negatives):>19}   "
            f"{_percent(report.document_precision):>13}   "
            f"{_percent(report.precision):>17}   {_distance(p_bound):>7}{marker}"
        )
    return lines


def _format_ranking_ceiling(evaluation: SweepEvaluation) -> list[str]:
    lines = ["RANKING CEILING (no cutoff)"]
    lines.append("  k   recall@k [95% CI]")
    for report in evaluation.ranking_ceiling:
        lines.append(
            f"  {report.k:>2}   {_rate_with_interval(report.recalled, report.positives):>20}"
        )
    return lines


def _format_distances(evaluation: SweepEvaluation) -> list[str]:
    lines = [f"NEGATIVE AND POSITIVE DISTANCES AT k={CUTOFF_K}"]
    recommended_cutoff = evaluation.recommended[0] if evaluation.recommended else None

    negatives = sorted(
        (
            (negative_distance(result), result)
            for result in evaluation.discovery_results
            if result.is_negative
        ),
        key=lambda pair: pair[0],
    )
    if negatives:
        lines.append("  Negatives, nearest first:")
        for distance, result in negatives:
            nearest = select_passages(result.passages, k=1, cutoff=COSINE_DISTANCE_CEILING)
            document = nearest[0].document_source if nearest else "none"
            marker = (
                "  <- leaks"
                if recommended_cutoff is not None and distance < recommended_cutoff
                else ""
            )
            lines.append(f"    {_distance(distance):>8}  {document:<40}  {result.question}{marker}")

    positives = sorted(
        (
            (positive_distance(result, CUTOFF_K), result)
            for result in evaluation.discovery_results
            if not result.is_negative
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )[:10]
    if positives:
        lines.append("  Ten positives with the largest distance at k=5:")
        for distance, result in positives:
            lines.append(f"    {_distance(distance):>8}  {result.question}")
    return lines


def _format_routing_negatives(evaluation: SweepEvaluation) -> list[str]:
    if not evaluation.routing_results:
        return []

    pair = failure_pair(evaluation)
    lines = ["ROUTING NEGATIVES (reported, not gated)"]
    lines.append(
        "These are intended to be routed to the data tools by the coach; gating them is the "
        "agent eval's job (#17)."
    )
    lines.append(f"  distance  nearest Document  status at cutoff {pair.cutoff:.4f}  question")
    for result in evaluation.routing_results:
        distance = negative_distance(result)
        nearest = select_passages(result.passages, k=1, cutoff=COSINE_DISTANCE_CEILING)
        document = nearest[0].document_source if nearest else "none"
        status = "would leak" if distance < pair.cutoff else "no match"
        lines.append(
            f'  {_distance(distance):>8}  {document:<40}  {status:<10}  "{result.question}"'
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
