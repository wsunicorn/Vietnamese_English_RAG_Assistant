import logging

from app.core.config import Settings
from app.retrieval.embeddings import EmbeddingClient
from app.retrieval.reranker import maybe_rerank
from app.retrieval.vector_store import QdrantHybridStore, RetrievedChunk

logger = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(
        self,
        *,
        settings: Settings,
        embedding_client: EmbeddingClient,
        vector_store: QdrantHybridStore,
    ):
        self.settings = settings
        self.embedding_client = embedding_client
        self.vector_store = vector_store

    async def retrieve(
        self,
        *,
        question: str,
        document_ids: list[str] | None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        mode = (self.settings.retrieval_mode or "hybrid").lower()
        force_sparse = False
        dense_query: list[float] | None = None

        if mode != "sparse":
            try:
                dense_query = await self.embedding_client.embed_query(question)
            except Exception as exc:
                if mode in {"hybrid", "hybrid_rerank"} and self.settings.retrieval_sparse_fallback:
                    force_sparse = True
                    logger.warning(
                        "Dense query embedding failed; falling back to sparse retrieval. error=%s",
                        exc,
                    )
                else:
                    raise

        chunks = await self.vector_store.search(
            query=question,
            dense_vector=dense_query,
            top_k=top_k or self.settings.retrieval_top_k,
            prefetch_limit=self.settings.retrieval_prefetch_limit,
            document_ids=document_ids,
            force_sparse=force_sparse,
        )
        if mode == "hybrid_rerank":
            return await maybe_rerank(question=question, chunks=chunks, settings=self.settings)
        return await maybe_rerank(question=question, chunks=chunks, settings=self.settings)
