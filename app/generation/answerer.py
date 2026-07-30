import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.core.config import Settings
from app.core.costs import estimate_cost_usd
from app.generation.prompts import SYSTEM_PROMPT, build_context, build_user_prompt
from app.retrieval.embeddings import normalize_provider
from app.retrieval.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0")


@dataclass(slots=True)
class GeneratedAnswer:
    answer: str
    no_answer: bool
    confidence: float
    citations: list[dict]
    retrieval_trace: list[dict]
    usage: Usage


@dataclass(slots=True)
class LlmProviderConfig:
    name: str
    api_key: str
    model: str
    base_url: str | None = None


class GroundedAnswerer:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def answer(self, *, question: str, retrieved: list[RetrievedChunk]) -> GeneratedAnswer:
        retrieval_trace = [retrieved_chunk_to_dict(chunk) for chunk in retrieved]
        if self._should_no_answer(retrieved):
            return self._no_answer(question=question, retrieval_trace=retrieval_trace)

        citations = [citation_from_chunk(index, chunk) for index, chunk in enumerate(retrieved, start=1)]
        provider = resolve_llm_provider(self.settings)
        if provider is None:
            return self._development_answer(
                question=question,
                retrieved=retrieved,
                citations=citations,
                retrieval_trace=retrieval_trace,
            )

        try:
            return await self._provider_answer(
                provider=provider,
                question=question,
                retrieved=retrieved,
                citations=citations,
                retrieval_trace=retrieval_trace,
            )
        except Exception as exc:
            logger.warning("LLM provider failed; using deterministic fallback. provider=%s", provider.name, exc_info=exc)
            return self._development_answer(
                question=question,
                retrieved=retrieved,
                citations=citations,
                retrieval_trace=retrieval_trace,
            )

    def _should_no_answer(self, retrieved: list[RetrievedChunk]) -> bool:
        if not retrieved:
            return True
        return retrieved[0].score < self.settings.no_answer_min_score

    def _no_answer(self, *, question: str, retrieval_trace: list[dict]) -> GeneratedAnswer:
        if looks_vietnamese(question):
            answer = (
                "Toi khong tim thay thong tin du chac trong cac tai lieu da tai len "
                "de tra loi cau hoi nay."
            )
        else:
            answer = "I could not find enough evidence in the uploaded documents to answer this question."
        return GeneratedAnswer(
            answer=answer,
            no_answer=True,
            confidence=0.0,
            citations=[],
            retrieval_trace=retrieval_trace,
            usage=Usage(),
        )

    def _development_answer(
        self,
        *,
        question: str,
        retrieved: list[RetrievedChunk],
        citations: list[dict],
        retrieval_trace: list[dict],
    ) -> GeneratedAnswer:
        top = retrieved[:2]
        if looks_vietnamese(question):
            prefix = "Cau tra loi tam thoi tu cac doan lien quan nhat"
        else:
            prefix = "Development answer from the most relevant chunks"
        evidence = " ".join(chunk.text[:450] for chunk in top)
        markers = ", ".join(f"[C{index}]" for index in range(1, len(top) + 1))
        return GeneratedAnswer(
            answer=f"{prefix}: {evidence} {markers}".strip(),
            no_answer=False,
            confidence=min(1.0, max(0.0, retrieved[0].score)),
            citations=citations[: len(top)],
            retrieval_trace=retrieval_trace,
            usage=Usage(),
        )

    async def _provider_answer(
        self,
        *,
        provider: LlmProviderConfig,
        question: str,
        retrieved: list[RetrievedChunk],
        citations: list[dict],
        retrieval_trace: list[dict],
    ) -> GeneratedAnswer:
        from openai import AsyncOpenAI

        context_items = [retrieved_chunk_to_dict(chunk) for chunk in retrieved]
        context = build_context(context_items)
        client_kwargs = {"api_key": provider.api_key}
        if provider.base_url:
            client_kwargs["base_url"] = provider.base_url
        client = AsyncOpenAI(**client_kwargs)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, context)},
        ]
        response = await self._create_chat_completion(client, provider.model, messages)
        payload = parse_answer_payload(message_content(response))
        used = {normalize_citation_id(item) for item in payload.get("used_citations") or []}
        filtered_citations = [
            citation for citation in citations if normalize_citation_id(citation.get("citation_id")) in used
        ] or citations[:2]

        usage = usage_from_response(
            response=response,
            input_cost_per_1m_tokens=self.settings.input_cost_per_1m_tokens,
            output_cost_per_1m_tokens=self.settings.output_cost_per_1m_tokens,
        )
        no_answer = coerce_bool(payload.get("no_answer"), default=False)

        return GeneratedAnswer(
            answer=str(payload["answer"]),
            no_answer=no_answer,
            confidence=coerce_confidence(payload.get("confidence"), default=0.5),
            citations=[] if no_answer else filtered_citations,
            retrieval_trace=retrieval_trace,
            usage=usage,
        )

    async def _create_chat_completion(self, client: Any, model: str, messages: list[dict]) -> Any:
        request = {
            "model": model,
            "messages": messages,
            "temperature": 0,
        }
        try:
            return await client.chat.completions.create(
                **request,
                response_format={"type": "json_object"},
            )
        except Exception:
            return await client.chat.completions.create(**request)


def resolve_llm_provider(settings: Settings) -> LlmProviderConfig | None:
    provider = normalize_provider(settings.llm_provider)
    if provider in {"development", "dev", "local", "none"}:
        return None

    if provider == "openai":
        if not settings.openai_api_key:
            return None
        return LlmProviderConfig(
            name="openai",
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_chat_model,
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            return None
        return LlmProviderConfig(
            name="gemini",
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model=settings.gemini_chat_model,
        )

    if provider == "groq":
        if not settings.groq_api_key:
            return None
        return LlmProviderConfig(
            name="groq",
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            model=settings.groq_chat_model,
        )

    if provider in {"openai-compatible", "compatible", "custom"}:
        if not settings.openai_compatible_api_key:
            return None
        if not settings.openai_compatible_base_url or not settings.openai_compatible_chat_model:
            raise ValueError(
                "OPENAI_COMPATIBLE_BASE_URL and OPENAI_COMPATIBLE_CHAT_MODEL "
                "are required when LLM_PROVIDER=openai-compatible."
            )
        return LlmProviderConfig(
            name="openai-compatible",
            api_key=settings.openai_compatible_api_key,
            base_url=settings.openai_compatible_base_url,
            model=settings.openai_compatible_chat_model,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER={settings.llm_provider!r}.")


def citation_from_chunk(index: int, chunk: RetrievedChunk) -> dict:
    metadata = chunk.metadata or {}
    return {
        "citation_id": f"C{index}",
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "page": chunk.page,
        "chunk_id": chunk.chunk_id,
        "quote": chunk.text[:650],
        "score": chunk.score,
        "source_type": metadata.get("source_type"),
        "source_url": metadata.get("source_url"),
        "source_title": metadata.get("source_title"),
        "source_path": metadata.get("source_path"),
    }


def retrieved_chunk_to_dict(chunk: RetrievedChunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "page": chunk.page,
        "section": chunk.section,
        "text": chunk.text,
        "score": chunk.score,
        "metadata": chunk.metadata,
    }


def message_content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", "") if message else ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text") or ""))
            else:
                parts.append(str(getattr(part, "text", "") or ""))
        return "".join(parts)
    return str(content or "")


def parse_answer_payload(content: str) -> dict:
    text = content.strip()
    if not text:
        raise ValueError("LLM returned an empty answer.")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        payload = json.loads(text[start : end + 1])

    if not isinstance(payload, dict) or "answer" not in payload:
        raise ValueError("LLM answer must be a JSON object with an answer field.")
    return payload


def usage_from_response(
    *,
    response: Any,
    input_cost_per_1m_tokens: float,
    output_cost_per_1m_tokens: float,
) -> Usage:
    raw_usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(raw_usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(raw_usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(raw_usage, "total_tokens", prompt_tokens + completion_tokens) or 0)
    cost = estimate_cost_usd(
        prompt_tokens,
        completion_tokens,
        input_cost_per_1m_tokens,
        output_cost_per_1m_tokens,
    )
    return Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
    )


def normalize_citation_id(value: Any) -> str:
    return str(value or "").strip().strip("[]").upper()


def coerce_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return default


def coerce_confidence(value: Any, *, default: float) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = default
    return min(1.0, max(0.0, confidence))


def looks_vietnamese(text: str) -> bool:
    markers = (
        "\u0103\u00e2\u0111\u00ea\u00f4\u01a1\u01b0"
        "\u00e1\u00e0\u1ea3\u00e3\u1ea1\u1ea5\u1ea7\u1ea9\u1eab\u1ead"
        "\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7\u00e9\u00e8\u1ebb\u1ebd\u1eb9"
        "\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7\u00ed\u00ec\u1ec9\u0129\u1ecb"
        "\u00f3\u00f2\u1ecf\u00f5\u1ecd\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9"
        "\u1edb\u1edd\u1edf\u1ee1\u1ee3\u00fa\u00f9\u1ee7\u0169\u1ee5"
        "\u1ee9\u1eeb\u1eed\u1eef\u1ef1\u00fd\u1ef3\u1ef7\u1ef9\u1ef5"
    )
    lowered = text.lower()
    return any(char in lowered for char in markers)
