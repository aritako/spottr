"""Model-facing correction turns.

A correction turn is the coach's one silent retry, sent when a Guardrail finds a fixable
Violation. Its input is plain app-written copy — never the lifter's question — that names the
complaint and points back at the tools, so the model can correct the slip without the lifter
seeing the exchange. The loop chains it from the previous response with the same instructions and
tool menu, matching how the first turn sends the question.
"""

__all__ = ["SCOPE_RETRY", "grounding_retry"]

SCOPE_RETRY = (
    "You answered without calling any tool, so no tool output backs that answer. Answer the "
    "lifter's question again, and consult your tools first: query_workouts or query_exercises "
    "for their logged workouts, and search_coaching_docs for training principles. Do not answer "
    "from your own knowledge."
)

GROUNDING_RETRY = (
    'Your answer states the number "{numeral}", which is neither present in nor derivable from '
    "the tool results. Answer the lifter's question again, using only numbers that appear in the "
    "tool output, or call a tool to retrieve the number you need."
)


def grounding_retry(numeral: str) -> str:
    """Build the correction turn for one numeral that no tool output backs."""
    return GROUNDING_RETRY.format(numeral=numeral)
