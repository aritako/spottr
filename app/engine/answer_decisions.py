"""The coach loop's judgement of a finished answer.

A finished answer is judged once, after the Responses API loop produces it. ``AnswerOutcome``
names the three possible fates — the answer is valid and ships, a fixable Violation earns one
retry, or the answer is replaced by an app-written Rejection — and ``AnswerDecision`` carries
whichever message that fate needs. The types live here as plain data so ``app/engine/coach.py``
stays focused on orchestration.
"""

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["AnswerDecision", "AnswerOutcome"]


class AnswerOutcome(StrEnum):
    """What the loop does with a finished answer."""

    VALID = "valid"
    RETRY = "retry"
    REJECTION = "rejection"


@dataclass(frozen=True)
class AnswerDecision:
    """The loop's single judgement of a finished answer.

    A valid answer carries no message; a retry carries the complaint to send the model; a
    Rejection carries the canned app-written text to ship in the answer's place.
    """

    outcome: AnswerOutcome
    complaint: str | None = None
    rejection: str | None = None
