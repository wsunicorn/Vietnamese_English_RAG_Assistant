import asyncio

from app.core.config import Settings
from app.generation.answerer import GroundedAnswerer
from app.retrieval.vector_store import RetrievedChunk


def test_no_answer_when_no_context():
    settings = Settings(llm_provider="development")
    answer = asyncio.run(
        GroundedAnswerer(settings).answer(question="What is the policy?", retrieved=[])
    )

    assert answer.no_answer is True
    assert answer.citations == []


def test_no_answer_when_score_is_weak():
    settings = Settings(llm_provider="development", no_answer_min_score=0.5)
    answer = asyncio.run(
        GroundedAnswerer(settings).answer(
            question="What is the policy?",
            retrieved=[
                RetrievedChunk(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    filename="policy.txt",
                    text="The policy mentions onboarding.",
                    page=1,
                    section=None,
                    score=0.1,
                    metadata={},
                )
            ],
        )
    )

    assert answer.no_answer is True
    assert answer.confidence == 0.0
