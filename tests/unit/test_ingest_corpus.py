import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ingest_corpus.py"

spec = importlib.util.spec_from_file_location("ingest_corpus", SCRIPT)
assert spec is not None and spec.loader is not None
ingest_corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest_corpus)


def test_read_title_returns_the_h1() -> None:
    text = "## Ignored heading\n\n# Deloads\n\nBody text."
    assert ingest_corpus.read_title(text, Path("deloads.md")) == "Deloads"


def test_read_title_trims_whitespace_after_the_marker() -> None:
    text = "#   Volume Landmarks  \n"
    assert ingest_corpus.read_title(text, Path("volume-landmarks.md")) == "Volume Landmarks"


def test_read_title_rejects_a_document_without_an_h1() -> None:
    with pytest.raises(SystemExit, match="no H1 title"):
        ingest_corpus.read_title("## Only an h2\n", Path("broken.md"))


def test_corpus_paths_skips_the_readme_and_non_markdown_files(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("# B\n")
    (tmp_path / "README.md").write_text("# Corpus contract\n")
    (tmp_path / "a.md").write_text("# A\n")
    (tmp_path / "notes.txt").write_text("ignored\n")

    names = [path.name for path in ingest_corpus.corpus_paths(tmp_path)]

    assert names == ["a.md", "b.md"]
