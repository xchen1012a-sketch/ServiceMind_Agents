# 当前阶段：07 AgentOps 前端

- **所属总计划**：`project-plan.md`
- **状态**：in-progress
- **阶段文件**：`phases/07-agentops-ui.md`
- **更新时间**：2026-06-22

## 当前目标

- 基于现有 React 控制台实现 AgentOps 前端入口。
- 在前端展示工单主流程、Agent 节点链路、RAG 引用、MCP 工具调用、审批状态和执行结果。
- 保持权限与数据范围由后端强制，前端只做体验层展示和操作入口。

## 已完成

1. Phase 05 已完成知识库文档导入、chunk、确定性 embedding、检索和 RAG 查询/命中审计。
2. Agent 生成摘要前已接入 RAG 检索，新增 `retrieve_knowledge` run step。
3. Agent 回复 payload 和 `generate_summary` step 已返回 document、version、chunk、rank、score 与 source anchor 引用来源。
4. 已补充 Agent + RAG 服务层、路由层和知识库 used-in-answer 测试。
5. 已修复后端接口高风险输入信任问题：业务接口从后端请求上下文派生 tenant、user 和权限，公开 body/query 不再接收租户、操作者或 Agent/RAG 内部审计字段。
6. 已加固公开输入的数据注入边界：工单和知识库入口使用业务白名单、文本长度上限、控制字符拦截和存储型 `source_uri` scheme 白名单；前端已同步为请求头上下文，不再发送租户或审计字段到业务 body。
7. 已实现第一版 mock MCP 工具与审批闭环：`ticket.get_context` 低风险工具立即执行并写入 `tool_calls`，`ticket.transition_status` 高风险工具先生成 `approval_requests`，审批通过后才写入 `approved_action_executions` 并执行状态变更。
8. Agent 高风险暂停已接入 MCP/Approval：运行中写入 `call_tools` step，等待审批时关联 tool call 与 approval request，恢复审批时记录决策和执行状态。

## 下一步

1. 梳理当前 `apps/web/src/App.tsx` 状态结构，设计 Agent 链路、MCP 工具和审批中心的前端数据模型。
2. 接入现有后端接口，完成工单创建、运行 Agent、审批恢复和链路详情展示。
3. 做桌面和移动宽度布局验证，确保主要文本和按钮不重叠。

## 阻塞项

- PostgreSQL smoke 需要可用 PostgreSQL/pgvector，并设置 `SERVICEMIND_RUN_POSTGRES_SMOKE=1`。
- Phase 07 先复用本地开发请求头上下文，不实现真实登录/角色管理。
- Phase 06 PostgreSQL smoke 尚未启用环境变量补跑；当前默认测试中 PostgreSQL smoke 仍为 skipped。
- 当前请求上下文由本地开发头提供，后续接认证模块时需要替换为真实 session/JWT 派生。
- 当前知识库导入仅存储 `source_uri`，不执行外部 URL 抓取；后续若实现 URL 导入，需要另行补 SSRF 防护、重定向限制和网络出口策略。
- 禁止把真实密钥、Token 或客户隐私数据写入仓库。

## 上下文入口

- 总计划：`docs/plans/project-plan.md`
- 数据库设计：`docs/plans/database-design-plan.md`
- Agent 运行时：`docs/plans/agent-runtime-decision.md`
- 模块边界：`docs/architecture/modules.md`
- 当前阶段：`docs/plans/phases/07-agentops-ui.md`
- 上一阶段验收：`docs/plans/phases/06-mcp-approval.md`
