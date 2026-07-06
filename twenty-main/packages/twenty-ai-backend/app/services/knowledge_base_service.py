"""Business logic for AI Knowledge Base."""

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge_base import KnowledgeDocument, KnowledgeChunk
from app.schemas.knowledge_base import KnowledgeDocumentCreate, KnowledgeQueryResponse, KnowledgeQuerySource
from app.services.embedding_service import embedding_service
from app.services.vector_store import VectorStore
from app.services.llm_service import get_llm_service
from app.utils.chunking import chunk_text, estimate_token_count
from app.utils.json_helpers import to_json, embedding_to_db, from_json


class KnowledgeBaseService:
    """Service for managing knowledge base documents and queries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.vector_store = VectorStore(session)
        self.llm = get_llm_service()

    async def create_document(
        self, workspace_id: str, data: KnowledgeDocumentCreate
    ) -> KnowledgeDocument:
        """Create a document, chunk it, and generate embeddings."""
        document = KnowledgeDocument(
            workspace_id=workspace_id,
            title=data.title,
            content=data.content,
            source_type=data.source_type,
            source_record_type=data.source_record_type,
            source_record_id=data.source_record_id,
            metadata_=to_json(data.metadata) if data.metadata else None,
            created_by=data.created_by,
        )
        self.session.add(document)
        await self.session.flush()

        chunks_text = chunk_text(data.content)
        embeddings = await embedding_service.embed_texts(chunks_text)

        for i, (chunk_content, emb) in enumerate(zip(chunks_text, embeddings)):
            chunk = KnowledgeChunk(
                document_id=document.id,
                workspace_id=workspace_id,
                chunk_index=i,
                content=chunk_content,
                embedding=embedding_to_db(emb),
                token_count=estimate_token_count(chunk_content),
            )
            self.session.add(chunk)

        await self.session.commit()
        # Eagerly load chunks
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.id == document.id)
            .options(selectinload(KnowledgeDocument.chunks))
        )
        result = await self.session.execute(stmt)
        loaded = result.scalar_one()
        return loaded

    async def list_documents(
        self, workspace_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[KnowledgeDocument], int]:
        """List documents for a workspace."""
        query = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.workspace_id == workspace_id,
                KnowledgeDocument.deleted_at.is_(None),
            )
            .order_by(KnowledgeDocument.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(
                KnowledgeDocument.workspace_id == workspace_id,
                KnowledgeDocument.deleted_at.is_(None),
            )
        )

        result = await self.session.execute(query)
        documents = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return documents, total

    async def get_document(self, document_id: str) -> KnowledgeDocument | None:
        """Get a single document by ID."""
        query = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.deleted_at.is_(None),
            )
            .options(selectinload(KnowledgeDocument.chunks))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete_document(self, document_id: str) -> bool:
        """Hard-delete a document and its chunks."""
        document = await self.get_document(document_id)
        if not document:
            return False
        await self.session.delete(document)
        await self.session.commit()
        return True

    async def query(
        self,
        workspace_id: str,
        query_text: str,
        top_k: int = 5,
        conversation_id: str | None = None,
    ) -> KnowledgeQueryResponse:
        """Execute a RAG query against the knowledge base."""
        query_embedding = await embedding_service.embed_text(query_text)

        chunks = await self.vector_store.search_similar(
            table_name="knowledge_chunks",
            query_embedding=query_embedding,
            workspace_id=workspace_id,
            top_k=top_k,
        )

        if not chunks:
            return KnowledgeQueryResponse(
                answer="I couldn't find relevant information in the knowledge base. Try rephrasing your query.",
                sources=[],
                conversation_id=conversation_id,
            )

        context_parts = []
        sources = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[Source {i+1}]: {chunk['content']}")
            doc_title = "Unknown"
            doc = await self.session.get(KnowledgeChunk, chunk["id"])
            if doc:
                doc_obj = await self.session.get(KnowledgeDocument, doc.document_id)
                if doc_obj:
                    doc_title = doc_obj.title
            sources.append(
                KnowledgeQuerySource(
                    chunk_id=chunk["id"],
                    document_title=doc_title,
                    excerpt=chunk["content"][:200],
                    score=chunk["similarity"],
                )
            )

        context = "\n\n".join(context_parts)

        system = "You are an enterprise knowledge base assistant. Answer questions based only on context. Cite sources."
        prompt = f"""Answer the question based on the following context. Cite sources as [Source N].

CONTEXT:
{context}

QUESTION: {query_text}"""
        answer = await self.llm.generate(system, prompt)

        return KnowledgeQueryResponse(
            answer=answer,
            sources=sources,
            conversation_id=conversation_id,
        )
