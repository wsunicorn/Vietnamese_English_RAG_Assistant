from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ChatLogORM,
    ChunkORM,
    DataSourceORM,
    DocumentORM,
    FeedbackORM,
    RequestMetricORM,
    SyncJobORM,
    now_utc,
)


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
        source_id: str | None = None,
    ) -> DocumentORM:
        document = DocumentORM(
            id=document_id,
            filename=filename,
            content_type=content_type,
            source_type=source_type,
            source_id=source_id,
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

    async def document_ids_for_source(self, source_id: str) -> list[str]:
        result = await self.session.execute(select(DocumentORM.id).where(DocumentORM.source_id == source_id))
        return list(result.scalars().all())

    async def delete_documents_for_source(self, source_id: str) -> int:
        result = await self.session.execute(delete(DocumentORM).where(DocumentORM.source_id == source_id))
        await self.session.commit()
        return int(result.rowcount or 0)


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

    async def add_request_context(self, *, chat_id: str, metadata: dict) -> None:
        self.session.add(
            RequestMetricORM(
                id=str(uuid4()),
                endpoint="/chat/context",
                metadata_json={"chat_id": chat_id, **metadata},
            )
        )
        await self.session.commit()

    async def metrics_summary(self) -> dict:
        documents = await self.session.scalar(select(func.count(DocumentORM.id)))
        chunks = await self.session.scalar(select(func.count(ChunkORM.id)))
        chats = await self.session.scalar(select(func.count(ChatLogORM.id)))
        feedback = await self.session.scalar(select(func.count(FeedbackORM.id)))
        sources = await self.session.scalar(select(func.count(DataSourceORM.id)))
        queued_jobs = await self.session.scalar(
            select(func.count(SyncJobORM.id)).where(SyncJobORM.status == "queued")
        )
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
            "sources": sources or 0,
            "queued_jobs": queued_jobs or 0,
            "avg_chat_latency_ms": int(avg_latency or 0),
            "total_tokens": int(total_tokens or 0),
            "estimated_cost_usd": float(total_cost or 0),
        }


class DataSourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_source(
        self,
        *,
        name: str,
        source_type: str,
        uri: str | None,
        sync_interval_minutes: int | None = None,
        metadata: dict | None = None,
        status: str = "queued",
    ) -> DataSourceORM:
        source = DataSourceORM(
            id=str(uuid4()),
            name=name,
            source_type=source_type,
            uri=uri,
            status=status,
            sync_interval_minutes=sync_interval_minutes,
            metadata_json=metadata or {},
        )
        self.session.add(source)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def get_source(self, source_id: str) -> DataSourceORM | None:
        return await self.session.get(DataSourceORM, source_id)

    async def list_sources(self) -> list[dict]:
        document_count = func.count(func.distinct(DocumentORM.id))
        chunk_count = func.count(ChunkORM.id)
        result = await self.session.execute(
            select(DataSourceORM, document_count, chunk_count)
            .outerjoin(DocumentORM, DocumentORM.source_id == DataSourceORM.id)
            .outerjoin(ChunkORM, ChunkORM.document_id == DocumentORM.id)
            .group_by(DataSourceORM.id)
            .order_by(DataSourceORM.created_at.desc())
        )
        rows = []
        for source, documents, chunks in result.all():
            rows.append(
                {
                    "source": source,
                    "document_count": int(documents or 0),
                    "chunk_count": int(chunks or 0),
                }
            )
        return rows

    async def update_source_status(
        self,
        source_id: str,
        *,
        status: str,
        error: str | None = None,
        synced: bool = False,
    ) -> None:
        source = await self.get_source(source_id)
        if source is None:
            return
        source.status = status
        source.last_error = error
        source.updated_at = now_utc()
        if synced:
            source.last_synced_at = now_utc()
        await self.session.commit()

    async def update_source_metadata(self, source_id: str, metadata: dict) -> None:
        source = await self.get_source(source_id)
        if source is None:
            return
        source.metadata_json = {**(source.metadata_json or {}), **metadata}
        source.updated_at = now_utc()
        await self.session.commit()

    async def delete_source(self, source_id: str) -> bool:
        result = await self.session.execute(delete(DataSourceORM).where(DataSourceORM.id == source_id))
        await self.session.commit()
        return bool(result.rowcount)

    async def sources_due_for_sync(self) -> list[DataSourceORM]:
        result = await self.session.execute(
            select(DataSourceORM).where(
                DataSourceORM.sync_interval_minutes.is_not(None),
                DataSourceORM.status.in_(["indexed", "failed"]),
            )
        )
        now = now_utc()
        due = []
        for source in result.scalars().all():
            if source.last_synced_at is None:
                due.append(source)
                continue
            elapsed = (now - source.last_synced_at).total_seconds() / 60
            if elapsed >= (source.sync_interval_minutes or 0):
                due.append(source)
        return due


class SyncJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(
        self,
        *,
        job_type: str,
        source_id: str | None = None,
        payload: dict | None = None,
        status: str = "queued",
    ) -> SyncJobORM:
        job = SyncJobORM(
            id=str(uuid4()),
            job_type=job_type,
            source_id=source_id,
            payload_json=payload or {},
            status=status,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> SyncJobORM | None:
        return await self.session.get(SyncJobORM, job_id)

    async def mark_running(self, job_id: str) -> None:
        await self.session.execute(
            update(SyncJobORM)
            .where(SyncJobORM.id == job_id)
            .values(status="running", started_at=now_utc(), error=None)
        )
        await self.session.commit()

    async def mark_complete(self, job_id: str) -> None:
        await self.session.execute(
            update(SyncJobORM)
            .where(SyncJobORM.id == job_id)
            .values(status="completed", completed_at=now_utc(), error=None)
        )
        await self.session.commit()

    async def mark_failed(self, job_id: str, error: str) -> None:
        await self.session.execute(
            update(SyncJobORM)
            .where(SyncJobORM.id == job_id)
            .values(status="failed", completed_at=now_utc(), error=error[:2000])
        )
        await self.session.commit()

    async def next_queued_job(self) -> SyncJobORM | None:
        result = await self.session.execute(
            select(SyncJobORM).where(SyncJobORM.status == "queued").order_by(SyncJobORM.created_at)
        )
        return result.scalars().first()

    async def has_active_source_job(self, source_id: str) -> bool:
        result = await self.session.execute(
            select(func.count(SyncJobORM.id)).where(
                SyncJobORM.source_id == source_id,
                SyncJobORM.status.in_(["queued", "running"]),
            )
        )
        return bool(result.scalar() or 0)
