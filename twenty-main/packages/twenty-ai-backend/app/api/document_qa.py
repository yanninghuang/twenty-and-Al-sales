"""API routes for Document QA — with file upload support."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_session
from app.core.security import verify_api_key
from app.schemas.document_qa import (
    QADocumentCreate,
    QADocumentResponse,
    QADocumentListResponse,
    QAConversationCreate,
    QAConversationResponse,
    QAConversationListResponse,
    QAMessageCreate,
    QAMessageResponse,
)
from app.utils.file_parser import parse_file
from app.services.document_qa_service import DocumentQAService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/document-qa",
    tags=["Document QA"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/documents/upload", response_model=QADocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_file(
    workspace_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Upload a file (PDF, DOCX, TXT, etc.) for Document Q&A with auto-parsing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        content_text, file_type = parse_file(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not content_text or not content_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    service = DocumentQAService(session)
    document = await service.create_document(
        workspace_id=workspace_id,
        title=f"{file.filename} ({file_type.upper()})",
        content_text=content_text,
        file_name=file.filename,
        file_type=file_type,
        file_size_bytes=len(file_bytes),
    )
    return document


@router.post("/documents", response_model=QADocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    workspace_id: str,
    data: QADocumentCreate,
    session: AsyncSession = Depends(get_session),
):
    """Upload a document for Q&A from text content."""
    service = DocumentQAService(session)
    document = await service.create_document(
        workspace_id=workspace_id,
        title=data.title,
        content_text=data.content_text,
        file_name=data.file_name,
        file_type=data.file_type,
        file_size_bytes=data.file_size_bytes,
        source_type=data.source_type,
        source_record_type=data.source_record_type,
        source_record_id=data.source_record_id,
        twenty_attachment_id=data.twenty_attachment_id,
        created_by=data.created_by,
    )
    return document


@router.get("/documents", response_model=QADocumentListResponse)
async def list_documents(
    workspace_id: str,
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """List QA documents."""
    service = DocumentQAService(session)
    documents, total = await service.list_documents(workspace_id, offset, limit)
    return QADocumentListResponse(documents=documents, total=total)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    workspace_id: str,
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Remove a QA document."""
    service = DocumentQAService(session)
    deleted = await service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/conversations", response_model=QAConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    workspace_id: str,
    data: QAConversationCreate,
    session: AsyncSession = Depends(get_session),
):
    """Start a new Q&A conversation scoped to specific documents."""
    service = DocumentQAService(session)
    conversation = await service.create_conversation(
        workspace_id=workspace_id,
        document_ids=data.document_ids,
        title=data.title,
    )
    return conversation


@router.get("/conversations", response_model=QAConversationListResponse)
async def list_conversations(
    workspace_id: str,
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """List Q&A conversations."""
    service = DocumentQAService(session)
    conversations, total = await service.list_conversations(workspace_id, offset, limit)
    return QAConversationListResponse(conversations=conversations, total=total)


@router.get("/conversations/{conversation_id}", response_model=QAConversationResponse)
async def get_conversation(
    workspace_id: str,
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a conversation with all messages."""
    service = DocumentQAService(session)
    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/conversations/{conversation_id}/messages", response_model=QAMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    workspace_id: str,
    conversation_id: UUID,
    data: QAMessageCreate,
    session: AsyncSession = Depends(get_session),
):
    """Send a question and get an AI-generated answer with citations."""
    service = DocumentQAService(session)
    result = await service.ask_question(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        question=data.content,
    )
    # Fetch the last assistant message
    from uuid import UUID as PyUUID
    conversation = await service.get_conversation(conversation_id)
    if conversation and conversation.messages:
        return conversation.messages[-1]
    raise HTTPException(status_code=500, detail="Failed to retrieve answer")


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    workspace_id: str,
    conversation_id: UUID,
    data: QAMessageCreate,
    session: AsyncSession = Depends(get_session),
):
    """Send a question and stream the answer via SSE."""
    service = DocumentQAService(session)

    async def event_generator():
        try:
            result = await service.ask_question(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                question=data.content,
            )
            answer = result["answer"]
            citations = result.get("citations", [])

            # Simulate streaming by chunking the answer
            words = answer.split()
            chunk_size = max(1, len(words) // 10)
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i : i + chunk_size])
                yield {"event": "text", "data": chunk}

            # Send citations at the end
            import json
            yield {
                "event": "citation",
                "data": json.dumps(citations),
            }
            yield {"event": "done", "data": ""}

        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
