from dataclasses import dataclass

from app.core.config import Settings
from app.ingestion.chunking import DocumentChunk


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    text: str
    page: int | None
    section: str | None
    score: float
    metadata: dict


class QdrantHybridStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._sparse_model = None

    @property
    def client(self):
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key or None,
                timeout=30,
            )
        return self._client

    @property
    def sparse_model(self):
        if self._sparse_model is None:
            from fastembed import SparseTextEmbedding

            self._sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        return self._sparse_model

    async def ensure_collection(self, vector_size: int | None = None) -> None:
        from qdrant_client import models

        dense_size = vector_size or self.settings.embedding_dimensions
        existing = [collection.name for collection in self.client.get_collections().collections]
        if self.settings.qdrant_collection in existing:
            existing_size = self._existing_dense_vector_size()
            if existing_size and existing_size != dense_size:
                raise ValueError(
                    f"Qdrant collection {self.settings.qdrant_collection!r} uses dense vector "
                    f"size {existing_size}, but the current embedding provider returned {dense_size}. "
                    "Use the same embedding provider/model or recreate the collection."
                )
            return

        self.client.create_collection(
            collection_name=self.settings.qdrant_collection,
            vectors_config={
                self.settings.qdrant_dense_vector_name: models.VectorParams(
                    size=dense_size,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                self.settings.qdrant_sparse_vector_name: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            },
        )

    def _existing_dense_vector_size(self) -> int | None:
        try:
            collection = self.client.get_collection(self.settings.qdrant_collection)
            vectors = collection.config.params.vectors
            if isinstance(vectors, dict):
                dense_vector = vectors.get(self.settings.qdrant_dense_vector_name)
                return getattr(dense_vector, "size", None)
            return getattr(vectors, "size", None)
        except Exception:
            return None

    async def upsert_chunks(self, chunks: list[DocumentChunk], dense_vectors: list[list[float]]) -> None:
        from qdrant_client import models

        if not chunks:
            return

        sparse_vectors = list(self.sparse_model.embed([chunk.text for chunk in chunks]))
        points = []
        for chunk, dense_vector, sparse_vector in zip(chunks, dense_vectors, sparse_vectors, strict=True):
            points.append(
                models.PointStruct(
                    id=chunk.point_id,
                    vector={
                        self.settings.qdrant_dense_vector_name: dense_vector,
                        self.settings.qdrant_sparse_vector_name: models.SparseVector(
                            indices=sparse_vector.indices.tolist(),
                            values=sparse_vector.values.tolist(),
                        ),
                    },
                    payload={
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "filename": chunk.metadata.get("filename", ""),
                        "text": chunk.text,
                        "page": chunk.page,
                        "section": chunk.section,
                        "token_count": chunk.token_count,
                        "metadata": chunk.metadata,
                    },
                )
            )

        self.client.upsert(
            collection_name=self.settings.qdrant_collection,
            points=points,
            wait=True,
        )

    async def search(
        self,
        *,
        query: str,
        dense_vector: list[float],
        top_k: int,
        prefetch_limit: int,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        from qdrant_client import models

        sparse_query = next(iter(self.sparse_model.embed([query])))
        filters = None
        if document_ids:
            filters = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=document_ids),
                    )
                ]
            )

        result = self.client.query_points(
            collection_name=self.settings.qdrant_collection,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using=self.settings.qdrant_dense_vector_name,
                    limit=prefetch_limit,
                    filter=filters,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_query.indices.tolist(),
                        values=sparse_query.values.tolist(),
                    ),
                    using=self.settings.qdrant_sparse_vector_name,
                    limit=prefetch_limit,
                    filter=filters,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        chunks: list[RetrievedChunk] = []
        for point in result.points:
            payload = point.payload or {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=str(payload.get("chunk_id", point.id)),
                    document_id=str(payload.get("document_id", "")),
                    filename=str(payload.get("filename", "")),
                    text=str(payload.get("text", "")),
                    page=payload.get("page"),
                    section=payload.get("section"),
                    score=float(point.score or 0.0),
                    metadata=dict(payload.get("metadata") or {}),
                )
            )
        return chunks

    async def delete_document(self, document_id: str) -> None:
        from qdrant_client import models

        self.client.delete(
            collection_name=self.settings.qdrant_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )
