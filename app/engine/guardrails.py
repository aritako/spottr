"""Pure Scope Guardrail for the coach's finished answer.

An answer may ship only when substantive tool output backs it. This module consumes plain values
scraped from tool results — never ORM objects — so unit tests and the offline evaluation tier can
import it without a database, network, or fixtures. ``app/engine/coach.py`` owns what to do with
each verdict.

The rule separates three outcomes:

- ``SUPPORTED``: at least one tool returned substantive output (data rows, an exercise list, or
  retrieved Passages), so the answer may ship with its Citations.
- ``ALL_EMPTY``: tools ran and every substantive result was legitimately empty — retrieval
  ``no_match`` or ``empty_corpus``, the no-matching-workout-data result, or an empty exercise
  list. The model cannot fix reality, so this normalizes immediately without a retry.
- ``NO_SUBSTANTIVE_CALL``: no substantive call was made at all — no tool calls, or only failed
  calls (an unknown tool or unreadable arguments). A failed call is never an empty result: it is
  a mistake the model can still fix.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.shared.enums.docs import RetrievalStatus


class ToolOutcome(StrEnum):
    """What one tool call contributed to the answer's evidence."""

    SUBSTANTIVE = "substantive"
    EMPTY = "empty"
    ERROR = "error"


class ScopeVerdict(StrEnum):
    """The Scope rule's judgment of the whole loop's tool evidence."""

    SUPPORTED = "supported"
    ALL_EMPTY = "all_empty"
    NO_SUBSTANTIVE_CALL = "no_substantive_call"


@dataclass(frozen=True)
class ToolEvidence:
    """One tool call's contribution, in plain values the Scope rule can judge."""

    tool: str
    outcome: ToolOutcome


def error_evidence(tool: str) -> ToolEvidence:
    """Evidence for a call that produced an error result instead of tool output."""
    return ToolEvidence(tool=tool, outcome=ToolOutcome.ERROR)


def tool_evidence(tool: str, result: object) -> ToolEvidence:
    """Scrape one successful tool result into Scope evidence.

    Emptiness is a property of each tool's real result shape, so the scraper reads the shapes the
    tools in ``app/engine/tools.py`` actually return rather than assuming one common envelope.
    A result the scraper cannot read contributes no evidence, never a false positive.
    """
    match tool:
        case "search_coaching_docs":
            outcome = _retrieval_outcome(result)
        case "query_workouts":
            outcome = _workout_outcome(result)
        case "query_exercises":
            outcome = _exercise_outcome(result)
        case _:
            outcome = ToolOutcome.ERROR
    return ToolEvidence(tool=tool, outcome=outcome)


def scope_verdict(evidence: Sequence[ToolEvidence]) -> ScopeVerdict:
    """Judge whether substantive tool output backs the finished answer."""
    outcomes = {item.outcome for item in evidence}
    if ToolOutcome.SUBSTANTIVE in outcomes:
        return ScopeVerdict.SUPPORTED
    if ToolOutcome.EMPTY in outcomes:
        return ScopeVerdict.ALL_EMPTY
    return ScopeVerdict.NO_SUBSTANTIVE_CALL


def _retrieval_outcome(result: object) -> ToolOutcome:
    """Retrieval reports emptiness with ``status``; Passages are the evidence."""
    if not isinstance(result, dict):
        return ToolOutcome.ERROR
    status = result.get("status")
    passages = result.get("passages")
    if status == RetrievalStatus.OK and isinstance(passages, (list, tuple)) and passages:
        return ToolOutcome.SUBSTANTIVE
    if status in (RetrievalStatus.NO_MATCH, RetrievalStatus.EMPTY_CORPUS):
        return ToolOutcome.EMPTY
    return ToolOutcome.ERROR


def _workout_outcome(result: object) -> ToolOutcome:
    """Workout data arrives as ``{"result": rows}``; no data arrives as a status string."""
    if not isinstance(result, dict) or "result" not in result:
        return ToolOutcome.ERROR
    rows = result["result"]
    if isinstance(rows, str):
        # "No matching workout data found." and other no-data statuses are strings, not rows.
        return ToolOutcome.EMPTY
    if isinstance(rows, (list, tuple, dict)):
        return ToolOutcome.SUBSTANTIVE if rows else ToolOutcome.EMPTY
    return ToolOutcome.ERROR


def _exercise_outcome(result: object) -> ToolOutcome:
    """The exercise tool returns a list of ``(id, name)`` pairs."""
    if isinstance(result, (list, tuple)):
        return ToolOutcome.SUBSTANTIVE if result else ToolOutcome.EMPTY
    return ToolOutcome.ERROR
