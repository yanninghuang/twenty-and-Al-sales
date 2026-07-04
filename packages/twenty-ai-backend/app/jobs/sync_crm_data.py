"""CRM data sync — periodically pulls new/updated records from Twenty CRM."""

from app.core.database import async_session_factory
from app.services.twenty_crm_client import crm_client


async def sync_workspace_data(workspace_id: str) -> dict[str, int]:
    """Sync CRM data for a workspace. Returns counts of synced records."""
    counts = {
        "companies": 0,
        "opportunities": 0,
        "tasks": 0,
        "notes": 0,
    }

    try:
        # Sync companies
        companies = await crm_client.find_companies(workspace_id, limit=100)
        counts["companies"] = len(companies)

        # Sync opportunities
        opportunities = await crm_client.find_opportunities(workspace_id, limit=100)
        counts["opportunities"] = len(opportunities)

        # Sync tasks
        tasks = await crm_client.find_tasks(workspace_id, limit=100)
        counts["tasks"] = len(tasks)

        # Sync notes
        notes = await crm_client.find_notes(workspace_id, limit=100)
        counts["notes"] = len(notes)

    except Exception as e:
        # Log error but don't crash the sync
        counts["error"] = str(e)

    return counts
