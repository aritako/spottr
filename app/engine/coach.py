import json
from typing import cast

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)
from sqlalchemy.orm import Session

from app.config import settings
from app.engine.tools import query_workouts
from app.repository.workouts import WorkoutsRepository

client = OpenAI(api_key=settings.openai_api_key)


class Coach:
    def __init__(self, db: Session):
        self.TOOL_REGISTRY = {"query_workouts": query_workouts}

        self.TOOLS: list[ChatCompletionToolParam] = [
            {
                "type": "function",
                "function": {
                    "name": "query_workouts",
                    "description": """
                        Query the user's logged workout data. Use for any question
                        about their actual numbers, trends, volume, or PRs.
                    """,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "exercise": {
                                "type": "string",
                                "description": "Exercise name, e.g. 'Back Squat'. Omit for all.",
                            },
                            "metric": {
                                "type": "string",
                                "enum": ["e1rm", "tonnage", "max_weight", "avg_rpe", "set_count"],
                            },
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "group_by": {"type": "string", "enum": ["day", "week", "month"]},
                        },
                        "required": ["metric"],
                    },
                },
            },
        ]

        self.workoutsRepository = WorkoutsRepository(db)

    def ask_coach(self, question: str, max_iterations: int = 5) -> str:
        messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": question}]

        for _ in range(max_iterations):
            # Send the ENTIRE history + the tool menu, every time.
            response = client.chat.completions.create(
                model="gpt-5.4-nano",
                messages=messages,
                tools=self.TOOLS,
            )

            message: ChatCompletionMessage = response.choices[0].message

            # ---- Branch: did the model ask for a tool, or give a final answer? ----
            if not message.tool_calls:
                # No tool requested -> this is the final answer. Done.
                return message.content if message.content else "I couldn't complete that request."

            # ---- Branch: the model wants to call one or more tools. ----
            # First, append the model's OWN message (the tool request) to history.
            # This is essential — the result we send next must reference it.
            messages.append(
                cast(ChatCompletionAssistantMessageParam, message.model_dump(exclude_none=True))
            )

            if not message.tool_calls:
                return "I couldn't complete that request."

            # Run each requested tool and feed its result back.
            for tool_call in message.tool_calls:
                tool_call = cast(ChatCompletionMessageFunctionToolCall, tool_call)
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                # Dispatch to the real function via the registry.
                fn = self.TOOL_REGISTRY[fn_name]
                result = fn(**fn_args)  # **fn_args unpacks {} for a no-arg tool

                # Append the result as a 'tool' message, linked by tool_call_id.
                # The id is how the model knows WHICH call this answers.
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                )

            # Loop continues: next iteration sends the updated history,
            # now including the tool result, so the model can answer.

        # Safety valve: we hit the iteration cap without a final answer.
        return "I couldn't complete that request."
