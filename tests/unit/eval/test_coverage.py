from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

from app.eval.coverage import find_coverage_gaps, format_coverage_gaps
from app.eval.golden_set import DEFAULT_GOLDEN_SET_PATH, GoldenEntry, load_golden_set
from scripts.ingest_corpus import corpus_paths

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_DIR = REPO_ROOT / "docs" / "corpus"
CORPUS_README = "README.md"


def _entry(document: str) -> GoldenEntry:
    return GoldenEntry(question=f"Question about {document}?", expected_document=document)


def _expected_documents(entries: Sequence[GoldenEntry]) -> list[str | None]:
    """The Document each golden entry expects, or None for a Negative question."""
    return [entry.expected_document for entry in entries]


def _corpus_documents() -> list[str]:
    """The coaching corpus Documents, excluding the contract README."""
    return [path.name for path in corpus_paths(CORPUS_DIR)]


def _assert_coverage(document_names: Iterable[str], entries: Sequence[GoldenEntry]) -> None:
    """Fail with a named shortfall when a Document has too few golden questions."""
    gaps = find_coverage_gaps(document_names, _expected_documents(entries))
    assert not gaps, format_coverage_gaps(gaps)


def test_every_corpus_document_has_at_least_three_golden_questions() -> None:
    golden_set = load_golden_set(DEFAULT_GOLDEN_SET_PATH)

    _assert_coverage(_corpus_documents(), golden_set.entries)


def test_the_check_requires_three_questions_by_default() -> None:
    two = [_entry("thin.md"), _entry("thin.md")]
    three = [*two, _entry("thin.md")]

    with pytest.raises(AssertionError):
        _assert_coverage(["thin.md"], two)

    _assert_coverage(["thin.md"], three)


def test_a_document_with_too_few_questions_fails_and_names_its_shortfall() -> None:
    entries = [_entry("covered.md"), _entry("covered.md"), _entry("covered.md"), _entry("thin.md")]

    with pytest.raises(AssertionError) as error:
        _assert_coverage(["covered.md", "thin.md"], entries)

    message = str(error.value)
    assert "thin.md" in message
    assert "1 of 3" in message
    assert "short by 2" in message
    assert "covered.md" not in message


def test_a_document_with_no_questions_is_reported() -> None:
    gaps = find_coverage_gaps(["unwritten.md"], [])

    assert [(gap.document, gap.questions, gap.shortfall) for gap in gaps] == [
        ("unwritten.md", 0, 3)
    ]


def test_negative_questions_do_not_count_toward_document_coverage() -> None:
    entries = [
        GoldenEntry(
            question="What was my squat e1RM last month?",
            no_match=True,
            negative_kind="retrieval",
        ),
        _entry("deloads.md"),
        _entry("deloads.md"),
        _entry("deloads.md"),
    ]

    assert find_coverage_gaps(["deloads.md"], _expected_documents(entries)) == ()


def test_gaps_are_ordered_by_document_name() -> None:
    gaps = find_coverage_gaps(["zebra.md", "alpha.md"], [])

    assert [gap.document for gap in gaps] == ["alpha.md", "zebra.md"]


def test_the_contract_readme_is_not_a_corpus_document() -> None:
    documents = _corpus_documents()

    assert documents
    assert CORPUS_README not in documents


def test_format_coverage_gaps_says_so_when_nothing_is_missing() -> None:
    assert format_coverage_gaps(()) == "Every corpus Document has enough golden questions."
