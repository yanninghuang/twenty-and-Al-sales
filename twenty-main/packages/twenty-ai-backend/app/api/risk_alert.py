"""API routes for Risk Alerts."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import verify_api_key
from app.schemas.risk_alert import (
    RiskAlertRuleCreate,
    RiskAlertRuleUpdate,
    RiskAlertRuleResponse,
    RiskAlertStatusUpdate,
    RiskAlertResponse,
    RiskAlertListResponse,
    RiskAlertSummaryResponse,
    RiskEvaluateRequest,
)
from app.services.risk_alert_service import RiskAlertService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/risk-alerts",
    tags=["Risk Alerts"],
    dependencies=[Depends(verify_api_key)],
)


# ── Rules ─────────────────────────────────────────────────────

@router.post("/rules", response_model=RiskAlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    workspace_id: str,
    data: RiskAlertRuleCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a risk alert rule."""
    service = RiskAlertService(session)
    rule = await service.create_rule(
        workspace_id=workspace_id,
        name=data.name,
        rule_type=data.rule_type,
        target_type=data.target_type,
        conditions=data.conditions,
        severity=data.severity,
        is_active=data.is_active,
        notification_channels=data.notification_channels,
        cooldown_hours=data.cooldown_hours,
        description=data.description,
    )
    return rule


@router.get("/rules", response_model=list[RiskAlertRuleResponse])
async def list_rules(
    workspace_id: str,
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """List risk alert rules."""
    service = RiskAlertService(session)
    rules, total = await service.list_rules(workspace_id, offset, limit)
    return rules


@router.put("/rules/{rule_id}", response_model=RiskAlertRuleResponse)
async def update_rule(
    workspace_id: str,
    rule_id: UUID,
    data: RiskAlertRuleUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a risk alert rule."""
    service = RiskAlertService(session)
    rule = await service.update_rule(rule_id, data.model_dump(exclude_none=True))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    workspace_id: str,
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a risk alert rule."""
    service = RiskAlertService(session)
    deleted = await service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")


# ── Alerts ────────────────────────────────────────────────────

@router.get("", response_model=RiskAlertListResponse)
async def list_alerts(
    workspace_id: str,
    status_filter: str | None = None,
    severity: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """List risk alerts with optional filters."""
    service = RiskAlertService(session)
    alerts, total = await service.list_alerts(
        workspace_id=workspace_id,
        status=status_filter,
        severity=severity,
        target_type=target_type,
        target_id=target_id,
        offset=offset,
        limit=limit,
    )
    return RiskAlertListResponse(alerts=alerts, total=total)


@router.patch("/{alert_id}/status", response_model=RiskAlertResponse)
async def update_alert_status(
    workspace_id: str,
    alert_id: UUID,
    data: RiskAlertStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Acknowledge, resolve, or dismiss a risk alert."""
    service = RiskAlertService(session)
    alert = await service.update_alert_status(
        alert_id=alert_id,
        status=data.status,
        performed_by=data.performed_by,
        dismissed_reason=data.dismissed_reason,
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/summary", response_model=RiskAlertSummaryResponse)
async def get_summary(
    workspace_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a dashboard summary of risk alerts for the workspace."""
    service = RiskAlertService(session)
    return await service.get_summary(workspace_id)


@router.post("/evaluate", status_code=status.HTTP_202_ACCEPTED)
async def evaluate_risks(
    workspace_id: str,
    data: RiskEvaluateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Trigger a manual risk evaluation for all targets or a specific target."""
    if data.target_id:
        service = RiskAlertService(session)
        alerts = await service.evaluate_target(
            workspace_id=workspace_id,
            target_type=data.target_type,
            target_id=data.target_id,
        )
        return {
            "status": "completed",
            "message": f"Evaluated target. {len(alerts)} alerts generated.",
            "alert_count": len(alerts),
        }

    return {
        "status": "accepted",
        "message": "Full workspace evaluation queued in background.",
    }
