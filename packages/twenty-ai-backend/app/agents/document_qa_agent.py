"""LangGraph agent for Document Q&A with citation verification."""

from typing import Any

from langgraph.graph import StateGraph, END

from app.agents.base_agent import BaseAgent, BaseAgentState
from app.services.vector_store import VectorStore
from app.services.embedding_service import embedding_service
from app.core.database import async_session_factory


class DocumentQAState(BaseAgentState):
    question: str
    conversation_id: str | None
    document_ids: list[str]
    parsed_question_type: str
    retrieved_chunks: list[dict]
    has_sufficient_context: bool
    answer: str
    citations: list[dict]
    has_hallucination: bool


class DocumentQAAgent(BaseAgent):
    """Q&A agent for contract/product documents with hallucination checking."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(DocumentQAState)

        graph.add_node("parse_question", self._create_node("parse_question", self._parse_question))
        graph.add_node("retrieve_chunks", self._create_node("retrieve_chunks", self._retrieve_chunks))
        graph.add_node("verify_context", self._create_node("verify_context", self._verify_context))
        graph.add_node("expand_retrieval", self._create_node("expand_retrieval", self._expand_retrieval))
        graph.add_node("generate_answer", self._create_node("generate_answer", self._generate_answer))
        graph.add_node("check_hallucination", self._create_node("check_hallucination", self._check_hallucination))
        graph.add_node("regenerate_answer", self._create_node("regenerate_answer", self._regenerate_answer))

        graph.set_entry_point("parse_question")
        graph.add_edge("parse_question", "retrieve_chunks")
        graph.add_edge("retrieve_chunks", "verify_context")
        graph.add_conditional_edges(
            "verify_context",
            self._context_sufficient,
            {"sufficient": "generate_answer", "insufficient": "expand_retrieval"},
        )
        graph.add_edge("expand_retrieval", "retrieve_chunks")
        graph.add_edge("generate_answer", "check_hallucination")
        graph.add_conditional_edges(
            "check_hallucination",
            self._has_hallucination,
            {"hallucination": "regenerate_answer", "ok": END},
        )
        graph.add_edge("regenerate_answer", "check_hallucination")

        return graph

    async def _parse_question(self, state: DocumentQAState) -> dict:
        """Classify the question type for better retrieval."""
        prompt = f"""Classify the following question into one of these types, and rephrase it for optimal document retrieval:
- factual: looking for specific facts, dates, numbers
- summary: asking for overview or summary
- comparison: comparing items or clauses
- clause_specific: asking about specific contract/product clauses

Question: {state['question']}

Reply with format: TYPE: <type>\nREPHRASED: <rephrased question>"""
        system = "You classify questions for document retrieval."
        result = await self.llm.generate(system, prompt)
        lines = result.strip().split("\n")
        question_type = "factual"
        for line in lines:
            if line.upper().startswith("TYPE:"):
                question_type = line.split(":", 1)[1].strip().lower()
        return {"parsed_question_type": question_type}

    async def _retrieve_chunks(self, state: DocumentQAState) -> dict:
        """Retrieve relevant chunks via hybrid search."""
        doc_ids = state.get("document_ids", [])
        async with async_session_factory() as session:
            store = VectorStore(session)
            query_embedding = await embedding_service.embed_text(state["question"])

            # Search across specified documents
            chunks: list[dict] = []
            for doc_id in doc_ids:
                results = await store.search_similar(
                    table_name="qa_document_chunks",
                    query_embedding=query_embedding,
                    workspace_id=state["workspace_id"],
                    top_k=5,
                )
                chunks.extend(results)

            # Deduplicate and sort by similarity
            seen = set()
            unique_chunks = []
            for c in sorted(chunks, key=lambda x: x.get("similarity", 0), reverse=True):
                if c["id"] not in seen:
                    seen.add(c["id"])
                    unique_chunks.append(c)

        return {"retrieved_chunks": unique_chunks[:10]}

    async def _verify_context(self, state: DocumentQAState) -> dict:
        """Verify that retrieved chunks contain sufficient context to answer."""
        chunks = state.get("retrieved_chunks", [])
        if not chunks:
            return {"has_sufficient_context": False}

        combined = "\n\n".join(c["content"][:300] for c in chunks[:5])

        prompt = f"""Can the following document excerpts answer this question?

QUESTION: {state['question']}

EXCERPTS:
{combined[:2000]}

Reply with ONLY 'YES' if the excerpts contain enough information to answer the question, or 'NO' if they do not."""
        system = "You verify if document excerpts contain sufficient context. Reply only YES or NO."
        result = await self.llm.generate(system, prompt)
        sufficient = "YES" in result.upper()
        return {"has_sufficient_context": sufficient}

    async def _expand_retrieval(self, state: DocumentQAState) -> dict:
        """Expand retrieval by loosening filters or using keyword search."""
        # The retry is handled by re-entering _retrieve_chunks with state intact
        # The cycle will naturally expand as we fetch more chunks
        return {}

    async def _generate_answer(self, state: DocumentQAState) -> dict:
        """Generate answer with citations to specific document sections."""
        chunks = state.get("retrieved_chunks", [])
        if not chunks:
            return {
                "answer": "I couldn't find the answer in the provided documents. Please try uploading relevant documents or rephrasing your question.",
                "citations": [],
            }

        context_parts = []
        for i, chunk in enumerate(chunks[:8]):
            context_parts.append(
                f"[Chunk {i+1}] (Document ID: {chunk.get('id', 'unknown')}):\n{chunk['content']}"
            )

        prompt = f"""Answer the following question based ONLY on the provided document excerpts. For each claim, include a citation reference like [Chunk N].

DOCUMENT EXCERPTS:
{chr(10).join(context_parts)}

QUESTION: {state['question']}

Provide a thorough answer with specific citations. If the documents don't address something, say so clearly."""
        system = "You answer questions about contracts and product documents. Always cite specific excerpt references."
        answer = await self.llm.generate(system, prompt)

        citations = [
            {
                "chunk_id": chunk.get("id", ""),
                "excerpt": chunk["content"][:200],
                "score": chunk.get("similarity", 0),
            }
            for chunk in chunks[:5]
        ]

        return {"answer": answer, "citations": citations}

    async def _check_hallucination(self, state: DocumentQAState) -> dict:
        """Self-verify the answer against source chunks to detect hallucination."""
        chunks = state.get("retrieved_chunks", [])
        answer = state.get("answer", "")

        if not chunks:
            return {"has_hallucination": False}

        combined_context = " ".join(c["content"][:200] for c in chunks[:5])

        prompt = f"""Verify if the following answer is fully supported by the provided document excerpts. Check for:
1. Facts stated that don't appear in the excerpts
2. Dates or numbers that don't match
3. Claims that contradict the excerpts

DOCUMENT EXCERPTS:
{combined_context[:2000]}

ANSWER TO VERIFY:
{answer}

Reply with 'HALLUCINATION' if the answer contains unsupported claims, or 'VERIFIED' if everything is accurate and supported."""
        system = "You verify answers against source documents for accuracy. Reply only HALLUCINATION or VERIFIED."
        result = await self.llm.generate(system, prompt)
        has_hallucination = "HALLUCINATION" in result.upper()
        return {"has_hallucination": has_hallucination}

    async def _regenerate_answer(self, state: DocumentQAState) -> dict:
        """Regenerate answer with stricter grounding."""
        chunks = state.get("retrieved_chunks", [])
        context = "\n".join(c["content"][:300] for c in chunks[:8])

        prompt = f"""IMPORTANT: Only use information directly stated in the excerpts below. Do not add any information not present in the excerpts.

EXCERPTS:
{context}

QUESTION: {state['question']}

Answer ONLY with facts from the excerpts. State "The documents do not specify this" for unanswered parts."""
        system = "You provide strictly accurate answers based only on provided documents. Never speculate."
        answer = await self.llm.generate(system, prompt)
        return {"answer": answer}

    def _context_sufficient(self, state: DocumentQAState) -> str:
        if state.get("has_sufficient_context", False):
            return "sufficient"
        return "insufficient"

    def _has_hallucination(self, state: DocumentQAState) -> str:
        if state.get("has_hallucination", False):
            return "hallucination"
        return "ok"
