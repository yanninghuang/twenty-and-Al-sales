"""LangGraph agent for AI Knowledge Base RAG."""

from typing import Any

from langgraph.graph import StateGraph, END

from app.agents.base_agent import BaseAgent, BaseAgentState
from app.services.vector_store import VectorStore
from app.services.embedding_service import embedding_service
from app.core.database import async_session_factory


class KnowledgeBaseState(BaseAgentState):
    query: str
    rewritten_query: str
    retrieved_chunks: list[dict]
    relevant_chunks: list[dict]
    answer: str
    sources: list[dict]


class KnowledgeBaseAgent(BaseAgent):
    """RAG agent for querying the enterprise knowledge base."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(KnowledgeBaseState)

        graph.add_node("rewrite_query", self._create_node("rewrite_query", self._rewrite_query))
        graph.add_node("retrieve_chunks", self._create_node("retrieve_chunks", self._retrieve_chunks))
        graph.add_node("grade_relevance", self._create_node("grade_relevance", self._grade_relevance))
        graph.add_node("transform_query", self._create_node("transform_query", self._transform_query))
        graph.add_node("generate_answer", self._create_node("generate_answer", self._generate_answer))

        graph.set_entry_point("rewrite_query")
        graph.add_edge("rewrite_query", "retrieve_chunks")
        graph.add_edge("retrieve_chunks", "grade_relevance")
        graph.add_conditional_edges(
            "grade_relevance",
            self._should_retry,
            {"retry": "transform_query", "generate": "generate_answer"},
        )
        graph.add_edge("transform_query", "retrieve_chunks")
        graph.add_edge("generate_answer", END)

        return graph

    async def _rewrite_query(self, state: KnowledgeBaseState) -> dict:
        """Rewrite the user query for better retrieval."""
        prompt = f"""You are a query optimization assistant. Improve the following search query to be more specific and search-friendly for a vector database.

Original query: {state['query']}

Reply with ONLY the rewritten query, no explanations."""
        system = "You are a helpful assistant that rewrites search queries to improve retrieval."
        rewritten = await self.llm.generate(system, prompt)
        return {"rewritten_query": rewritten.strip()}

    async def _retrieve_chunks(self, state: KnowledgeBaseState) -> dict:
        """Retrieve relevant chunks using vector similarity."""
        async with async_session_factory() as session:
            store = VectorStore(session)
            query_embedding = await embedding_service.embed_text(state["rewritten_query"])
            chunks = await store.search_similar(
                table_name="knowledge_chunks",
                query_embedding=query_embedding,
                workspace_id=state["workspace_id"],
                top_k=10,
            )
        return {"retrieved_chunks": chunks}

    async def _grade_relevance(self, state: KnowledgeBaseState) -> dict:
        """Grade each retrieved chunk for relevance."""
        relevant: list[dict] = []
        for chunk in state["retrieved_chunks"]:
            # Simple threshold-based filtering (cosine similarity)
            if chunk.get("similarity", 0) >= 0.5:
                relevant.append(chunk)

        return {"relevant_chunks": relevant}

    async def _transform_query(self, state: KnowledgeBaseState) -> dict:
        """Transform the query when retrieval results are poor."""
        prompt = f"""The search for "{state['query']}" returned poor results. Generate a different search query that might retrieve better results. Think about related terms, synonyms, or broader concepts.

Reply with ONLY the new query."""
        system = "You reformulate search queries to improve retrieval."
        new_query = await self.llm.generate(system, prompt)
        return {"rewritten_query": new_query.strip()}

    async def _generate_answer(self, state: KnowledgeBaseState) -> dict:
        """Generate the final answer with citations."""
        if not state.get("relevant_chunks"):
            return {
                "answer": "I couldn't find relevant information in the knowledge base to answer your question. Try rephrasing your query or adding more documents to the knowledge base.",
                "sources": [],
            }

        context_parts: list[str] = []
        for i, chunk in enumerate(state["relevant_chunks"]):
            context_parts.append(f"[Source {i+1}]: {chunk['content']}")

        context = "\n\n".join(context_parts)

        prompt = f"""Based on the following knowledge base excerpts, answer the user's question thoroughly. Cite sources using [Source N] notation.

CONTEXT:
{context}

QUESTION: {state['query']}

Provide a clear, direct answer. If the context doesn't fully address the question, acknowledge the limitations."""
        system = "You are an enterprise knowledge base assistant. Answer questions based only on the provided context. Always cite sources."

        answer = await self.llm.generate(system, prompt)
        sources = [
            {
                "chunk_id": chunk["id"],
                "excerpt": chunk["content"][:200],
                "score": chunk["similarity"],
            }
            for chunk in state["relevant_chunks"]
        ]

        return {"answer": answer, "sources": sources}

    def _should_retry(self, state: KnowledgeBaseState) -> str:
        """Determine if we should retry with a transformed query."""
        relevant = state.get("relevant_chunks", [])
        # Retry if fewer than 2 relevant chunks found
        if len(relevant) < 2 and state.get("retrieved_chunks", []):
            # Guard against infinite loops: don't retry if already transformed
            retrieved = state.get("retrieved_chunks", [])
            avg_similarity = sum(c.get("similarity", 0) for c in retrieved) / max(len(retrieved), 1)
            if avg_similarity < 0.3:
                return "retry"
        return "generate"
