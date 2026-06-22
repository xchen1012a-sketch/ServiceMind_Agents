import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeSpaceCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description_text: str | None = None
    visibility: str = Field(default="private", min_length=1, max_length=40)
    created_by_user_id: uuid.UUID | None = None


class KnowledgeSpaceRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description_text: str | None
    visibility: str
    status: str
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentImport(BaseModel):
    tenant_id: uuid.UUID
    knowledge_space_id: uuid.UUID
    title: str = Field(min_length=1, max_length=240)
    content_text: str = Field(min_length=1)
    source_type: str = Field(default="manual", min_length=1, max_length=40)
    source_uri: str | None = None
    file_name: str | None = None
    mime_type: str | None = Field(default="text/plain", max_length=120)
    created_by_user_id: uuid.UUID | None = None


class KnowledgeDocumentEmbeddingGenerate(BaseModel):
    tenant_id: uuid.UUID


class KnowledgeSearchRequest(BaseModel):
    tenant_id: uuid.UUID
    query_text: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    knowledge_space_id: uuid.UUID | None = None
    agent_run_id: uuid.UUID | None = None
    agent_run_step_id: uuid.UUID | None = None


class KnowledgeChunkRead(BaseModel):
    id: uuid.UUID
    chunk_index: int
    chunk_text: str
    token_count: int | None
    heading_path: str | None
    page_number: int | None
    source_anchor: str | None
    metadata_json: dict | None
    created_at: datetime


class KnowledgeDocumentVersionRead(BaseModel):
    id: uuid.UUID
    version_no: int
    storage_uri: str
    content_hash: str
    parser_name: str | None
    parser_version: str | None
    parse_status: str
    created_at: datetime


class KnowledgeDocumentRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    knowledge_space_id: uuid.UUID
    title: str
    source_type: str
    source_uri: str | None
    file_name: str | None
    mime_type: str | None
    status: str
    current_version_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    current_version: KnowledgeDocumentVersionRead | None
    chunks: list[KnowledgeChunkRead]


class KnowledgeEmbeddingModelRead(BaseModel):
    id: uuid.UUID
    provider_code: str
    model_name: str
    dimension: int
    status: str
    created_at: datetime


class KnowledgeChunkEmbeddingRead(BaseModel):
    id: uuid.UUID
    chunk_id: uuid.UUID
    embedding_model_id: uuid.UUID
    embedding_hash: str
    created_at: datetime


class KnowledgeDocumentEmbeddingRead(BaseModel):
    tenant_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    embedding_model: KnowledgeEmbeddingModelRead
    embeddings: list[KnowledgeChunkEmbeddingRead]
    created_count: int


class KnowledgeSearchHitRead(BaseModel):
    id: uuid.UUID
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    document_title: str
    source_uri: str | None
    rank_no: int
    similarity_score: float | None
    used_in_answer: bool
    chunk: KnowledgeChunkRead
    created_at: datetime


class KnowledgeSearchResponse(BaseModel):
    tenant_id: uuid.UUID
    rag_query_id: uuid.UUID
    query_text: str
    retrieval_params_json: dict
    hits: list[KnowledgeSearchHitRead]
