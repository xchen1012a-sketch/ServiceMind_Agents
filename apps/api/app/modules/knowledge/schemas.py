import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.input_security import validate_business_text, validate_stored_source_uri


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


KnowledgeVisibility = Literal["private", "internal", "public"]
KnowledgeSourceType = Literal["manual", "file_upload", "api_import"]
KnowledgeMimeType = Literal["text/plain", "text/markdown", "application/json"]


class KnowledgeSpaceCreateInput(StrictInputModel):
    name: str = Field(min_length=1, max_length=200)
    description_text: str | None = Field(default=None, max_length=4_000)
    visibility: KnowledgeVisibility = "private"

    @field_validator("name", "description_text")
    @classmethod
    def validate_text_fields(cls, value: str | None) -> str | None:
        return validate_business_text(value)


class KnowledgeSpaceCreate(KnowledgeSpaceCreateInput):
    tenant_id: uuid.UUID
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


class KnowledgeDocumentImportInput(StrictInputModel):
    knowledge_space_id: uuid.UUID
    title: str = Field(min_length=1, max_length=240)
    content_text: str = Field(min_length=1, max_length=200_000)
    source_type: KnowledgeSourceType = "manual"
    source_uri: str | None = Field(default=None, max_length=500)
    file_name: str | None = Field(default=None, max_length=240)
    mime_type: KnowledgeMimeType | None = "text/plain"

    @field_validator("title", "content_text", "file_name")
    @classmethod
    def validate_text_fields(cls, value: str | None) -> str | None:
        return validate_business_text(value)

    @field_validator("source_uri")
    @classmethod
    def validate_source_uri(cls, value: str | None) -> str | None:
        return validate_stored_source_uri(value)


class KnowledgeDocumentImport(KnowledgeDocumentImportInput):
    tenant_id: uuid.UUID
    created_by_user_id: uuid.UUID | None = None


class KnowledgeDocumentEmbeddingGenerateInput(StrictInputModel):
    pass


class KnowledgeDocumentEmbeddingGenerate(BaseModel):
    tenant_id: uuid.UUID


class KnowledgeSearchInput(StrictInputModel):
    query_text: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=20)
    knowledge_space_id: uuid.UUID | None = None

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, value: str) -> str:
        validated = validate_business_text(value)
        if validated is None:
            raise ValueError("query_text is required")
        return validated


class KnowledgeSearchRequest(KnowledgeSearchInput):
    tenant_id: uuid.UUID
    agent_run_id: uuid.UUID | None = None
    agent_run_step_id: uuid.UUID | None = None
    used_in_answer: bool = False


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
