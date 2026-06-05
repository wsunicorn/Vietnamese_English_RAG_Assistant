from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repository import DataSourceRepository, DocumentRepository
from app.ingestion.chunking import ParsedDocument
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.embeddings import EmbeddingClient
from app.retrieval.vector_store import QdrantHybridStore


@dataclass(slots=True)
class IndexedDocument:
    document_id: str
    filename: str
    status: str
    page_count: int
    chunk_count: int
    metadata: dict


class IndexingService:
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
        self.pipeline = IngestionPipeline(settings)

    async def parse_file(self, path: Path, *, filename: str, content_type: str) -> list[ParsedDocument]:
        return self.pipeline.parse_many(path, filename=filename, content_type=content_type)

    async def index_parsed_documents(
        self,
        *,
        session: AsyncSession,
        parsed_documents: list[ParsedDocument],
        source_id: str | None,
        file_path: str,
        content_type: str,
        default_source_type: str,
        sync_run_id: str | None = None,
        metadata_extra: dict | None = None,
    ) -> list[IndexedDocument]:
        repository = DocumentRepository(session)
        indexed: list[IndexedDocument] = []

        for parsed in parsed_documents:
            document_id = str(uuid4())
            source_type = parsed.metadata.get("source_type") or default_source_type
            metadata = {
                **parsed.metadata,
                **(metadata_extra or {}),
                "source_id": source_id,
                "source_type": source_type,
            }
            if sync_run_id:
                metadata["sync_run_id"] = sync_run_id

            await repository.create_document(
                document_id=document_id,
                filename=parsed.filename,
                content_type=str(metadata.get("content_type") or content_type),
                source_type=source_type,
                source_id=source_id,
                file_path=file_path,
            )

            try:
                enriched = ParsedDocument(
                    filename=parsed.filename,
                    pages=parsed.pages,
                    metadata=metadata,
                    language=parsed.language,
                )
                chunks = self.pipeline.chunk_parsed(document_id=document_id, parsed=enriched)
                dense_vectors = await self.embedding_client.embed_texts([chunk.text for chunk in chunks])
                vector_size = len(dense_vectors[0]) if dense_vectors else self.settings.embedding_dimensions
                await self.vector_store.ensure_collection(vector_size=vector_size)
                await self.vector_store.upsert_chunks(chunks, dense_vectors)
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
                await repository.mark_document_indexed(
                    document_id,
                    language=parsed.language,
                    page_count=len(parsed.pages),
                    chunk_count=len(chunks),
                    metadata=metadata,
                )
                indexed.append(
                    IndexedDocument(
                        document_id=document_id,
                        filename=parsed.filename,
                        status="indexed",
                        page_count=len(parsed.pages),
                        chunk_count=len(chunks),
                        metadata=metadata,
                    )
                )
            except Exception as exc:
                await repository.mark_document_failed(document_id, str(exc))
                raise

        if source_id:
            total_chunks = sum(item.chunk_count for item in indexed)
            await DataSourceRepository(session).update_source_metadata(
                source_id,
                {"document_count": len(indexed), "chunk_count": total_chunks},
            )
        return indexed
