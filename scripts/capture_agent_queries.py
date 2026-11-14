"""Capture the queries the coach writes for the retrieval golden set.

For every golden question, send one first-turn ``responses.create`` call using exactly the
instructions, model and tool schema that ``Coach.ask_coach`` sends, then record every
``search_coaching_docs`` call's query and ``k``. No tools are executed and no follow-up turns
are requested.

The result is a frozen, single-sample fixture used by ``scripts/eval_retrieval.py
--agent-queries``. Re-capture when the model or the instructions change.

Usage (from the repository root, with a real OPENAI_API_KEY):

    python scripts/capture_agent_queries.py
    python scripts/capture_agent_queries.py --force
"""

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAIError

# Make `app` importable when the script is run directly from the repo root, matching
# scripts/seed.py and scripts/eval_retrieval.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.core.openai.client import client  # noqa: E402
from app.engine.coach import Coach, build_coach_instructions  # noqa: E402
from app.eval.golden_set import (  # noqa: E402
    DEFAULT_AGENT_QUERIES_PATH,
    DEFAULT_GOLDEN_SET_PATH,
    AgentDocsCall,
    AgentQueries,
    AgentQueryEntry,
    GoldenSet,
    GoldenSetError,
    load_golden_set,
)

INSTRUCTIONS_PATH = Path("app/engine/prompts/instructions.py")


class CaptureError(RuntimeError):
    """The capture could not complete, with an actionable message."""


def parse_docs_calls(output: Sequence[Any]) -> list[AgentDocsCall]:
    """Extract every search_coaching_docs call from one first-turn response."""
    calls: list[AgentDocsCall] = []
    for item in output:
        if getattr(item, "type", None) != "function_call":
            continue
        if getattr(item, "name", None) != "search_coaching_docs":
            continue

        try:
            arguments = json.loads(item.arguments)
        except (TypeError, json.JSONDecodeError) as error:
            raise CaptureError(
                f"search_coaching_docs returned unreadable arguments: {error}"
            ) from error

        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise CaptureError("search_coaching_docs returned a call without a query")

        k = arguments.get("k")
        if k is not None and (not isinstance(k, int) or isinstance(k, bool)):
            raise CaptureError(f"search_coaching_docs returned a non-integer k: {k!r}")

        calls.append(AgentDocsCall(query=query, k=k))
    return calls


def instructions_sha() -> str:
    """The last commit that touched the instructions file, or a clear error."""
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", str(INSTRUCTIONS_PATH)],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise CaptureError(
            f"{INSTRUCTIONS_PATH} has uncommitted changes; commit them before capturing so "
            "the fixture header records the instructions that produced it."
        )

    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", str(INSTRUCTIONS_PATH)],
        check=True,
        capture_output=True,
        text=True,
    )
    sha = result.stdout.strip()
    if not sha:
        raise CaptureError(f"Could not find a git commit for {INSTRUCTIONS_PATH}")
    return sha


def capture(golden_set: GoldenSet, *, sha: str | None = None) -> AgentQueries:
    """Run the first-turn calls and build the frozen fixture."""
    session = SessionLocal()
    try:
        coach = Coach(session)
        query_model = coach.QUERY_MODEL
        tools = coach.TOOLS
    finally:
        session.close()

    sha = sha or instructions_sha()
    instructions = build_coach_instructions(date.today())
    entries: dict[str, AgentQueryEntry] = {}
    total_calls = 0

    for index, entry in enumerate(golden_set.entries, start=1):
        response = client.responses.create(
            instructions=instructions,
            model=query_model,
            input=entry.question,
            tools=tools,
        )
        calls = parse_docs_calls(response.output)
        total_calls += len(calls)
        entries[entry.question] = AgentQueryEntry(docs_calls=tuple(calls))
        print(f"[{index}/{len(golden_set.entries)}] docs calls: {len(calls)}")

    print(f"Captured {total_calls} search_coaching_docs calls across {len(entries)} questions")
    return AgentQueries(
        query_model=query_model,
        captured_at=datetime.now(UTC),
        instructions_sha=sha,
        entries=entries,
    )


def write_fixture(path: Path, agent_queries: AgentQueries, *, force: bool) -> None:
    if path.exists() and not force:
        raise CaptureError(f"{path} already exists; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_dump(
        agent_queries.model_dump(mode="json"),
        sort_keys=False,
        allow_unicode=True,
    )
    header = (
        "# Captured by scripts/capture_agent_queries.py. This is one nondeterministic sample;\n"
        "# re-capture when the model or the instructions change.\n"
    )
    path.write_text(header + payload, encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=DEFAULT_GOLDEN_SET_PATH,
        help="Golden-set YAML file (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_AGENT_QUERIES_PATH,
        help="Agent-query fixture to write (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing fixture",
    )
    parser.add_argument(
        "--instructions-sha",
        default=None,
        help=(
            "Commit SHA for app/engine/prompts/instructions.py. Use when running outside a git "
            "checkout, such as a copy inside a container."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not settings.openai_api_key or settings.openai_api_key == "dummy":
        print(
            "error: OPENAI_API_KEY is not set. Capturing agent queries calls the real coach "
            "model, so a dummy key cannot run it.",
            file=sys.stderr,
        )
        return 1

    try:
        golden_set = load_golden_set(args.golden_set)
        agent_queries = capture(golden_set, sha=args.instructions_sha)
        write_fixture(args.output, agent_queries, force=args.force)
    except GoldenSetError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except CaptureError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except OpenAIError as error:
        print(
            "error: the capture call failed. Check that OPENAI_API_KEY is a real key and "
            f"that the API is reachable. Details: {error}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
