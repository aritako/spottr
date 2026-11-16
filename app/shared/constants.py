"""Shared string constants that cross module boundaries."""

# The status a workout query returns when the requested range has no rows. The coach's Guardrail
# classifies exactly this string as emptiness, so the producer and the classifier share it.
NO_MATCHING_WORKOUT_DATA = "No matching workout data found."
