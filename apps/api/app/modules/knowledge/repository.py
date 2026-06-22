import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ChunkEmbedding,
    EmbeddingModel,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeSpace,
    RagQuery,
    RagRetrievalHit,
)


class KnowledgeRepository(Protocol):
    def add_space(self, space: KnowledgeSpace) -> None: ...

    def get_space(self, tenant_id: uuid.UUID, knowledge_space_id: uuid.UUID) -> KnowledgeSpace | None: ...

    def add_document(self, document: KnowledgeDocument) -> None: ...

    def add_version(self, version: KnowledgeDocumentVersion) -> None: ...

    def add_chunk(self, chunk: KnowledgeChunk) -> None: ...

    def get_embedding_model(self, provider_code: str, model_name: str) -> EmbeddingModel | None: ...

    def add_embedding_model(self, embedding_model: EmbeddingModel) -> None: ...

    def list_chunk_embeddings(
        self,
        tenant_id: uuid.UUID,
        chunk_ids: list[uuid.UUID],
        embedding_model_id: uuid.UUID,
    ) -> list[ChunkEmbedding]: ...

    def add_chunk_embedding(self, chunk_embedding: ChunkEmbedding) -> None: ...

    def list_searchable_embeddings(
        self,
        tenant_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
        knowledge_space_id: uuid.UUID | None = None,
    ) -> list[tuple[ChunkEmbedding, KnowledgeChunk, KnowledgeDocumentVersion, KnowledgeDocument]]: ...

    def add_rag_query(self, rag_query: RagQuery) -> None: ...

    def add_rag_retrieval_hit(self, rag_retrieval_hit: RagRetrievalHit) -> None: ...

    def get_document(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> KnowledgeDocument | None: ...

    def get_version(
        self, tenant_id: uuid.UUID, version_id: uuid.UUID
    ) -> KnowledgeDocumentVersion | None: ...

    def list_chunks(self, tenant_id: uuid.UUID, document_version_id: uuid.UUID) -> list[KnowledgeChunk]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class SqlAlchemyKnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_space(self, space: KnowledgeSpace) -> None:
        self.db.add(space)
        self.db.flush()

    def get_space(self, tenant_id: uuid.UUID, knowledge_space_id: uuid.UUID) -> KnowledgeSpace | None:
        statement = select(KnowledgeSpace).where(
            KnowledgeSpace.tenant_id == tenant_id,
            KnowledgeSpace.id == knowledge_space_id,
            KnowledgeSpace.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def add_document(self, document: KnowledgeDocument) -> None:
        self.db.add(document)
        self.db.flush()

    def add_version(self, version: KnowledgeDocumentVersion) -> None:
        self.db.add(version)
        self.db.flush()

    def add_chunk(self, chunk: KnowledgeChunk) -> None:
        self.db.add(chunk)
        self.db.flush()

    def get_embedding_model(self, provider_code: str, model_name: str) -> EmbeddingModel | None:
        statement = (
            select(EmbeddingModel)
            .where(
                EmbeddingModel.provider_code == provider_code,
                EmbeddingModel.model_name == model_name,
            )
            .order_by(EmbeddingModel.created_at.asc())
        )
        return self.db.scalar(statement)

    def add_embedding_model(self, embedding_model: EmbeddingModel) -> None:
        self.db.add(embedding_model)
        self.db.flush()

    def list_chunk_embeddings(
        self,
        tenant_id: uuid.UUID,
        chunk_ids: list[uuid.UUID],
        embedding_model_id: uuid.UUID,
    ) -> list[ChunkEmbedding]:
        if not chunk_ids:
            return []
        statement = select(ChunkEmbedding).where(
            ChunkEmbedding.tenant_id == tenant_id,
            ChunkEmbedding.chunk_id.in_(chunk_ids),
            ChunkEmbedding.embedding_model_id == embedding_model_id,
        )
        return list(self.db.scalars(statement).all())

    def add_chunk_embedding(self, chunk_embedding: ChunkEmbedding) -> None:
        self.db.add(chunk_embedding)
        self.db.flush()

    def list_searchable_embeddings(
        self,
        tenant_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
        knowledge_space_id: uuid.UUID | None = None,
    ) -> list[tuple[ChunkEmbedding, KnowledgeChunk, KnowledgeDocumentVersion, KnowledgeDocument]]:
        statement = (
            select(ChunkEmbedding, KnowledgeChunk, KnowledgeDocumentVersion, KnowledgeDocument)
            .join(KnowledgeChunk, KnowledgeChunk.id == ChunkEmbedding.chunk_id)
            .join(
                KnowledgeDocumentVersion,
                KnowledgeDocumentVersion.id == KnowledgeChunk.document_version_id,
            )
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeDocumentVersion.document_id)
            .where(
                ChunkEmbedding.tenant_id == tenant_id,
                ChunkEmbedding.embedding_model_id == embedding_model_id,
                KnowledgeDocument.deleted_at.is_(None),
            )
        )
        if knowledge_space_id is not None:
            statement = statement.where(KnowledgeDocument.knowledge_space_id == knowledge_space_id)
        return list(self.db.execute(statement).all())

    def add_rag_query(self, rag_query: RagQuery) -> None:
        self.db.add(rag_query)
        self.db.flush()

    def add_rag_retrieval_hit(self, rag_retrieval_hit: RagRetrievalHit) -> None:
        self.db.add(rag_retrieval_hit)
        self.db.flush()

    def get_document(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> KnowledgeDocument | None:
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.tenant_id == tenant_id,
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def get_version(
        self, tenant_id: uuid.UUID, version_id: uuid.UUID
    ) -> KnowledgeDocumentVersion | None:
        statement = select(KnowledgeDocumentVersion).where(
            KnowledgeDocumentVersion.tenant_id == tenant_id,
            KnowledgeDocumentVersion.id == version_id,
        )
        return self.db.scalar(statement)

    def list_chunks(self, tenant_id: uuid.UUID, document_version_id: uuid.UUID) -> list[KnowledgeChunk]:
        statement = (
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.tenant_id == tenant_id,
                KnowledgeChunk.document_version_id == document_version_id,
            )
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        return list(self.db.scalars(statement).all())

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
