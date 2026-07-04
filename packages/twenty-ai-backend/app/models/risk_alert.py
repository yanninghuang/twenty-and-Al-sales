"""ORM models for Risk Alerts (SQLite/PostgreSQL compatible)."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RiskAlertRule(Base):
    __tablename__ = "risk_alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    severity: Mapped[str] = mapped_column(String(10), default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_channels: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alerts: Mapped[list["RiskAlert"]] = relationship(back_populates="rule")


class RiskAlert(Base):
    __tablename__ = "risk_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("risk_alert_rules.id", ondelete="SET NULL"), nullable=True
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_actions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    related_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    status: Mapped[str] = mapped_column(String(20), default="open")
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rule: Mapped["RiskAlertRule | None"] = relationship(back_populates="alerts")
    logs: Mapped[list["RiskAlertLog"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_ra_workspace_target", "workspace_id", "target_type", "target_id"),
        Index("idx_ra_status_severity", "workspace_id", "status", "severity"),
        Index("idx_ra_created", "workspace_id", "created_at"),
    )


class RiskAlertLog(Base):
    __tablename__ = "risk_alert_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("risk_alerts.id", ondelete="CASCADE")
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    performed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    alert: Mapped["RiskAlert"] = relationship(back_populates="logs")
