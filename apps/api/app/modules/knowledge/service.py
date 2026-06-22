import hashlib
import json
import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

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
from app.modules.knowledge.chunking import PlainTextChunker
from app.modules.knowledge.embedding import DeterministicTextEmbedder
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import (
    KnowledgeChunkEmbeddingRead,
    KnowledgeChunkRead,
    KnowledgeDocumentEmbeddingGenerate,
    KnowledgeDocumentEmbeddingRead,
    KnowledgeDocumentImport,
    KnowledgeDocumentRead,
    KnowledgeDocumentVersionRead,
    KnowledgeEmbeddingModelRead,
    KnowledgeSearchHitRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSpaceCreate,
    KnowledgeSpaceRead,
)


class KnowledgeSpaceNotFoundError(Exception):
    pass


class KnowledgeDocumentNotFoundError(Exception):
    pass


class KnowledgeImportError(Exception):
    pass


class KnowledgeEmbeddingError(Exception):
    pass


class KnowledgeSearchError(Exception):
    pass


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        chunker: PlainTextChunker | None = None,
    ) -> None:
        self.repository = repository
        self.chunker = chunker or PlainTextChunker()

    def create_space(self, payload: KnowledgeSpaceCreate) -> KnowledgeSpaceRead:
        space = KnowledgeSpace(
            tenant_id=payload.tenant_id,
            name=payload.name,
            description_text=payload.description_text,
            visibility=payload.visibility,
            status="active",
            created_by_user_id=payload.created_by_user_id,
        )
        self.repository.add_space(space)
        self.repository.commit()
        return self._space_to_read(space)

    def import_document(self, payload: KnowledgeDocumentImport) -> KnowledgeDocumentRead:
        space = self.repository.get_space(payload.tenant_id, payload.knowledge_space_id)
        if space is None:
            raise KnowledgeSpaceNotFoundError("knowledge space not found")

        parsed_chunks = self.chunker.split(payload.content_text)
        if not parsed_chunks:
            raise KnowledgeImportError("document did not produce chunks")

        now = datetime.now(UTC)
        content_hash = hashlib.sha256(payload.content_text.encode("utf-8")).hexdigest()
        document = KnowledgeDocument(
            tenant_id=payload.tenant_id,
            knowledge_space_id=space.id,
            title=payload.title,
            source_type=payload.source_type,
            source_uri=payload.source_uri,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            status="ready",
            created_by_user_id=payload.created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self.repository.add_document(document)

        version = KnowledgeDocumentVersion(
            tenant_id=payload.tenant_id,
            document_id=document.id,
            version_no=1,
            storage_uri=f"inline://sha256/{content_hash}",
            content_hash=content_hash,
            parser_name=self.chunker.parser_name,
            parser_version=self.chunker.parser_version,
            parse_status="completed",
            created_at=now,
        )
        self.repository.add_version(version)
        document.current_version_id = version.id

        for parsed_chunk in parsed_chunks:
            self.repository.add_chunk(
                KnowledgeChunk(
                    tenant_id=payload.tenant_id,
                    document_version_id=version.id,
                    chunk_index=parsed_chunk.chunk_index,
                    chunk_text=parsed_chunk.chunk_text,
                    token_count=parsed_chunk.token_count,
                    heading_path=parsed_chunk.heading_path,
                    page_number=None,
                    source_anchor=parsed_chunk.source_anchor,
                    metadata_json=parsed_chunk.metadata_json,
                    created_at=now,
                )
            )

        self.repository.commit()
        return self.get_document(payload.tenant_id, document.id)

    def get_document(self, tenant_id: uuid.UUID, document_id: uuid.UUID) -> KnowledgeDocumentRead:
        document = self.repository.get_document(tenant_id=tenant_id, document_id=document_id)
        if document is None:
            raise KnowledgeDocumentNotFoundError("knowledge document not found")
        return self._document_to_read(document)

    def generate_document_embeddings(
        self,
        document_id: uuid.UUID,
        payload: KnowledgeDocumentEmbeddingGenerate,
    ) -> KnowledgeDocumentEmbeddingRead:
        document = self.repository.get_document(tenant_id=payload.tenant_id, document_id=document_id)
        if document is None:
            raise KnowledgeDocumentNotFoundError("knowledge document not found")
        if document.current_version_id is None:
            raise KnowledgeEmbeddingError("knowledge document has no current version")

        version = self.repository.get_version(payload.tenant_id, document.current_version_id)
        if version is None:
            raise KnowledgeEmbeddingError("knowledge document version not found")

        chunks = self.repository.list_chunks(payload.tenant_id, version.id)
        if not chunks:
            raise KnowledgeEmbeddingError("knowledge document has no chunks")

        embedder = DeterministicTextEmbedder()
        embedding_model = self.repository.get_embedding_model(
            provider_code=embedder.provider_code,
            model_name=embedder.model_name,
        )
        if embedding_model is None:
            embedding_model = EmbeddingModel(
                provider_code=embedder.provider_code,
                model_name=embedder.model_name,
                dimension=embedder.dimension,
                status="active",
            )
            self.repository.add_embedding_model(embedding_model)
        if embedding_model.dimension != embedder.dimension:
            raise KnowledgeEmbeddingError("embedding model dimension mismatch")

        chunk_ids = [chunk.id for chunk in chunks]
        existing_embeddings = self.repository.list_chunk_embeddings(
            tenant_id=payload.tenant_id,
            chunk_ids=chunk_ids,
            embedding_model_id=embedding_model.id,
        )
        existing_by_chunk_id = {
            chunk_embedding.chunk_id: chunk_embedding for chunk_embedding in existing_embeddings
        }

        created_count = 0
        embeddings = list(existing_embeddings)
        now = datetime.now(UTC)
        for chunk in chunks:
            if chunk.id in existing_by_chunk_id:
                continue
            embedded = embedder.embed(chunk.chunk_text)
            chunk_embedding = ChunkEmbedding(
                tenant_id=payload.tenant_id,
                chunk_id=chunk.id,
                embedding_model_id=embedding_model.id,
                embedding_vector=embedded.vector,
                embedding_hash=embedded.embedding_hash,
                created_at=now,
            )
            self.repository.add_chunk_embedding(chunk_embedding)
            embeddings.append(chunk_embedding)
            created_count += 1

        self.repository.commit()
        embeddings.sort(key=lambda item: chunk_ids.index(item.chunk_id))
        return KnowledgeDocumentEmbeddingRead(
            tenant_id=payload.tenant_id,
            document_id=document.id,
            document_version_id=version.id,
            embedding_model=self._embedding_model_to_read(embedding_model),
            embeddings=[self._chunk_embedding_to_read(embedding) for embedding in embeddings],
            created_count=created_count,
        )

    def search(self, payload: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        embedder = DeterministicTextEmbedder()
        retrieval_params = {
            "top_k": payload.top_k,
            "provider_code": embedder.provider_code,
            "model_name": embedder.model_name,
            "knowledge_space_id": str(payload.knowledge_space_id)
            if payload.knowledge_space_id is not None
            else None,
        }
        rag_query = RagQuery(
            tenant_id=payload.tenant_id,
            agent_run_id=payload.agent_run_id,
            agent_run_step_id=payload.agent_run_step_id,
            query_text=payload.query_text,
            retrieval_params_json=retrieval_params,
            created_at=datetime.now(UTC),
        )
        self.repository.add_rag_query(rag_query)

        embedding_model = self.repository.get_embedding_model(
            provider_code=embedder.provider_code,
            model_name=embedder.model_name,
        )
        if embedding_model is None:
            self.repository.commit()
            return KnowledgeSearchResponse(
                tenant_id=payload.tenant_id,
                rag_query_id=rag_query.id,
                query_text=payload.query_text,
                retrieval_params_json=retrieval_params,
                hits=[],
            )
        if embedding_model.dimension != embedder.dimension:
            raise KnowledgeSearchError("embedding model dimension mismatch")

        query_vector = embedder.embed(payload.query_text).vector
        candidates = []
        for chunk_embedding, chunk, version, document in self.repository.list_searchable_embeddings(
            tenant_id=payload.tenant_id,
            embedding_model_id=embedding_model.id,
            knowledge_space_id=payload.knowledge_space_id,
        ):
            score = self._cosine_similarity(
                query_vector,
                self._vector_to_floats(chunk_embedding.embedding_vector),
            )
            candidates.append((score, chunk_embedding, chunk, version, document))
        candidates.sort(key=lambda item: item[0], reverse=True)

        hits: list[KnowledgeSearchHitRead] = []
        now = datetime.now(UTC)
        for rank_no, (score, _chunk_embedding, chunk, version, document) in enumerate(
            candidates[: payload.top_k], start=1
        ):
            rag_hit = RagRetrievalHit(
                tenant_id=payload.tenant_id,
                rag_query_id=rag_query.id,
                chunk_id=chunk.id,
                rank_no=rank_no,
                similarity_score=Decimal(f"{score:.6f}"),
                rerank_score=None,
                used_in_answer=payload.used_in_answer,
                created_at=now,
            )
            self.repository.add_rag_retrieval_hit(rag_hit)
            hits.append(
                self._search_hit_to_read(
                    rag_hit=rag_hit,
                    chunk=chunk,
                    version=version,
                    document=document,
                )
            )

        self.repository.commit()
        return KnowledgeSearchResponse(
            tenant_id=payload.tenant_id,
            rag_query_id=rag_query.id,
            query_text=payload.query_text,
            retrieval_params_json=retrieval_params,
            hits=hits,
        )

    def _space_to_read(self, space: KnowledgeSpace) -> KnowledgeSpaceRead:
        return KnowledgeSpaceRead(
            id=space.id,
            tenant_id=space.tenant_id,
            name=space.name,
            description_text=space.description_text,
            visibility=space.visibility,
            status=space.status,
            created_by_user_id=space.created_by_user_id,
            created_at=space.created_at,
            updated_at=space.updated_at,
        )

    def _document_to_read(self, document: KnowledgeDocument) -> KnowledgeDocumentRead:
        version = None
        chunks = []
        if document.current_version_id is not None:
            version = self.repository.get_version(document.tenant_id, document.current_version_id)
        if version is not None:
            chunks = self.repository.list_chunks(document.tenant_id, version.id)

        return KnowledgeDocumentRead(
            id=document.id,
            tenant_id=document.tenant_id,
            knowledge_space_id=document.knowledge_space_id,
            title=document.title,
            source_type=document.source_type,
            source_uri=document.source_uri,
            file_name=document.file_name,
            mime_type=document.mime_type,
            status=document.status,
            current_version_id=document.current_version_id,
            created_by_user_id=document.created_by_user_id,
            created_at=document.created_at,
            updated_at=document.updated_at,
            current_version=self._version_to_read(version) if version is not None else None,
            chunks=[self._chunk_to_read(chunk) for chunk in chunks],
        )

    def _version_to_read(
        self, version: KnowledgeDocumentVersion
    ) -> KnowledgeDocumentVersionRead:
        return KnowledgeDocumentVersionRead(
            id=version.id,
            version_no=version.version_no,
            storage_uri=version.storage_uri,
            content_hash=version.content_hash,
            parser_name=version.parser_name,
            parser_version=version.parser_version,
            parse_status=version.parse_status,
            created_at=version.created_at,
        )

    def _chunk_to_read(self, chunk: KnowledgeChunk) -> KnowledgeChunkRead:
        return KnowledgeChunkRead(
            id=chunk.id,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.chunk_text,
            token_count=chunk.token_count,
            heading_path=chunk.heading_path,
            page_number=chunk.page_number,
            source_anchor=chunk.source_anchor,
            metadata_json=chunk.metadata_json,
            created_at=chunk.created_at,
        )

    def _embedding_model_to_read(self, embedding_model: EmbeddingModel) -> KnowledgeEmbeddingModelRead:
        return KnowledgeEmbeddingModelRead(
            id=embedding_model.id,
            provider_code=embedding_model.provider_code,
            model_name=embedding_model.model_name,
            dimension=embedding_model.dimension,
            status=embedding_model.status,
            created_at=embedding_model.created_at,
        )

    def _chunk_embedding_to_read(
        self, chunk_embedding: ChunkEmbedding
    ) -> KnowledgeChunkEmbeddingRead:
        return KnowledgeChunkEmbeddingRead(
            id=chunk_embedding.id,
            chunk_id=chunk_embedding.chunk_id,
            embedding_model_id=chunk_embedding.embedding_model_id,
            embedding_hash=chunk_embedding.embedding_hash,
            created_at=chunk_embedding.created_at,
        )

    def _search_hit_to_read(
        self,
        rag_hit: RagRetrievalHit,
        chunk: KnowledgeChunk,
        version: KnowledgeDocumentVersion,
        document: KnowledgeDocument,
    ) -> KnowledgeSearchHitRead:
        return KnowledgeSearchHitRead(
            id=rag_hit.id,
            chunk_id=rag_hit.chunk_id,
            document_id=document.id,
            document_version_id=version.id,
            document_title=document.title,
            source_uri=document.source_uri,
            rank_no=rag_hit.rank_no,
            similarity_score=float(rag_hit.similarity_score)
            if rag_hit.similarity_score is not None
            else None,
            used_in_answer=rag_hit.used_in_answer,
            chunk=self._chunk_to_read(chunk),
            created_at=rag_hit.created_at,
        )

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            raise KnowledgeSearchError("embedding vector dimension mismatch")
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        score = sum(
            left_value * right_value for left_value, right_value in zip(left, right, strict=True)
        ) / (left_norm * right_norm)
        return max(min(score, 1.0), -1.0)

    def _vector_to_floats(self, vector: object) -> list[float]:
        if isinstance(vector, str):
            parsed = json.loads(vector)
            return [float(value) for value in parsed]
        return [float(value) for value in vector]
