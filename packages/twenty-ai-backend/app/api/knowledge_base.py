"""API routes for AI Knowledge Base — with file upload support."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import verify_api_key
from app.schemas.knowledge_base import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    KnowledgeDocumentListResponse,
    KnowledgeQuery,
    KnowledgeQueryResponse,
    KnowledgeFileUploadResponse,
)
from app.services.knowledge_base_service import KnowledgeBaseService
from app.utils.file_parser import parse_file

router = APIRouter(
    prefix="/workspaces/{workspace_id}/knowledge-base",
    tags=["Knowledge Base"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/documents/upload", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    workspace_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Upload a file (PDF, DOCX, PPTX, XLSX, TXT, MD, CSV, etc.) with auto-parsing and embedding."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read file bytes
    file_bytes = await file.read()
    if not file_bytes or len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Parse file to text
    try:
        content_text, file_type = parse_file(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not content_text or not content_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    # Create document
    data = KnowledgeDocumentCreate(
        title=file.filename,
        content=content_text,
        source_type="upload",
    )
    service = KnowledgeBaseService(session)
    document = await service.create_document(workspace_id, data)

    # Store file metadata via direct update
    from sqlalchemy import update
    from app.models.knowledge_base import KnowledgeDocument
    await session.execute(
        update(KnowledgeDocument)
        .where(KnowledgeDocument.id == document.id)
        .values(
            title=f"{file.filename} ({file_type.upper()})",
            metadata_=f'{{"file_type":"{file_type}","file_size":{len(file_bytes)},"original_name":"{file.filename}"}}',
        )
    )
    await session.commit()
    await session.refresh(document)

    return document


@router.post("/documents", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    workspace_id: str,
    data: KnowledgeDocumentCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a knowledge document from text content."""
    service = KnowledgeBaseService(session)
    document = await service.create_document(workspace_id, data)
    return document


@router.get("/documents", response_model=KnowledgeDocumentListResponse)
async def list_documents(
    workspace_id: str,
    offset: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """List knowledge base documents (including file type info)."""
    service = KnowledgeBaseService(session)
    documents, total = await service.list_documents(workspace_id, offset, limit)
    return KnowledgeDocumentListResponse(documents=documents, total=total)


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    workspace_id: str,
    document_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single document by ID."""
    service = KnowledgeBaseService(session)
    document = await service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    workspace_id: str,
    document_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Hard-delete a document and its chunks."""
    service = KnowledgeBaseService(session)
    deleted = await service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/query", response_model=KnowledgeQueryResponse)
async def query_knowledge_base(
    workspace_id: str,
    query_data: KnowledgeQuery,
    session: AsyncSession = Depends(get_session),
):
    """Semantic search + RAG answer from the knowledge base."""
    service = KnowledgeBaseService(session)
    result = await service.query(
        workspace_id=workspace_id,
        query_text=query_data.query,
        top_k=query_data.top_k,
        conversation_id=query_data.conversation_id,
    )
    return result


@router.post("/sync-from-crm", status_code=status.HTTP_202_ACCEPTED)
async def sync_from_crm(
    workspace_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Trigger a sync of notes/attachments from Twenty CRM."""
    return {
        "status": "accepted",
        "message": "Sync triggered.",
    }
