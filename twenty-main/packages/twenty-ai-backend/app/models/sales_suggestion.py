"""ORM models for AI Sales Suggestions (SQLite/PostgreSQL compatible)."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, Float, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SalesSuggestion(Base):
    __tablename__ = "sales_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_actions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    status: Mapped[str] = mapped_column(String(20), default="pending")
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    feedbacks: Mapped[list["SuggestionFeedback"]] = relationship(
        back_populates="suggestion", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_ss_workspace_target", "workspace_id", "target_type", "target_id"),
        Index("idx_ss_status", "workspace_id", "status"),
    )


class SuggestionFeedback(Base):
    __tablename__ = "suggestion_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    suggestion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_suggestions.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    suggestion: Mapped["SalesSuggestion"] = relationship(back_populates="feedbacks")
