"""LangGraph agent for Payment/Opportunity Risk Alerts."""

from typing import Any

from langgraph.graph import StateGraph, END

from app.agents.base_agent import BaseAgent, BaseAgentState
from app.services.twenty_crm_client import crm_client


class RiskAlertState(BaseAgentState):
    rule_type: str
    target_type: str
    target_id: str
    conditions: list[dict]
    rule_conditions_met: bool
    related_data: dict
    risk_analysis: str
    severity: str
    title: str
    description: str
    suggested_actions: list[dict]


class RiskAlertAgent(BaseAgent):
    """Agent that evaluates risk rules and generates alerts."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(RiskAlertState)

        graph.add_node("evaluate_conditions", self._create_node("evaluate_conditions", self._evaluate_conditions))
        graph.add_node("fetch_related_data", self._create_node("fetch_related_data", self._fetch_related_data))
        graph.add_node("analyze_risk", self._create_node("analyze_risk", self._analyze_risk))
        graph.add_node("determine_severity", self._create_node("determine_severity", self._determine_severity))
        graph.add_node("generate_alert", self._create_node("generate_alert", self._generate_alert))

        graph.set_entry_point("evaluate_conditions")
        graph.add_conditional_edges(
            "evaluate_conditions",
            self._conditions_result,
            {"triggered": "fetch_related_data", "skip": END},
        )
        graph.add_edge("fetch_related_data", "analyze_risk")
        graph.add_edge("analyze_risk", "determine_severity")
        graph.add_edge("determine_severity", "generate_alert")
        graph.add_edge("generate_alert", END)

        return graph

    async def _evaluate_conditions(self, state: RiskAlertState) -> dict:
        """Evaluate if rule conditions are met against CRM data."""
        conditions = state.get("conditions", [])
        target_type = state["target_type"]
        target_id = state["target_id"]

        # Fetch basic data based on target type
        crm_data: dict = {}
        if target_type == "opportunity":
            opp = await crm_client.get_opportunity(target_id)
            if opp:
                crm_data["opportunity"] = opp

        elif target_type == "company":
            company = await crm_client.get_company(target_id)
            if company:
                crm_data["company"] = company

        # Evaluate each condition
        conditions_met = True
        for condition in conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "eq")
            value = condition.get("value")

            # Simple condition evaluation against CRM data
            field_value = self._extract_field_value(crm_data, field)
            if field_value is None:
                conditions_met = False
                break
            if not self._evaluate_condition(field_value, operator, value):
                conditions_met = False
                break

        return {"rule_conditions_met": conditions_met}

    async def _fetch_related_data(self, state: RiskAlertState) -> dict:
        """Fetch additional related data for risk analysis."""
        crm_data: dict = {}
        target_type = state["target_type"]
        target_id = state["target_id"]

        if target_type == "opportunity":
            opp = await crm_client.get_opportunity(target_id)
            crm_data["opportunity"] = opp
            if opp and opp.get("company"):
                company = await crm_client.get_company(opp["company"]["id"])
                crm_data["company"] = company

        elif target_type == "company":
            company = await crm_client.get_company(target_id)
            crm_data["company"] = company

        # Also fetch tasks and notes
        tasks = await crm_client.find_tasks(state["workspace_id"])
        crm_data["tasks"] = tasks

        return {"related_data": crm_data}

    async def _analyze_risk(self, state: RiskAlertState) -> dict:
        """Perform LLM-based risk analysis on the fetched data."""
        data = state.get("related_data", {})
        rule_type = state.get("rule_type", "")

        if not data:
            return {"risk_analysis": "Unable to perform risk analysis — insufficient data."}

        prompt = f"""Analyze the following CRM data for risk factors related to '{rule_type}':

CRM DATA:
{str(data)[:3000]}

Consider:
1. Payment history and overdue indicators
2. Deal stagnation (opportunities stuck at same stage)
3. Communication gaps or silence periods
4. Sudden changes in deal amount or close date
5. Customer churn signals

Provide a detailed risk analysis (4-6 sentences)."""
        system = "You are a risk analyst. Identify and explain risk factors from CRM data."
        analysis = await self.llm.generate(system, prompt)
        return {"risk_analysis": analysis.strip()}

    async def _determine_severity(self, state: RiskAlertState) -> dict:
        """Determine alert severity based on risk analysis."""
        analysis = state.get("risk_analysis", "")
        conditions = state.get("conditions", [])
        default_severity = state.get("severity", "medium")

        if not analysis:
            return {"severity": default_severity}

        prompt = f"""Based on the following risk analysis, determine the appropriate severity level:

RISK ANALYSIS:
{analysis}

CONDITIONS THAT TRIGGERED:
{str(conditions)}

Classify as one of: critical, high, medium, low.

Consider:
- Financial impact magnitude
- Urgency (time sensitivity)
- Probability of negative outcome
- Customer relationship value

Reply with ONLY the severity level (critical/high/medium/low)."""
        system = "You classify risk severity. Reply with a single word: critical, high, medium, or low."
        severity = await self.llm.generate(system, prompt)
        severity = severity.strip().lower()
        valid = {"critical", "high", "medium", "low"}
        if severity not in valid:
            severity = default_severity
        return {"severity": severity}

    async def _generate_alert(self, state: RiskAlertState) -> dict:
        """Generate the final alert with title, description, and suggested actions."""
        analysis = state.get("risk_analysis", "")
        severity = state.get("severity", "medium")
        target_type = state.get("target_type", "opportunity")

        if not analysis:
            return {
                "title": f"Risk detected in {target_type}",
                "description": "An automated risk check has been triggered. Please review the related record.",
                "suggested_actions": [],
            }

        prompt = f"""Generate a risk alert based on the following analysis:

RISK ANALYSIS: {analysis}
SEVERITY: {severity}
TARGET TYPE: {target_type}

Generate:
1. A concise alert title (max 100 chars)
2. A detailed description explaining the risk (2-3 sentences)
3. 2-4 suggested actions the user should take [{action_type, description}]

Format as JSON with keys: title, description, suggested_actions."""
        system = "You create risk alerts for a CRM system. Reply with valid JSON."
        result = await self.llm.generate(system, prompt)

        import json
        try:
            if "```" in result:
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            data = json.loads(result.strip())
        except json.JSONDecodeError:
            data = {
                "title": f"{severity.upper()} risk: {target_type} requires attention",
                "description": analysis[:300],
                "suggested_actions": [],
            }

        return {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "suggested_actions": data.get("suggested_actions", []),
        }

    def _extract_field_value(self, data: dict, field_path: str) -> Any:
        """Extract a nested field value from a dict using dot notation."""
        keys = field_path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current

    def _evaluate_condition(self, field_value: Any, operator: str, compare_value: Any) -> bool:
        """Evaluate a single condition."""
        if operator == "eq":
            return field_value == compare_value
        elif operator == "neq":
            return field_value != compare_value
        elif operator == "gt":
            try:
                return float(field_value) > float(compare_value)
            except (ValueError, TypeError):
                return False
        elif operator == "lt":
            try:
                return float(field_value) < float(compare_value)
            except (ValueError, TypeError):
                return False
        elif operator == "gte":
            try:
                return float(field_value) >= float(compare_value)
            except (ValueError, TypeError):
                return False
        elif operator == "lte":
            try:
                return float(field_value) <= float(compare_value)
            except (ValueError, TypeError):
                return False
        elif operator == "contains":
            return str(compare_value).lower() in str(field_value).lower()
        elif operator == "in":
            return field_value in (compare_value if isinstance(compare_value, list) else [compare_value])
        return False

    def _conditions_result(self, state: RiskAlertState) -> str:
        if state.get("rule_conditions_met", False):
            return "triggered"
        return "skip"
