from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import app.models  # noqa: F401
from app.db.base import Base


def test_all_tables_compile_to_postgresql_ddl() -> None:
    dialect = postgresql.dialect()

    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table.name}" in ddl


def test_all_indexes_compile_to_postgresql_ddl() -> None:
    dialect = postgresql.dialect()

    for table in Base.metadata.tables.values():
        for index in table.indexes:
            ddl = str(CreateIndex(index).compile(dialect=dialect))
            assert f"CREATE INDEX {index.name}" in ddl


def test_pgvector_column_is_declared() -> None:
    table = Base.metadata.tables["chunk_embeddings"]
    ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))

    assert "embedding_vector vector NOT NULL" in ddl
