import hashlib
import math
from dataclasses import dataclass

from app.core.config import Settings


@dataclass(slots=True)
class EmbeddingProviderConfig:
    name: str
    api_key: str
    model: str
    base_url: str | None = None
    request_dimensions: bool = False


class EmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_texts([text]))[0]


class OpenAICompatibleEmbeddingClient(EmbeddingClient):
    def __init__(self, config: EmbeddingProviderConfig, *, dimensions: int):
        self.config = config
        self.dimensions = dimensions
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        request = {
            "model": self.config.model,
            "input": texts,
        }
        if self.config.request_dimensions:
            request["dimensions"] = self.dimensions

        response = await self.client.embeddings.create(**request)
        return [item.embedding for item in response.data]


class HashEmbeddingClient(EmbeddingClient):
    """Deterministic local fallback for development without an API key."""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def create_embedding_client(settings: Settings) -> EmbeddingClient:
    provider = normalize_provider(settings.embedding_provider)
    fallback = HashEmbeddingClient(dimensions=settings.embedding_dimensions)

    if provider in {"hash", "local", "development", "dev", "none"}:
        return fallback

    if provider == "openai":
        if not settings.openai_api_key:
            return fallback
        return OpenAICompatibleEmbeddingClient(
            EmbeddingProviderConfig(
                name="openai",
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_embedding_model,
                request_dimensions=settings.embedding_request_dimensions,
            ),
            dimensions=settings.embedding_dimensions,
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            return fallback
        return OpenAICompatibleEmbeddingClient(
            EmbeddingProviderConfig(
                name="gemini",
                api_key=settings.gemini_api_key,
                base_url=settings.gemini_base_url,
                model=settings.gemini_embedding_model,
                request_dimensions=False,
            ),
            dimensions=settings.embedding_dimensions,
        )

    if provider in {"openai-compatible", "compatible", "custom"}:
        if not settings.openai_compatible_api_key:
            return fallback
        if not settings.openai_compatible_base_url or not settings.openai_compatible_embedding_model:
            raise ValueError(
                "OPENAI_COMPATIBLE_BASE_URL and OPENAI_COMPATIBLE_EMBEDDING_MODEL "
                "are required when EMBEDDING_PROVIDER=openai-compatible."
            )
        return OpenAICompatibleEmbeddingClient(
            EmbeddingProviderConfig(
                name="openai-compatible",
                api_key=settings.openai_compatible_api_key,
                base_url=settings.openai_compatible_base_url,
                model=settings.openai_compatible_embedding_model,
                request_dimensions=settings.embedding_request_dimensions,
            ),
            dimensions=settings.embedding_dimensions,
        )

    if provider == "groq":
        raise ValueError("Groq is chat-only for this app. Use EMBEDDING_PROVIDER=gemini, openai, or hash.")

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER={settings.embedding_provider!r}.")


def normalize_provider(value: str | None) -> str:
    return (value or "").strip().lower().replace("_", "-")
