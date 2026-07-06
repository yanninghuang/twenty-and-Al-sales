"""Business logic for AI Customer Profile."""

from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_profile import CustomerProfile, ProfileInsight
from app.agents.customer_profile_agent import CustomerProfileAgent
from app.services.embedding_service import embedding_service


class CustomerProfileService:
    """Service for generating and managing customer profiles."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_profile(
        self,
        workspace_id: str,
        company_id: str | None = None,
        person_id: str | None = None,
        profile_type: str = "company",
    ) -> CustomerProfile:
        """Generate a new customer profile using the LangGraph agent."""
        agent = CustomerProfileAgent(workspace_id)

        initial_state = {
            "workspace_id": workspace_id,
            "company_id": company_id,
            "person_id": person_id,
            "profile_type": profile_type,
            "error": None,
            "result": {},
        }

        result = await agent.run(initial_state)

        # Create profile record
        profile = CustomerProfile(
            workspace_id=workspace_id,
            company_id=company_id,
            person_id=person_id,
            profile_type=profile_type,
            summary=result.get("summary", ""),
            tags=result.get("tags", []),
            sentiment_score=result.get("sentiment_score"),
            engagement_level=result.get("engagement_level"),
            churn_risk_score=result.get("churn_risk_score"),
            upsell_potential_score=result.get("upsell_potential_score"),
            key_contacts=result.get("key_contacts", []),
            recent_activities_summary=result.get("recent_activities_summary", ""),
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        self.session.add(profile)
        await self.session.flush()

        # Generate embedding for semantic search
        if profile.summary:
            emb = await embedding_service.embed_text(profile.summary)
            profile.embedding = emb

        # Create insights
        for insight_data in result.get("insights", []):
            insight = ProfileInsight(
                profile_id=profile.id,
                category=insight_data.get("category", "behavior"),
                title=insight_data.get("title", ""),
                description=insight_data.get("description", ""),
                confidence=insight_data.get("confidence", 0.5),
                evidence=insight_data.get("evidence", []),
            )
            self.session.add(insight)

        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def get_profile(
        self,
        workspace_id: str,
        profile_id: UUID | None = None,
        company_id: str | None = None,
        person_id: str | None = None,
    ) -> CustomerProfile | None:
        """Get a profile by ID, company, or person."""
        from sqlalchemy.orm import selectinload

        query = select(CustomerProfile).options(selectinload(CustomerProfile.insights))

        if profile_id:
            query = query.where(CustomerProfile.id == profile_id)
        elif company_id:
            query = query.where(
                CustomerProfile.workspace_id == workspace_id,
                CustomerProfile.company_id == company_id,
            ).order_by(CustomerProfile.generated_at.desc())
        elif person_id:
            query = query.where(
                CustomerProfile.workspace_id == workspace_id,
                CustomerProfile.person_id == person_id,
            ).order_by(CustomerProfile.generated_at.desc())

        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_profiles(
        self, workspace_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[CustomerProfile], int]:
        """List profiles for a workspace."""
        from sqlalchemy.orm import selectinload

        query = (
            select(CustomerProfile)
            .where(CustomerProfile.workspace_id == workspace_id)
            .options(selectinload(CustomerProfile.insights))
            .order_by(CustomerProfile.generated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(CustomerProfile)
            .where(CustomerProfile.workspace_id == workspace_id)
        )

        result = await self.session.execute(query)
        profiles = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return profiles, total
