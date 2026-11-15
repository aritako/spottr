import json
import logging
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from openai.types.responses import (
    FunctionToolParam,
    Response,
    ResponseInputItemParam,
)
from sqlalchemy.orm import Session

from app.api.repository.workouts import WorkoutsRepository
from app.core.openai.client import client
from app.engine.guardrails import (
    ScopeVerdict,
    ToolEvidence,
    error_evidence,
    grounding_violation,
    scope_verdict,
    scrape_receipts,
    tool_evidence,
)
from app.engine.prompts import SCOPE_RETRY, TOOL_SCHEMAS, grounding_retry
from app.engine.prompts import build_instructions as build_coach_instructions
from app.engine.rejections import (
    COULD_NOT_COMPLETE,
    NOTHING_FOUND,
    OUT_OF_SCOPE,
    build_rejection,
)
from app.engine.tools import Tools
from app.shared.enums.coach import Metric
from app.shared.schemas.coach import Citation

logger = logging.getLogger(__name__)


class _UnreadableArguments(Exception):
    """Raised when a function call's arguments cannot become tool keyword arguments."""


class _AnswerOutcome(StrEnum):
    """What the loop does with a finished answer."""

    SHIP = "ship"
    RETRY = "retry"
    REJECTION = "rejection"


@dataclass(frozen=True)
class _AnswerDecision:
    """The loop's single judgement of a finished answer.

    A ship carries no message; a retry carries the complaint to send the model; a Rejection
    carries the canned app-written text to ship in the answer's place.
    """

    outcome: _AnswerOutcome
    complaint: str | None = None
    rejection: str | None = None


def _tools_in_flight(used_tools: Sequence[str]) -> str:
    """Name the tools that actually ran, for a log line."""
    return ", ".join(used_tools) if used_tools else "none"


class Coach:
    def __init__(self, db: Session):
        self.tools = Tools(db)
        self.client = client

        self.QUERY_MODEL = "gpt-5.4-nano"
        self.TOOL_REGISTRY = {
            "query_exercises": self.tools.query_exercises,
            "query_workouts": self.tools.query_workouts,
            # search_coaching_docs is rebound in ask_coach with the received question. This base
            # entry keeps the schema/registry consistency check; the loop does not dispatch it.
            "search_coaching_docs": self.tools.search_coaching_docs,
        }
        self.TOOLS: list[FunctionToolParam] = list(TOOL_SCHEMAS)
        # Tools whose results carry citable passages, so the loop never branches on a tool name.
        self.CITATION_COLLECTORS = {
            "search_coaching_docs": self._collect_citations,
        }

        self.workoutsRepository = WorkoutsRepository(db)

    def ask_coach(self, question: str, max_iterations: int = 5) -> dict[str, Any]:
        used_tools: list[str] = []
        citations: list[Citation] = []
        evidence: list[ToolEvidence] = []
        # Every numeral any successful tool returned during this request, so a later turn can
        # quote data that an earlier turn retrieved.
        receipts: set[Decimal] = set()
        # One correction turn per request, however many Violations it produces: the budget is
        # counted per request, not per Violation kind.
        retry_used = False

        def search_coaching_docs(k: int | None = None, **arguments: Any) -> dict[str, Any]:
            # The model no longer writes the search text. A stray query from an older schema
            # is dropped; the user's question is the only search text.
            arguments.pop("query", None)
            return self.tools.search_coaching_docs(question, k=k)

        tool_registry = {
            **self.TOOL_REGISTRY,
            "search_coaching_docs": search_coaching_docs,
        }
        available_tools = ", ".join(tool_registry)

        instructions = build_coach_instructions(date.today())
        response = self.client.responses.create(
            instructions=instructions,
            model=self.QUERY_MODEL,
            input=question,
            tools=self.TOOLS,
        )

        for iteration in range(max_iterations):
            tool_calls = [item for item in response.output if item.type == "function_call"]

            if not tool_calls:
                decision = self._judge_answer(
                    response.output_text,
                    evidence,
                    receipts=receipts,
                    retry_used=retry_used,
                    # The correction turn spends this iteration, so its response needs the
                    # next one in which to be judged.
                    retry_available=iteration + 1 < max_iterations,
                    used_tools=used_tools,
                    available_tools=available_tools,
                )
                if decision.outcome is _AnswerOutcome.SHIP:
                    return {
                        "answer": response.output_text,
                        "used_tools": used_tools,
                        "citations": [citation.model_dump() for citation in citations],
                    }
                if decision.outcome is _AnswerOutcome.RETRY:
                    assert decision.complaint is not None
                    response = self._send_correction_turn(
                        response.id, decision.complaint, instructions
                    )
                    retry_used = True
                    continue
                assert decision.rejection is not None
                return build_rejection(decision.rejection, used_tools)

            tool_outputs: list[ResponseInputItemParam] = []
            for tool_call in tool_calls:
                fn_name = tool_call.name

                if fn_name not in tool_registry:
                    logger.warning(
                        "coach called unknown tool %s; returning an error result", fn_name
                    )
                    evidence.append(error_evidence(fn_name))
                    tool_outputs.append(
                        self._tool_error_output(
                            tool_call.call_id,
                            fn_name,
                            f"Unknown tool '{fn_name}'. Available tools: {available_tools}.",
                        )
                    )
                    continue

                try:
                    fn_args = self._decode_arguments(tool_call)
                except _UnreadableArguments as error:
                    logger.warning(
                        "coach sent unreadable arguments for tool %s: %s", fn_name, error
                    )
                    evidence.append(error_evidence(fn_name))
                    tool_outputs.append(
                        self._tool_error_output(
                            tool_call.call_id,
                            fn_name,
                            f"Could not read the arguments for tool '{fn_name}': {error}.",
                        )
                    )
                    continue

                if fn_name not in used_tools:
                    used_tools.append(fn_name)

                fn = tool_registry[fn_name]
                result = fn(**fn_args)
                evidence.append(tool_evidence(fn_name, result))
                receipts |= scrape_receipts(result)
                collect_citations = self.CITATION_COLLECTORS.get(fn_name)
                if collect_citations:
                    collect_citations(citations, result)
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
                instructions=instructions,
                model=self.QUERY_MODEL,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=self.TOOLS,
            )

        logger.warning(
            "coach loop exhausted its %d-iteration budget; tools in flight: %s",
            max_iterations,
            _tools_in_flight(used_tools),
        )
        return build_rejection(COULD_NOT_COMPLETE, used_tools)

    def _judge_answer(
        self,
        output_text: str,
        evidence: Sequence[ToolEvidence],
        *,
        receipts: Collection[Decimal],
        retry_used: bool,
        retry_available: bool,
        used_tools: Sequence[str],
        available_tools: str,
    ) -> _AnswerDecision:
        """Judge one finished answer and decide its fate: ship, retry, or Rejection.

        This is the loop's single judgement point, so every Guardrail attaches here. Scope comes
        first because it decides whether any evidence exists; only a supported answer reaches
        the Grounding check. A Rejection always goes through the one canned swap, which drops
        Citations and preserves the tools that actually ran.
        """
        verdict = scope_verdict(evidence)
        if verdict is ScopeVerdict.ALL_EMPTY:
            logger.warning(
                "coach answer normalized to nothing-found: every substantive tool result was "
                "empty; tools in flight: %s",
                _tools_in_flight(used_tools),
            )
            return _AnswerDecision(_AnswerOutcome.REJECTION, rejection=NOTHING_FOUND)
        if verdict is ScopeVerdict.NO_SUBSTANTIVE_CALL:
            return self._decide_violation(
                "no substantive tool call",
                SCOPE_RETRY,
                retry_used=retry_used,
                retry_available=retry_available,
                used_tools=used_tools,
                available_tools=available_tools,
            )
        if not output_text:
            return _AnswerDecision(_AnswerOutcome.REJECTION, rejection=COULD_NOT_COMPLETE)
        violation = grounding_violation(output_text, receipts)
        if violation is not None:
            return self._decide_violation(
                f"grounding: numeral {violation.numeral} has no Receipt in the tool results",
                grounding_retry(violation.numeral),
                retry_used=retry_used,
                retry_available=retry_available,
                used_tools=used_tools,
                available_tools=available_tools,
            )
        return _AnswerDecision(_AnswerOutcome.SHIP)

    @staticmethod
    def _decide_violation(
        reason: str,
        complaint: str,
        *,
        retry_used: bool,
        retry_available: bool,
        used_tools: Sequence[str],
        available_tools: str,
    ) -> _AnswerDecision:
        """Apply the one per-request retry budget to a fixable Violation.

        The budget counts retries, not Violation kinds: the first Violation of any kind spends
        the correction turn, a second one is the two-strike out-of-scope Rejection, and a first
        Violation with no iteration left to carry its correction turn is the couldn't-complete
        Rejection.
        """
        tools = _tools_in_flight(used_tools)
        if retry_used:
            logger.warning(
                "coach answer blocked: %s again after one correction turn; returning the "
                "out-of-scope Rejection; tools in flight: %s; available tools: %s",
                reason,
                tools,
                available_tools,
            )
            return _AnswerDecision(_AnswerOutcome.REJECTION, rejection=OUT_OF_SCOPE)
        if not retry_available:
            logger.warning(
                "coach answer blocked: %s but the iteration budget is spent; returning the "
                "couldn't-complete Rejection; tools in flight: %s; available tools: %s",
                reason,
                tools,
                available_tools,
            )
            return _AnswerDecision(_AnswerOutcome.REJECTION, rejection=COULD_NOT_COMPLETE)
        logger.warning(
            "coach answer retried: %s; sending one correction turn; tools in flight: %s; "
            "available tools: %s",
            reason,
            tools,
            available_tools,
        )
        return _AnswerDecision(_AnswerOutcome.RETRY, complaint=complaint)

    def _send_correction_turn(
        self, previous_response_id: str, complaint: str, instructions: str
    ) -> Response:
        """Send the one silent retry, chained from the answer it corrects.

        The tool menu and the instructions are re-sent so the model keeps its menu and its
        rules, and the complaint is a plain message input — the same shape the first turn sends
        the question in — rather than a fabricated assistant turn.
        """
        return self.client.responses.create(
            instructions=instructions,
            model=self.QUERY_MODEL,
            previous_response_id=previous_response_id,
            input=complaint,
            tools=self.TOOLS,
        )

    @staticmethod
    def _decode_arguments(tool_call: Any) -> dict[str, Any]:
        """Turn a function call's raw arguments into keyword arguments for its tool."""
        try:
            arguments = json.loads(tool_call.arguments)
        except (json.JSONDecodeError, TypeError) as error:
            raise _UnreadableArguments("the arguments are not valid JSON") from error
        if not isinstance(arguments, dict):
            raise _UnreadableArguments("the arguments must be a JSON object")

        # The schema sends `metric` as a string; convert to the enum
        # so Tools.query_workouts' match statement works.
        metric = arguments.get("metric")
        if isinstance(metric, str):
            try:
                arguments["metric"] = Metric(metric)
            except ValueError as error:
                raise _UnreadableArguments(
                    "metric must be one of: " + ", ".join(enum.value for enum in Metric)
                ) from error
        return arguments

    @staticmethod
    def _tool_error_output(call_id: str, tool_name: str, message: str) -> ResponseInputItemParam:
        """Build the one function_call_output that answers a failed tool call."""
        return {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps({"tool": tool_name, "error": message}),
        }

    @staticmethod
    def _collect_citations(citations: list[Citation], result: Any) -> None:
        """Record every passage the coach consulted, deduplicated by document and chunk."""
        if not isinstance(result, dict):
            return
        for passage in result.get("passages", []):
            citation = Citation(
                document_id=passage["document_id"],
                document_title=passage["document_title"],
                chunk_index=passage["chunk_index"],
            )
            if not any(
                known.document_id == citation.document_id
                and known.chunk_index == citation.chunk_index
                for known in citations
            ):
                citations.append(citation)
