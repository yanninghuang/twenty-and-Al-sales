"""Business logic for Risk Alerts."""

from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.risk_alert import RiskAlertRule, RiskAlert, RiskAlertLog
from app.agents.risk_alert_agent import RiskAlertAgent
from app.schemas.risk_alert import RiskAlertSummaryResponse


class RiskAlertService:
    """Service for managing risk alert rules and alerts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Rules ──────────────────────────────────────────────────

    async def create_rule(
        self,
        workspace_id: str,
        name: str,
        rule_type: str,
        target_type: str,
        conditions: list[dict],
        severity: str = "medium",
        is_active: bool = True,
        notification_channels: list[str] | None = None,
        cooldown_hours: int = 24,
        description: str | None = None,
        created_by: str | None = None,
    ) -> RiskAlertRule:
        """Create a risk alert rule."""
        rule = RiskAlertRule(
            workspace_id=workspace_id,
            name=name,
            description=description,
            rule_type=rule_type,
            target_type=target_type,
            conditions=conditions,
            severity=severity,
            is_active=is_active,
            notification_channels=notification_channels or ["in_app"],
            cooldown_hours=cooldown_hours,
            created_by=created_by,
        )
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def list_rules(
        self, workspace_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[RiskAlertRule], int]:
        """List rules for a workspace."""
        query = (
            select(RiskAlertRule)
            .where(RiskAlertRule.workspace_id == workspace_id)
            .order_by(RiskAlertRule.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(RiskAlertRule)
            .where(RiskAlertRule.workspace_id == workspace_id)
        )

        result = await self.session.execute(query)
        rules = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return rules, total

    async def update_rule(
        self, rule_id: UUID, updates: dict
    ) -> RiskAlertRule | None:
        """Update a risk alert rule."""
        rule = await self.session.get(RiskAlertRule, rule_id)
        if not rule:
            return None

        for key, value in updates.items():
            if value is not None and hasattr(rule, key):
                setattr(rule, key, value)

        rule.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a risk alert rule."""
        rule = await self.session.get(RiskAlertRule, rule_id)
        if not rule:
            return False
        await self.session.delete(rule)
        await self.session.commit()
        return True

    # ── Alerts ─────────────────────────────────────────────────

    async def evaluate_target(
        self,
        workspace_id: str,
        target_type: str,
        target_id: str,
    ) -> list[RiskAlert]:
        """Evaluate all active rules against a target and generate alerts."""
        # Fetch active rules for the workspace matching this target type
        rules_query = select(RiskAlertRule).where(
            RiskAlertRule.workspace_id == workspace_id,
            RiskAlertRule.is_active == True,
            RiskAlertRule.target_type == target_type,
        )
        rules_result = await self.session.execute(rules_query)
        rules = list(rules_result.scalars().all())

        alerts: list[RiskAlert] = []
        for rule in rules:
            agent = RiskAlertAgent(workspace_id)
            initial_state = {
                "workspace_id": workspace_id,
                "rule_type": rule.rule_type,
                "target_type": target_type,
                "target_id": target_id,
                "conditions": rule.conditions,
                "severity": rule.severity,
                "error": None,
                "result": {},
            }

            result = await agent.run(initial_state)

            if not result.get("rule_conditions_met"):
                continue

            alert = RiskAlert(
                workspace_id=workspace_id,
                rule_id=rule.id,
                alert_type=rule.rule_type,
                target_type=target_type,
                target_id=target_id,
                target_name=result.get("target_name", ""),
                severity=result.get("severity", rule.severity),
                title=result.get("title", f"{rule.rule_type} risk detected"),
                description=result.get("description", ""),
                ai_analysis=result.get("risk_analysis", ""),
                suggested_actions=result.get("suggested_actions", []),
                related_data=result.get("related_data", {}),
                status="open",
            )
            self.session.add(alert)
            alerts.append(alert)

            # Log creation
            log = RiskAlertLog(
                alert_id=alert.id,
                action="created",
                performed_by=None,
                details={"rule_id": str(rule.id), "rule_type": rule.rule_type},
            )
            self.session.add(log)

        if alerts:
            await self.session.commit()

        return alerts

    async def list_alerts(
        self,
        workspace_id: str,
        status: str | None = None,
        severity: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[RiskAlert], int]:
        """List alerts with optional filters."""
        conditions = [RiskAlert.workspace_id == workspace_id]
        if status:
            conditions.append(RiskAlert.status == status)
        if severity:
            conditions.append(RiskAlert.severity == severity)
        if target_type:
            conditions.append(RiskAlert.target_type == target_type)
        if target_id:
            conditions.append(RiskAlert.target_id == target_id)

        query = (
            select(RiskAlert)
            .options(selectinload(RiskAlert.logs))
            .where(*conditions)
            .order_by(RiskAlert.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count()).select_from(RiskAlert).where(*conditions)
        )

        result = await self.session.execute(query)
        alerts = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return alerts, total

    async def update_alert_status(
        self,
        alert_id: UUID,
        status: str,
        performed_by: str | None = None,
        dismissed_reason: str | None = None,
    ) -> RiskAlert | None:
        """Update alert status and log the action."""
        alert = await self.session.get(RiskAlert, alert_id)
        if not alert:
            return None

        now = datetime.utcnow()
        alert.status = status
        if status == "acknowledged":
            alert.acknowledged_by = performed_by
            alert.acknowledged_at = now
        elif status == "resolved":
            alert.resolved_by = performed_by
            alert.resolved_at = now
        elif status == "dismissed":
            alert.dismissed_reason = dismissed_reason

        log = RiskAlertLog(
            alert_id=alert_id,
            action=status,
            performed_by=performed_by,
            details={},
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def get_summary(self, workspace_id: str) -> RiskAlertSummaryResponse:
        """Get a summary of alerts for the workspace dashboard."""
        # Open alerts by severity
        severity_query = (
            select(RiskAlert.severity, func.count())
            .where(
                RiskAlert.workspace_id == workspace_id,
                RiskAlert.status == "open",
            )
            .group_by(RiskAlert.severity)
        )
        severity_result = await self.session.execute(severity_query)
        severity_counts = dict(severity_result.all())

        # Recently resolved (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        resolved_query = select(func.count()).select_from(RiskAlert).where(
            RiskAlert.workspace_id == workspace_id,
            RiskAlert.status == "resolved",
            RiskAlert.resolved_at >= week_ago,
        )
        resolved_result = await self.session.execute(resolved_query)
        recently_resolved = resolved_result.scalar() or 0

        return RiskAlertSummaryResponse(
            total_open=sum(severity_counts.values()),
            critical_count=severity_counts.get("critical", 0),
            high_count=severity_counts.get("high", 0),
            medium_count=severity_counts.get("medium", 0),
            low_count=severity_counts.get("low", 0),
            recently_resolved=recently_resolved,
            workspace_id=workspace_id,
        )
