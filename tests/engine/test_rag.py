import pytest

from app.engine.rag import chunk_text


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
