from pathlib import Path

import pytest

from app.eval.golden_set import (
    DEFAULT_GOLDEN_SET_PATH,
    AgentQueriesError,
    GoldenEntry,
    GoldenSet,
    GoldenSetError,
    load_agent_queries,
    load_golden_set,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_golden_set_reads_positive_and_negative_entries(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        """
entries:
  - question: "When should I take a deload?"
    expected_document: "deloads.md"
  - question: "What was my squat e1RM last month?"
    no_match: true
    negative_kind: retrieval
""",
    )

    golden_set = load_golden_set(path)

    assert [entry.question for entry in golden_set.entries] == [
        "When should I take a deload?",
        "What was my squat e1RM last month?",
    ]
    assert golden_set.entries[0].expected_document == "deloads.md"
    assert golden_set.entries[0].no_match is False
    assert golden_set.entries[1].expected_document is None
    assert golden_set.entries[1].no_match is True


def test_load_golden_set_rejects_an_entry_with_no_expectation(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        """
entries:
  - question: "When should I take a deload?"
""",
    )

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    message = str(error.value)
    assert "entries.0" in message
    assert "expected_document" in message
    assert "no_match" in message


def test_load_golden_set_rejects_an_entry_with_two_expectations(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        """
entries:
  - question: "When should I take a deload?"
    expected_document: "deloads.md"
    no_match: true
""",
    )

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    message = str(error.value)
    assert "entries.0" in message
    assert "both" in message


def test_load_golden_set_rejects_a_blank_question(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        """
entries:
  - question: "   "
    expected_document: "deloads.md"
""",
    )

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "question" in str(error.value)


@pytest.mark.parametrize(
    "expected_document",
    ["docs/deloads.md", "../deloads.md", "/tmp/deloads.md"],
)
def test_load_golden_set_rejects_a_path_instead_of_a_source_filename(
    tmp_path: Path, expected_document: str
) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        f"""
entries:
  - question: "When should I take a deload?"
    expected_document: "{expected_document}"
""",
    )

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "source filename" in str(error.value)


def test_load_golden_set_rejects_an_unknown_field(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        """
entries:
  - question: "When should I take a deload?"
    expected_document: "deloads.md"
    expected_chunk: 2
""",
    )

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "expected_chunk" in str(error.value)


def test_load_golden_set_rejects_an_empty_set(tmp_path: Path) -> None:
    path = _write(tmp_path / "retrieval.yaml", "entries: []\n")

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "entries" in str(error.value)


def test_load_golden_set_rejects_invalid_yaml(tmp_path: Path) -> None:
    path = _write(tmp_path / "retrieval.yaml", "entries: [\n")

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "valid YAML" in str(error.value)


def test_load_golden_set_reports_a_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.yaml"

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "not found" in str(error.value)


def test_load_golden_set_rejects_a_non_mapping_root(tmp_path: Path) -> None:
    path = _write(tmp_path / "retrieval.yaml", "- question: orphan\n")

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "mapping" in str(error.value)


def test_load_golden_set_accepts_the_shipped_scaffold() -> None:
    golden_set = load_golden_set(DEFAULT_GOLDEN_SET_PATH)

    assert any(entry.no_match for entry in golden_set.entries)
    assert any(not entry.no_match for entry in golden_set.entries)


def test_load_golden_set_reads_both_negative_kinds(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        """
entries:
  - question: "When should I take a deload?"
    expected_document: "deloads.md"
  - question: "What was my squat e1RM last month?"
    no_match: true
    negative_kind: retrieval
  - question: "How much protein should I eat?"
    no_match: true
    negative_kind: routing
""",
    )

    golden_set = load_golden_set(path)

    assert [entry.negative_kind for entry in golden_set.entries] == [None, "retrieval", "routing"]


def test_load_golden_set_rejects_negative_kind_on_a_positive(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        """
entries:
  - question: "When should I take a deload?"
    expected_document: "deloads.md"
    negative_kind: retrieval
""",
    )

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "only valid on a Negative question" in str(error.value)


def test_load_golden_set_rejects_a_negative_without_a_kind(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "retrieval.yaml",
        """
entries:
  - question: "What was my squat e1RM last month?"
    no_match: true
""",
    )

    with pytest.raises(GoldenSetError) as error:
        load_golden_set(path)

    assert "negative_kind" in str(error.value)


def _golden_set_for(*questions: str) -> GoldenSet:
    return GoldenSet(
        entries=[
            GoldenEntry(question=question, expected_document="deloads.md") for question in questions
        ]
    )


def _agent_fixture(*questions: str, query: str = "deload timing") -> str:
    entries = "\n".join(
        f'  "{question}":\n    docs_calls:\n      - query: "{query}"\n        k: null'
        for question in questions
    )
    return (
        "query_model: gpt-test\n"
        'captured_at: "2026-11-14T10:00:00+00:00"\n'
        'instructions_sha: "0123456789abcdef0123456789abcdef01234567"\n'
        f"entries:\n{entries}\n"
    )


def test_load_agent_queries_reads_the_fixture_and_covers_the_golden_set(
    tmp_path: Path,
) -> None:
    question = "When should I take a deload?"
    path = _write(tmp_path / "agent_queries.yaml", _agent_fixture(question))

    agent_queries = load_agent_queries(path, _golden_set_for(question))

    assert agent_queries.query_model == "gpt-test"
    assert agent_queries.entries[question].docs_calls[0].query == "deload timing"
    assert agent_queries.entries[question].docs_calls[0].k is None


def test_load_agent_queries_rejects_a_missing_question(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "agent_queries.yaml",
        _agent_fixture("When should I take a deload?"),
    )

    with pytest.raises(AgentQueriesError) as error:
        load_agent_queries(
            path,
            _golden_set_for("When should I take a deload?", "How much volume?"),
        )

    assert "missing questions" in str(error.value)


def test_load_agent_queries_rejects_an_unknown_question(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "agent_queries.yaml",
        _agent_fixture("When should I take a deload?", "An unknown question?"),
    )

    with pytest.raises(AgentQueriesError) as error:
        load_agent_queries(path, _golden_set_for("When should I take a deload?"))

    assert "unknown questions" in str(error.value)


def test_load_agent_queries_rejects_a_blank_query(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "agent_queries.yaml",
        _agent_fixture("When should I take a deload?", query="   "),
    )

    with pytest.raises(AgentQueriesError) as error:
        load_agent_queries(path, _golden_set_for("When should I take a deload?"))

    assert "query" in str(error.value)
