"""Pydantic schemas for Risk Alerts API."""

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Request schemas ───────────────────────────────────────────

class RiskAlertRuleCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = None
    rule_type: str
    target_type: str
    conditions: list[dict]
    severity: str = "medium"
    is_active: bool = True
    notification_channels: list[str] = Field(default_factory=lambda: ["in_app"])
    cooldown_hours: int = 24


class RiskAlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    rule_type: str | None = None
    target_type: str | None = None
    conditions: list[dict] | None = None
    severity: str | None = None
    is_active: bool | None = None
    notification_channels: list[str] | None = None
    cooldown_hours: int | None = None


class RiskAlertStatusUpdate(BaseModel):
    status: str
    dismissed_reason: str | None = None
    performed_by: str | None = None


class RiskEvaluateRequest(BaseModel):
    target_type: str = "opportunity"
    target_id: str | None = None


# ── Response schemas ──────────────────────────────────────────

class RiskAlertRuleResponse(BaseModel):
    id: UUID
    workspace_id: str
    name: str
    description: str | None = None
    rule_type: str
    target_type: str
    conditions: list[dict] = Field(default_factory=list)
    severity: str
    is_active: bool
    notification_channels: list[str] = Field(default_factory=list)
    cooldown_hours: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: object) -> object:
        for field in ["conditions", "notification_channels"]:
            val = data.get(field) if isinstance(data, dict) else getattr(data, field, None)
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(data, dict):
                        data[field] = parsed
                    else:
                        object.__setattr__(data, field, parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
        return data


class RiskAlertLogResponse(BaseModel):
    id: UUID
    alert_id: UUID
    action: str
    performed_by: str | None = None
    details: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: dict) -> dict:
        if isinstance(data, dict) and isinstance(data.get("details"), str):
            try:
                data["details"] = json.loads(data["details"])
            except (json.JSONDecodeError, TypeError):
                data["details"] = {}
        return data


class RiskAlertResponse(BaseModel):
    id: UUID
    workspace_id: str
    rule_id: UUID | None = None
    alert_type: str
    target_type: str
    target_id: str
    target_name: str | None = None
    severity: str
    title: str
    description: str
    ai_analysis: str | None = None
    suggested_actions: list[dict] = Field(default_factory=list)
    related_data: dict = Field(default_factory=dict)
    status: str
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    dismissed_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: object) -> object:
        """Parse JSON string fields from DB (works for both dict and ORM objects)."""
        for field in ["suggested_actions"]:
            val = data.get(field) if isinstance(data, dict) else getattr(data, field, None)
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(data, dict):
                        data[field] = parsed
                    else:
                        object.__setattr__(data, field, parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
        for field in ["related_data"]:
            val = data.get(field) if isinstance(data, dict) else getattr(data, field, None)
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(data, dict):
                        data[field] = parsed
                    else:
                        object.__setattr__(data, field, parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
        # Remove logs to avoid MissingGreenlet lazy-load issue
        if isinstance(data, dict):
            data.pop("logs", None)
        elif hasattr(data, "logs"):
            object.__setattr__(data, "logs", [])
        return data


class RiskAlertListResponse(BaseModel):
    alerts: list[RiskAlertResponse]
    total: int


class RiskAlertSummaryResponse(BaseModel):
    total_open: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    recently_resolved: int
    workspace_id: str
