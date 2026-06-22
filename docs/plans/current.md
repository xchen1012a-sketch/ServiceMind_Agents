# 当前阶段：05 知识库 RAG

- **所属总计划**：`project-plan.md`
- **状态**：in-progress
- **阶段文件**：`phases/05-knowledge-rag.md`
- **更新时间**：2026-06-22

## 当前目标

- 实现知识库文档导入、chunk、embedding、检索和引用来源记录。
- 让 Agent 后续回复能够带可审计的知识来源，而不是只返回确定性占位摘要。
- 保持 Agent run 与 step 写入规则不变，RAG 检索和命中结果必须可追踪。

## 已完成

1. 梳理现有知识库数据表、迁移和模块边界，确认 Phase 05 最小闭环从文档导入切入。
2. 实现第一版知识库空间创建、纯文本文档导入、文档版本和 chunk 持久化接口。
3. 增加服务层、路由层和 PostgreSQL 烟测，验证 chunk 可以写入真实数据库。
4. 实现确定性 embedding 写入链路，复用 `embedding_models` 与 `chunk_embeddings`，并验证 pgvector 字段可写入。
5. 实现第一版知识库检索接口，基于确定性 embedding 返回相似 chunk，并写入 `rag_queries` 与 `rag_retrieval_hits`。

## 下一步

1. 将 Agent 生成摘要节点接入 RAG 检索结果，并在 run step 中记录引用来源。
2. 在 Agent 回复 payload 中返回引用来源，至少包含 document、version、chunk、rank 和 score。
3. 补充 Agent + RAG 联动的服务层、路由层和 PostgreSQL smoke 测试。

## 阻塞项

- 是否初始化 Git 尚未确认。
- Docker CLI 和 WSL 发行版在当前环境不可用；真实 PostgreSQL smoke 可通过临时便携 PostgreSQL 18 + pgvector 0.8.2 执行。
- Phase 05 暂不接真实外部模型供应商，当前使用 `local/deterministic-hash-v1`，避免把密钥写入仓库。

## 上下文入口

- 总计划：`docs/plans/project-plan.md`
- 数据库设计：`docs/plans/database-design-plan.md`
- 模块边界：`docs/architecture/modules.md`
- 当前阶段：`docs/plans/phases/05-knowledge-rag.md`
- 上一阶段验收：`docs/plans/phases/04-langgraph-runtime.md`
