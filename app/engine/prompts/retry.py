"""Model-facing correction turns.

A correction turn is the coach's one silent retry, sent when a Guardrail finds a fixable
Violation. Its input is plain app-written copy — never the lifter's question — that names the
complaint and points back at the tools, so the model can correct the slip without the lifter
seeing the exchange. The loop chains it from the previous response with the same instructions and
tool menu, matching how the first turn sends the question.
"""

__all__ = ["SCOPE_RETRY"]

SCOPE_RETRY = (
    "You answered without calling any tool, so no tool output backs that answer. Answer the "
    "lifter's question again, and consult your tools first: query_workouts or query_exercises "
    "for their logged workouts, and search_coaching_docs for training principles. Do not answer "
    "from your own knowledge."
)
