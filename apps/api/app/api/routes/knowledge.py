import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.knowledge.repository import SqlAlchemyKnowledgeRepository
from app.modules.knowledge.schemas import (
    KnowledgeDocumentEmbeddingGenerate,
    KnowledgeDocumentEmbeddingRead,
    KnowledgeDocumentImport,
    KnowledgeDocumentRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSpaceCreate,
    KnowledgeSpaceRead,
)
from app.modules.knowledge.service import (
    KnowledgeDocumentNotFoundError,
    KnowledgeEmbeddingError,
    KnowledgeImportError,
    KnowledgeSearchError,
    KnowledgeService,
    KnowledgeSpaceNotFoundError,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(SqlAlchemyKnowledgeRepository(db))


@router.post("/spaces", response_model=KnowledgeSpaceRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_space(
    payload: KnowledgeSpaceCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSpaceRead:
    return service.create_space(payload)


@router.post(
    "/documents/import",
    response_model=KnowledgeDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def import_knowledge_document(
    payload: KnowledgeDocumentImport,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocumentRead:
    try:
        return service.import_document(payload)
    except KnowledgeSpaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KnowledgeImportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentRead)
def get_knowledge_document(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Query(...),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocumentRead:
    try:
        return service.get_document(tenant_id=tenant_id, document_id=document_id)
    except KnowledgeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/documents/{document_id}/embeddings",
    response_model=KnowledgeDocumentEmbeddingRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_knowledge_document_embeddings(
    document_id: uuid.UUID,
    payload: KnowledgeDocumentEmbeddingGenerate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocumentEmbeddingRead:
    try:
        return service.generate_document_embeddings(document_id=document_id, payload=payload)
    except KnowledgeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KnowledgeEmbeddingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    payload: KnowledgeSearchRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSearchResponse:
    try:
        return service.search(payload)
    except KnowledgeSearchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
