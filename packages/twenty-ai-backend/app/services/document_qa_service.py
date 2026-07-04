"""Business logic for Document QA."""

from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document_qa import QADocument, QADocumentChunk, QAConversation, QAMessage
from app.agents.document_qa_agent import DocumentQAAgent
from app.services.embedding_service import embedding_service
from app.utils.chunking import chunk_text, estimate_token_count


class DocumentQAService:
    """Service for managing documents and Q&A conversations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_document(
        self,
        workspace_id: str,
        title: str,
        content_text: str,
        file_name: str | None = None,
        file_type: str | None = None,
        file_size_bytes: int | None = None,
        source_type: str = "upload",
        source_record_type: str | None = None,
        source_record_id: str | None = None,
        twenty_attachment_id: str | None = None,
        created_by: str | None = None,
    ) -> QADocument:
        """Create a QA document with chunking and embeddings."""
        document = QADocument(
            workspace_id=workspace_id,
            title=title,
            file_name=file_name,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            content_text=content_text,
            source_type=source_type,
            source_record_type=source_record_type,
            source_record_id=source_record_id,
            twenty_attachment_id=twenty_attachment_id,
            created_by=created_by,
        )
        self.session.add(document)
        await self.session.flush()

        # Chunk and embed
        chunks_text = chunk_text(content_text)
        embeddings = await embedding_service.embed_texts(chunks_text)

        for i, (chunk_content, emb) in enumerate(zip(chunks_text, embeddings)):
            chunk = QADocumentChunk(
                document_id=document.id,
                workspace_id=workspace_id,
                chunk_index=i,
                content=chunk_content,
                embedding=emb,
                token_count=estimate_token_count(chunk_content),
            )
            self.session.add(chunk)

        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def list_documents(
        self, workspace_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[QADocument], int]:
        """List documents for a workspace (excluding soft-deleted)."""
        query = (
            select(QADocument)
            .where(
                QADocument.workspace_id == workspace_id,
                QADocument.deleted_at.is_(None),
            )
            .order_by(QADocument.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(QADocument)
            .where(
                QADocument.workspace_id == workspace_id,
                QADocument.deleted_at.is_(None),
            )
        )

        result = await self.session.execute(query)
        documents = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return documents, total

    async def delete_document(self, document_id: UUID) -> bool:
        """Soft-delete a document."""
        doc = await self.session.get(QADocument, document_id)
        if not doc:
            return False
        doc.deleted_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def create_conversation(
        self,
        workspace_id: str,
        document_ids: list[UUID],
        title: str | None = None,
        created_by: str | None = None,
    ) -> QAConversation:
        """Start a new Q&A conversation."""
        conversation = QAConversation(
            workspace_id=workspace_id,
            document_ids=document_ids,
            title=title,
            created_by=created_by,
        )
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def ask_question(
        self,
        workspace_id: str,
        conversation_id: UUID,
        question: str,
    ) -> dict:
        """Ask a question in a conversation and get an answer with citations."""
        conversation = await self.session.get(QAConversation, conversation_id)
        if not conversation:
            return {"answer": "Conversation not found.", "citations": []}

        # Save user message
        user_msg = QAMessage(
            conversation_id=conversation_id,
            role="user",
            content=question,
        )
        self.session.add(user_msg)

        # Use agent for RAG
        agent = DocumentQAAgent(workspace_id)
        initial_state = {
            "workspace_id": workspace_id,
            "question": question,
            "conversation_id": str(conversation_id),
            "document_ids": [str(did) for did in conversation.document_ids],
            "error": None,
            "result": {},
        }
        result = await agent.run(initial_state)

        answer_text = result.get("answer", "Unable to generate answer.")
        citations = result.get("citations", [])

        # Save assistant message
        assistant_msg = QAMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=answer_text,
            citations=citations,
        )
        self.session.add(assistant_msg)

        conversation.updated_at = datetime.utcnow()
        await self.session.commit()

        return {
            "answer": answer_text,
            "citations": citations,
            "message_id": str(assistant_msg.id),
        }

    async def list_conversations(
        self, workspace_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[QAConversation], int]:
        """List conversations for a workspace."""
        query = (
            select(QAConversation)
            .where(QAConversation.workspace_id == workspace_id)
            .options(selectinload(QAConversation.messages))
            .order_by(QAConversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(QAConversation)
            .where(QAConversation.workspace_id == workspace_id)
        )

        result = await self.session.execute(query)
        conversations = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return conversations, total

    async def get_conversation(self, conversation_id: UUID) -> QAConversation | None:
        """Get a conversation with messages."""
        query = (
            select(QAConversation)
            .where(QAConversation.id == conversation_id)
            .options(selectinload(QAConversation.messages))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
