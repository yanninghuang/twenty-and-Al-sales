"""Risk monitor — evaluates all active rules against relevant targets."""

from app.core.database import async_session_factory
from app.services.risk_alert_service import RiskAlertService
from app.models.risk_alert import RiskAlertRule
from sqlalchemy import select


async def run_risk_evaluation(workspace_id: str) -> int:
    """Evaluate all active rules for a workspace. Returns number of alerts generated."""
    total_alerts = 0

    async with async_session_factory() as session:
        # Fetch all active rules
        rules_query = select(RiskAlertRule).where(
            RiskAlertRule.workspace_id == workspace_id,
            RiskAlertRule.is_active == True,
        )
        rules_result = await session.execute(rules_query)
        rules = list(rules_result.scalars().all())

        service = RiskAlertService(session)

        for rule in rules:
            # For each rule, evaluate against relevant targets
            # This would query the CRM for targets matching the rule's target_type
            # For now, this is a framework — the actual CRM query is async/scheduled
            pass

    return total_alerts
