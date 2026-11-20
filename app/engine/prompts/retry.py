"""Model-facing correction turns.

A correction turn is the coach's one silent retry, sent when a Guardrail finds a fixable
Violation. Its input is plain app-written copy — never the lifter's question — that names the
complaint and points back at the tools, so the model can correct the slip without the lifter
seeing the exchange. The loop chains it from the previous response with the same instructions and
tool menu, matching how the first turn sends the question.
"""

__all__ = ["SCOPE_RETRY", "grounding_retry"]

SCOPE_RETRY = (
    "No tool output backs that answer. Answer the lifter's question again, and consult your "
    "tools first: query_workouts or query_exercises for their logged workouts, and "
    "search_coaching_docs for training principles. Do not answer from your own knowledge."
)

_GROUNDING_RETRY_TEMPLATE = (
    'Your answer states the number "{numeral}" in "{context}", which is neither present in nor '
    "derivable from the tool results. Rewrite your answer now, using only numbers that appear in "
    "the tool output you already have; reword or drop the phrase around the number if it is not "
    "a statistic. Only call a tool if the number you need is genuinely missing from the results "
    "you already have."
)


def grounding_retry(numeral: str, context: str) -> str:
    """Build the correction turn for one numeral that no tool output backs."""
    return _GROUNDING_RETRY_TEMPLATE.format(numeral=numeral, context=context)
