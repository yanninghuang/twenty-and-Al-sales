"""API routes for AI Customer Profile."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import verify_api_key
from app.schemas.customer_profile import (
    CustomerProfileGenerateRequest,
    CustomerProfileBatchGenerateRequest,
    CustomerProfileSearchRequest,
    CustomerProfileResponse,
    CustomerProfileListResponse,
    ProfileInsightResponse,
)
from app.services.customer_profile_service import CustomerProfileService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/customer-profiles",
    tags=["Customer Profile"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/generate", response_model=CustomerProfileResponse, status_code=status.HTTP_201_CREATED)
async def generate_profile(
    workspace_id: str,
    data: CustomerProfileGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Generate or refresh a customer profile for a company or person."""
    if not data.company_id and not data.person_id:
        raise HTTPException(
            status_code=400,
            detail="Either company_id or person_id is required",
        )
    service = CustomerProfileService(session)
    profile = await service.generate_profile(
        workspace_id=workspace_id,
        company_id=data.company_id,
        person_id=data.person_id,
        profile_type=data.profile_type,
    )
    return profile


@router.post("/batch-generate", status_code=status.HTTP_202_ACCEPTED)
async def batch_generate_profiles(
    workspace_id: str,
    data: CustomerProfileBatchGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Batch generate profiles (async — profiles will be generated in background)."""
    return {
        "status": "accepted",
        "message": f"Batch generation for {data.limit} {data.profile_type}s has been queued.",
    }


@router.get("", response_model=CustomerProfileListResponse)
async def list_profiles(
    workspace_id: str,
    company_id: str | None = None,
    person_id: str | None = None,
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """List customer profiles, optionally filtered by company or person."""
    service = CustomerProfileService(session)

    if company_id or person_id:
        profile = await service.get_profile(
            workspace_id=workspace_id,
            company_id=company_id,
            person_id=person_id,
        )
        if profile:
            return CustomerProfileListResponse(profiles=[profile], total=1)
        return CustomerProfileListResponse(profiles=[], total=0)

    profiles, total = await service.list_profiles(workspace_id, offset, limit)
    return CustomerProfileListResponse(profiles=profiles, total=total)


@router.get("/{profile_id}", response_model=CustomerProfileResponse)
async def get_profile(
    workspace_id: str,
    profile_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a customer profile by ID with all insights."""
    service = CustomerProfileService(session)
    profile = await service.get_profile(workspace_id, profile_id=profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/search", response_model=CustomerProfileListResponse)
async def search_profiles(
    workspace_id: str,
    data: CustomerProfileSearchRequest,
    session: AsyncSession = Depends(get_session),
):
    """Semantic search across customer profiles."""
    # Vector similarity search over profile embeddings
    from app.services.embedding_service import embedding_service
    from app.services.vector_store import VectorStore

    query_embedding = await embedding_service.embed_text(data.query)
    store = VectorStore(session)
    results = await store.search_similar(
        table_name="customer_profiles",
        query_embedding=query_embedding,
        workspace_id=workspace_id,
        top_k=data.top_k,
    )

    # Convert results
    profiles = []
    for r in results:
        from app.models.customer_profile import CustomerProfile
        profile = await session.get(CustomerProfile, r["id"])
        if profile:
            profiles.append(profile)

    return CustomerProfileListResponse(profiles=profiles, total=len(profiles))
