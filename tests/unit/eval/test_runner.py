import importlib.util
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError

from app.eval.golden_set import GoldenEntry, GoldenSet
from app.eval.metrics import QuestionResult, RetrievedPassage

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "eval_retrieval.py"

spec = importlib.util.spec_from_file_location("eval_retrieval", SCRIPT)
assert spec is not None and spec.loader is not None
eval_retrieval = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = eval_retrieval
spec.loader.exec_module(eval_retrieval)

DIMENSIONS = 1536


def _vector(*values: float) -> list[float]:
    """Build a 1536-dimensional vector from its leading values."""
    if len(values) > DIMENSIONS:
        raise ValueError("too many leading values")
    return [*values, *([0.0] * (DIMENSIONS - len(values)))]


def _result(
    question: str,
    expected_document: str | None,
    *passages: tuple[str, int, float],
) -> QuestionResult:
    return QuestionResult(
        question=question,
        expected_document=expected_document,
        passages=tuple(
            RetrievedPassage(document_source=source, chunk_index=index, distance=distance)
            for source, index, distance in passages
        ),
    )


def _golden_set(*entries: GoldenEntry) -> GoldenSet:
    return GoldenSet(entries=list(entries))


def _evaluate(
    results: list[QuestionResult],
    *,
    corpus: list[tuple[str, list[float]]] | None = None,
    routing: set[str] | None = None,
) -> "eval_retrieval.SweepEvaluation":
    """Run the real evaluator through a tiny in-memory retriever.

    Each synthetic question gets a distinct unit vector so the retriever can recover its
    pre-built passages, then applies the same strict cutoff and limit a real query would.
    """
    embeddings = [_vector(float(index + 1)) for index in range(len(results))]
    passages_by_embedding = {
        tuple(embedding): result.passages
        for embedding, result in zip(embeddings, results, strict=True)
    }
    routing_questions = routing or set()
    entries = [
        _entry_for(result, routing=result.question in routing_questions) for result in results
    ]

    def retrieve(
        query_embedding: list[float], k: int, max_distance: float
    ) -> tuple[RetrievedPassage, ...]:
        matching = passages_by_embedding[tuple(query_embedding)]
        return tuple(passage for passage in matching if passage.distance < max_distance)[:k]

    return eval_retrieval.evaluate_results(
        _golden_set(*entries), embeddings, retrieve, corpus=corpus
    )


def _entry_for(result: QuestionResult, *, routing: bool = False) -> GoldenEntry:
    if result.expected_document is None:
        return GoldenEntry(
            question=result.question,
            no_match=True,
            negative_kind="routing" if routing else "retrieval",
        )
    return GoldenEntry(question=result.question, expected_document=result.expected_document)


class _FakeDocument:
    def __init__(self, source: str | None) -> None:
        self.source: str | None = source


class _FakeChunk:
    def __init__(
        self,
        chunk_id: int,
        source: str | None,
        *,
        chunk_index: int = 0,
        embedding: list[float] | None = None,
    ) -> None:
        self.id: int = chunk_id
        self.document_id: int = chunk_id
        self.chunk_index: int = chunk_index
        self.embedding: list[float] = embedding if embedding is not None else _vector()
        self.document: _FakeDocument = _FakeDocument(source)


class _FakeRepository:
    """A tiny pgvector stand-in: filter by distance, order ascending, then limit."""

    def __init__(self, chunks: list[_FakeChunk]) -> None:
        self.chunks: list[_FakeChunk] = chunks
        self.queries: list[tuple[int, float]] = []

    def has_chunks(self) -> bool:
        return bool(self.chunks)

    def list_chunks(self) -> list[_FakeChunk]:
        return list(self.chunks)

    def retrieve(
        self, query_embedding: list[float], k: int, max_distance: float
    ) -> list[_FakeChunk]:
        self.queries.append((k, max_distance))
        scored = [
            (eval_retrieval.cosine_distance(query_embedding, chunk.embedding), chunk)
            for chunk in self.chunks
        ]
        scored.sort(key=lambda pair: pair[0])
        return [chunk for distance, chunk in scored[:k] if distance < max_distance]


def test_cosine_distance_matches_the_cosine_metric() -> None:
    assert eval_retrieval.cosine_distance(_vector(1.0), _vector(1.0)) == pytest.approx(0.0)
    assert eval_retrieval.cosine_distance(_vector(1.0), _vector(0.0, 1.0)) == pytest.approx(1.0)
    assert eval_retrieval.cosine_distance(_vector(1.0), _vector(-1.0)) == pytest.approx(2.0)


def test_cosine_distance_rejects_mismatched_or_empty_vectors() -> None:
    with pytest.raises(ValueError, match="dimension"):
        eval_retrieval.cosine_distance([1.0, 0.0], [1.0])

    with pytest.raises(ValueError, match="zero"):
        eval_retrieval.cosine_distance([0.0, 0.0], [1.0, 0.0])


def test_run_sweep_fails_clearly_when_the_corpus_is_empty() -> None:
    repository = _FakeRepository([])
    golden_set = _golden_set(GoldenEntry(question="Should I deload?", expected_document="a.md"))

    with pytest.raises(eval_retrieval.RunnerError) as error:
        eval_retrieval.run_sweep(
            golden_set,
            repository,
            embed=lambda texts: pytest.fail("must not embed when the corpus is empty"),
        )

    assert "corpus" in str(error.value).lower()
    assert "ingest" in str(error.value).lower()


def test_run_sweep_embeds_each_question_once_and_locks_the_constants() -> None:
    repository = _FakeRepository(
        [
            _FakeChunk(1, "a.md", embedding=_vector(1.0)),
            _FakeChunk(2, "b.md", embedding=_vector(0.0, 1.0)),
        ]
    )
    golden_set = _golden_set(
        GoldenEntry(question="positive question", expected_document="a.md"),
        GoldenEntry(question="negative question", no_match=True, negative_kind="retrieval"),
    )
    embedded_questions: list[str] = []

    def embed(questions: list[str]) -> list[list[float]]:
        embedded_questions.extend(questions)
        return [_vector(1.0), _vector(0.0, 0.0, 1.0)]

    evaluation = eval_retrieval.run_sweep(golden_set, repository, embed=embed)

    assert embedded_questions == ["positive question", "negative question"]
    assert evaluation.cutoff_lock.qualifies is True
    assert evaluation.cutoff_lock.cutoff == pytest.approx(0.5)
    assert evaluation.cutoff_lock.margin == pytest.approx(1.0)
    assert evaluation.top_k_lock is not None
    assert evaluation.top_k_lock.qualifies is True
    assert evaluation.top_k_lock.k == 1
    # Every candidate cutoff and every locked top-k answers through the repository cutoff path.
    assert (5, pytest.approx(0.5)) in repository.queries
    assert (5, pytest.approx(1.5)) in repository.queries
    assert (1, pytest.approx(0.5)) in repository.queries


def test_run_sweep_rejects_embeddings_that_do_not_match_the_questions() -> None:
    repository = _FakeRepository([_FakeChunk(1, "a.md")])
    golden_set = _golden_set(GoldenEntry(question="positive", expected_document="a.md"))

    with pytest.raises(eval_retrieval.RunnerError, match="embedding"):
        eval_retrieval.run_sweep(golden_set, repository, embed=lambda _: [])


def test_run_sweep_rejects_chunks_without_a_source() -> None:
    repository = _FakeRepository([_FakeChunk(1, None, embedding=_vector(1.0))])
    golden_set = _golden_set(GoldenEntry(question="positive", expected_document="a.md"))

    with pytest.raises(eval_retrieval.RunnerError, match="source"):
        eval_retrieval.run_sweep(
            golden_set,
            repository,
            embed=lambda _: [_vector(1.0)],
        )


def test_to_retrieved_passage_rejects_an_unusable_chunk_embedding() -> None:
    with pytest.raises(eval_retrieval.RunnerError, match="unusable embedding"):
        eval_retrieval._to_retrieved_passage(_FakeChunk(1, "a.md"), _vector(1.0))


def test_true_ranks_rank_every_chunk_and_keep_ties_behind_the_expected_document() -> None:
    results = [
        _result("positive", "a.md", ("a.md", 0, 0.3)),
        _result("negative", None),
    ]
    embeddings = [_vector(1.0), _vector(0.0, 0.0, 1.0)]
    corpus = [
        ("b.md", _vector(1.0)),  # distance 0, so it ranks ahead of the expected chunk
        ("a.md", _vector(0.0, 1.0)),  # the expected Document's nearest chunk at distance 1
        ("a.md", _vector(0.0, 1.0)),  # a tie, which does not rank ahead
    ]

    ranks = eval_retrieval.true_ranks(results, embeddings, corpus)

    assert set(ranks) == {"positive"}
    rank, distance = ranks["positive"] or (None, None)
    assert rank == 2
    assert distance == pytest.approx(1.0)


def test_true_ranks_report_none_when_the_expected_document_has_no_chunks() -> None:
    results = [_result("positive", "a.md", ("a.md", 0, 0.2))]

    ranks = eval_retrieval.true_ranks(
        results,
        [_vector(1.0)],
        [("b.md", _vector(1.0))],
    )

    assert ranks == {"positive": None}


def test_format_report_appends_a_true_rank_to_a_recall_failure() -> None:
    results = [
        _result(
            "positive question",
            "a.md",
            ("c.md", 0, 0.1),
            ("c.md", 1, 0.2),
            ("c.md", 2, 0.3),
            ("c.md", 3, 0.4),
            ("c.md", 4, 0.5),
            ("a.md", 5, 0.95),
        ),
        _result("negative question", None, ("c.md", 6, 0.1)),
    ]

    evaluation = _evaluate(
        results,
        corpus=[
            ("b.md", _vector(1.0)),  # the positive question's vector is _vector(1.0)
            ("a.md", _vector(0.0, 1.0)),
        ],
    )

    report = eval_retrieval.format_report(evaluation)

    assert "true rank 2 at distance 1.0000" in report


def test_format_report_says_when_a_missed_document_has_no_chunks() -> None:
    results = [
        _result("positive question", "a.md", ("c.md", 0, 0.2)),
        _result("negative question", None, ("c.md", 1, 0.1)),
    ]

    evaluation = _evaluate(results, corpus=[("b.md", _vector(1.0))])

    assert "expected Document has no chunks" in eval_retrieval.format_report(evaluation)


def test_format_report_names_the_recommended_constants_with_evidence() -> None:
    results = [
        _result("positive one", "a.md", ("a.md", 0, 0.2), ("b.md", 0, 0.3)),
        _result("positive two", "b.md", ("b.md", 2, 0.4)),
        _result("negative one", None, ("c.md", 0, 0.9)),
        _result("negative two", None),
    ]
    evaluation = _evaluate(results)

    report = eval_retrieval.format_report(evaluation)

    assert "RECOMMENDATION" in report
    assert "MAX_COSINE_DISTANCE = 0.6500" in report
    assert "DEFAULT_TOP_K = 1" in report
    assert "recall@5 = 100.0%" in report
    assert "no_match = 100.0%" in report
    assert "margin" in report
    assert "0.6500" in report  # the candidate-cutoff table
    assert "PER-ENTRY FAILURES" in report
    assert "None. Every positive question" in report


def test_format_report_prints_a_row_for_every_candidate_cutoff() -> None:
    results = [
        _result("positive", "a.md", ("a.md", 0, 0.2)),
        _result("negative", None, ("b.md", 0, 0.8)),
    ]
    evaluation = _evaluate(results)

    report = eval_retrieval.format_report(evaluation)
    table = report.split("CUTOFF SWEEP AT k=5", 1)[1].split("TOP-K SWEEP", 1)[0]
    rows = [line for line in table.splitlines() if line.strip().startswith(tuple("0123456789."))]

    assert len(rows) == len(evaluation.cutoff_reports)
    assert "0.1000" in table
    assert "0.5000" in table
    assert "1.4000" in table


def test_format_report_lists_per_entry_failures_with_what_was_retrieved() -> None:
    results = [
        _result("positive question", "a.md", ("c.md", 3, 0.2), ("b.md", 0, 0.3)),
        _result("negative question", None, ("c.md", 1, 0.1)),
    ]
    evaluation = _evaluate(results)

    report = eval_retrieval.format_report(evaluation)

    assert "RECOMMENDATION" in report
    assert "None." in report
    assert "No cutoff reaches recall@5" in report
    assert "PER-ENTRY FAILURES" in report
    assert '"positive question"' in report
    assert "c.md #3" in report
    assert '"negative question"' in report
    assert "c.md #1" in report


def test_format_report_reports_a_positive_miss_with_the_expected_document_distance() -> None:
    results = [
        _result("positive question", "a.md", ("c.md", 0, 0.2), ("a.md", 4, 2.0)),
        _result("negative question", None),
    ]
    evaluation = _evaluate(results)

    report = eval_retrieval.format_report(evaluation)

    assert "positive question" in report
    assert "expected Document nearest" in report
    assert "a.md #4 at 2.000" in report


def test_format_report_summarizes_documents_hijacking_retrievals() -> None:
    results = [
        _result("positive one", "a.md", ("hijacker.md", 0, 0.1)),
        _result("positive two", "b.md", ("hijacker.md", 1, 0.1)),
        _result("negative", None, ("hijacker.md", 2, 0.1)),
    ]
    evaluation = _evaluate(results)

    report = eval_retrieval.format_report(evaluation)

    assert "UNEXPECTED DOCUMENTS" in report
    assert "hijacker.md" in report
    assert "3 passages" in report
    assert "3 questions" in report


def test_evaluate_results_skips_the_top_k_sweep_when_no_cutoff_locks() -> None:
    results = [
        _result("positive", "a.md", ("c.md", 0, 0.2)),
        _result("negative", None, ("c.md", 0, 0.1)),
    ]

    evaluation = _evaluate(results)

    assert evaluation.cutoff_lock.qualifies is False
    assert evaluation.top_k_lock is None
    assert evaluation.top_k_reports == ()
    assert "TOP-K SWEEP" in eval_retrieval.format_report(evaluation)
    assert "Skipped" in eval_retrieval.format_report(evaluation)


def test_evaluate_results_gates_only_retrieval_negatives() -> None:
    results = [
        _result("positive", "a.md", ("a.md", 0, 0.2)),
        _result("retrieval negative", None, ("b.md", 0, 0.9)),
        _result("routing negative", None, ("c.md", 0, 0.1)),
    ]

    evaluation = _evaluate(results, routing={"routing negative"})

    assert evaluation.cutoff_lock.qualifies is True
    assert evaluation.cutoff_lock.cutoff == pytest.approx(0.55)
    assert [result.question for result in evaluation.discovery_results] == [
        "positive",
        "retrieval negative",
    ]
    assert [result.question for result in evaluation.routing_results] == ["routing negative"]
    assert all(report.negatives == 1 for report in evaluation.cutoff_reports)

    report = eval_retrieval.format_report(evaluation)

    assert "1 retrieval Negative" in report
    assert "1 routing Negative" in report
    assert "ROUTING NEGATIVES (reported, not gated)" in report
    assert "routing negative" in report
    assert "would leak" in report


def test_format_report_omits_the_routing_section_without_routing_negatives() -> None:
    results = [
        _result("positive", "a.md", ("a.md", 0, 0.2)),
        _result("negative", None, ("b.md", 0, 0.9)),
    ]

    report = eval_retrieval.format_report(_evaluate(results))

    assert "ROUTING NEGATIVES" not in report


def test_format_report_renders_rates_as_percentages() -> None:
    # Guard the display against silently switching to raw fractions: a 0.95 rate is 95.0%.
    results = [
        *[
            _result(f"positive {index}", f"a-{index}.md", (f"a-{index}.md", 0, 0.2))
            for index in range(19)
        ],
        _result("missed", "missing.md", ("other.md", 0, 0.8)),
        _result("negative", None, ("other.md", 0, 0.9)),
    ]

    report = eval_retrieval.format_report(_evaluate(results))

    assert "recall@5 = 95.0%" in report
    assert "recall = 0.95" not in report


def test_main_requires_a_real_api_key(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(eval_retrieval.settings, "openai_api_key", "")

    assert eval_retrieval.main([]) == 1

    assert "OPENAI_API_KEY" in capsys.readouterr().err


def test_main_fails_clearly_when_the_corpus_is_empty(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(eval_retrieval.settings, "openai_api_key", "dummy")

    @contextmanager
    def fake_session(_database_url: str) -> Iterator[object]:
        yield object()

    monkeypatch.setattr(eval_retrieval, "_open_session", fake_session)
    monkeypatch.setattr(eval_retrieval, "DocsRepository", lambda _session: _FakeRepository([]))

    assert eval_retrieval.main([]) == 1

    stderr = capsys.readouterr().err.lower()
    assert "corpus" in stderr
    assert "ingest" in stderr


def test_main_reports_an_invalid_golden_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    monkeypatch.setattr(eval_retrieval.settings, "openai_api_key", "dummy")
    path = tmp_path / "retrieval.yaml"
    path.write_text("entries: []\n", encoding="utf-8")

    assert eval_retrieval.main(["--golden-set", str(path)]) == 1

    assert "Invalid golden set" in capsys.readouterr().err


def test_main_reports_a_database_error(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(eval_retrieval.settings, "openai_api_key", "dummy")

    @contextmanager
    def failing_session(_database_url: str) -> Iterator[object]:
        raise SQLAlchemyError("boom")
        yield object()  # pragma: no cover — keeps this a generator for contextmanager

    monkeypatch.setattr(eval_retrieval, "_open_session", failing_session)

    assert eval_retrieval.main([]) == 1

    assert "database query failed" in capsys.readouterr().err


def test_main_reports_an_embedding_error(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(eval_retrieval.settings, "openai_api_key", "dummy")

    @contextmanager
    def fake_session(_database_url: str) -> Iterator[object]:
        yield object()

    monkeypatch.setattr(eval_retrieval, "_open_session", fake_session)
    monkeypatch.setattr(eval_retrieval, "DocsRepository", lambda _session: object())

    def failing_sweep(_golden_set, _repository):
        raise OpenAIError("boom")

    monkeypatch.setattr(eval_retrieval, "run_sweep", failing_sweep)

    assert eval_retrieval.main([]) == 1

    assert "embedding call failed" in capsys.readouterr().err


def test_main_returns_zero_when_the_sweep_recommends_a_pair(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(eval_retrieval.settings, "openai_api_key", "dummy")

    @contextmanager
    def fake_session(_database_url: str) -> Iterator[object]:
        yield object()

    evaluation = _evaluate(
        [
            _result("positive", "a.md", ("a.md", 0, 0.2)),
            _result("negative", None, ("b.md", 0, 0.9)),
        ]
    )
    monkeypatch.setattr(eval_retrieval, "_open_session", fake_session)
    monkeypatch.setattr(eval_retrieval, "DocsRepository", lambda _session: object())
    monkeypatch.setattr(eval_retrieval, "run_sweep", lambda _golden_set, _repository: evaluation)

    assert eval_retrieval.main([]) == 0

    assert "MAX_COSINE_DISTANCE = 0.5500" in capsys.readouterr().out
