"""LangGraph agent for AI Sales Suggestions generation."""

from typing import Any

from langgraph.graph import StateGraph, END

from app.agents.base_agent import BaseAgent, BaseAgentState
from app.services.twenty_crm_client import crm_client


class SalesSuggestionsState(BaseAgentState):
    target_type: str
    target_id: str
    context_data: dict
    historical_analysis: str
    identified_patterns: str
    suggestions: list[dict]
    ranked_suggestions: list[dict]


class SalesSuggestionsAgent(BaseAgent):
    """Agent that generates and ranks sales suggestions for CRM targets."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(SalesSuggestionsState)

        graph.add_node("fetch_context", self._create_node("fetch_context", self._fetch_context))
        graph.add_node("analyze_history", self._create_node("analyze_history", self._analyze_history))
        graph.add_node("identify_patterns", self._create_node("identify_patterns", self._identify_patterns))
        graph.add_node("generate_suggestions", self._create_node("generate_suggestions", self._generate_suggestions))
        graph.add_node("rank_suggestions", self._create_node("rank_suggestions", self._rank_suggestions))

        graph.set_entry_point("fetch_context")
        graph.add_edge("fetch_context", "analyze_history")
        graph.add_edge("analyze_history", "identify_patterns")
        graph.add_edge("identify_patterns", "generate_suggestions")
        graph.add_edge("generate_suggestions", "rank_suggestions")
        graph.add_edge("rank_suggestions", END)

        return graph

    async def _fetch_context(self, state: SalesSuggestionsState) -> dict:
        """Fetch relevant CRM context for the target."""
        context_data: dict = {}

        target_type = state["target_type"]
        target_id = state["target_id"]

        if target_type == "company":
            company = await crm_client.get_company(target_id)
            if company:
                context_data["company"] = company
                # Also fetch related opportunities
                context_data["opportunities"] = company.get("opportunities", [])

        elif target_type == "opportunity":
            opportunity = await crm_client.get_opportunity(target_id)
            if opportunity:
                context_data["opportunity"] = opportunity
                company_id = opportunity.get("company", {}).get("id")
                if company_id:
                    company = await crm_client.get_company(company_id)
                    context_data["company"] = company

        elif target_type == "person":
            person = await crm_client.get_person(target_id)
            if person:
                context_data["person"] = person

        return {"context_data": context_data}

    async def _analyze_history(self, state: SalesSuggestionsState) -> dict:
        """Analyze historical patterns from CRM data."""
        context = state.get("context_data", {})
        if not context:
            return {"historical_analysis": "Insufficient data for historical analysis."}

        prompt = f"""Analyze the following CRM data for historical patterns relevant to sales:
1. Past deal outcomes (won/lost)
2. Purchase history and frequency
3. Product/service preferences
4. Interaction timeline

CRM CONTEXT:
{str(context)[:3000]}

Provide a concise historical analysis (3-5 sentences)."""
        system = "You are a sales analyst. Analyze CRM history for patterns and trends."
        analysis = await self.llm.generate(system, prompt)
        return {"historical_analysis": analysis.strip()}

    async def _identify_patterns(self, state: SalesSuggestionsState) -> dict:
        """Identify key patterns that inform sales suggestions."""
        prompt = f"""Based on the following historical analysis, identify key patterns that suggest sales opportunities or actions:

HISTORICAL ANALYSIS:
{state.get('historical_analysis', 'N/A')}

CONTEXT:
{str(state.get('context_data', {}))[:2000]}

Identify:
1. Cross-sell or upsell opportunities
2. Follow-up gaps
3. Renewal timing
4. Engagement opportunities
5. Risk indicators to address

Provide your analysis as a structured paragraph."""
        system = "You are a sales strategist. Identify actionable patterns from CRM data."
        patterns = await self.llm.generate(system, prompt)
        return {"identified_patterns": patterns.strip()}

    async def _generate_suggestions(self, state: SalesSuggestionsState) -> dict:
        """Generate specific actionable sales suggestions."""
        prompt = f"""Generate 3-5 specific, actionable sales suggestions based on the following analysis:

TARGET TYPE: {state['target_type']}
TARGET ID: {state['target_id']}

PATTERNS:
{state.get('identified_patterns', 'N/A')}

CONTEXT:
{str(state.get('context_data', {}))[:2000]}

Each suggestion should have:
- suggestion_type: 'next_action', 'cross_sell', 'upsell', 'follow_up', or 'meeting_prep'
- priority: 'high', 'medium', or 'low'
- title: a clear, action-oriented title
- description: detailed description of what to do
- rationale: why this suggestion is being made
- suggested_actions: array of specific action items [{action_type, description}]

Format as JSON with a 'suggestions' array."""
        system = "You are a sales coach. Generate specific, actionable sales suggestions. Reply with valid JSON."

        result = await self.llm.generate(system, prompt)

        import json
        try:
            if "```" in result:
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            data = json.loads(result.strip())
            suggestions = data.get("suggestions", [])
        except json.JSONDecodeError:
            suggestions = []

        return {"suggestions": suggestions}

    async def _rank_suggestions(self, state: SalesSuggestionsState) -> dict:
        """Rank suggestions by priority and potential impact."""
        suggestions = state.get("suggestions", [])
        if not suggestions:
            return {"ranked_suggestions": []}

        # Sort: high priority first, then by suggestion_type importance
        priority_order = {"high": 0, "medium": 1, "low": 2}
        type_order = {
            "follow_up": 0,
            "meeting_prep": 1,
            "next_action": 2,
            "upsell": 3,
            "cross_sell": 4,
        }
        ranked = sorted(
            suggestions,
            key=lambda s: (
                priority_order.get(s.get("priority", "medium"), 1),
                type_order.get(s.get("suggestion_type", "next_action"), 5),
            ),
        )

        return {"ranked_suggestions": ranked}
