import asyncio

from app.bots.common import parse_ask_command
from app.core.config import Settings
from app.retrieval.reranker import maybe_rerank
from app.retrieval.vector_store import RetrievedChunk
from app.services.jobs import JobQueue


def test_parse_ask_command_strips_command_prefix():
    assert parse_ask_command("/ask What is PTO?") == "What is PTO?"
    assert parse_ask_command("What is PTO?") == "What is PTO?"


def test_job_queue_enqueue_uses_redis(monkeypatch):
    pushed = []

    class FakeRedis:
        async def lpush(self, queue, job_id):
            pushed.append((queue, job_id))

    async def fake_redis(self):
        return FakeRedis()

    monkeypatch.setattr(JobQueue, "redis", fake_redis)
    settings = Settings(redis_queue_name="test-queue")

    asyncio.run(JobQueue(settings).enqueue("job-1"))

    assert pushed == [("test-queue", "job-1")]


def test_reranker_none_keeps_order():
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            filename="doc.md",
            text="first",
            page=None,
            section=None,
            score=0.8,
            metadata={},
        ),
        RetrievedChunk(
            chunk_id="c2",
            document_id="d1",
            filename="doc.md",
            text="second",
            page=None,
            section=None,
            score=0.7,
            metadata={},
        ),
    ]

    reranked = asyncio.run(maybe_rerank(question="test", chunks=chunks, settings=Settings()))

    assert [chunk.chunk_id for chunk in reranked] == ["c1", "c2"]
