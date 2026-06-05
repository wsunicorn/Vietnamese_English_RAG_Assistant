from pathlib import Path
from asyncio import sleep
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentListItem,
    DocumentUploadResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    JobResponse,
    MetricsResponse,
    SourceListItem,
    UrlIngestionRequest,
)
from app.core.config import Settings, get_settings
from app.db.repository import ChatRepository, DataSourceRepository, DocumentRepository, SyncJobRepository
from app.db.session import get_session
from app.ingestion.parsers import SUPPORTED_EXTENSIONS
from app.ingestion.web import normalize_url
from app.retrieval.embeddings import EmbeddingClient, create_embedding_client
from app.retrieval.vector_store import QdrantHybridStore
from app.services.ask import AskService
from app.services.indexing import IndexingService
from app.services.jobs import JobQueue
from app.services.realtime import iter_events, publish_event, realtime_payload

router = APIRouter()


def get_vector_store(settings: Settings = Depends(get_settings)) -> QdrantHybridStore:
    return QdrantHybridStore(settings)


def get_embedding_client(settings: Settings = Depends(get_settings)) -> EmbeddingClient:
    return create_embedding_client(settings)


@router.get("/healthz", response_model=HealthResponse, tags=["system"])
async def healthz(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, environment=settings.environment)


@router.websocket("/ws/realtime")
async def realtime_socket(websocket: WebSocket, settings: Settings = Depends(get_settings)) -> None:
    await websocket.accept()
    await websocket.send_json(realtime_payload("connected", message="Realtime channel ready."))
    try:
        try:
            async for event in iter_events(settings):
                await websocket.send_json(event)
        except Exception as exc:
            await websocket.send_json(
                realtime_payload(
                    "realtime.degraded",
                    message="Redis pub/sub is unavailable; realtime updates are paused.",
                    error=str(exc),
                )
            )
            while True:
                await sleep(20)
                await websocket.send_json(realtime_payload("heartbeat"))
    except WebSocketDisconnect:
        return


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    vector_store: QdrantHybridStore = Depends(get_vector_store),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> DocumentUploadResponse:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only {', '.join(sorted(SUPPORTED_EXTENSIONS))} files are supported.",
        )

    safe_name = Path(file.filename or f"document{extension}").name
    source_type = source_type_from_extension(extension)
    target_path = settings.upload_dir / f"{uuid4()}_{safe_name}"

    bytes_written = 0
    with target_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > settings.max_file_bytes:
                target_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds {settings.max_file_mb} MB limit.",
                )
            output.write(chunk)

    source_repository = DataSourceRepository(session)
    source = await source_repository.create_source(
        name=safe_name,
        source_type=source_type,
        uri=str(target_path),
        metadata={
            "file_path": str(target_path),
            "content_type": file.content_type or "application/octet-stream",
            "original_filename": safe_name,
            "bytes": bytes_written,
        },
        status="running",
    )

    try:
        indexing = IndexingService(
            settings=settings,
            vector_store=vector_store,
            embedding_client=embedding_client,
        )
        parsed_documents = await indexing.parse_file(
            target_path,
            filename=safe_name,
            content_type=file.content_type or "application/octet-stream",
        )
        metadata = {
            "bytes": bytes_written,
            "original_filename": safe_name,
            "source_id": source.id,
            "source_type": source_type,
        }
        indexed = await indexing.index_parsed_documents(
            session=session,
            parsed_documents=parsed_documents,
            source_id=source.id,
            file_path=str(target_path),
            content_type=file.content_type or "application/octet-stream",
            default_source_type=source_type,
            metadata_extra=metadata,
        )
        await source_repository.update_source_status(source.id, status="indexed", synced=True)
    except Exception as exc:
        await source_repository.update_source_status(source.id, status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Document indexing failed: {exc}") from exc

    total_pages = sum(item.page_count for item in indexed)
    total_chunks = sum(item.chunk_count for item in indexed)
    first = indexed[0]

    response = DocumentUploadResponse(
        document_id=first.document_id,
        source_id=source.id,
        filename=safe_name,
        status="indexed",
        page_count=total_pages,
        chunk_count=total_chunks,
        documents=[
            {
                "document_id": item.document_id,
                "filename": item.filename,
                "page_count": item.page_count,
                "chunk_count": item.chunk_count,
            }
            for item in indexed
        ],
        metadata=metadata,
    )
    await publish_event(
        settings,
        "document.uploaded",
        source_id=source.id,
        document_id=first.document_id,
        filename=safe_name,
        chunk_count=total_chunks,
        refresh=["documents", "sources", "metrics"],
    )
    return response


@router.get("/documents", response_model=list[DocumentListItem], tags=["documents"])
async def list_documents(session: AsyncSession = Depends(get_session)) -> list[DocumentListItem]:
    repository = DocumentRepository(session)
    documents = await repository.list_documents()
    return [
        DocumentListItem(
            document_id=document.id,
            source_id=document.source_id,
            source_type=document.source_type,
            filename=document.filename,
            content_type=document.content_type,
            status=document.status,
            language=document.language,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
        )
        for document in documents
    ]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["documents"])
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    vector_store: QdrantHybridStore = Depends(get_vector_store),
) -> None:
    try:
        await vector_store.delete_document(document_id)
    except Exception:
        pass

    repository = DocumentRepository(session)
    deleted = await repository.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    await publish_event(
        get_settings(),
        "document.deleted",
        document_id=document_id,
        refresh=["documents", "sources", "metrics"],
    )


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    vector_store: QdrantHybridStore = Depends(get_vector_store),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> ChatResponse:
    service = AskService(
        settings=settings,
        vector_store=vector_store,
        embedding_client=embedding_client,
    )
    response = await service.ask(
        question=request.question,
        session=session,
        document_ids=request.document_ids,
        top_k=request.top_k,
    )
    await publish_event(
        settings,
        "chat.completed",
        chat_id=response.chat_id,
        no_answer=response.no_answer,
        citation_count=len(response.citations),
        latency_ms=response.latency_ms,
        refresh=["metrics"],
    )
    return response


@router.post("/feedback", response_model=FeedbackResponse, tags=["feedback"])
async def feedback(
    request: FeedbackRequest,
    session: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    feedback_id = await ChatRepository(session).add_feedback(
        chat_id=request.chat_id,
        rating=request.rating,
        comment=request.comment,
        correction=request.correction,
    )
    await publish_event(
        get_settings(),
        "feedback.stored",
        feedback_id=feedback_id,
        chat_id=request.chat_id,
        rating=request.rating,
        refresh=["metrics"],
    )
    return FeedbackResponse(feedback_id=feedback_id)


@router.get("/metrics", response_model=MetricsResponse, tags=["system"])
async def metrics(session: AsyncSession = Depends(get_session)) -> MetricsResponse:
    summary = await ChatRepository(session).metrics_summary()
    return MetricsResponse(**summary)


@router.post("/documents/ingest-url", response_model=JobResponse, tags=["documents"])
async def ingest_url(
    request: UrlIngestionRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> JobResponse:
    url = normalize_url(request.url)
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Only HTTP and HTTPS URLs are supported.")

    source_type = "sitemap" if request.mode == "sitemap" else "web"
    source = await DataSourceRepository(session).create_source(
        name=url,
        source_type=source_type,
        uri=url,
        sync_interval_minutes=request.sync_interval_minutes,
        metadata={"mode": request.mode, "max_pages": request.max_pages},
        status="queued",
    )
    job = await SyncJobRepository(session).create_job(
        job_type="source_sync",
        source_id=source.id,
        payload={"url": url, "mode": request.mode, "max_pages": request.max_pages},
    )
    await JobQueue(settings).enqueue(job.id)
    await publish_event(
        settings,
        "source.queued",
        source_id=source.id,
        job_id=job.id,
        source_type=source_type,
        url=url,
        refresh=["sources", "metrics"],
    )
    return JobResponse(source_id=source.id, status=source.status, queued_job_id=job.id)


@router.get("/sources", response_model=list[SourceListItem], tags=["sources"])
async def list_sources(session: AsyncSession = Depends(get_session)) -> list[SourceListItem]:
    rows = await DataSourceRepository(session).list_sources()
    return [
        SourceListItem(
            source_id=row["source"].id,
            name=row["source"].name,
            source_type=row["source"].source_type,
            uri=row["source"].uri,
            status=row["source"].status,
            sync_interval_minutes=row["source"].sync_interval_minutes,
            last_synced_at=row["source"].last_synced_at,
            last_error=row["source"].last_error,
            document_count=row["document_count"],
            chunk_count=row["chunk_count"],
            metadata=row["source"].metadata_json or {},
            created_at=row["source"].created_at,
        )
        for row in rows
    ]


@router.post("/sources/{source_id}/sync", response_model=JobResponse, tags=["sources"])
async def sync_source(
    source_id: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> JobResponse:
    source = await DataSourceRepository(session).get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    job = await SyncJobRepository(session).create_job(
        job_type="source_sync",
        source_id=source_id,
        payload={"reason": "manual"},
    )
    await DataSourceRepository(session).update_source_status(source_id, status="queued", error=None)
    await JobQueue(settings).enqueue(job.id)
    await publish_event(
        settings,
        "source.sync_queued",
        source_id=source_id,
        job_id=job.id,
        refresh=["sources", "metrics"],
    )
    return JobResponse(source_id=source_id, status="queued", queued_job_id=job.id)


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["sources"])
async def delete_source(
    source_id: str,
    session: AsyncSession = Depends(get_session),
    vector_store: QdrantHybridStore = Depends(get_vector_store),
) -> None:
    source_repository = DataSourceRepository(session)
    source = await source_repository.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    try:
        await vector_store.delete_source(source_id)
    except Exception:
        pass
    await DocumentRepository(session).delete_documents_for_source(source_id)
    deleted = await source_repository.delete_source(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found.")
    await publish_event(
        get_settings(),
        "source.deleted",
        source_id=source_id,
        refresh=["documents", "sources", "metrics"],
    )


@router.post("/reindex", response_model=JobResponse, tags=["sources"])
async def reindex_all(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> JobResponse:
    job = await SyncJobRepository(session).create_job(job_type="reindex_all", payload={"scope": "all"})
    await JobQueue(settings).enqueue(job.id)
    await publish_event(
        settings,
        "reindex.queued",
        job_id=job.id,
        refresh=["sources", "metrics"],
    )
    return JobResponse(source_id=None, status="queued", queued_job_id=job.id)


@router.post("/bots/slack/ask", tags=["bots"])
async def slack_ask(
    text: str = Form(default=""),
    user_id: str | None = Form(default=None),
    token: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    vector_store: QdrantHybridStore = Depends(get_vector_store),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> dict:
    if settings.slack_verification_token and token != settings.slack_verification_token:
        raise HTTPException(status_code=401, detail="Invalid Slack verification token.")
    question = text.strip()
    if not question:
        return {"response_type": "ephemeral", "text": "Usage: /ask your question"}
    service = AskService(
        settings=settings,
        vector_store=vector_store,
        embedding_client=embedding_client,
    )
    answer = await service.ask(
        question=question,
        session=session,
        channel="slack",
        user_id=user_id,
    )
    return {"response_type": "in_channel", "text": format_bot_answer(answer)}


def source_type_from_extension(extension: str) -> str:
    if extension in {".md", ".markdown"}:
        return "markdown"
    if extension == ".zip":
        return "notion"
    return extension.removeprefix(".")


def format_bot_answer(answer: ChatResponse) -> str:
    citations = []
    for citation in answer.citations[:3]:
        label = citation.source_url or citation.source_path or citation.filename
        citations.append(f"[{citation.citation_id}] {label}")
    suffix = "\n\nSources:\n" + "\n".join(citations) if citations else ""
    return f"{answer.answer}{suffix}"
