from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Vietnamese/English RAG Document Assistant"
    environment: str = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    max_file_mb: int = 25
    upload_dir: Path = Path("data/uploads")

    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag_assistant"
    auto_create_tables: bool = True

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "rag_chunks"
    qdrant_dense_vector_name: str = "dense"
    qdrant_sparse_vector_name: str = "sparse"

    llm_provider: str = "gemini"
    embedding_provider: str = "gemini"

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_chat_model: str = "gpt-5.5"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_reasoning_effort: str = "low"

    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-2-preview"

    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_chat_model: str = "llama-3.1-8b-instant"

    openai_compatible_api_key: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_chat_model: str | None = None
    openai_compatible_embedding_model: str | None = None

    embedding_dimensions: int = 3072
    embedding_request_dimensions: bool = False
    tokenizer_model: str = "text-embedding-3-large"

    chunk_size_tokens: int = 700
    chunk_overlap_tokens: int = 120
    retrieval_top_k: int = 6
    retrieval_prefetch_limit: int = 30
    no_answer_min_score: float = 0.16

    input_cost_per_1m_tokens: float = Field(default=0.0, ge=0)
    output_cost_per_1m_tokens: float = Field(default=0.0, ge=0)

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @property
    def static_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "static"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
