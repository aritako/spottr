from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedPassage:
    """A Passage returned by retrieval, with the distance used to rank it."""

    document_source: str
    chunk_index: int
    distance: float


@dataclass(frozen=True)
class QuestionResult:
    """The candidates retrieval produced for one golden-set question.

    ``expected_document`` is the corpus source filename that must be retrieved, or ``None`` for
    a Negative question.
    """

    question: str
    expected_document: str | None
    passages: tuple[RetrievedPassage, ...]

    @property
    def is_negative(self) -> bool:
        """Whether this is a Negative question."""
        return self.expected_document is None


@dataclass(frozen=True)
class EntryMargin:
    """How cleanly one question separates its expected Document from other Passages.

    ``margin`` is positive when every selected Passage from the expected Document is closer
    than every selected Passage from another Document. It is ``None`` when one side of the
    comparison is absent from the selected window.
    """

    question: str
    worst_positive_distance: float | None
    best_negative_distance: float | None
    margin: float | None


@dataclass(frozen=True)
class ScoringReport:
    """Retrieval quality for one ``(k, cutoff)`` pair."""

    k: int
    cutoff: float
    recall: float
    no_match_rate: float
    precision: float
    margins: tuple[EntryMargin, ...]
    positives: int
    negatives: int
    retrieved: int


def score(results: Sequence[QuestionResult], k: int, cutoff: float) -> ScoringReport:
    """Score retrieval results at a top-k and relevance cutoff.

    Only Passages with ``distance < cutoff`` are considered, matching the repository's strict
    cutoff. Candidates are ordered by ascending distance before the top-k is taken.

    - recall@k: the fraction of positive questions whose expected Document is in the top k.
    - no_match rate: the fraction of Negative questions with no Passage selected.
    - precision: the fraction of selected Passages that belong to the question's expected
      Document. Negative questions expect no Document, so every Passage selected for one
      counts against precision.
    """
    if k < 1:
        raise ValueError("k must be at least 1")

    positives = 0
    negatives = 0
    recalled = 0
    no_matches = 0
    retrieved = 0
    expected_retrieved = 0
    margins: list[EntryMargin] = []

    for result in results:
        selected = select_passages(result.passages, k=k, cutoff=cutoff)
        retrieved += len(selected)

        expected = result.expected_document
        relevant = relevant_passages(selected, expected)
        expected_retrieved += len(relevant)
        margins.append(_margin(result.question, expected, selected))

        if result.is_negative:
            negatives += 1
            if not selected:
                no_matches += 1
        else:
            positives += 1
            if relevant:
                recalled += 1

    return ScoringReport(
        k=k,
        cutoff=cutoff,
        recall=recalled / positives if positives else 0.0,
        no_match_rate=no_matches / negatives if negatives else 0.0,
        precision=expected_retrieved / retrieved if retrieved else 0.0,
        margins=tuple(margins),
        positives=positives,
        negatives=negatives,
        retrieved=retrieved,
    )


def select_passages(
    passages: Sequence[RetrievedPassage], *, k: int, cutoff: float
) -> tuple[RetrievedPassage, ...]:
    """Apply the strict relevance cutoff, order by distance, and keep the top k."""
    ordered = sorted(
        (passage for passage in passages if passage.distance < cutoff),
        key=lambda passage: passage.distance,
    )
    return tuple(ordered[:k])


def relevant_passages(
    passages: Sequence[RetrievedPassage], expected_document: str | None
) -> tuple[RetrievedPassage, ...]:
    """The Passages that belong to the question's expected Document."""
    return tuple(passage for passage in passages if passage.document_source == expected_document)


def _margin(
    question: str,
    expected_document: str | None,
    selected: Sequence[RetrievedPassage],
) -> EntryMargin:
    relevant = relevant_passages(selected, expected_document)
    irrelevant = tuple(
        passage for passage in selected if passage.document_source != expected_document
    )

    worst_positive = max((passage.distance for passage in relevant), default=None)
    best_negative = min((passage.distance for passage in irrelevant), default=None)
    margin = (
        best_negative - worst_positive
        if worst_positive is not None and best_negative is not None
        else None
    )
    return EntryMargin(
        question=question,
        worst_positive_distance=worst_positive,
        best_negative_distance=best_negative,
        margin=margin,
    )
