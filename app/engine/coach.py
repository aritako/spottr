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
from app.engine.prompts import TOOL_SCHEMAS
from app.engine.prompts import build_instructions as build_coach_instructions
from app.engine.tools import Tools
from app.shared.enums.coach import Metric
from app.shared.schemas.coach import Citation


class Coach:
    def __init__(self, db: Session):
        self.tools = Tools(db)
        self.client = client

        self.QUERY_MODEL = "gpt-5.4-nano"
        self.TOOL_REGISTRY = {
            "query_exercises": self.tools.query_exercises,
            "query_workouts": self.tools.query_workouts,
            "search_coaching_docs": self.tools.search_coaching_docs,
        }
        self.TOOLS: list[FunctionToolParam] = list(TOOL_SCHEMAS)

        self.workoutsRepository = WorkoutsRepository(db)

    def build_instructions(self) -> str:
        return build_coach_instructions(date.today())

    def ask_coach(self, question: str, max_iterations: int = 5) -> dict[str, Any]:
        used_tools: list[str] = []
        citations: list[Citation] = []

        response = self.client.responses.create(
            instructions=Coach.build_instructions(self),
            model=self.QUERY_MODEL,
            input=question,
            tools=self.TOOLS,
        )

        for _ in range(max_iterations):
            tool_calls = [item for item in response.output if item.type == "function_call"]

            if not tool_calls:
                return {
                    "answer": response.output_text or "I couldn't complete that request.",
                    "used_tools": used_tools,
                    "citations": [citation.model_dump() for citation in citations],
                }

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

                if fn_name not in used_tools:
                    used_tools.append(fn_name)

                fn = self.TOOL_REGISTRY[fn_name]
                result = fn(**fn_args)
                if fn_name == "search_coaching_docs":
                    self._collect_citations(citations, result)
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
            response = self.client.responses.create(
                model=self.QUERY_MODEL,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=self.TOOLS,
            )

        return {
            "answer": "I couldn't complete that request.",
            "used_tools": used_tools,
            "citations": [citation.model_dump() for citation in citations],
        }

    @staticmethod
    def _collect_citations(citations: list[Citation], result: Any) -> None:
        """Record every passage the coach consulted, deduplicated by document and chunk."""
        if not isinstance(result, dict):
            return
        for passage in result.get("results", []):
            citation = Citation(
                document_id=passage["document_id"],
                document=passage["document"],
                chunk_index=passage["chunk_index"],
            )
            if not any(
                known.document_id == citation.document_id
                and known.chunk_index == citation.chunk_index
                for known in citations
            ):
                citations.append(citation)
