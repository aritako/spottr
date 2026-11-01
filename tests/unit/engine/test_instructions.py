from datetime import date

from app.engine.prompts import build_instructions

TODAY = date(2026, 1, 2)


def test_instructions_carry_the_given_date() -> None:
    text = build_instructions(TODAY)

    assert "2026-01-02" in text
    assert "Today's date is 2026-01-02" in text


def test_instructions_explain_every_retrieval_status() -> None:
    text = build_instructions(TODAY)

    for status in ("ok", "no_match", "empty_corpus"):
        assert f'"{status}"' in text


def test_instructions_allow_refusing_irrelevant_passages() -> None:
    text = build_instructions(TODAY)

    assert "Check they actually answer the question" in text
    assert "do not substitute general knowledge" in text


def test_instructions_forbid_inline_citation_numbers() -> None:
    text = build_instructions(TODAY)

    assert "bracketed citation numbers" in text
    assert "Never invent a document title" in text
