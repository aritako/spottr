from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    database_url: str = "postgresql+psycopg://coach:coach@db:5432/coach"
    test_database_url: str | None = None
    embedding_model: str = "text-embedding-3-small"


settings = Settings()
