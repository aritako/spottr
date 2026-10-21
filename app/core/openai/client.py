from openai import OpenAI

from app.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the configured embedding model."""
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [d.embedding for d in response.data]
