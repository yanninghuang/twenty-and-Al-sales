"""API routes for AI Sales Suggestions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import verify_api_key
from app.schemas.sales_suggestion import (
    SalesSuggestionGenerateRequest,
    SalesSuggestionStatusUpdate,
    SuggestionFeedbackCreate,
    SalesSuggestionResponse,
    SalesSuggestionListResponse,
    SuggestionFeedbackResponse,
    DailyBriefRequest,
    DailyBriefResponse,
)
from app.services.sales_suggestion_service import SalesSuggestionService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/sales-suggestions",
    tags=["Sales Suggestions"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/generate", response_model=list[SalesSuggestionResponse], status_code=status.HTTP_201_CREATED)
async def generate_suggestions(
    workspace_id: str,
    data: SalesSuggestionGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Generate AI-powered sales suggestions for a target."""
    service = SalesSuggestionService(session)
    suggestions = await service.generate_suggestions(
        workspace_id=workspace_id,
        target_type=data.target_type,
        target_id=data.target_id,
        limit=data.limit,
    )
    return suggestions


@router.get("", response_model=SalesSuggestionListResponse)
async def list_suggestions(
    workspace_id: str,
    target_type: str | None = None,
    target_id: str | None = None,
    status_filter: str | None = None,
    assigned_to: str | None = None,
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """List sales suggestions with optional filters."""
    service = SalesSuggestionService(session)
    suggestions, total = await service.list_suggestions(
        workspace_id=workspace_id,
        target_type=target_type,
        target_id=target_id,
        status=status_filter,
        assigned_to=assigned_to,
        offset=offset,
        limit=limit,
    )
    return SalesSuggestionListResponse(suggestions=suggestions, total=total)


@router.patch("/{suggestion_id}/status", response_model=SalesSuggestionResponse)
async def update_suggestion_status(
    workspace_id: str,
    suggestion_id: UUID,
    data: SalesSuggestionStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Accept, dismiss, or mark a suggestion as completed."""
    service = SalesSuggestionService(session)
    suggestion = await service.update_status(
        suggestion_id=suggestion_id,
        status=data.status,
        dismissed_reason=data.dismissed_reason,
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return suggestion


@router.post("/{suggestion_id}/feedback", response_model=SuggestionFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    workspace_id: str,
    suggestion_id: UUID,
    data: SuggestionFeedbackCreate,
    user_id: str = "anonymous",  # In production, extract from auth context
    session: AsyncSession = Depends(get_session),
):
    """Rate a suggestion or provide feedback."""
    service = SalesSuggestionService(session)
    feedback = await service.add_feedback(
        suggestion_id=suggestion_id,
        user_id=user_id,
        rating=data.rating,
        helpful=data.helpful,
        comment=data.comment,
    )
    return feedback


@router.post("/daily-brief", response_model=DailyBriefResponse)
async def daily_brief(
    workspace_id: str,
    data: DailyBriefRequest,
    session: AsyncSession = Depends(get_session),
):
    """Generate a daily sales brief for a user."""
    from datetime import datetime

    suggestions, total = await SalesSuggestionService(session).list_suggestions(
        workspace_id=workspace_id,
        assigned_to=data.user_id,
        status="pending",
        limit=data.limit,
    )

    # Generate summary
    from app.services.llm_service import get_llm_service
    llm = get_llm_service()

    if suggestions:
        suggestion_texts = "\n".join(
            f"- [{s.priority.upper()}] {s.title}: {s.description[:100]}"
            for s in suggestions
        )
        prompt = f"""Summarize the following sales suggestions into a brief daily overview (2-3 sentences):

{suggestion_texts}"""
    else:
        prompt = "Generate an encouraging message for a salesperson with no pending suggestions today."

    summary = await llm.generate(
        "You are a helpful sales coach. Provide motivating daily briefs.",
        prompt,
    )

    return DailyBriefResponse(
        user_id=data.user_id,
        generated_at=datetime.utcnow(),
        suggestions=suggestions,
        summary=summary,
    )
