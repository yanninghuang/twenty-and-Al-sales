"""Pydantic schemas for AI Sales Suggestions API."""

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Request schemas ───────────────────────────────────────────

class SalesSuggestionGenerateRequest(BaseModel):
    target_type: str
    target_id: str
    limit: int = Field(default=5, ge=1, le=10)


class SalesSuggestionStatusUpdate(BaseModel):
    status: str
    dismissed_reason: str | None = None


class SuggestionFeedbackCreate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    helpful: bool | None = None
    comment: str | None = None


class DailyBriefRequest(BaseModel):
    user_id: str
    limit: int = Field(default=10, ge=1, le=20)


# ── Response schemas ──────────────────────────────────────────

class SuggestionFeedbackResponse(BaseModel):
    id: UUID
    user_id: str
    rating: int | None = None
    helpful: bool | None = None
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SalesSuggestionResponse(BaseModel):
    id: UUID
    workspace_id: str
    target_type: str
    target_id: str
    suggestion_type: str
    priority: str
    title: str
    description: str
    rationale: str | None = None
    suggested_actions: list[dict] = Field(default_factory=list)
    status: str
    dismissed_reason: str | None = None
    generated_at: datetime
    expires_at: datetime | None = None
    accepted_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: str | None = None
    feedbacks: list[SuggestionFeedbackResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: object) -> object:
        field = "suggested_actions"
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
        # Remove feedbacks to avoid MissingGreenlet
        if isinstance(data, dict):
            data.pop("feedbacks", None)
        elif hasattr(data, "feedbacks"):
            object.__setattr__(data, "feedbacks", [])
        return data


class SalesSuggestionListResponse(BaseModel):
    suggestions: list[SalesSuggestionResponse]
    total: int


class DailyBriefResponse(BaseModel):
    user_id: str
    generated_at: datetime
    suggestions: list[SalesSuggestionResponse]
    summary: str
