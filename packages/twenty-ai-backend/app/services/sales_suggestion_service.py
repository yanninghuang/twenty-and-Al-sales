"""Business logic for AI Sales Suggestions."""

from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sales_suggestion import SalesSuggestion, SuggestionFeedback
from app.agents.sales_suggestions_agent import SalesSuggestionsAgent


class SalesSuggestionService:
    """Service for generating and managing sales suggestions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_suggestions(
        self,
        workspace_id: str,
        target_type: str,
        target_id: str,
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[SalesSuggestion]:
        """Generate sales suggestions using the agent."""
        agent = SalesSuggestionsAgent(workspace_id)

        initial_state = {
            "workspace_id": workspace_id,
            "target_type": target_type,
            "target_id": target_id,
            "error": None,
            "result": {},
        }

        result = await agent.run(initial_state)
        ranked = result.get("ranked_suggestions", [])[:limit]

        suggestions: list[SalesSuggestion] = []
        for item in ranked:
            suggestion = SalesSuggestion(
                workspace_id=workspace_id,
                target_type=target_type,
                target_id=target_id,
                suggestion_type=item.get("suggestion_type", "next_action"),
                priority=item.get("priority", "medium"),
                title=item.get("title", ""),
                description=item.get("description", ""),
                rationale=item.get("rationale", ""),
                suggested_actions=item.get("suggested_actions", []),
                status="pending",
                generated_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7),
                created_by=user_id,
            )
            self.session.add(suggestion)
            suggestions.append(suggestion)

        await self.session.commit()
        return suggestions

    async def list_suggestions(
        self,
        workspace_id: str,
        target_type: str | None = None,
        target_id: str | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[SalesSuggestion], int]:
        """List suggestions with optional filters."""
        conditions = [SalesSuggestion.workspace_id == workspace_id]
        if target_type:
            conditions.append(SalesSuggestion.target_type == target_type)
        if target_id:
            conditions.append(SalesSuggestion.target_id == target_id)
        if status:
            conditions.append(SalesSuggestion.status == status)
        if assigned_to:
            conditions.append(SalesSuggestion.created_by == assigned_to)

        query = (
            select(SalesSuggestion)
            .options(selectinload(SalesSuggestion.feedbacks))
            .where(*conditions)
            .order_by(
                SalesSuggestion.priority == "high",
                SalesSuggestion.generated_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count()).select_from(SalesSuggestion).where(*conditions)
        )

        result = await self.session.execute(query)
        suggestions = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return suggestions, total

    async def update_status(
        self, suggestion_id: UUID, status: str, dismissed_reason: str | None = None
    ) -> SalesSuggestion | None:
        """Update suggestion status."""
        suggestion = await self.session.get(SalesSuggestion, suggestion_id)
        if not suggestion:
            return None

        suggestion.status = status
        if status == "accepted":
            suggestion.accepted_at = datetime.utcnow()
        elif status == "completed":
            suggestion.completed_at = datetime.utcnow()
        elif status == "dismissed":
            suggestion.dismissed_reason = dismissed_reason

        await self.session.commit()
        await self.session.refresh(suggestion)
        return suggestion

    async def add_feedback(
        self,
        suggestion_id: UUID,
        user_id: str,
        rating: int | None = None,
        helpful: bool | None = None,
        comment: str | None = None,
    ) -> SuggestionFeedback:
        """Add feedback to a suggestion."""
        feedback = SuggestionFeedback(
            suggestion_id=suggestion_id,
            user_id=user_id,
            rating=rating,
            helpful=helpful,
            comment=comment,
        )
        self.session.add(feedback)
        await self.session.commit()
        return feedback
