"""Pydantic schemas for AI Customer Profile API."""

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Request schemas ───────────────────────────────────────────

class CustomerProfileGenerateRequest(BaseModel):
    company_id: str | None = None
    person_id: str | None = None
    profile_type: str


class CustomerProfileBatchGenerateRequest(BaseModel):
    profile_type: str = "company"
    limit: int = Field(default=50, ge=1, le=200)


class CustomerProfileSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


# ── Response schemas ──────────────────────────────────────────

class ProfileInsightResponse(BaseModel):
    id: UUID
    category: str
    title: str
    description: str
    confidence: float = 0.0
    evidence: list[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: object) -> object:
        field = "evidence"
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


class CustomerProfileResponse(BaseModel):
    id: UUID
    workspace_id: str
    company_id: str | None = None
    person_id: str | None = None
    profile_type: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    sentiment_score: float | None = None
    engagement_level: str | None = None
    churn_risk_score: float | None = None
    upsell_potential_score: float | None = None
    key_contacts: list[dict] = Field(default_factory=list)
    recent_activities_summary: str | None = None
    generated_at: datetime
    expires_at: datetime | None = None
    insights: list[ProfileInsightResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: object) -> object:
        for field in ["tags", "key_contacts"]:
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
        # Remove insights to avoid MissingGreenlet
        if isinstance(data, dict):
            data.pop("insights", None)
        elif hasattr(data, "insights"):
            object.__setattr__(data, "insights", [])
        return data


class CustomerProfileListResponse(BaseModel):
    profiles: list[CustomerProfileResponse]
    total: int
