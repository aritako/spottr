"""Golden-set coverage over the coaching corpus.

Pure and offline: callers pass the corpus Document names and the golden entries' expected
Documents in, so this module never touches the filesystem, database, or network. The test tier
does the reading.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

MINIMUM_QUESTIONS_PER_DOCUMENT = 3


@dataclass(frozen=True)
class CoverageGap:
    """A corpus Document with too few golden questions pointing at it."""

    document: str
    questions: int

    @property
    def shortfall(self) -> int:
        """How many more golden questions the Document needs."""
        return MINIMUM_QUESTIONS_PER_DOCUMENT - self.questions


def find_coverage_gaps(
    document_names: Iterable[str],
    expected_documents: Iterable[str | None],
) -> tuple[CoverageGap, ...]:
    """Return every Document with fewer than the minimum positive golden questions.

    ``expected_documents`` holds each golden entry's expected corpus filename, or ``None`` for a
    Negative question; those are ignored. Gaps are ordered by Document name so the failure message
    is stable, and Documents with no questions at all are included.
    """
    counts = Counter(document for document in expected_documents if document is not None)
    return tuple(
        CoverageGap(document=name, questions=counts[name])
        for name in sorted(set(document_names))
        if counts[name] < MINIMUM_QUESTIONS_PER_DOCUMENT
    )


def format_coverage_gaps(gaps: Sequence[CoverageGap]) -> str:
    """A failure message that names each uncovered Document and its shortfall."""
    if not gaps:
        return "Every corpus Document has enough golden questions."

    lines = [f"{len(gaps)} corpus Document(s) have too few golden questions:"]
    lines.extend(
        f"  - {gap.document}: {gap.questions} of {MINIMUM_QUESTIONS_PER_DOCUMENT} "
        f"(short by {gap.shortfall})"
        for gap in gaps
    )
    return "\n".join(lines)
