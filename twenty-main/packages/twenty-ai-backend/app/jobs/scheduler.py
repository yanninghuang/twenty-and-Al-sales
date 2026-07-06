"""APScheduler configuration for background jobs."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """Start the background scheduler with all periodic jobs."""
    # Risk evaluation job
    scheduler.add_job(
        risk_monitor_job,
        trigger="interval",
        minutes=settings.risk_evaluation_interval_minutes,
        id="risk_monitor",
        name="Risk Monitor",
        replace_existing=True,
    )

    # CRM data sync job
    scheduler.add_job(
        crm_sync_job,
        trigger="interval",
        minutes=settings.crm_sync_interval_minutes,
        id="crm_sync",
        name="CRM Data Sync",
        replace_existing=True,
    )

    scheduler.start()


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    scheduler.shutdown(wait=False)


async def risk_monitor_job() -> None:
    """Periodic risk evaluation job."""
    # This would iterate over active workspaces and evaluate their rules.
    # For now, it's a placeholder that will be wired when workspace management is added.
    pass


async def crm_sync_job() -> None:
    """Periodic CRM data sync job."""
    # This would sync new/updated records from Twenty CRM into the AI Backend.
    # For now, it's a placeholder that will be wired when workspace management is added.
    pass
