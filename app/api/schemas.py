from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    page_count: int
    chunk_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    content_type: str
    status: str
    language: str | None
    page_count: int
    chunk_count: int
    created_at: datetime


class Citation(BaseModel):
    citation_id: str
    document_id: str
    filename: str
    page: int | None
    chunk_id: str
    quote: str
    score: float


class UsageSummary(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    document_ids: list[str] | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class ChatResponse(BaseModel):
    chat_id: str
    answer: str
    citations: list[Citation]
    no_answer: bool
    confidence: float
    retrieval_trace: list[dict[str, Any]]
    usage: UsageSummary
    latency_ms: int


class FeedbackRequest(BaseModel):
    chat_id: str | None = None
    rating: int = Field(ge=-1, le=1)
    comment: str | None = Field(default=None, max_length=2000)
    correction: str | None = Field(default=None, max_length=4000)


class FeedbackResponse(BaseModel):
    feedback_id: str
    status: str = "stored"


class MetricsResponse(BaseModel):
    documents: int
    chunks: int
    chats: int
    feedback: int
    avg_chat_latency_ms: int
    total_tokens: int
    estimated_cost_usd: float


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
