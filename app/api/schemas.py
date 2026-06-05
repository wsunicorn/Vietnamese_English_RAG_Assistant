from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: str | None = None
    source_id: str | None = None
    filename: str
    status: str
    page_count: int
    chunk_count: int
    documents: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentListItem(BaseModel):
    document_id: str
    source_id: str | None = None
    source_type: str
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
    source_type: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    source_path: str | None = None


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
    sources: int = 0
    chats: int
    feedback: int
    queued_jobs: int = 0
    avg_chat_latency_ms: int
    total_tokens: int
    estimated_cost_usd: float


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str


class UrlIngestionRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    mode: str = Field(default="page", pattern="^(page|sitemap)$")
    max_pages: int = Field(default=20, ge=1, le=200)
    sync_interval_minutes: int | None = Field(default=None, ge=5, le=60 * 24 * 30)


class JobResponse(BaseModel):
    source_id: str | None = None
    status: str
    queued_job_id: str


class SourceListItem(BaseModel):
    source_id: str
    name: str
    source_type: str
    uri: str | None = None
    status: str
    sync_interval_minutes: int | None = None
    last_synced_at: datetime | None = None
    last_error: str | None = None
    document_count: int = 0
    chunk_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
