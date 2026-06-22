# 阶段计划：05 知识库 RAG

- **所属总计划**：`../project-plan.md`
- **完成状态**：in-progress
- **更新时间**：2026-06-22

## 阶段目标

- 实现文档上传、解析、chunk、embedding、检索、引用来源和 RAG Agent 接入。

## 本轮已完成

- 新增知识库模块服务层和仓储层，复用既有 `knowledge_spaces`、`knowledge_documents`、`knowledge_document_versions`、`knowledge_chunks` 表。
- 新增纯文本 chunker，导入文档时生成 document version、content hash、parser 信息和 chunk source anchor。
- 新增确定性本地 embedding provider，写入 `embedding_models` 与 `chunk_embeddings`，重复调用保持幂等。
- 新增检索接口，基于确定性 embedding 计算相似度并返回 ranked chunk。
- 写入 `rag_queries` 与 `rag_retrieval_hits`，保存检索参数、rank、score、chunk 命中。
- 新增 API：
  - `POST /api/v1/knowledge/spaces`
  - `POST /api/v1/knowledge/documents/import`
  - `GET /api/v1/knowledge/documents/{document_id}?tenant_id=<uuid>`
  - `POST /api/v1/knowledge/documents/{document_id}/embeddings`
  - `POST /api/v1/knowledge/search`
- 新增服务层、路由层和 PostgreSQL 烟测覆盖。

## 验收标准

- [x] 文档可导入并生成 chunk。
- [x] chunk embedding 可写入。
- [x] chunk embedding 可检索。
- [ ] Agent 回复包含引用来源。
- [x] RAG 查询和命中结果可审计。

## 验证记录

- 2026-06-22 文档导入小步：
  - `.\.venv\Scripts\python -m pytest tests/knowledge`：4 passed, 1 skipped。
  - `.\.venv\Scripts\ruff check app tests alembic`：passed。
  - `.\.venv\Scripts\python -m pytest tests`：28 passed, 3 skipped。
  - PostgreSQL smoke（`SERVICEMIND_RUN_POSTGRES_SMOKE=1`）：
    - `.\.venv\Scripts\alembic upgrade head`：passed。
    - `.\.venv\Scripts\python -m pytest tests/knowledge/test_knowledge_postgres_smoke.py tests/tickets/test_ticket_postgres_smoke.py tests/agent/test_agent_postgres_smoke.py`：3 passed。
    - `.\.venv\Scripts\python -m pytest tests`：31 passed。
- 2026-06-22 embedding 写入小步：
  - `.\.venv\Scripts\python -m pytest tests/knowledge`：6 passed, 1 skipped。
  - `.\.venv\Scripts\ruff check app tests alembic`：passed。
  - `.\.venv\Scripts\python -m pytest tests`：30 passed, 3 skipped。
  - PostgreSQL smoke（`SERVICEMIND_RUN_POSTGRES_SMOKE=1`）：
    - `.\.venv\Scripts\alembic upgrade head`：passed。
    - `.\.venv\Scripts\python -m pytest tests`：33 passed。
- 2026-06-22 检索审计小步：
  - `.\.venv\Scripts\python -m pytest tests/knowledge`：8 passed, 1 skipped。
  - `.\.venv\Scripts\ruff check app tests alembic`：passed。
  - `.\.venv\Scripts\python -m pytest tests`：32 passed, 3 skipped。
  - PostgreSQL smoke（`SERVICEMIND_RUN_POSTGRES_SMOKE=1`）：
    - `.\.venv\Scripts\alembic upgrade head`：passed。
    - `.\.venv\Scripts\python -m pytest tests`：35 passed。

## 下一步

1. 将 Agent 运行链路接入检索命中与引用来源。
2. 在 Agent 回复中返回 document、version、chunk、rank、score 等引用信息。
3. 补充 Agent + RAG 联动测试和 PostgreSQL smoke。

## 风险与约束

- 当前仅支持纯文本手动导入，不含文件上传和二进制解析。
- 当前 chunker 为确定性本地实现，后续需要替换或扩展真实 parser。
- 当前检索为应用层余弦相似度排序，后续可切换为 pgvector 索引查询。
- 当前暂不接外部 embedding 供应商，使用 `local/deterministic-hash-v1` 避免密钥和环境依赖进入仓库。
