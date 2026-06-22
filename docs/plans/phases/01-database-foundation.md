# 阶段计划：01 数据库地基与迁移骨架

- **所属总计划**：`../project-plan.md`
- **完成状态**：completed
- **更新时间**：2026-06-22

## 阶段目标

- 基于 `../database-design-plan.md` 落地数据库 schema 文档、迁移策略和第一批 Alembic 迁移骨架。

## 实施范围

- 包含：
  - PostgreSQL + pgvector 基线。
  - 租户、用户、权限、工单、Agent run、知识库、MCP、审批、评估、审计表。
  - 命名规范、索引规范、迁移规范。
- 不包含：
  - 业务 API 实现。
  - 前端页面。
  - 真实外部系统接入。
- 依赖与前置条件：
  - 阶段 00 完成。
  - 用户确认数据库技术栈和字段规范。
- 停止条件：
  - 对租户模型、权限模型、Agent runtime 模型存在重大分歧。

## 验收标准

- [x] 数据库 schema 文档完整覆盖核心业务表。
- [x] Alembic 迁移能在空库成功执行。
- [x] 关键索引、唯一约束和外键关系有文档说明。
- [x] 破坏性迁移策略和回滚策略记录清楚。

## 验证命令

```text
alembic upgrade head
pytest tests/db
```

## 实施假设

- ORM 采用 SQLAlchemy 2.0 declarative，迁移采用 Alembic。
- 外部模板只在临时目录调研和选择性迁移，不覆盖项目规范、模块边界和数据库设计。

## 实施记录

- 2026-06-22：完成 `docs/plans/template-adoption-plan.md`，固化 FastAPI、shadcn-admin、LangGraph 模板的采用边界。
- 2026-06-22：完成 `docs/architecture/database-schema.md`，覆盖租户、RBAC、工单、Agent、RAG、MCP、审批、Prompt、评估、审计和后台任务。
- 2026-06-22：创建 `apps/api` 后端数据库骨架，包含 SQLAlchemy 2.0 declarative models、Alembic env、首批 bootstrap migration。
- 2026-06-22：创建 `infra/local/compose.db.yml`，用于本地 PostgreSQL + pgvector。
- 2026-06-22：创建 `apps/api/scripts/verify-db.ps1`，用于依赖安装、测试、Ruff、Alembic head 和真实迁移验证。
- 2026-06-22：在 WSL Ubuntu-26.04 安装 PostgreSQL 18.4 与 `postgresql-18-pgvector`，创建 `servicemind` 角色和数据库，并启用 `vector`、`pgcrypto` 扩展。

## 验证记录

- 已执行：`python -m compileall apps/api/app apps/api/alembic`，结果通过。
- 已执行：`powershell -ExecutionPolicy Bypass -File .ai-spec/scripts/validate.ps1`，结果通过；仍有既有警告：当前项目无 `.git` 仓库。
- 已执行：`python -c "from app.db.base import Base; import app.models; ..."`，结果通过，当前 SQLAlchemy metadata 包含 39 张表。
- 已执行：新增 PostgreSQL DDL 编译测试，覆盖全部表、索引和 pgvector 字段。
- 已执行：`python -m pytest tests/db`，结果通过，5 passed。
- 已执行：`ruff check app tests alembic`，结果通过。
- 已执行：`python -m compileall app alembic tests`，结果通过。
- 已执行：`alembic heads`，结果识别到 `20260622_001 (head)`。
- 已执行：`alembic upgrade head --sql`，结果通过，离线 SQL 包含 `CREATE EXTENSION IF NOT EXISTS vector`、`CREATE TABLE tenants`、`CREATE TABLE chunk_embeddings`。
- 已执行：`Test-NetConnection -ComputerName localhost -Port 5432`，初始结果 `TcpTestSucceeded=False`，确认本机未运行 Windows 原生 PostgreSQL。
- 已执行：WSL 内部 `/tmp/servicemind-api-venv/bin/python -m alembic upgrade head`，结果通过，`alembic_version` 为 `20260622_001`。
- 已执行：WSL 内部 SQL 验证，PostgreSQL 版本为 `18.4`，扩展包含 `pgcrypto`、`vector`，`public` schema 当前包含 40 张表。
