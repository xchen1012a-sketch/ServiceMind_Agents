import uuid
from datetime import UTC, datetime

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


class InMemoryKnowledgeRepository:
    def __init__(self) -> None:
        self.spaces: list[KnowledgeSpace] = []
        self.documents: list[KnowledgeDocument] = []
        self.versions: list[KnowledgeDocumentVersion] = []
        self.chunks: list[KnowledgeChunk] = []
        self.embedding_models: list[EmbeddingModel] = []
        self.chunk_embeddings: list[ChunkEmbedding] = []
        self.rag_queries: list[RagQuery] = []
        self.rag_retrieval_hits: list[RagRetrievalHit] = []
        self.commits = 0

    def add_space(self, space: KnowledgeSpace) -> None:
        self._ensure_identity(space)
        self.spaces.append(space)

    def get_space(self, tenant_id: uuid.UUID, knowledge_space_id: uuid.UUID) -> KnowledgeSpace | None:
        return next(
            (
                space
                for space in self.spaces
                if space.tenant_id == tenant_id and space.id == knowledge_space_id
            ),
            None,
        )

    def add_document(self, document: KnowledgeDocument) -> None:
        self._ensure_identity(document)
        self.documents.append(document)

    def add_version(self, version: KnowledgeDocumentVersion) -> None:
        self._ensure_identity(version)
        self.versions.append(version)

    def add_chunk(self, chunk: KnowledgeChunk) -> None:
        self._ensure_identity(chunk)
        self.chunks.append(chunk)

    def get_embedding_model(self, provider_code: str, model_name: str) -> EmbeddingModel | None:
        return next(
            (
                embedding_model
                for embedding_model in self.embedding_models
                if embedding_model.provider_code == provider_code
                and embedding_model.model_name == model_name
            ),
            None,
        )

    def add_embedding_model(self, embedding_model: EmbeddingModel) -> None:
        self._ensure_identity(embedding_model)
        self.embedding_models.append(embedding_model)

    def list_chunk_embeddings(
        self,
        tenant_id: uuid.UUID,
        chunk_ids: list[uuid.UUID],
        embedding_model_id: uuid.UUID,
    ) -> list[ChunkEmbedding]:
        return [
            chunk_embedding
            for chunk_embedding in self.chunk_embeddings
            if chunk_embedding.tenant_id == tenant_id
            and chunk_embedding.chunk_id in chunk_ids
            and chunk_embedding.embedding_model_id == embedding_model_id
        ]

    def add_chunk_embedding(self, chunk_embedding: ChunkEmbedding) -> None:
        self._ensure_identity(chunk_embedding)
        self.chunk_embeddings.append(chunk_embedding)

    def list_searchable_embeddings(
        self,
        tenant_id: uuid.UUID,
        embedding_model_id: uuid.UUID,
        knowledge_space_id: uuid.UUID | None = None,
    ) -> list[tuple[ChunkEmbedding, KnowledgeChunk, KnowledgeDocumentVersion, KnowledgeDocument]]:
        rows = []
        for chunk_embedding in self.chunk_embeddings:
            if (
                chunk_embedding.tenant_id != tenant_id
                or chunk_embedding.embedding_model_id != embedding_model_id
            ):
                continue
            chunk = next(
                (item for item in self.chunks if item.id == chunk_embedding.chunk_id),
                None,
            )
            if chunk is None:
                continue
            version = next(
                (item for item in self.versions if item.id == chunk.document_version_id),
                None,
            )
            if version is None:
                continue
            document = next(
                (item for item in self.documents if item.id == version.document_id),
                None,
            )
            if document is None:
                continue
            if knowledge_space_id is not None and document.knowledge_space_id != knowledge_space_id:
                continue
            rows.append((chunk_embedding, chunk, version, document))
        return rows

    def add_rag_query(self, rag_query: RagQuery) -> None:
        self._ensure_identity(rag_query)
        self.rag_queries.append(rag_query)

    def add_rag_retrieval_hit(self, rag_retrieval_hit: RagRetrievalHit) -> None:
        self._ensure_identity(rag_retrieval_hit)
        self.rag_retrieval_hits.append(rag_retrieval_hit)

    def get_document(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> KnowledgeDocument | None:
        return next(
            (
                document
                for document in self.documents
                if document.tenant_id == tenant_id and document.id == document_id
            ),
            None,
        )

    def get_version(
        self, tenant_id: uuid.UUID, version_id: uuid.UUID
    ) -> KnowledgeDocumentVersion | None:
        return next(
            (
                version
                for version in self.versions
                if version.tenant_id == tenant_id and version.id == version_id
            ),
            None,
        )

    def list_chunks(self, tenant_id: uuid.UUID, document_version_id: uuid.UUID) -> list[KnowledgeChunk]:
        return [
            chunk
            for chunk in sorted(self.chunks, key=lambda item: item.chunk_index)
            if chunk.tenant_id == tenant_id and chunk.document_version_id == document_version_id
        ]

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass

    def _ensure_identity(
        self,
        item: (
            KnowledgeSpace
            | KnowledgeDocument
            | KnowledgeDocumentVersion
            | KnowledgeChunk
            | EmbeddingModel
            | ChunkEmbedding
            | RagQuery
            | RagRetrievalHit
        ),
    ) -> None:
        now = datetime.now(UTC)
        if item.id is None:
            item.id = uuid.uuid4()
        if item.created_at is None:
            item.created_at = now
        if hasattr(item, "updated_at") and getattr(item, "updated_at", None) is None:
            item.updated_at = now
