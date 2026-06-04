import asyncio

import pytest

from app.core.config import Settings
from app.generation.answerer import GroundedAnswerer, resolve_llm_provider
from app.retrieval.embeddings import (
    HashEmbeddingClient,
    OpenAICompatibleEmbeddingClient,
    create_embedding_client,
)
from app.retrieval.vector_store import RetrievedChunk


def test_gemini_llm_provider_resolves_with_key():
    settings = Settings(llm_provider="gemini", gemini_api_key="test-key")

    provider = resolve_llm_provider(settings)

    assert provider is not None
    assert provider.name == "gemini"
    assert provider.model == settings.gemini_chat_model


def test_missing_provider_key_uses_development_answer():
    settings = Settings(llm_provider="gemini", gemini_api_key=None)
    answer = asyncio.run(
        GroundedAnswerer(settings).answer(
            question="What does the policy say?",
            retrieved=[
                RetrievedChunk(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    filename="policy.txt",
                    text="The policy says employees can request annual leave.",
                    page=1,
                    section=None,
                    score=0.9,
                    metadata={},
                )
            ],
        )
    )

    assert answer.no_answer is False
    assert "Development answer" in answer.answer


def test_hash_embedding_provider_is_local():
    client = create_embedding_client(Settings(embedding_provider="hash", embedding_dimensions=32))

    assert isinstance(client, HashEmbeddingClient)


def test_gemini_embedding_provider_uses_openai_compatible_client_when_key_exists():
    client = create_embedding_client(Settings(embedding_provider="gemini", gemini_api_key="test-key"))

    assert isinstance(client, OpenAICompatibleEmbeddingClient)


def test_groq_cannot_be_used_for_embeddings():
    with pytest.raises(ValueError, match="Groq is chat-only"):
        create_embedding_client(Settings(embedding_provider="groq", groq_api_key="test-key"))
