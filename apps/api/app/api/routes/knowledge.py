import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.security import RequestContext, get_request_context
from app.db.session import get_db
from app.modules.knowledge.repository import SqlAlchemyKnowledgeRepository
from app.modules.knowledge.schemas import (
    KnowledgeDocumentEmbeddingGenerate,
    KnowledgeDocumentEmbeddingGenerateInput,
    KnowledgeDocumentEmbeddingRead,
    KnowledgeDocumentImport,
    KnowledgeDocumentImportInput,
    KnowledgeDocumentRead,
    KnowledgeSearchInput,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSpaceCreate,
    KnowledgeSpaceCreateInput,
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
    payload: KnowledgeSpaceCreateInput,
    context: RequestContext = Depends(get_request_context),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSpaceRead:
    context.require("knowledge:write")
    return service.create_space(
        KnowledgeSpaceCreate(
            **payload.model_dump(),
            tenant_id=context.tenant_id,
            created_by_user_id=context.user_id,
        )
    )


@router.post(
    "/documents/import",
    response_model=KnowledgeDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def import_knowledge_document(
    payload: KnowledgeDocumentImportInput,
    context: RequestContext = Depends(get_request_context),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocumentRead:
    context.require("knowledge:write")
    try:
        return service.import_document(
            KnowledgeDocumentImport(
                **payload.model_dump(),
                tenant_id=context.tenant_id,
                created_by_user_id=context.user_id,
            )
        )
    except KnowledgeSpaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KnowledgeImportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentRead)
def get_knowledge_document(
    document_id: uuid.UUID,
    context: RequestContext = Depends(get_request_context),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocumentRead:
    context.require("knowledge:read")
    try:
        return service.get_document(tenant_id=context.tenant_id, document_id=document_id)
    except KnowledgeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/documents/{document_id}/embeddings",
    response_model=KnowledgeDocumentEmbeddingRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_knowledge_document_embeddings(
    document_id: uuid.UUID,
    payload: KnowledgeDocumentEmbeddingGenerateInput,
    context: RequestContext = Depends(get_request_context),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDocumentEmbeddingRead:
    context.require("knowledge:write")
    try:
        return service.generate_document_embeddings(
            document_id=document_id,
            payload=KnowledgeDocumentEmbeddingGenerate(tenant_id=context.tenant_id),
        )
    except KnowledgeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KnowledgeEmbeddingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    payload: KnowledgeSearchInput,
    context: RequestContext = Depends(get_request_context),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSearchResponse:
    context.require("knowledge:read")
    try:
        return service.search(
            KnowledgeSearchRequest(
                **payload.model_dump(),
                tenant_id=context.tenant_id,
            )
        )
    except KnowledgeSearchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
