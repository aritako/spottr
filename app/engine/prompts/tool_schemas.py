from openai.types.responses import FunctionToolParam

from app.engine.rag import DEFAULT_TOP_K, MAX_TOP_K, MIN_TOP_K

TOOL_SCHEMAS: list[FunctionToolParam] = [
    {
        "type": "function",
        "name": "query_exercises",
        "description": """
            Used to fetch the list of Exercises of user. Used before query_workouts to
            determine the workout's exercise selection before determining the metric.
            If no exercise is specified, the default is to provide the metric for each
            exercise.
        """,
        "parameters": {},
        "strict": False,
    },
    {
        "type": "function",
        "name": "query_workouts",
        "description": """
            Query the user's logged workout data. Use for any question
            about their actual numbers, trends, volume, or PRs.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "exercise": {
                    "type": ["string", "null"],
                    "description": "Exercise name, e.g. 'Back Squat'.",
                },
                "metric": {
                    "type": "string",
                    "enum": ["e1rm", "tonnage"],
                },
                "start_date": {
                    "type": ["string", "null"],
                    "format": "date",
                },
                "end_date": {
                    "type": ["string", "null"],
                    "format": "date",
                },
                "group_by": {
                    "type": ["string", "null"],
                    "enum": ["day", "week", "month", "year"],
                    "description": (
                        """
                        Time bucket size. Use 'day' for ranges under ~2 weeks, 'week' for
                        month-scale ranges, 'month' or 'year' for multi-month/year trends.
                        Pass null to default to weekly.
                        """
                    ),
                },
            },
            "required": ["exercise", "metric", "start_date", "end_date", "group_by"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_coaching_docs",
        "description": """
            Search the coaching corpus for training principles, deload
            guidance, programming advice, technique cues, and recovery or
            autoregulation guidance. Use for general "should I..." / "how do I..."
            questions that are not about the user's logged numbers. Returns passages
            with their document title and chunk index, plus a status of "ok",
            "no_match", or "empty_corpus".
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query.",
                },
                "k": {
                    "type": ["integer", "null"],
                    "description": (
                        "Number of passages to retrieve. Pass null for the default "
                        f"({DEFAULT_TOP_K}). Values are clamped to {MIN_TOP_K}-{MAX_TOP_K}."
                    ),
                },
            },
            "required": ["query", "k"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
