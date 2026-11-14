from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

DEFAULT_GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden" / "retrieval.yaml"
DEFAULT_AGENT_QUERIES_PATH = Path(__file__).resolve().parent / "golden" / "agent_queries.yaml"


class GoldenSetError(ValueError):
    """A golden set could not be read or does not match the authored format."""


class AgentQueriesError(ValueError):
    """An agent-query fixture could not be read or does not match the authored format."""


class GoldenEntry(BaseModel):
    """One authored question and the retrieval outcome it expects.

    A positive entry names the corpus source filename that must be retrieved. A Negative
    question sets ``no_match`` instead, meaning retrieval must return no Passage at all. A
    Negative question is either a ``retrieval`` negative, which gates the relevance threshold,
    or a ``routing`` negative, which belongs to the data tools and is reported, not gated.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    question: str = Field(min_length=1)
    expected_document: str | None = Field(default=None, min_length=1)
    no_match: bool = False
    negative_kind: Literal["retrieval", "routing"] | None = None

    @model_validator(mode="after")
    def _validate_expectation(self) -> "GoldenEntry":
        has_document = self.expected_document is not None
        if has_document and self.no_match:
            raise ValueError("entry sets both expected_document and no_match; choose exactly one")
        if not has_document and not self.no_match:
            raise ValueError("entry needs expected_document or no_match: true")
        if self.no_match and self.negative_kind is None:
            raise ValueError("a Negative question needs negative_kind: retrieval or routing")
        if has_document and self.negative_kind is not None:
            raise ValueError("negative_kind is only valid on a Negative question")
        if has_document:
            document = self.expected_document or ""
            if document in {".", ".."} or "/" in document or "\\" in document:
                raise ValueError("expected_document must be a corpus source filename, not a path")
        return self


class GoldenSet(BaseModel):
    """The authored retrieval ground truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: list[GoldenEntry] = Field(min_length=1)


class AgentDocsCall(BaseModel):
    """One search_coaching_docs call the coach wrote for a golden question."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    query: str = Field(min_length=1)
    k: int | None = None


class AgentQueryEntry(BaseModel):
    """The docs calls the coach wrote for one golden question. Empty means no call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    docs_calls: tuple[AgentDocsCall, ...] = ()


class AgentQueries(BaseModel):
    """A frozen sample of the queries the coach actually sends to the docs tool."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_model: str = Field(min_length=1)
    captured_at: datetime
    instructions_sha: str = Field(min_length=7)
    entries: dict[str, AgentQueryEntry] = Field(min_length=1)


def load_golden_set(path: str | Path = DEFAULT_GOLDEN_SET_PATH) -> GoldenSet:
    """Load and validate a golden set from YAML.

    Raises:
        GoldenSetError: The file is missing, is not valid YAML, or contains an entry that does
            not match the format. The message names the file and the offending field.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise GoldenSetError(f"Golden set not found: {path}") from error

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise GoldenSetError(f"Golden set at {path} is not valid YAML: {error}") from error

    if not isinstance(raw, dict):
        raise GoldenSetError(
            f"Golden set at {path} must be a mapping with an 'entries' list, "
            f"not {type(raw).__name__}."
        )

    try:
        return GoldenSet.model_validate(raw)
    except ValidationError as error:
        raise GoldenSetError(_format_validation_error(path, error)) from error


def load_agent_queries(
    path: str | Path = DEFAULT_AGENT_QUERIES_PATH,
    golden_set: GoldenSet | None = None,
) -> AgentQueries:
    """Load and validate a captured agent-query fixture from YAML.

    When ``golden_set`` is supplied, every golden question must have exactly one record and
    the fixture may not contain records for unknown questions.

    Raises:
        AgentQueriesError: The file is missing, is not valid YAML, does not match the format,
            or does not cover the golden set exactly.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise AgentQueriesError(f"Agent-query fixture not found: {path}") from error

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise AgentQueriesError(
            f"Agent-query fixture at {path} is not valid YAML: {error}"
        ) from error

    if not isinstance(raw, dict):
        raise AgentQueriesError(
            f"Agent-query fixture at {path} must be a mapping with an 'entries' mapping, "
            f"not {type(raw).__name__}."
        )

    try:
        agent_queries = AgentQueries.model_validate(raw)
    except ValidationError as error:
        raise AgentQueriesError(
            _format_validation_error(path, error, label="agent-query fixture")
        ) from error

    if golden_set is not None:
        expected = {entry.question for entry in golden_set.entries}
        actual = set(agent_queries.entries)
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        if missing:
            raise AgentQueriesError(
                f"Agent-query fixture at {path} is missing questions: {', '.join(missing)}"
            )
        if unknown:
            raise AgentQueriesError(
                f"Agent-query fixture at {path} has unknown questions: {', '.join(unknown)}"
            )

    return agent_queries


def _format_validation_error(
    path: Path, error: ValidationError, *, label: str = "golden set"
) -> str:
    lines = [f"Invalid {label} at {path}:"]
    for detail in error.errors():
        location = ".".join(str(part) for part in detail["loc"]) or "root"
        lines.append(f"  - {location}: {detail['msg']}")
    return "\n".join(lines)
