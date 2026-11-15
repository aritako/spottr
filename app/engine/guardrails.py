"""Pure Guardrail checks for the coach's finished answer.

The Guardrails are the post-hoc checks defined by ADR 0005: an answer may ship only when
deterministic code, not a prompt, says it is backed. This module consumes plain values scraped
from tool results — never ORM objects — so unit tests and the offline evaluation tier can import
it without a database, network, or fixtures. ``app/engine/coach.py`` owns what to do with each
verdict.

The Scope rule reads the loop's tool-usage signature and separates three outcomes:

- ``SUPPORTED``: at least one tool returned substantive output (data rows, an exercise list, or
  retrieved Passages), so the answer may ship with its Citations.
- ``ALL_EMPTY``: tools ran and every substantive result was legitimately empty — retrieval
  ``no_match`` or ``empty_corpus``, the no-matching-workout-data result, or an empty exercise
  list. The model cannot fix reality, so this normalizes immediately without a retry.
- ``NO_SUBSTANTIVE_CALL``: no substantive call was made at all — no tool calls, or only failed
  calls (an unknown tool or unreadable arguments). A failed call is never an empty result: it is
  a mistake the model can still fix.

The Grounding rule reads the numerals in the answer text. A numeral ships only when its value
appears literally in tool output — a Receipt — after format normalization: thousands separators
are stripped, a trailing decimal or zero does not change the value, and an adjacent unit suffix
or percent sign is not part of the value, so ``12,400``, ``12400.0`` and ``12400`` are one
Receipt. Matching is exact: there is no tolerance band, and no derivation recipe exists yet, so a
computed statistic — a difference, percentage, sum, or average — is unbacked until #37 adds one.

Every numeral-looking token is checked independently. A range needs Receipts for both ends; a
fraction is its two numerals rather than an evaluated quotient; a leading sign is part of the
value when it is orthographically attached, while a hyphen between digits separates a range;
date-like numerals are checked component by component. Digits embedded in a word are still
numerals, so ``e1RM`` carries a ``1`` and ``5x5`` carries two ``5``s. Letters after a numeral are
ignored as a unit suffix, never as a multiplier, so ``10k`` is ``10``; an explicit scientific
exponent is part of the numeral itself, so ``1e5`` is ``100000``. Spelled-out and Roman numerals
are not numerals and never violate.
"""

import json
import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from decimal import Decimal
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


# A numeral is ASCII digits with optional thousands separators, an optional decimal fraction, and
# an optional scientific exponent. A leading sign is captured so it can be attached to the value
# only when it is not a range separator; a leading dot is accepted in ``.5``. Letters are never
# part of the token, so an adjacent unit suffix does not change the value.
_NUMERAL_PATTERN = re.compile(
    r"(?P<sign>[+\-\u2212])?"
    r"(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
    r"(?:[eE][+-]?\d+)?"
)


@dataclass(frozen=True)
class Numeral:
    """One numeral as written in text, with its normalized numeric value."""

    text: str
    value: Decimal


@dataclass(frozen=True)
class GroundingViolation:
    """A numeral in the answer with no Receipt in the tool output."""

    numeral: str
    value: Decimal


def extract_numerals(text: str) -> tuple[Numeral, ...]:
    """Extract every numeral-looking token in text, in the order it appears.

    Each token is independent: a range contributes both ends, a fraction contributes both of its
    numerals, and an ISO date contributes its year, month, and day. A hyphen directly after a
    digit is a range separator rather than a sign. The raw text is kept so a correction turn can
    name the numeral exactly as the answer wrote it.
    """
    numerals: list[Numeral] = []
    for match in _NUMERAL_PATTERN.finditer(text):
        token = match.group(0)
        if match.group("sign") and _follows_digit(text, match.start()):
            # "4-6" is a range, not 4 and negative 6.
            token = token[1:]
        numerals.append(Numeral(text=token, value=_numeral_value(token)))
    return tuple(numerals)


def _follows_digit(text: str, start: int) -> bool:
    """Whether a token starts right after a digit, making its leading sign a range separator."""
    return start > 0 and text[start - 1].isdigit()


def _numeral_value(token: str) -> Decimal:
    """Normalize one numeral token: sign, separators, and a leading decimal point."""
    signed = token.replace("\u2212", "-")
    sign, unsigned = (signed[0], signed[1:]) if signed[:1] in "+-" else ("", signed)
    unsigned = unsigned.replace(",", "")
    if unsigned.startswith("."):
        unsigned = "0" + unsigned
    return Decimal(sign + unsigned)


def scrape_receipts(result: object) -> frozenset[Decimal]:
    """Scrape every Receipt numeral from one successful tool result.

    The scrape reads the same text the model read: a string result as-is, any other result through
    the JSON serialization the loop sends in the function call output. Numbers in data rows,
    bucket labels ("Week of Jun 15, 2026"), exercise ids and names, Passage metadata, and Passage
    text all count as Receipts, because quoting any of them is legitimate.
    """
    text = result if isinstance(result, str) else json.dumps(result)
    return frozenset(numeral.value for numeral in extract_numerals(text))


def grounding_violation(
    output_text: str, receipts: Collection[Decimal]
) -> GroundingViolation | None:
    """Return the first numeral in the answer that has no Receipt, if any.

    Every numeral is checked independently, so one backed numeral never licenses another: a range
    needs Receipts for both ends, and one unsupported numeral among supported ones is a Violation.
    Matching is exact after format normalization; a numeral close to a tool value is unbacked.
    """
    for numeral in extract_numerals(output_text):
        if numeral.value not in receipts:
            return GroundingViolation(numeral=numeral.text, value=numeral.value)
    return None
