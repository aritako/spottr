from pathlib import Path

import pytest

from app.engine.rag import chunk_document, chunk_text


def _words(prefix: str, count: int) -> list[str]:
    return [f"{prefix}{index}" for index in range(count)]


def test_chunk_text_empty_returns_empty_list() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_chunk_text_short_text_is_single_chunk() -> None:
    assert chunk_text("one two three", chunk_size=10, overlap=2) == ["one two three"]


def test_chunk_text_splits_with_overlap() -> None:
    text = " ".join(f"w{i}" for i in range(10))
    chunks = chunk_text(text, chunk_size=4, overlap=2)
    assert chunks[0] == "w0 w1 w2 w3"
    assert chunks[1] == "w2 w3 w4 w5"
    assert chunks[-1].endswith("w9")


def test_chunk_text_rejects_overlap_too_large() -> None:
    with pytest.raises(ValueError):
        chunk_text("a b c", chunk_size=2, overlap=2)


def test_chunk_document_empty_returns_empty_list() -> None:
    assert chunk_document("") == []
    assert chunk_document("   \n  ") == []


def test_chunk_document_drops_the_sources_section() -> None:
    text = f"# Title\n\n{' '.join(_words('w', 45))}\n\n## Sources\n\n- doi.org/10.1234/example\n"

    chunks = chunk_document(text)

    assert len(chunks) == 1
    assert "Sources" not in chunks[0]
    assert "doi.org" not in chunks[0]


def test_chunk_document_drops_the_h1_and_attaches_a_heading_only_block() -> None:
    text = "# Title\n\n## Section\n\n" + " ".join(_words("w", 45))

    chunks = chunk_document(text)

    assert len(chunks) == 1
    assert chunks[0].startswith("## Section\n")
    assert not chunks[0].startswith("# Title")


def test_chunk_document_drops_a_trailing_heading_only_block() -> None:
    text = "# Title\n\n" + " ".join(_words("w", 45)) + "\n\n## Appendix\n"

    chunks = chunk_document(text)

    assert len(chunks) == 1
    assert "Appendix" not in chunks[0]


def test_chunk_document_merges_a_short_paragraph_forward() -> None:
    short = " ".join(_words("s", 20))
    long = " ".join(_words("l", 40))

    chunks = chunk_document(f"{short}\n\n{long}\n")

    assert len(chunks) == 1
    assert len(chunks[0].split()) == 60
    assert chunks[0].startswith(short)


def test_chunk_document_merges_a_short_final_paragraph_backward() -> None:
    long = " ".join(_words("l", 45))
    short = " ".join(_words("s", 20))

    chunks = chunk_document(f"{long}\n\n{short}\n")

    assert len(chunks) == 1
    assert len(chunks[0].split()) == 65
    assert chunks[0].endswith(short)


def test_chunk_document_keeps_a_short_document_as_one_chunk() -> None:
    assert chunk_document("one two three four") == ["one two three four"]


def test_chunk_document_splits_a_long_paragraph_with_overlap() -> None:
    text = " ".join(_words("w", 650))

    chunks = chunk_document(text)

    assert [len(chunk.split()) for chunk in chunks] == [300, 300, 110]
    assert chunks[1].split()[:3] == ["w270", "w271", "w272"]  # 30-word overlap
    assert chunks[1].split()[-1] == "w569"
    assert chunks[2].split()[0] == "w540"


def test_chunk_document_rejoins_a_short_tail_onto_the_previous_piece() -> None:
    text = " ".join(_words("w", 305))

    chunks = chunk_document(text)

    assert len(chunks) == 1
    assert len(chunks[0].split()) == 305
    assert chunks[0].split()[0] == "w0"
    assert chunks[0].split()[-1] == "w304"


def test_chunk_document_splits_the_real_corpus_into_paragraph_chunks() -> None:
    corpus = Path(__file__).resolve().parents[3] / "docs" / "corpus"
    documents = sorted(path for path in corpus.glob("*.md") if path.name != "README.md")
    chunks = [
        chunk
        for document in documents
        for chunk in chunk_document(document.read_text(encoding="utf-8"))
    ]
    word_counts = [len(chunk.split()) for chunk in chunks]

    assert len(chunks) == 96, f"expected 96 chunks, got {len(chunks)}"
    assert min(word_counts) >= 40, f"shortest chunk has {min(word_counts)} words"
    assert max(word_counts) <= 300, f"longest chunk has {max(word_counts)} words"
    assert all("doi.org" not in chunk and "## Sources" not in chunk for chunk in chunks), (
        "a chunk contains the Sources bibliography"
    )
