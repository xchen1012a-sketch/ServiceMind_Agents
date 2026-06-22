import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import UserDefinedType

from app.db.base import Base


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimension: int | None = None) -> None:
        self.dimension = dimension

    def get_col_spec(self, **kw: Any) -> str:
        if self.dimension is None:
            return "vector"
        return f"vector({self.dimension})"


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Tenant(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    status: Mapped[str] = mapped_column(Text)


class User(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Role(Base, IdMixin, TimestampMixin):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text)


class Permission(Base, IdMixin, TimestampMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)


class RolePermission(Base, IdMixin):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permissions"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserRole(Base, IdMixin):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Ticket(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ticket_no", name="uq_tickets_tenant_ticket_no"),
        Index("ix_tickets_tenant_status_created_at", "tenant_id", "status", "created_at"),
        Index("ix_tickets_tenant_category_created_at", "tenant_id", "category_code", "created_at"),
        Index("ix_tickets_tenant_risk_created_at", "tenant_id", "risk_level", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    ticket_no: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    description_text: Mapped[str] = mapped_column(Text)
    category_code: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    source_channel: Mapped[str] = mapped_column(Text)
    requester_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    requester_contact: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class TicketMessage(Base, IdMixin):
    __tablename__ = "ticket_messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"))
    sender_type: Mapped[str] = mapped_column(Text)
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    message_text: Mapped[str] = mapped_column(Text)
    message_format: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentGraphVersion(Base, IdMixin):
    __tablename__ = "agent_graph_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "graph_name", "graph_version", name="uq_agent_graph_versions"
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    runtime_type: Mapped[str] = mapped_column(Text)
    graph_name: Mapped[str] = mapped_column(Text)
    graph_version: Mapped[str] = mapped_column(Text)
    definition_hash: Mapped[str] = mapped_column(Text)
    definition_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Base, IdMixin):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_tenant_ticket_created_at", "tenant_id", "ticket_id", "created_at"),
        Index("ix_agent_runs_tenant_status_created_at", "tenant_id", "status", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    runtime_type: Mapped[str] = mapped_column(Text)
    graph_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_graph_versions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    total_completion_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    total_cost_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), server_default="0")
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TicketStatusEvent(Base, IdMixin):
    __tablename__ = "ticket_status_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"))
    from_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_status: Mapped[str] = mapped_column(Text)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_type: Mapped[str] = mapped_column(Text)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentRunStep(Base, IdMixin):
    __tablename__ = "agent_run_steps"
    __table_args__ = (
        UniqueConstraint("agent_run_id", "step_order", name="uq_agent_run_steps_order"),
        Index("ix_agent_run_steps_tenant_run_order", "tenant_id", "agent_run_id", "step_order"),
        Index("ix_agent_run_steps_tenant_type_status", "tenant_id", "step_type", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    agent_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id"))
    step_name: Mapped[str] = mapped_column(Text)
    step_type: Mapped[str] = mapped_column(Text)
    step_order: Mapped[int] = mapped_column(Integer)
    external_step_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text)
    input_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelInvocation(Base, IdMixin):
    __tablename__ = "model_invocations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    agent_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id"))
    agent_run_step_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_run_steps.id"), nullable=True
    )
    provider_code: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(Text)
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id"), nullable=True
    )
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), server_default="0")
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeSpace(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "knowledge_spaces"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class KnowledgeDocument(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "knowledge_documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    knowledge_space_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_spaces.id"))
    title: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class KnowledgeDocumentVersion(Base, IdMixin):
    __tablename__ = "knowledge_document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_no", name="uq_document_versions"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_documents.id"))
    version_no: Mapped[int] = mapped_column(Integer)
    storage_uri: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    parser_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeChunk(Base, IdMixin):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_version_id", "chunk_index", name="uq_knowledge_chunks"),
        Index(
            "ix_knowledge_chunks_tenant_version_index",
            "tenant_id",
            "document_version_id",
            "chunk_index",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    document_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_document_versions.id"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_anchor: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmbeddingModel(Base, IdMixin):
    __tablename__ = "embedding_models"

    provider_code: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(Text)
    dimension: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChunkEmbedding(Base, IdMixin):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "embedding_model_id", name="uq_chunk_embeddings"),
        Index("ix_chunk_embeddings_chunk_id", "chunk_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_chunks.id"))
    embedding_model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("embedding_models.id"))
    embedding_vector: Mapped[Any] = mapped_column(Vector())
    embedding_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RagQuery(Base, IdMixin):
    __tablename__ = "rag_queries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    agent_run_step_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_run_steps.id"), nullable=True
    )
    query_text: Mapped[str] = mapped_column(Text)
    retrieval_params_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RagRetrievalHit(Base, IdMixin):
    __tablename__ = "rag_retrieval_hits"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    rag_query_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rag_queries.id"))
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_chunks.id"))
    rank_no: Mapped[int] = mapped_column(Integer)
    similarity_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    rerank_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    used_in_answer: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class McpServer(Base, IdMixin, TimestampMixin):
    __tablename__ = "mcp_servers"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_mcp_servers_tenant_code"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    transport_type: Mapped[str] = mapped_column(Text)
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text)


class McpTool(Base, IdMixin, TimestampMixin):
    __tablename__ = "mcp_tools"
    __table_args__ = (
        UniqueConstraint("mcp_server_id", "tool_name", name="uq_mcp_tools_server_tool_name"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    mcp_server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mcp_servers.id"))
    tool_name: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output_schema_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[str] = mapped_column(Text)
    requires_approval: Mapped[bool] = mapped_column(Boolean, server_default="false")
    status: Mapped[str] = mapped_column(Text)


class ToolCall(Base, IdMixin):
    __tablename__ = "tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_tenant_run_created_at", "tenant_id", "agent_run_id", "created_at"),
        Index("ix_tool_calls_tenant_tool_status", "tenant_id", "mcp_tool_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    agent_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id"))
    agent_run_step_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_run_steps.id"), nullable=True
    )
    mcp_server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mcp_servers.id"))
    mcp_tool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mcp_tools.id"))
    status: Mapped[str] = mapped_column(Text)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approval_request_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApprovalRequest(Base, IdMixin, TimestampMixin):
    __tablename__ = "approval_requests"
    __table_args__ = (
        Index("ix_approval_requests_tenant_status_created_at", "tenant_id", "status", "created_at"),
        Index("ix_approval_requests_tenant_ticket_created_at", "tenant_id", "ticket_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    tool_call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tool_calls.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(Text)
    reason_text: Mapped[str] = mapped_column(Text)
    proposed_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text)
    requested_by_type: Mapped[str] = mapped_column(Text)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalDecision(Base, IdMixin):
    __tablename__ = "approval_decisions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    approval_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approval_requests.id"))
    decision: Mapped[str] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApprovedActionExecution(Base, IdMixin):
    __tablename__ = "approved_action_executions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    approval_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approval_requests.id"))
    tool_call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tool_calls.id"), nullable=True)
    execution_status: Mapped[str] = mapped_column(Text)
    execution_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    execution_result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromptTemplate(Base, IdMixin, TimestampMixin):
    __tablename__ = "prompt_templates"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_prompt_templates_tenant_code"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)


class PromptVersion(Base, IdMixin):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("prompt_template_id", "version_no", name="uq_prompt_versions"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    prompt_template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prompt_templates.id"))
    version_no: Mapped[int] = mapped_column(Integer)
    prompt_text: Mapped[str] = mapped_column(Text)
    prompt_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiskPolicy(Base, IdMixin, TimestampMixin):
    __tablename__ = "risk_policies"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_risk_policies_tenant_code"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    version_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)


class RiskPolicyRule(Base, IdMixin):
    __tablename__ = "risk_policy_rules"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    risk_policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risk_policies.id"))
    rule_order: Mapped[int] = mapped_column(Integer)
    condition_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    outcome_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalDataset(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "eval_datasets"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text)


class EvalCase(Base, IdMixin, TimestampMixin):
    __tablename__ = "eval_cases"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    eval_dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_datasets.id"))
    case_key: Mapped[str] = mapped_column(Text)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    expected_output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tags_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(Text)


class EvalRun(Base, IdMixin):
    __tablename__ = "eval_runs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    eval_dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_datasets.id"))
    graph_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_graph_versions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalCaseResult(Base, IdMixin):
    __tablename__ = "eval_case_results"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    eval_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_runs.id"))
    eval_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_cases.id"))
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    status: Mapped[str] = mapped_column(Text)
    actual_output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalMetricResult(Base, IdMixin):
    __tablename__ = "eval_metric_results"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    eval_case_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_case_results.id"))
    metric_code: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    metric_detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base, IdMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_resource_created_at", "tenant_id", "resource_type", "resource_id", "created_at"),
        Index("ix_audit_logs_tenant_actor_created_at", "tenant_id", "actor_user_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    actor_type: Mapped[str] = mapped_column(Text)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(Text)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base, IdMixin):
    __tablename__ = "outbox_events"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(Text)
    aggregate_type: Mapped[str] = mapped_column(Text)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, server_default="0")
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BackgroundJob(Base, IdMixin):
    __tablename__ = "background_jobs"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    job_type: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, server_default="0")
    max_retries: Mapped[int] = mapped_column(Integer, server_default="3")
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
