"""Main API router that aggregates all module routers."""

from fastapi import APIRouter

from app.api.knowledge_base import router as knowledge_base_router
from app.api.customer_profile import router as customer_profile_router
from app.api.sales_suggestion import router as sales_suggestion_router
from app.api.document_qa import router as document_qa_router
from app.api.risk_alert import router as risk_alert_router
from app.api.chat import router as chat_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(knowledge_base_router)
api_router.include_router(customer_profile_router)
api_router.include_router(sales_suggestion_router)
api_router.include_router(document_qa_router)
api_router.include_router(risk_alert_router)
api_router.include_router(chat_router)


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
