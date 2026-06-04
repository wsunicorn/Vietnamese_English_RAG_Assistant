from app.db.models import ChatLogORM


def test_chat_log_accepts_json_lists():
    chat_log = ChatLogORM(
        id="chat-1",
        question="What is covered?",
        answer="The document covers AI engineering. [C1]",
        citations=[{"citation_id": "C1"}],
        retrieval_trace=[{"chunk_id": "chunk-1"}],
    )

    assert chat_log.citations == [{"citation_id": "C1"}]
    assert chat_log.retrieval_trace == [{"chunk_id": "chunk-1"}]
