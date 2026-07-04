"""LangGraph agent for AI Customer Profile generation."""

from typing import Any

from langgraph.graph import StateGraph, END

from app.agents.base_agent import BaseAgent, BaseAgentState
from app.services.twenty_crm_client import crm_client
from app.services.embedding_service import embedding_service


class CustomerProfileState(BaseAgentState):
    company_id: str | None
    person_id: str | None
    profile_type: str
    crm_data: dict
    behavior_analysis: str
    finance_analysis: str
    communication_analysis: str
    summary: str
    sentiment_score: float
    engagement_level: str
    churn_risk_score: float
    upsell_potential_score: float
    tags: list[str]
    insights: list[dict]
    key_contacts: list[dict]
    recent_activities_summary: str


class CustomerProfileAgent(BaseAgent):
    """Multi-faceted customer 360 profile analysis agent."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(CustomerProfileState)

        graph.add_node("fetch_crm_data", self._create_node("fetch_crm_data", self._fetch_crm_data))
        graph.add_node("analyze_behavior", self._create_node("analyze_behavior", self._analyze_behavior))
        graph.add_node("analyze_finance", self._create_node("analyze_finance", self._analyze_finance))
        graph.add_node("analyze_communications", self._create_node("analyze_communications", self._analyze_communications))
        graph.add_node("synthesize_profile", self._create_node("synthesize_profile", self._synthesize_profile))
        graph.add_node("generate_insights", self._create_node("generate_insights", self._generate_insights))

        graph.set_entry_point("fetch_crm_data")
        graph.add_edge("fetch_crm_data", "analyze_behavior")
        graph.add_edge("fetch_crm_data", "analyze_finance")
        graph.add_edge("fetch_crm_data", "analyze_communications")
        graph.add_edge("analyze_behavior", "synthesize_profile")
        graph.add_edge("analyze_finance", "synthesize_profile")
        graph.add_edge("analyze_communications", "synthesize_profile")
        graph.add_edge("synthesize_profile", "generate_insights")
        graph.add_edge("generate_insights", END)

        return graph

    async def _fetch_crm_data(self, state: CustomerProfileState) -> dict:
        """Fetch CRM data from Twenty for the target company or person."""
        crm_data: dict = {}

        if state.get("company_id"):
            company_data = await crm_client.get_company(state["company_id"])
            if company_data:
                crm_data["company"] = company_data

        if state.get("person_id"):
            person_data = await crm_client.get_person(state["person_id"])
            if person_data:
                crm_data["person"] = person_data

        return {"crm_data": crm_data}

    async def _analyze_behavior(self, state: CustomerProfileState) -> dict:
        """Analyze behavioral patterns from CRM data."""
        crm_data = state.get("crm_data", {})
        if not crm_data:
            return {"behavior_analysis": "No CRM data available for behavior analysis."}

        prompt = f"""Analyze the following CRM data for behavioral patterns. Consider:
1. Activity frequency and trends
2. Engagement patterns with the business
3. Product/service usage indicators
4. Responsiveness to outreach

CRM DATA:
{str(crm_data)[:3000]}

Provide a concise analysis of behavioral patterns (3-5 sentences)."""
        system = "You are a customer behavior analyst. Analyze CRM data for behavioral patterns."
        analysis = await self.llm.generate(system, prompt)
        return {"behavior_analysis": analysis.strip()}

    async def _analyze_finance(self, state: CustomerProfileState) -> dict:
        """Analyze financial aspects from CRM data."""
        crm_data = state.get("crm_data", {})
        company = crm_data.get("company", {})
        opportunities = company.get("opportunities", []) if company else []

        if not opportunities:
            return {"finance_analysis": "No opportunity/deal data available for financial analysis."}

        prompt = f"""Analyze the financial profile based on deal/opportunity data:
1. Total deal value and trends
2. Win/loss patterns
3. Revenue potential
4. Payment behavior (if available)

OPPORTUNITIES:
{str(opportunities)[:3000]}

Provide a concise financial analysis (3-5 sentences)."""
        system = "You are a financial analyst. Analyze deal and revenue data for customer financial profile."
        analysis = await self.llm.generate(system, prompt)
        return {"finance_analysis": analysis.strip()}

    async def _analyze_communications(self, state: CustomerProfileState) -> dict:
        """Analyze communication patterns from CRM data."""
        crm_data = state.get("crm_data", {})
        if not crm_data:
            return {"communication_analysis": "No CRM data available for communication analysis."}

        prompt = f"""Analyze communication patterns from the available CRM data:
1. Communication frequency
2. Key contact persons and their roles
3. Sentiment indicators (if any)
4. Information gaps

CRM DATA:
{str(crm_data)[:3000]}

Provide a concise communication analysis (3-5 sentences)."""
        system = "You are a communication analyst. Analyze CRM data for communication patterns."
        analysis = await self.llm.generate(system, prompt)
        return {"communication_analysis": analysis.strip()}

    async def _synthesize_profile(self, state: CustomerProfileState) -> dict:
        """Synthesize all analyses into a unified 360-degree profile."""
        prompt = f"""Create a comprehensive 360-degree customer profile summary based on the following analyses:

BEHAVIOR ANALYSIS:
{state.get('behavior_analysis', 'N/A')}

FINANCIAL ANALYSIS:
{state.get('finance_analysis', 'N/A')}

COMMUNICATION ANALYSIS:
{state.get('communication_analysis', 'N/A')}

Generate:
1. A 2-3 paragraph summary of the overall customer profile
2. A sentiment score (-1.0 to 1.0, where -1 is very negative and 1 is very positive)
3. An engagement level (high/medium/low/none)
4. A churn risk score (0.0 to 1.0)
5. An upsell potential score (0.0 to 1.0)
6. 3-5 relevant keyword tags
7. A list of key contacts with influence level
8. Recent activities summary

Format your response as JSON with keys: summary, sentiment_score, engagement_level, churn_risk_score, upsell_potential_score, tags, key_contacts, recent_activities_summary"""
        system = "You are a customer intelligence analyst. Synthesize analyses into customer profiles. Always reply with valid JSON."

        result = await self.llm.generate(system, prompt)

        # Parse JSON from LLM response (handle markdown code fences)
        import json
        try:
            if "```" in result:
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            data = json.loads(result.strip())
        except json.JSONDecodeError:
            data = {
                "summary": result[:500],
                "sentiment_score": 0.0,
                "engagement_level": "medium",
                "churn_risk_score": 0.3,
                "upsell_potential_score": 0.5,
                "tags": [],
                "key_contacts": [],
                "recent_activities_summary": "",
            }

        return {
            "summary": data.get("summary", ""),
            "sentiment_score": data.get("sentiment_score", 0.0),
            "engagement_level": data.get("engagement_level", "medium"),
            "churn_risk_score": data.get("churn_risk_score", 0.3),
            "upsell_potential_score": data.get("upsell_potential_score", 0.5),
            "tags": data.get("tags", []),
            "key_contacts": data.get("key_contacts", []),
            "recent_activities_summary": data.get("recent_activities_summary", ""),
        }

    async def _generate_insights(self, state: CustomerProfileState) -> dict:
        """Generate actionable insights from the synthesized profile."""
        prompt = f"""Based on the following customer profile summary, generate 3-5 actionable insights for the sales team. Each insight should have a category (behavior/finance/communication/risk/opportunity), a title, a description, and a confidence score (0.0 to 1.0).

PROFILE SUMMARY:
{state.get('summary', 'N/A')}

SENTIMENT: {state.get('sentiment_score', 0)}
ENGAGEMENT: {state.get('engagement_level', 'N/A')}
CHURN RISK: {state.get('churn_risk_score', 0)}
UPSELL POTENTIAL: {state.get('upsell_potential_score', 0)}

Format your response as JSON with an 'insights' array containing objects with: category, title, description, confidence, evidence."""
        system = "You are a customer intelligence analyst. Generate actionable insights from customer profiles. Reply with valid JSON."

        result = await self.llm.generate(system, prompt)

        import json
        try:
            if "```" in result:
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            data = json.loads(result.strip())
            insights = data.get("insights", [])
        except json.JSONDecodeError:
            insights = []

        return {"insights": insights}
