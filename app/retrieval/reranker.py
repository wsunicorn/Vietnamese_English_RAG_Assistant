from __future__ import annotations

import logging

import httpx

from app.core.config import Settings
from app.retrieval.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)


async def maybe_rerank(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    settings: Settings,
) -> list[RetrievedChunk]:
    provider = (settings.reranker_provider or "none").strip().lower()
    if not chunks or provider in {"", "none", "off", "disabled"}:
        return chunks
    if provider == "cohere":
        return await cohere_rerank(question=question, chunks=chunks, settings=settings)
    if provider == "cross-encoder":
        logger.warning("cross-encoder reranker is configured but not installed in v2; using hybrid order.")
        return chunks
    logger.warning("Unknown reranker provider %r; using hybrid order.", provider)
    return chunks


async def cohere_rerank(
    *,
    question: str,
    chunks: list[RetrievedChunk],
    settings: Settings,
) -> list[RetrievedChunk]:
    if not settings.cohere_api_key:
        logger.warning("COHERE_API_KEY is missing; using hybrid order.")
        return chunks

    model = settings.reranker_model or "rerank-v3.5"
    payload = {
        "model": model,
        "query": question,
        "documents": [chunk.text for chunk in chunks],
        "top_n": len(chunks),
    }
    headers = {
        "x-api-key": settings.cohere_api_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://api.cohere.com/v2/rerank", json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    ranked = []
    for result in data.get("results", []):
        index = int(result.get("index", -1))
        if 0 <= index < len(chunks):
            chunk = chunks[index]
            chunk.score = float(result.get("relevance_score", chunk.score))
            ranked.append(chunk)
    return ranked or chunks
