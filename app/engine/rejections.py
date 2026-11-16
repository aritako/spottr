"""App-written Rejection copy.

A Rejection is the canned response that replaces an answer no Guardrail passed, an answer no
substantive tool output backed, or a loop that could not finish. It is static, app-owned text, so
the coach cannot talk its way around the boundary in its own words. Every Rejection names what the
coach can answer — questions about the lifter's logged workouts, and training principles from the
coaching corpus — so a refusal teaches the boundary rather than merely declining. A Rejection
never carries Citations.
"""

from collections.abc import Sequence
from typing import Any

__all__ = ["COULD_NOT_COMPLETE", "NOTHING_FOUND", "OUT_OF_SCOPE", "build_rejection"]

_CAPABILITIES = (
    "I can answer questions about your logged workouts — the sets you have recorded, your volume, "
    "and your strength trends — and training principles from the coaching material in my library, "
    "such as programming, deloads, technique, and recovery."
)

OUT_OF_SCOPE = f"{_CAPABILITIES} That question is outside those areas, so I can't answer it."

NOTHING_FOUND = (
    f"{_CAPABILITIES} I couldn't find anything in your logged workouts or in my coaching material "
    "that answers that. Try logging the workout, or ask about something you have already recorded."
)

COULD_NOT_COMPLETE = (
    f"{_CAPABILITIES} I couldn't finish working that answer out, so I won't guess. Please ask "
    "again, perhaps with a narrower question."
)


def build_rejection(rejection: str, used_tools: Sequence[str]) -> dict[str, Any]:
    """Swap a canned Rejection in for an answer the Guardrails blocked.

    This is the one substitution every Rejection goes through. The model's text and every Citation
    collected during the loop are discarded — a Citation records a Passage consulted for an
    answer, and a Rejection has no answer — while the tools that actually ran are preserved so a
    Rejection stays diagnosable.
    """
    return {
        "answer": rejection,
        "used_tools": list(used_tools),
        "citations": [],
    }
