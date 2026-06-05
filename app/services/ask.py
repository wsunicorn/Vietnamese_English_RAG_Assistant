import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ChatResponse, UsageSummary
from app.core.config import Settings
from app.db.repository import ChatRepository
from app.generation.answerer import GroundedAnswerer
from app.retrieval.embeddings import EmbeddingClient
from app.retrieval.retriever import HybridRetriever
from app.retrieval.vector_store import QdrantHybridStore


class AskService:
    def __init__(
        self,
        *,
        settings: Settings,
        vector_store: QdrantHybridStore,
        embedding_client: EmbeddingClient,
    ):
        self.settings = settings
        self.vector_store = vector_store
        self.embedding_client = embedding_client

    async def ask(
        self,
        *,
        question: str,
        session: AsyncSession,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
        channel: str | None = None,
        user_id: str | None = None,
    ) -> ChatResponse:
        start = time.perf_counter()
        retriever = HybridRetriever(
            settings=self.settings,
            embedding_client=self.embedding_client,
            vector_store=self.vector_store,
        )
        retrieved = await retriever.retrieve(
            question=question,
            document_ids=document_ids,
            top_k=top_k,
        )
        generated = await GroundedAnswerer(self.settings).answer(question=question, retrieved=retrieved)
        latency_ms = int((time.perf_counter() - start) * 1000)

        chat_id = await ChatRepository(session).create_chat_log(
            question=question,
            answer=generated.answer,
            no_answer=generated.no_answer,
            confidence=generated.confidence,
            citations=generated.citations,
            retrieval_trace=generated.retrieval_trace,
            prompt_tokens=generated.usage.prompt_tokens,
            completion_tokens=generated.usage.completion_tokens,
            total_tokens=generated.usage.total_tokens,
            estimated_cost_usd=generated.usage.estimated_cost_usd,
            latency_ms=latency_ms,
        )

        if channel or user_id:
            await ChatRepository(session).add_request_context(
                chat_id=chat_id,
                metadata={"channel": channel, "user_id": user_id},
            )

        return ChatResponse(
            chat_id=chat_id,
            answer=generated.answer,
            citations=generated.citations,
            no_answer=generated.no_answer,
            confidence=generated.confidence,
            retrieval_trace=generated.retrieval_trace,
            usage=UsageSummary(
                prompt_tokens=generated.usage.prompt_tokens,
                completion_tokens=generated.usage.completion_tokens,
                total_tokens=generated.usage.total_tokens,
                estimated_cost_usd=float(generated.usage.estimated_cost_usd),
            ),
            latency_ms=latency_ms,
        )
