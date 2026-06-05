import asyncio
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.repository import DataSourceRepository, DocumentRepository, SyncJobRepository
from app.db.session import get_session_factory, init_db
from app.ingestion.web import fetch_web_documents
from app.retrieval.embeddings import create_embedding_client
from app.retrieval.vector_store import QdrantHybridStore
from app.services.indexing import IndexingService
from app.services.jobs import JobQueue
from app.services.realtime import publish_event

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_db()
    queue = JobQueue(settings)
    session_factory = get_session_factory()
    last_schedule_check = 0.0

    logger.info("RAG worker started.")
    while True:
        processed_job = False
        job_id = await queue.dequeue(timeout=settings.worker_poll_seconds)
        async with session_factory() as session:
            if job_id is None:
                job = await SyncJobRepository(session).next_queued_job()
                job_id = job.id if job else None
            if job_id:
                await process_job(job_id)
                processed_job = True

            now = asyncio.get_running_loop().time()
            if now - last_schedule_check >= settings.scheduled_sync_check_seconds:
                await enqueue_due_sources(queue)
                last_schedule_check = now
        if not processed_job:
            await asyncio.sleep(settings.worker_poll_seconds)


async def enqueue_due_sources(queue: JobQueue) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        source_repository = DataSourceRepository(session)
        job_repository = SyncJobRepository(session)
        for source in await source_repository.sources_due_for_sync():
            if await job_repository.has_active_source_job(source.id):
                continue
            job = await job_repository.create_job(
                job_type="source_sync",
                source_id=source.id,
                payload={"reason": "scheduled"},
            )
            await queue.enqueue(job.id)
            await publish_event(
                get_settings(),
                "source.sync_queued",
                source_id=source.id,
                job_id=job.id,
                reason="scheduled",
                refresh=["sources", "metrics"],
            )


async def process_job(job_id: str) -> None:
    session_factory = get_session_factory()
    settings = get_settings()
    async with session_factory() as session:
        job_repository = SyncJobRepository(session)
        job = await job_repository.get_job(job_id)
        if job is None or job.status != "queued":
            return
        await job_repository.mark_running(job_id)
        await publish_event(
            settings,
            "job.running",
            job_id=job.id,
            job_type=job.job_type,
            source_id=job.source_id,
            refresh=["sources", "metrics"],
        )

    try:
        async with session_factory() as session:
            job = await SyncJobRepository(session).get_job(job_id)
            if job is None:
                return
            if job.job_type == "source_sync":
                await sync_source(job_id, job.source_id)
            elif job.job_type == "reindex_all":
                await enqueue_reindex_all(job_id)
            else:
                raise ValueError(f"Unsupported job type: {job.job_type}")

        async with session_factory() as session:
            await SyncJobRepository(session).mark_complete(job_id)
            job = await SyncJobRepository(session).get_job(job_id)
            await publish_event(
                settings,
                "job.completed",
                job_id=job_id,
                job_type=job.job_type if job else None,
                source_id=job.source_id if job else None,
                refresh=["documents", "sources", "metrics"],
            )
    except Exception as exc:
        logger.exception("Job failed. job_id=%s", job_id)
        async with session_factory() as session:
            await SyncJobRepository(session).mark_failed(job_id, str(exc))
            job = await SyncJobRepository(session).get_job(job_id)
            if job and job.source_id:
                await DataSourceRepository(session).update_source_status(
                    job.source_id,
                    status="failed",
                    error=str(exc),
                )
            await publish_event(
                settings,
                "job.failed",
                job_id=job_id,
                job_type=job.job_type if job else None,
                source_id=job.source_id if job else None,
                error=str(exc),
                refresh=["sources", "metrics"],
            )


async def sync_source(job_id: str, source_id: str | None) -> None:
    if not source_id:
        raise ValueError("source_sync job requires source_id.")

    settings = get_settings()
    session_factory = get_session_factory()
    vector_store = QdrantHybridStore(settings)
    embedding_client = create_embedding_client(settings)
    indexing = IndexingService(
        settings=settings,
        vector_store=vector_store,
        embedding_client=embedding_client,
    )

    async with session_factory() as session:
        source_repository = DataSourceRepository(session)
        source = await source_repository.get_source(source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found.")
        await source_repository.update_source_status(source_id, status="running", error=None)
        metadata = source.metadata_json or {}
        await publish_event(
            settings,
            "source.running",
            source_id=source_id,
            source_type=source.source_type,
            refresh=["sources", "metrics"],
        )

    if source.source_type in {"web", "sitemap"}:
        parsed_documents = await fetch_web_documents(
            url=str(source.uri),
            mode=str(metadata.get("mode") or source.source_type),
            max_pages=int(metadata.get("max_pages") or settings.web_ingest_max_pages),
            settings=settings,
        )
        file_path = str(source.uri or "")
        content_type = "text/html"
    else:
        file_path = str(metadata.get("file_path") or source.uri or "")
        if not file_path:
            raise ValueError(f"Source {source_id} has no file path to reindex.")
        path = Path(file_path)
        parsed_documents = await indexing.parse_file(
            path,
            filename=path.name,
            content_type=str(metadata.get("content_type") or "application/octet-stream"),
        )
        content_type = str(metadata.get("content_type") or "application/octet-stream")

    async with session_factory() as session:
        document_repository = DocumentRepository(session)
        try:
            await vector_store.delete_source(source_id)
        except Exception:
            pass
        await document_repository.delete_documents_for_source(source_id)
        indexed = await indexing.index_parsed_documents(
            session=session,
            parsed_documents=parsed_documents,
            source_id=source_id,
            file_path=file_path,
            content_type=content_type,
            default_source_type=source.source_type,
            sync_run_id=job_id,
            metadata_extra={"source_name": source.name},
        )
        await DataSourceRepository(session).update_source_status(
            source_id,
            status="indexed",
            error=None,
            synced=True,
        )
        logger.info("Indexed source. source_id=%s documents=%s", source_id, len(indexed))
        await publish_event(
            settings,
            "source.indexed",
            source_id=source_id,
            source_type=source.source_type,
            document_count=len(indexed),
            chunk_count=sum(item.chunk_count for item in indexed),
            refresh=["documents", "sources", "metrics"],
        )


async def enqueue_reindex_all(job_id: str) -> None:
    settings = get_settings()
    queue = JobQueue(settings)
    session_factory = get_session_factory()
    async with session_factory() as session:
        source_repository = DataSourceRepository(session)
        job_repository = SyncJobRepository(session)
        for row in await source_repository.list_sources():
            source = row["source"]
            if await job_repository.has_active_source_job(source.id):
                continue
            job = await job_repository.create_job(
                job_type="source_sync",
                source_id=source.id,
                payload={"reason": "reindex_all", "parent_job_id": job_id},
            )
            await queue.enqueue(job.id)
            await publish_event(
                settings,
                "source.sync_queued",
                source_id=source.id,
                job_id=job.id,
                reason="reindex_all",
                refresh=["sources", "metrics"],
            )


if __name__ == "__main__":
    asyncio.run(main())
