"""Configuration for RAG API."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    api_title: str = "RAG API"
    api_version: str = "0.1.0"
    api_description: str = "Production-ready RAG API with document ingestion and search"

    # Pipeline Settings
    vector_db_path: str = "./vector_db"
    collection_name: str = "documents"
    metadata_db_url: str = "sqlite+aiosqlite:///./metadata.db"
    chunk_max_tokens: int = 512
    chunk_overlap_tokens: int = 50

    # Embedding Settings
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = "text-embedding-3-small"

    # LLM Settings
    default_chat_model: str = "gpt-4o-mini"

    # CORS Settings
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
