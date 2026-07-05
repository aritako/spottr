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

from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)


# ---- 1. The actual tool implementation (your "hands") ----
def get_current_bodyweight() -> float:
    """Dummy tool. Later this will query the database."""
    return 82.5


# ---- 2. Describe the tool to the model (the "menu") ----
# The model reads `description` to decide whether to call this.
# Write it like you're explaining the function to a colleague.
TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_bodyweight",
            "description": "Get the user's most recent recorded bodyweight in kilograms.",
            "parameters": {
                "type": "object",
                "properties": {},  # no arguments for this dummy tool
                "required": [],
            },
        },
    }
]

# Maps the tool NAME the model uses -> the real Python function to run.
# This is how you dispatch from "the model asked for X" to "run X".
TOOL_REGISTRY = {
    "get_current_bodyweight": get_current_bodyweight,
}


def ask_coach(question: str, max_iterations: int = 5) -> str:
    # ---- 3. The conversation is a GROWING list. We append to it each turn. ----
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": question}]

    for _ in range(max_iterations):
        # Send the ENTIRE history + the tool menu, every time.
        response = client.chat.completions.create(
            model="gpt-5.4-nano",
            messages=messages,
            tools=TOOLS,
        )

        message: ChatCompletionMessage = response.choices[0].message

        # ---- 4. Branch: did the model ask for a tool, or give a final answer? ----
        if not message.tool_calls:
            # No tool requested -> this is the final answer. Done.
            return message.content if message.content else "I couldn't complete that request."

        # ---- 5. The model wants to call one or more tools. ----
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
            fn = TOOL_REGISTRY[fn_name]
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
