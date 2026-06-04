import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentListItem,
    DocumentUploadResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    MetricsResponse,
    UsageSummary,
)
from app.core.config import Settings, get_settings
from app.db.repository import ChatRepository, DocumentRepository
from app.db.session import get_session
from app.generation.answerer import GroundedAnswerer
from app.ingestion.parsers import SUPPORTED_EXTENSIONS
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.embeddings import EmbeddingClient, create_embedding_client
from app.retrieval.retriever import HybridRetriever
from app.retrieval.vector_store import QdrantHybridStore

router = APIRouter()


def get_vector_store(settings: Settings = Depends(get_settings)) -> QdrantHybridStore:
    return QdrantHybridStore(settings)


def get_embedding_client(settings: Settings = Depends(get_settings)) -> EmbeddingClient:
    return create_embedding_client(settings)


@router.get("/healthz", response_model=HealthResponse, tags=["system"])
async def healthz(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, environment=settings.environment)


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

    document_id = str(uuid4())
    safe_name = Path(file.filename or f"document{extension}").name
    target_path = settings.upload_dir / f"{document_id}_{safe_name}"

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

    repository = DocumentRepository(session)
    await repository.create_document(
        document_id=document_id,
        filename=safe_name,
        content_type=file.content_type or "application/octet-stream",
        source_type=extension.removeprefix("."),
        file_path=str(target_path),
    )

    try:
        pipeline = IngestionPipeline(settings)
        parsed, chunks = pipeline.parse_and_chunk(
            target_path,
            document_id=document_id,
            filename=safe_name,
            content_type=file.content_type or "application/octet-stream",
        )
        dense_vectors = await embedding_client.embed_texts([chunk.text for chunk in chunks])
        vector_size = len(dense_vectors[0]) if dense_vectors else settings.embedding_dimensions
        await vector_store.ensure_collection(vector_size=vector_size)
        await vector_store.upsert_chunks(chunks, dense_vectors)
        await repository.add_chunks(
            [
                {
                    "id": chunk.id,
                    "document_id": document_id,
                    "qdrant_point_id": chunk.point_id,
                    "page": chunk.page,
                    "section": chunk.section,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                    "metadata_json": chunk.metadata,
                }
                for chunk in chunks
            ]
        )
        metadata = {
            **parsed.metadata,
            "bytes": bytes_written,
            "original_filename": safe_name,
        }
        await repository.mark_document_indexed(
            document_id,
            language=parsed.language,
            page_count=len(parsed.pages),
            chunk_count=len(chunks),
            metadata=metadata,
        )
    except Exception as exc:
        await repository.mark_document_failed(document_id, str(exc))
        raise HTTPException(status_code=500, detail=f"Document indexing failed: {exc}") from exc

    return DocumentUploadResponse(
        document_id=document_id,
        filename=safe_name,
        status="indexed",
        page_count=len(parsed.pages),
        chunk_count=len(chunks),
        metadata=metadata,
    )


@router.get("/documents", response_model=list[DocumentListItem], tags=["documents"])
async def list_documents(session: AsyncSession = Depends(get_session)) -> list[DocumentListItem]:
    repository = DocumentRepository(session)
    documents = await repository.list_documents()
    return [
        DocumentListItem(
            document_id=document.id,
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


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    vector_store: QdrantHybridStore = Depends(get_vector_store),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> ChatResponse:
    start = time.perf_counter()
    retriever = HybridRetriever(
        settings=settings,
        embedding_client=embedding_client,
        vector_store=vector_store,
    )
    retrieved = await retriever.retrieve(
        question=request.question,
        document_ids=request.document_ids,
        top_k=request.top_k,
    )
    generated = await GroundedAnswerer(settings).answer(question=request.question, retrieved=retrieved)
    latency_ms = int((time.perf_counter() - start) * 1000)

    chat_id = await ChatRepository(session).create_chat_log(
        question=request.question,
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
    return FeedbackResponse(feedback_id=feedback_id)


@router.get("/metrics", response_model=MetricsResponse, tags=["system"])
async def metrics(session: AsyncSession = Depends(get_session)) -> MetricsResponse:
    summary = await ChatRepository(session).metrics_summary()
    return MetricsResponse(**summary)
