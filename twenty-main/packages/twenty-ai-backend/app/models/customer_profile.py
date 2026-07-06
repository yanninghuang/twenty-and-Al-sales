"""ORM models for AI Customer Profile (SQLite/PostgreSQL compatible)."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    person_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    profile_type: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded list
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    churn_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    upsell_potential_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    key_contacts: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    recent_activities_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded vector
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    insights: Mapped[list["ProfileInsight"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_cp_company", "workspace_id", "company_id"),
        Index("idx_cp_person", "workspace_id", "person_id"),
    )


class ProfileInsight(Base):
    __tablename__ = "profile_insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_profiles.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped["CustomerProfile"] = relationship(back_populates="insights")
