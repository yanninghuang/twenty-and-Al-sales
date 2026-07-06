"""API routes for general AI Chat."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_session
from app.core.security import verify_api_key
from app.services.chat_service import ChatService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/chat",
    tags=["Chat"],
    dependencies=[Depends(verify_api_key)],
)


class ChatSendRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    role: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ConversationListItem(BaseModel):
    conversation_id: str
    title: str
    message_count: int
    last_message_at: str | None = None


@router.post("", response_model=ChatResponse)
async def send_message(
    workspace_id: str,
    data: ChatSendRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send a message to the AI assistant."""
    service = ChatService(session)
    result = await service.send_message(
        workspace_id=workspace_id,
        message=data.message,
        conversation_id=data.conversation_id,
    )
    return result


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    workspace_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List all chat conversations."""
    service = ChatService(session)
    return await service.list_conversations(workspace_id)


@router.get("/conversations/{conversation_id}", response_model=list[ChatMessageResponse])
async def get_conversation(
    workspace_id: str,
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get all messages in a conversation."""
    service = ChatService(session)
    messages = await service.get_conversation(workspace_id, conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return messages


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    workspace_id: str,
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a conversation and all its messages."""
    service = ChatService(session)
    deleted = await service.delete_conversation(workspace_id, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/stream")
async def stream_message(
    workspace_id: str,
    data: ChatSendRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send a message and stream the AI response via SSE."""
    service = ChatService(session)

    async def event_generator():
        try:
            async for chunk in service.stream_response(
                workspace_id=workspace_id,
                message=data.message,
                conversation_id=data.conversation_id,
            ):
                if chunk == "[DONE]":
                    yield f"data: [DONE]\n\n"
                else:
                    yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
