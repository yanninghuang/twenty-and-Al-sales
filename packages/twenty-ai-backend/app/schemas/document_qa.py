"""Pydantic schemas for Document QA API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────

class QADocumentCreate(BaseModel):
    """Schema for creating/uploading a QA document."""
    title: str = Field(..., max_length=500)
    content_text: str
    file_name: str | None = None
    file_type: str | None = None  # 'pdf', 'docx', 'txt', 'md'
    file_size_bytes: int | None = None
    source_type: str = "upload"  # 'upload', 'attachment', 'note'
    source_record_type: str | None = None
    source_record_id: str | None = None
    twenty_attachment_id: str | None = None
    created_by: str | None = None


class QAConversationCreate(BaseModel):
    """Start a new Q&A conversation."""
    document_ids: list[UUID] = Field(..., min_length=1)
    title: str | None = None


class QAMessageCreate(BaseModel):
    """Send a question in a conversation."""
    content: str = Field(..., min_length=1)


# ── Response schemas ──────────────────────────────────────────

class QAMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    citations: list[dict] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class QAConversationResponse(BaseModel):
    id: UUID
    workspace_id: str
    document_ids: list[UUID]
    title: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[QAMessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class QAConversationListResponse(BaseModel):
    conversations: list[QAConversationResponse]
    total: int


class QADocumentResponse(BaseModel):
    id: UUID
    workspace_id: str
    title: str
    file_name: str | None = None
    file_type: str | None = None
    file_size_bytes: int | None = None
    source_type: str
    source_record_type: str | None = None
    source_record_id: str | None = None
    created_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QADocumentListResponse(BaseModel):
    documents: list[QADocumentResponse]
    total: int


class QAStreamChunk(BaseModel):
    """A single chunk of a streaming Q&A response."""
    type: str  # 'text', 'citation', 'done', 'error'
    content: str = ""
    citations: list[dict] | None = None
