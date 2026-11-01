"""Ingest the coaching corpus into a running API.

Follows the contract in ``docs/corpus/README.md``: the H1 line is the title, the
filename is the source, and the whole file is the text. Documents already
present are skipped, because ingestion is not idempotent yet and re-posting the
same file would store a second copy.

Usage (API must be running):

    docker compose up -d db app
    python scripts/ingest_corpus.py

    docker compose exec app python scripts/ingest_corpus.py
    python scripts/ingest_corpus.py --dry-run
    python scripts/ingest_corpus.py --force          # ingest even if present

Inside Docker the API is reached at http://localhost:8000 from the host and at
http://localhost:8000 from the app container too, since the app serves it.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

PAGE_SIZE = 100


def corpus_paths(directory: Path) -> list[Path]:
    """Return the corpus markdown files, excluding the contract README."""
    return sorted(path for path in directory.glob("*.md") if path.name != "README.md")


def existing_documents(base_url: str) -> set[tuple[str, str]]:
    """Return (title, source) for everything already ingested."""
    documents: set[tuple[str, str]] = set()
    page = 0
    while True:
        url = f"{base_url}/docs?page={page}&page_size={PAGE_SIZE}"
        with urllib.request.urlopen(url) as response:
            batch = json.load(response)
        documents.update((document["title"], document["source"]) for document in batch)
        if len(batch) < PAGE_SIZE:
            return documents
        page += 1


def read_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    raise SystemExit(f"{path}: no H1 title (the corpus contract expects one)")


def ingest(base_url: str, payload: dict[str, str]) -> int:
    request = urllib.request.Request(
        f"{base_url}/docs/ingest",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)["id"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("docs/corpus"),
        help="Corpus directory (default: docs/corpus)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be ingested without calling the API",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ingest even when the title and source already exist",
    )
    args = parser.parse_args()

    paths = corpus_paths(args.dir)
    if not paths:
        raise SystemExit(f"No markdown files found in {args.dir}")

    known: set[tuple[str, str]] = set()
    if not args.dry_run and not args.force:
        known = existing_documents(args.base_url)

    ingested = skipped = failed = 0
    for path in paths:
        text = path.read_text()
        title = read_title(text, path)
        payload = {"title": title, "source": path.name, "text": text}
        words = len(text.split())

        if (title, path.name) in known:
            skipped += 1
            print(f"skip    {path.name:<40} {title} (already ingested)")
            continue

        if args.dry_run:
            ingested += 1
            print(f"would   {path.name:<40} {title} ({words} words)")
            continue

        try:
            document_id = ingest(args.base_url, payload)
        except urllib.error.HTTPError as error:
            failed += 1
            detail = error.read().decode(errors="replace")
            print(f"FAIL    {path.name:<40} {error.code} {detail}")
            continue
        except urllib.error.URLError as error:
            raise SystemExit(f"Cannot reach {args.base_url}: {error.reason}") from error

        ingested += 1
        print(f"ok      {path.name:<40} {title} -> id {document_id} ({words} words)")

    verb = "would ingest" if args.dry_run else "ingested"
    print(f"\n{verb} {ingested}, skipped {skipped}, failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
