import app.models  # noqa: F401
from app.db.base import Base


def test_foundation_metadata_contains_core_tables() -> None:
    expected_tables = {
        "tenants",
        "users",
        "roles",
        "permissions",
        "tickets",
        "ticket_messages",
        "ticket_status_events",
        "agent_runs",
        "agent_run_steps",
        "model_invocations",
        "knowledge_documents",
        "knowledge_chunks",
        "chunk_embeddings",
        "mcp_tools",
        "tool_calls",
        "approval_requests",
        "approval_decisions",
        "eval_runs",
        "audit_logs",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_all_core_business_tables_have_tenant_id_except_global_tables() -> None:
    global_tables = {"tenants", "permissions", "embedding_models"}
    missing_tenant_id = {
        table_name
        for table_name, table in Base.metadata.tables.items()
        if table_name not in global_tables and "tenant_id" not in table.columns
    }

    assert missing_tenant_id == set()
