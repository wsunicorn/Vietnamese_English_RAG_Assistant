from app.core.config import Settings
from app.retrieval.embeddings import EmbeddingClient
from app.retrieval.vector_store import QdrantHybridStore, RetrievedChunk


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
        dense_query = await self.embedding_client.embed_query(question)
        return await self.vector_store.search(
            query=question,
            dense_vector=dense_query,
            top_k=top_k or self.settings.retrieval_top_k,
            prefetch_limit=self.settings.retrieval_prefetch_limit,
            document_ids=document_ids,
        )
