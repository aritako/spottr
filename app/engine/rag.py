from app.core.config import settings
from app.core.openai.client import client

# Retrieval tuning constants. These are parameters of the retrieval algorithm, not deployment
# configuration, so they live here rather than in Settings (see docs/adr/0001).
DEFAULT_TOP_K = 5
MIN_TOP_K = 1
MAX_TOP_K = 10
# Retrieved chunks are deduplicated by content after the query, so ask for headroom.
DUPLICATE_OVERFETCH = 3
MAX_COSINE_DISTANCE = 0.606  # fallback, see docs/adr/0003-retrieval-fallback-cutoff.md
EMBEDDING_DIMENSIONS = 1536

MIN_CHUNK_WORDS = 40
MAX_CHUNK_WORDS = 300
SPLIT_OVERLAP_WORDS = 30


def normalize_k(k: int | None) -> int:
    """Resolve a requested passage count to a value within the supported range."""
    if k is None:
        return DEFAULT_TOP_K
    return max(MIN_TOP_K, min(k, MAX_TOP_K))


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the configured embedding model."""
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [d.embedding for d in response.data]


def chunk_document(text: str) -> list[str]:
    """Split a document into paragraph chunks for embedding."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "## Sources":
            lines = lines[:index]
            break

    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            blocks.append("\n".join(current).strip())
            current = []
    if current:
        blocks.append("\n".join(current).strip())

    without_h1: list[str] = []
    for block in blocks:
        block_lines = block.splitlines()
        if block_lines and block_lines[0].startswith("# "):
            block_lines = block_lines[1:]
        stripped = "\n".join(block_lines).strip()
        if stripped:
            without_h1.append(stripped)
    blocks = without_h1

    attached: list[str] = []
    pending_heading: str | None = None
    for block in blocks:
        if all(line.startswith("#") for line in block.splitlines()):
            pending_heading = block if pending_heading is None else f"{pending_heading}\n{block}"
            continue
        block = f"{pending_heading}\n{block}" if pending_heading is not None else block
        pending_heading = None
        attached.append(block)
    blocks = attached

    merged: list[str] = []
    pending: str | None = None
    for block in blocks:
        pending = block if pending is None else f"{pending}\n\n{block}"
        if len(pending.split()) >= MIN_CHUNK_WORDS:
            merged.append(pending)
            pending = None
    if pending is not None:
        if merged:
            merged[-1] = f"{merged[-1]}\n\n{pending}"
        else:
            merged.append(pending)  # a short document stays one chunk

    chunks: list[str] = []
    step = MAX_CHUNK_WORDS - SPLIT_OVERLAP_WORDS
    for block in merged:
        words = block.split()
        if len(words) <= MAX_CHUNK_WORDS:
            chunks.append(block)
            continue
        pieces = chunk_text(block, chunk_size=MAX_CHUNK_WORDS, overlap=SPLIT_OVERLAP_WORDS)
        if len(pieces) > 1 and len(pieces[-1].split()) < MIN_CHUNK_WORDS:
            previous_start = (len(pieces) - 2) * step
            pieces = [*pieces[:-2], " ".join(words[previous_start:])]
        chunks.extend(pieces)
    return chunks


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping, word-based chunks.

    Args:
        text (str): The source text to chunk.
        chunk_size (int): Maximum number of words per chunk.
        overlap (int): Number of words shared between consecutive chunks.

    Returns:
        list[str]: The chunks in order. Empty or whitespace-only input returns [].
    """
    words = text.split()
    if not words:
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if not chunk:
            continue
        chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks
