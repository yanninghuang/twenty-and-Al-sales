"""Base LangGraph agent class for all AI Sales Assistant agents."""

from typing import Any

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from app.services.llm_service import LLMService, get_llm_service
from app.services.embedding_service import embedding_service


class BaseAgentState(TypedDict):
    """Base state shared across all agents."""
    workspace_id: str
    error: str | None
    result: dict[str, Any]


class BaseAgent:
    """Common functionality for all LangGraph agents."""

    def __init__(
        self,
        workspace_id: str,
        llm: LLMService | None = None,
    ) -> None:
        self.workspace_id = workspace_id
        self.llm = llm or get_llm_service()

    def build_graph(self) -> StateGraph:
        """Build and return the LangGraph StateGraph. Override in subclasses."""
        raise NotImplementedError

    async def run(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent graph with the given initial state."""
        graph = self.build_graph()
        compiled = graph.compile()
        result = await compiled.ainvoke(initial_state)
        return result

    def _create_node(self, name: str, func):
        """Helper to create a graph node with error handling."""
        async def wrapper(state):
            try:
                return await func(state)
            except Exception as e:
                return {**state, "error": f"[{name}] {str(e)}"}
        return wrapper
