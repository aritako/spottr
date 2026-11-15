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

The Grounding rule reads the numerals in the answer text. A numeral ships only when it has a
Receipt. A Receipt is either the value appearing literally in tool output after format
normalization — thousands separators stripped, a trailing decimal or zero ignored, an adjacent
unit suffix or percent sign not part of the value, so ``12,400``, ``12400.0`` and ``12400`` are
one Receipt — or a value the app re-derives itself from Receipt values. The derivation whitelist
is closed and small:

- difference: one Receipt minus another, in either direction;
- percentage change: the signed change from one Receipt to another, in either direction, so a
  decrease is a negative percentage;
- sum: the exact total of a set of Receipts;
- average: the exact mean of a set of Receipts.

Every recipe computes in exact decimal arithmetic: the values are scaled to integers, so a
floating-point artefact can never manufacture a Receipt. Difference, sum, and average must match
exactly. A derived percentage must match the recomputation exactly when stated at any fractional
precision; a percentage stated as a whole percent is also accepted when it equals the exact
recomputation rounded half-up to a whole percent. That whole-percent rounding is the only
relaxation. A recipe needs a source pair or set among the Receipts; with too few source numbers
it produces nothing, and the numeral stays a Violation. Sums and averages search subsets of at
least two Receipts under a fixed work budget: anything the search finds is exact, and when the
budget is exhausted it claims nothing, so it can never invent a Receipt.

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
from itertools import combinations

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


class Derivation(StrEnum):
    """The closed whitelist of statistics the Grounding rule may re-derive.

    Adding a recipe is a deliberate decision, not an implementation detail: the whitelist stays
    closed until real dogfooding traffic on the build ticket shows a legitimate answer was
    blocked.
    """

    DIFFERENCE = "difference"
    PERCENTAGE_CHANGE = "percentage_change"
    SUM = "sum"
    AVERAGE = "average"


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


# A sum or average search may visit this many candidate subsets. The budget is a ceiling on work,
# never a tolerance: a derivation found inside it is exact, and one not found is not claimed. The
# cap keeps a pathological Receipt pile from turning a near-miss into an unbounded search.
_MAX_DERIVATION_STEPS = 20_000


def grounding_violation(
    output_text: str, receipts: Collection[Decimal]
) -> GroundingViolation | None:
    """Return the first numeral in the answer that has no Receipt, if any.

    Every numeral is checked independently, so one backed numeral never licenses another: a range
    needs Receipts for both ends, and one unsupported numeral among supported ones is a Violation.
    Matching is exact after format normalization; a numeral close to a tool value is unbacked. A
    numeral that is not literal may still be backed by one of the four derivation recipes.
    """
    values = tuple(dict.fromkeys(receipts))
    literals = frozenset(values)
    for numeral in extract_numerals(output_text):
        if numeral.value in literals:
            continue
        if _is_derived(numeral.value, values):
            continue
        return GroundingViolation(numeral=numeral.text, value=numeral.value)
    return None


def _is_derived(value: Decimal, receipts: tuple[Decimal, ...]) -> bool:
    """Whether one of the four recipes re-derives this value from the Receipts."""
    if len(receipts) < 2:
        # No recipe has a source pair or set to work from.
        return False
    scaled, target = _scaled_receipts(receipts, value)
    return (
        _is_difference(target, scaled)
        or _is_sum(target, scaled)
        or _is_average(target, scaled)
        or _is_percentage_change(value, scaled)
    )


def _scaled_receipts(receipts: tuple[Decimal, ...], target: Decimal) -> tuple[tuple[int, ...], int]:
    """Represent every value as an integer at one shared decimal scale.

    Decimal values are finite, so scaling by the largest fractional exponent turns every value
    into an exact integer. The recipes then use integer arithmetic only: no binary float and no
    division rounding can turn representation noise into a Receipt.
    """
    scale = 0
    for value in (*receipts, target):
        scale = max(scale, -value.as_tuple().exponent)
    return tuple(_scaled_int(value, scale) for value in receipts), _scaled_int(target, scale)


def _scaled_int(value: Decimal, scale: int) -> int:
    """Express one finite Decimal as an integer at the given decimal scale."""
    sign, digits, exponent = value.as_tuple()
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    if sign:
        coefficient = -coefficient
    return coefficient * 10 ** (exponent + scale)


def _is_difference(target: int, values: tuple[int, ...]) -> bool:
    """Whether two distinct Receipts subtract to the target, in either direction."""
    available = frozenset(values)
    for value in values:
        other = value - target
        if other != value and other in available:
            return True
    return False


def _is_sum(target: int, values: tuple[int, ...]) -> bool:
    """Whether a set of at least two Receipts totals the target exactly."""
    return _is_subset_total(target, values, average=False)


def _is_average(target: int, values: tuple[int, ...]) -> bool:
    """Whether a set of at least two Receipts has the target mean exactly."""
    return _is_subset_total(target, values, average=True)


def _is_subset_total(target: int, values: tuple[int, ...], *, average: bool) -> bool:
    """Search Receipt subsets for an exact total or exact mean.

    The whole set and every pair are checked directly before the bounded search, which covers the
    common "sum the rows" and "average the rows" cases without walking subsets. The bounded search
    then tries increasing subset sizes; if its budget runs out it returns False rather than
    guessing, so a large pile can delay a claim but never manufacture one.
    """
    if len(values) < 2:
        return False
    total = sum(values)
    if average:
        if total == target * len(values):
            return True
    elif total == target:
        return True
    if _has_pair_total(target, values, average=average):
        return True

    ordered = tuple(sorted(values, reverse=True))
    steps = 0
    for size in range(3, len(ordered) + 1):
        wanted = target * size if average else target
        for subset in combinations(ordered, size):
            steps += 1
            if steps > _MAX_DERIVATION_STEPS:
                return False
            if sum(subset) == wanted:
                return True
    return False


def _has_pair_total(target: int, values: tuple[int, ...], *, average: bool) -> bool:
    """Whether two distinct Receipts total the target, or average to it."""
    wanted = target * 2 if average else target
    available = frozenset(values)
    for value in values:
        other = wanted - value
        if other != value and other in available:
            return True
    return False


def _is_percentage_change(value: Decimal, values: tuple[int, ...]) -> bool:
    """Whether an ordered pair of Receipts yields this signed percentage change.

    The recomputation is ``100 * (end - start) / start``, so an increase is positive and a
    decrease is negative; both directions are derived. Whole-percent rounding is the only
    relaxation: any fractional statement must match the exact recomputation.
    """
    numerator, denominator = value.as_integer_ratio()
    available = frozenset(values)

    # Exact percentages are solved directly for the end value, so the common integer case is
    # linear in the number of Receipts rather than a pair scan.
    for start in values:
        if start == 0:
            continue
        scaled_end = start * (100 * denominator + numerator)
        scaled_denominator = 100 * denominator
        if scaled_end % scaled_denominator:
            continue
        end = scaled_end // scaled_denominator
        if end != start and end in available:
            return True

    if not _is_whole(value):
        return False

    # Whole-percent statements are checked against the exact recomputation rounded half-up.
    whole = int(value)
    for end in values:
        for start in values:
            if end == start or start == 0:
                continue
            if _round_half_up_ratio(100 * (end - start), start) == whole:
                return True
    return False


def _is_whole(value: Decimal) -> bool:
    """Whether a Decimal is a whole number, regardless of its written trailing zeros."""
    return value == value.to_integral_value()


def _round_half_up_ratio(numerator: int, denominator: int) -> int:
    """Round an exact rational to the nearest integer, with halves away from zero."""
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    if remainder * 2 >= denominator:
        quotient += 1
    return sign * quotient
