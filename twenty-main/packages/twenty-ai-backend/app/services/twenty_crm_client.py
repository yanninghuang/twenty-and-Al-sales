"""GraphQL client for reading data from Twenty CRM."""

from typing import Any

import httpx

from app.core.config import settings


class TwentyCRMClient:
    """Read-only GraphQL client for Twenty CRM data."""

    def __init__(
        self,
        crm_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (crm_url or settings.twenty_crm_default_url).rstrip("/")
        self.graphql_url = f"{self.base_url}{settings.twenty_crm_graphql_path}"
        self.api_key = api_key

    async def _execute(self, query: str, variables: dict | None = None) -> dict[str, Any]:
        """Execute a GraphQL query against the Twenty CRM API."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.graphql_url,
                json={"query": query, "variables": variables or {}},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                raise ValueError(f"GraphQL errors: {data['errors']}")
            return data["data"]

    # ── Companies ──────────────────────────────────────────────

    async def get_company(self, company_id: str) -> dict | None:
        """Fetch a company with related people and opportunities."""
        query = """
        query GetCompany($id: UUID!) {
            findOneCompany(input: { id: $id }) {
                id
                name
                domainName { primaryLinkUrl primaryLinkLabel }
                annualRevenue
                address { addressStreet1 addressStreet2 addressCity addressPostcode addressState addressCountry }
                linkedinLink { primaryLinkUrl }
                people {
                    id
                    name { firstName lastName }
                    emails { email }
                    jobTitle
                }
                opportunities {
                    id
                    name
                    amount { amountMicros currencyCode }
                    closeDate
                    stage
                }
            }
        }
        """
        result = await self._execute(query, {"id": company_id})
        return result.get("findOneCompany")

    async def find_companies(self, workspace_id: str, limit: int = 50) -> list[dict]:
        """List companies in a workspace."""
        query = """
        query FindCompanies($limit: Int) {
            companies(first: $limit) {
                edges {
                    node {
                        id
                        name
                        domainName { primaryLinkUrl }
                        annualRevenue
                    }
                }
            }
        }
        """
        result = await self._execute(query, {"limit": limit})
        edges = result.get("companies", {}).get("edges", [])
        return [edge["node"] for edge in edges]

    # ── People ─────────────────────────────────────────────────

    async def get_person(self, person_id: str) -> dict | None:
        """Fetch a person with related companies."""
        query = """
        query GetPerson($id: UUID!) {
            findOnePerson(input: { id: $id }) {
                id
                name { firstName lastName }
                emails { email }
                phone
                jobTitle
                city
                linkedinLink { primaryLinkUrl }
                company { id name }
            }
        }
        """
        result = await self._execute(query, {"id": person_id})
        return result.get("findOnePerson")

    # ── Opportunities ──────────────────────────────────────────

    async def get_opportunity(self, opportunity_id: str) -> dict | None:
        """Fetch an opportunity with company and point of contact."""
        query = """
        query GetOpportunity($id: UUID!) {
            findOneOpportunity(input: { id: $id }) {
                id
                name
                amount { amountMicros currencyCode }
                closeDate
                stage
                probability
                company { id name }
                pointOfContact { id name { firstName lastName } }
            }
        }
        """
        result = await self._execute(query, {"id": opportunity_id})
        return result.get("findOneOpportunity")

    async def find_opportunities(
        self, workspace_id: str, stage: str | None = None, limit: int = 50
    ) -> list[dict]:
        """List opportunities, optionally filtered by stage."""
        variables: dict = {"limit": limit}
        filter_clause = ""
        if stage:
            filter_clause = '(filter: { stage: { eq: "' + stage + '" } })'

        query = f"""
        query FindOpportunities($limit: Int) {{
            opportunities{filter_clause} (first: $limit) {{
                edges {{
                    node {{
                        id
                        name
                        amount {{ amountMicros currencyCode }}
                        closeDate
                        stage
                        probability
                        company {{ id name }}
                    }}
                }}
            }}
        }}
        """
        result = await self._execute(query, variables)
        edges = result.get("opportunities", {}).get("edges", [])
        return [edge["node"] for edge in edges]

    # ── Tasks ──────────────────────────────────────────────────

    async def find_tasks(
        self, workspace_id: str, target_type: str | None = None, target_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        """List tasks, optionally filtered by related record."""
        query = """
        query FindTasks($limit: Int) {
            tasks(first: $limit) {
                edges {
                    node {
                        id
                        title
                        bodyV2
                        dueAt
                        status
                    }
                }
            }
        }
        """
        result = await self._execute(query, {"limit": limit})
        edges = result.get("tasks", {}).get("edges", [])
        return [edge["node"] for edge in edges]

    # ── Notes ──────────────────────────────────────────────────

    async def find_notes(
        self, workspace_id: str, target_type: str | None = None, target_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        """List notes, optionally filtered by related record."""
        query = """
        query FindNotes($limit: Int) {
            notes(first: $limit) {
                edges {
                    node {
                        id
                        title
                        bodyV2
                    }
                }
            }
        }
        """
        result = await self._execute(query, {"limit": limit})
        edges = result.get("notes", {}).get("edges", [])
        return [edge["node"] for edge in edges]

    # ── Attachments ────────────────────────────────────────────

    async def find_attachments(
        self, workspace_id: str, limit: int = 50
    ) -> list[dict]:
        """List attachments."""
        query = """
        query FindAttachments($limit: Int) {
            attachments(first: $limit) {
                edges {
                    node {
                        id
                        name
                        fullPath
                        type
                    }
                }
            }
        }
        """
        result = await self._execute(query, {"limit": limit})
        edges = result.get("attachments", {}).get("edges", [])
        return [edge["node"] for edge in edges]


# Singleton
crm_client = TwentyCRMClient()
