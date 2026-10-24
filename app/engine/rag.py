from app.core.config import settings
from app.core.openai.client import client


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the configured embedding model."""
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [d.embedding for d in response.data]


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
