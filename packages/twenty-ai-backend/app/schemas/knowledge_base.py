"""Pydantic schemas for AI Knowledge Base API."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────

class KnowledgeDocumentCreate(BaseModel):
    """Schema for creating a knowledge document."""
    title: str = Field(..., max_length=500)
    content: str
    source_type: str = Field(default="manual")
    source_record_type: str | None = None
    source_record_id: str | None = None
    metadata: dict | None = None
    created_by: str | None = None


class KnowledgeQuery(BaseModel):
    """Schema for querying the knowledge base."""
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    conversation_id: str | None = None


class KnowledgeSyncRequest(BaseModel):
    """Request to sync documents from Twenty CRM."""
    source_record_type: str | None = None
    source_record_id: str | None = None


# ── Response schemas ──────────────────────────────────────────

class KnowledgeDocumentResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    content: str
    source_type: str
    source_record_type: str | None = None
    source_record_id: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeQuerySource(BaseModel):
    chunk_id: str
    document_title: str
    excerpt: str
    score: float


class KnowledgeQueryResponse(BaseModel):
    answer: str
    sources: list[KnowledgeQuerySource]
    conversation_id: str | None = None


class KnowledgeDocumentListResponse(BaseModel):
    documents: list[KnowledgeDocumentResponse]
    total: int


class KnowledgeFileUploadResponse(KnowledgeDocumentResponse):
    """Response for file upload, includes parsed info."""
    file_type: str | None = None
    file_size: int | None = None
