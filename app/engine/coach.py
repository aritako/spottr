import json
from collections.abc import Iterable
from typing import Any, cast

from openai.types.chat import ChatCompletionMessageFunctionToolCall
from openai.types.responses import (
    FunctionToolParam,
    ResponseInputItemParam,
    ResponseInputParam,
    ResponseOutputItem,
    ToolParam,
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
        self.TOOL_REGISTRY = {"query_workouts": self.tools.query_workouts}
        self.TOOLS: list[FunctionToolParam] = [
            {
                "type": "function",
                "name": "query_workouts",
                "description": (
                    "Query the user's logged workout data. Use for any question "
                    "about their actual numbers, trends, volume, or PRs."
                ),
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
                    },
                    "required": ["exercise", "metric", "start_date", "end_date"],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        ]

        self.workoutsRepository = WorkoutsRepository(db)

    def ask_coach(self, question: str, max_iterations: int = 5) -> str:
        response = client.responses.create(
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
            )

        return "I couldn't complete that request."
