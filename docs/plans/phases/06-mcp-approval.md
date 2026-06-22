# 阶段计划：06 MCP 工具与审批

- **所属总计划**：`../project-plan.md`
- **完成状态**：completed
- **更新时间**：2026-06-22

## 阶段目标

- 实现 MCP mock 工具服务、高风险工具审批和审批后执行记录。

## 本轮已完成

- Phase 05 已将 Agent 摘要节点接入 RAG 检索引用，Phase 06 可以从工具调用与审批链路开始。
- 完成公开输入安全加固：ticket / knowledge DTO 增加业务白名单、自由文本长度边界、控制字符拦截和存储型 `source_uri` scheme 白名单；前端请求改为通过后端上下文头传递租户和用户。
- 复用 foundation schema 中已有 `mcp_servers`、`mcp_tools`、`tool_calls`、`approval_requests`、`approval_decisions`、`approved_action_executions`，本轮无需新增迁移。
- 实现 `mcp_tools` 模块：自动注册 in-process mock server，支持 `ticket.get_context` 低风险读取和 `ticket.transition_status` 高风险状态变更提案。
- 实现 `approval` 模块：审批决策、拒绝不执行、批准后执行工具调用，并将审批决策和执行结果分表记录。
- Agent run 已接入 `call_tools` step；高风险暂停会关联 tool call 与 approval request，审批恢复时写入决策和执行状态。

## 变更影响矩阵

| 维度 | 是否涉及 | 影响 | 验证 |
|---|---|---|---|
| API/DTO | 是 | 已加固工单/知识库公开 body；新增 MCP tool call 与 approval decision API，公开 body 不接收租户、操作者或审批人字段 | `pytest tests` |
| DB/迁移 | 否 | MCP/审批表已在 bootstrap foundation schema 中存在，本轮只写业务代码 | `tests/db/test_metadata.py` |
| 权限/数据范围 | 是 | 新增 `mcp-tools:read`、`mcp-tools:call`、`approval:decide`；后端按请求上下文强制租户和用户 | 路由测试覆盖 403/422 |
| 页面/交互 | 是 | 工单工作台请求改用 `X-ServiceMind-*` 开发头，移除 `tenant_id` query/body | `pnpm --filter @servicemind/web build` |
| 外部系统 | 否 | 第一版只做 in-process mock MCP 工具，不接真实 CRM/订单系统 | 服务层测试覆盖 |
| 回归清单 | 是 | 覆盖 tool_calls、approval_requests、approval_decisions、approved_action_executions 和审批前不执行写动作 | 后端全量测试通过 |

## 验收标准

- [x] Agent 只能通过 MCP 工具访问 mock 业务能力。
- [x] 高风险工具调用生成审批请求。
- [x] 审批通过前不执行写动作。
- [x] 审批、工具调用、执行结果均可审计。

## 下一步

1. 启用 PostgreSQL/pgvector smoke 环境后，补跑 Phase 06 真实数据库链路。
2. 进入 Phase 07 前端 AgentOps，展示 run step、tool call、approval request 和执行结果。
