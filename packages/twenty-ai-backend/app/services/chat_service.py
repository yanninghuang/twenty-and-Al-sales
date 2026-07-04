"""General chat service — free-form conversation with DeepSeek."""

import json
import uuid
from datetime import datetime

from sqlalchemy import Text, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.services.llm_service import get_llm_service


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatService:
    """Handles general AI chat conversations."""

    SYSTEM_PROMPT = """You are an AI Sales Assistant for Twenty CRM. You help sales professionals with:
- Customer relationship management
- Sales strategy and pipeline analysis
- Lead and opportunity management
- General business and sales questions

Be concise, helpful, and professional. When appropriate, suggest specific CRM actions."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.llm = get_llm_service()

    async def send_message(
        self,
        workspace_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> dict:
        """Send a message and get AI response. Creates conversation if needed."""
        conv_id = conversation_id or str(uuid.uuid4())

        # Save user message
        user_msg = ChatMessage(
            workspace_id=workspace_id,
            conversation_id=conv_id,
            role="user",
            content=message,
        )
        self.session.add(user_msg)
        await self.session.commit()

        # Fetch conversation history
        from sqlalchemy import select
        history_query = (
            select(ChatMessage)
            .where(
                ChatMessage.workspace_id == workspace_id,
                ChatMessage.conversation_id == conv_id,
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(20)
        )
        result = await self.session.execute(history_query)
        all_messages = list(result.scalars().all())

        # Build messages for LLM (last 20 for context window)
        history_for_llm = [
            {"role": msg.role, "content": msg.content}
            for msg in all_messages[:-1]  # Exclude the one we just saved
        ]

        # Generate response
        reply = await self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=message,
            messages_history=history_for_llm if history_for_llm else None,
        )

        # Save assistant message
        assistant_msg = ChatMessage(
            workspace_id=workspace_id,
            conversation_id=conv_id,
            role="assistant",
            content=reply,
        )
        self.session.add(assistant_msg)
        await self.session.commit()

        return {
            "conversation_id": conv_id,
            "message": reply,
            "role": "assistant",
        }

    async def get_conversation(
        self, workspace_id: str, conversation_id: str
    ) -> list[dict]:
        """Get all messages in a conversation."""
        from sqlalchemy import select
        query = (
            select(ChatMessage)
            .where(
                ChatMessage.workspace_id == workspace_id,
                ChatMessage.conversation_id == conversation_id,
            )
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]

    async def list_conversations(self, workspace_id: str) -> list[dict]:
        """List all conversations (latest message preview)."""
        from sqlalchemy import select, distinct
        # Get distinct conversation IDs
        subq = (
            select(
                ChatMessage.conversation_id,
                func.max(ChatMessage.created_at).label("last_msg"),
                func.count(ChatMessage.id).label("msg_count"),
            )
            .where(ChatMessage.workspace_id == workspace_id)
            .group_by(ChatMessage.conversation_id)
            .order_by(func.max(ChatMessage.created_at).desc())
            .limit(20)
        )
        result = await self.session.execute(subq)
        rows = result.all()

        conversations: list[dict] = []
        for row in rows:
            # Get the first user message as title
            first_query = (
                select(ChatMessage)
                .where(
                    ChatMessage.workspace_id == workspace_id,
                    ChatMessage.conversation_id == row[0],
                    ChatMessage.role == "user",
                )
                .order_by(ChatMessage.created_at.asc())
                .limit(1)
            )
            first_result = await self.session.execute(first_query)
            first_msg = first_result.scalar_one_or_none()

            conversations.append({
                "conversation_id": row[0],
                "title": (first_msg.content[:60] + "..." if first_msg and len(first_msg.content) > 60 else first_msg.content) or "New conversation",
                "message_count": row[2],
                "last_message_at": row[1].isoformat() if row[1] else None,
            })

        return conversations

    async def delete_conversation(self, workspace_id: str, conversation_id: str) -> bool:
        """Delete all messages in a conversation."""
        from sqlalchemy import delete
        stmt = (
            delete(ChatMessage)
            .where(
                ChatMessage.workspace_id == workspace_id,
                ChatMessage.conversation_id == conversation_id,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def stream_response(self, workspace_id: str, message: str, conversation_id: str | None = None):
        """Async generator that yields response chunks (for SSE streaming)."""
        conv_id = conversation_id or str(uuid.uuid4())

        # Save user message
        user_msg = ChatMessage(
            workspace_id=workspace_id,
            conversation_id=conv_id,
            role="user",
            content=message,
        )
        self.session.add(user_msg)
        await self.session.commit()

        # In a real streaming implementation, we'd use the LLM's streaming API.
        # For now, we yield chunks of the complete response.
        reply = await self.llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=message,
        )

        # Save and yield in chunks
        assistant_msg = ChatMessage(
            workspace_id=workspace_id,
            conversation_id=conv_id,
            role="assistant",
            content=reply,
        )
        self.session.add(assistant_msg)
        await self.session.commit()

        # Simulate streaming by yielding word chunks
        words = reply.split()
        chunk_size = max(1, len(words) // 8)
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            yield chunk + " "

        yield "[DONE]"
