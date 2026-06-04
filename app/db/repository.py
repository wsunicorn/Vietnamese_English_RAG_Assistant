from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatLogORM, ChunkORM, DocumentORM, FeedbackORM, RequestMetricORM, now_utc


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str,
        source_type: str,
        file_path: str,
    ) -> DocumentORM:
        document = DocumentORM(
            id=document_id,
            filename=filename,
            content_type=content_type,
            source_type=source_type,
            status="processing",
            file_path=file_path,
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def mark_document_indexed(
        self,
        document_id: str,
        *,
        language: str | None,
        page_count: int,
        chunk_count: int,
        metadata: dict,
    ) -> None:
        document = await self.session.get(DocumentORM, document_id)
        if document is None:
            return
        document.status = "indexed"
        document.language = language
        document.page_count = page_count
        document.chunk_count = chunk_count
        document.metadata_json = metadata
        document.updated_at = now_utc()
        await self.session.commit()

    async def mark_document_failed(self, document_id: str, error: str) -> None:
        document = await self.session.get(DocumentORM, document_id)
        if document is None:
            return
        document.status = "failed"
        document.metadata_json = {**(document.metadata_json or {}), "error": error[:1000]}
        document.updated_at = now_utc()
        await self.session.commit()

    async def add_chunks(self, chunks: list[dict]) -> None:
        for chunk in chunks:
            self.session.add(ChunkORM(**chunk))
        await self.session.commit()

    async def list_documents(self) -> list[DocumentORM]:
        result = await self.session.execute(select(DocumentORM).order_by(DocumentORM.created_at.desc()))
        return list(result.scalars().all())

    async def delete_document(self, document_id: str) -> bool:
        result = await self.session.execute(delete(DocumentORM).where(DocumentORM.id == document_id))
        await self.session.commit()
        return bool(result.rowcount)


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chat_log(
        self,
        *,
        question: str,
        answer: str,
        no_answer: bool,
        confidence: float,
        citations: list[dict],
        retrieval_trace: list[dict],
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost_usd: Decimal,
        latency_ms: int,
    ) -> str:
        chat_id = str(uuid4())
        self.session.add(
            ChatLogORM(
                id=chat_id,
                question=question,
                answer=answer,
                no_answer=no_answer,
                confidence=confidence,
                citations=citations,
                retrieval_trace=retrieval_trace,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost_usd,
                latency_ms=latency_ms,
            )
        )
        self.session.add(
            RequestMetricORM(
                id=str(uuid4()),
                endpoint="/chat",
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost_usd,
                metadata_json={"no_answer": no_answer, "confidence": confidence},
            )
        )
        await self.session.commit()
        return chat_id

    async def add_feedback(
        self,
        *,
        chat_id: str | None,
        rating: int,
        comment: str | None,
        correction: str | None,
    ) -> str:
        feedback_id = str(uuid4())
        self.session.add(
            FeedbackORM(
                id=feedback_id,
                chat_id=chat_id,
                rating=rating,
                comment=comment,
                correction=correction,
            )
        )
        await self.session.commit()
        return feedback_id

    async def metrics_summary(self) -> dict:
        documents = await self.session.scalar(select(func.count(DocumentORM.id)))
        chunks = await self.session.scalar(select(func.count(ChunkORM.id)))
        chats = await self.session.scalar(select(func.count(ChatLogORM.id)))
        feedback = await self.session.scalar(select(func.count(FeedbackORM.id)))
        avg_latency = await self.session.scalar(select(func.avg(ChatLogORM.latency_ms)))
        total_tokens = await self.session.scalar(select(func.coalesce(func.sum(ChatLogORM.total_tokens), 0)))
        total_cost = await self.session.scalar(
            select(func.coalesce(func.sum(ChatLogORM.estimated_cost_usd), 0))
        )
        return {
            "documents": documents or 0,
            "chunks": chunks or 0,
            "chats": chats or 0,
            "feedback": feedback or 0,
            "avg_chat_latency_ms": int(avg_latency or 0),
            "total_tokens": int(total_tokens or 0),
            "estimated_cost_usd": float(total_cost or 0),
        }
