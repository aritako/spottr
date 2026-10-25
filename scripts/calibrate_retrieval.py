"""Print retrieval distances for sample questions so the cutoff can be tuned.

`MAX_COSINE_DISTANCE` in ``app/engine/rag.py`` is only meaningful relative to the
embedding model and the ingested corpus, so it has to be picked from real numbers
rather than guessed. This script runs the same search the coach uses, with the
cutoff effectively disabled, and shows how close each passage actually is.

Run from the repository root, with the database up and documents ingested:

    python scripts/calibrate_retrieval.py
    python scripts/calibrate_retrieval.py "should I deload?" "how much volume is junk?"

Inside Docker:

    docker compose exec app python scripts/calibrate_retrieval.py

Passages marked PASS fall inside the current cutoff; FAIL ones would be discarded.
"""

import argparse
import sys
from pathlib import Path

# Make `app` importable when this script is run directly from the repo root,
# without relying on an installed package or PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.repository.docs import DocsRepository  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.engine.rag import (  # noqa: E402
    MAX_COSINE_DISTANCE,
    MAX_TOP_K,
    get_embeddings,
)

DEFAULT_QUERIES = [
    "should I deload?",
    "how hard should my sets feel?",
    "how much weekly volume builds muscle?",
    "what should I eat before training?",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "queries",
        nargs="*",
        help="Questions to retrieve for. Defaults to a fixed sample set.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=MAX_TOP_K,
        help=f"Passages to show per query (default {MAX_TOP_K}).",
    )
    args = parser.parse_args()

    queries = args.queries or DEFAULT_QUERIES
    with SessionLocal() as session:
        repository = DocsRepository(session)
        if not repository.has_chunks():
            print("No chunks in the corpus. Ingest documents with POST /docs/ingest first.")
            return

        for query in queries:
            print(f"\n{query}")
            print("-" * len(query))
            embedding = get_embeddings([query])[0]
            # A cutoff above 1.0 keeps every candidate so the rejected ones are visible.
            for chunk, distance in repository.search(embedding, args.k, max_distance=1.1):
                verdict = "PASS" if distance < MAX_COSINE_DISTANCE else "FAIL"
                snippet = " ".join(chunk.content.split())[:100]
                print(
                    f"  {distance:.3f} {verdict}  {chunk.document.title} "
                    f"[chunk {chunk.chunk_index}]: {snippet}..."
                )

    print(f"\nCurrent MAX_COSINE_DISTANCE: {MAX_COSINE_DISTANCE}")


if __name__ == "__main__":
    main()
