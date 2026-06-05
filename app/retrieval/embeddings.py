import asyncio
import hashlib
import logging
import math
from dataclasses import dataclass

from app.core.config import Settings

logger = logging.getLogger(__name__)


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
    # Gemini BatchEmbedContents hard limit is 100 items, but the free tier also
    # caps at 100 *requests* per minute (each item in a batch counts as one).
    # Use a smaller batch size so we can spread requests across time.
    _MAX_BATCH_SIZE: int = 100
    _MAX_RETRIES: int = 5
    _INITIAL_BACKOFF: float = 5.0  # seconds
    _INTER_BATCH_DELAY: float = 4.5  # seconds between batches

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

        all_embeddings: list[list[float]] = []
        total_batches = math.ceil(len(texts) / self._MAX_BATCH_SIZE)

        for batch_idx, start in enumerate(range(0, len(texts), self._MAX_BATCH_SIZE)):
            batch = texts[start : start + self._MAX_BATCH_SIZE]
            request = {
                "model": self.config.model,
                "input": batch,
            }
            if self.config.request_dimensions:
                request["dimensions"] = self.dimensions

            response = await self._call_with_retry(request, batch_idx + 1, total_batches)
            all_embeddings.extend(item.embedding for item in response.data)

            # Delay between batches to stay under rate limits
            if start + self._MAX_BATCH_SIZE < len(texts):
                await asyncio.sleep(self._INTER_BATCH_DELAY)

        return all_embeddings

    async def _call_with_retry(self, request: dict, batch_num: int, total: int):
        from openai import RateLimitError

        backoff = self._INITIAL_BACKOFF
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                return await self.client.embeddings.create(**request)
            except RateLimitError as exc:
                if attempt == self._MAX_RETRIES:
                    logger.error(
                        "Embedding rate limit: giving up after %d retries. batch=%d/%d",
                        self._MAX_RETRIES, batch_num, total,
                    )
                    raise
                # Try to parse the server-suggested retry delay
                wait = self._parse_retry_delay(exc) or backoff
                logger.warning(
                    "Embedding rate limit hit (429). batch=%d/%d attempt=%d/%d "
                    "retrying in %.1fs",
                    batch_num, total, attempt, self._MAX_RETRIES, wait,
                )
                await asyncio.sleep(wait)
                backoff = min(backoff * 2, 120)  # exponential backoff, cap at 2 min

    @staticmethod
    def _parse_retry_delay(exc: Exception) -> float | None:
        """Extract the retry delay from a Gemini 429 error body if available."""
        try:
            body = exc.body
            if isinstance(body, dict):
                for detail in body.get("error", {}).get("details", []):
                    if "retryDelay" in detail:
                        delay_str = detail["retryDelay"]
                        # e.g. "18s" or "18.827488244s"
                        return float(delay_str.rstrip("s")) + 1.0  # +1s safety margin
        except Exception:
            pass
        return None


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
