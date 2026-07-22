import json
from datetime import date
from typing import Any

from openai.types.responses import (
    FunctionToolParam,
    ResponseInputItemParam,
)
from sqlalchemy.orm import Session

from app.api.repository.workouts import WorkoutsRepository
from app.core.openai.client import client
from app.engine.tools import Tools
from app.shared.enums.coach import Metric


class Coach:
    def __init__(self, db: Session):
        self.tools = Tools(db)
        self.client = client

        self.QUERY_MODEL = "gpt-5.4-nano"
        self.TOOL_REGISTRY = {
            "query_exercises": self.tools.query_exercises,
            "query_workouts": self.tools.query_workouts,
        }
        self.TOOLS: list[FunctionToolParam] = [
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
                            "enum": ["day", "week", "month", "year", None],
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
        ]

        self.workoutsRepository = WorkoutsRepository(db)

    def build_instructions(self) -> str:
        today = date.today().isoformat()
        return f"""
            You are Spottr, an AI strength-training coach. You answer questions about the
            user's logged workouts by calling tools — never guess or estimate numbers
            yourself; always retrieve them.

            CURRENT DATE
            Today's date is {today}. Use this as the authoritative "now" for any relative
            time expression (e.g. "this week," "past few days," "last month"). Do not
            rely on any other assumption about the current date.

            DATE RANGE TRANSLATION
            When a question uses relative time language, convert it to explicit
            start_date/end_date before calling query_workouts:
            - "today" -> start_date = end_date = {today}
            - "the past few days" -> the last 3-4 days up to and including today
            - "this week" -> the current ISO week (Monday through today)
            - "last week" -> the previous full ISO week (Monday-Sunday)
            - "this month" -> the 1st of the current month through today
            Always include today's date in the range when the question implies
            "recent" or "so far" — do not stop the range one day early.

            CHOOSING group_by
            Match the bucket size to the span of the question, not just the words used:
            - Ranges under ~2 weeks -> group_by="day"
            - Ranges of roughly 3-8 weeks -> group_by="week"
            - Ranges spanning multiple months -> group_by="month"
            - Ranges spanning a year or more -> group_by="year"
            A grain that produces only one bucket for the requested range is usually
            too coarse — prefer the finer grain unless the user asked for a summary
            total.

            CHOOSING A METRIC
            - "tonnage" answers questions about volume, total work, or "how much did I lift."
            - "e1rm" answers questions about strength, max potential, or "how strong am I getting."
            If the question doesn't specify, infer from context; if genuinely ambiguous,
            you may call query_workouts with both metrics in separate calls rather than guessing.

            USING query_exercises
            If the user's question doesn't name a specific exercise (e.g. "how's my
            training going overall"), call query_exercises first to see what exists,
            then call query_workouts once per relevant exercise (or omit the exercise
            filter if the tool supports querying across all of them).

            INTERPRETING RESULTS
            - If query_workouts returns no data for a range, say so plainly rather than
            inventing a plausible-sounding answer.
            - When comparing values over time, state the actual numbers and the
            direction/magnitude of change, not just a vague "trending well."
            - Keep a supportive, direct coaching tone — informative first, encouraging
            second. Don't overstate confidence from very few data points; say so when
            the sample is small (e.g. "only two sessions in this range, so treat this
            as a preliminary signal").
            """.strip()

    def ask_coach(self, question: str, max_iterations: int = 5) -> str:
        response = client.responses.create(
            instructions=Coach.build_instructions(self),
            model=self.QUERY_MODEL,
            input=question,
            tools=self.TOOLS,
        )

        for _ in range(max_iterations):
            tool_calls = [item for item in response.output if item.type == "function_call"]

            if not tool_calls:
                return response.output_text or "I couldn't complete that request."

            tool_outputs: list[ResponseInputItemParam] = []
            for tool_call in tool_calls:
                fn_name = tool_call.name
                fn_args: dict[str, Any] = json.loads(tool_call.arguments)

                # The schema sends `metric` as a string; convert to the enum
                # so Tools.query_workouts' match statement works.
                if isinstance(fn_args.get("metric"), str):
                    fn_args["metric"] = Metric(fn_args["metric"])

                if fn_name not in self.TOOL_REGISTRY:
                    continue

                fn = self.TOOL_REGISTRY[fn_name]
                result = fn(**fn_args)
                output_str = result if isinstance(result, str) else json.dumps(result)

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": output_str,
                    }
                )

            # Feed results back; previous_response_id chains the conversation
            # server-side so we don't rebuild the full message history.
            response = client.responses.create(
                model=self.QUERY_MODEL,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=self.TOOLS,
            )

        return "I couldn't complete that request."
