# 项目总计划：ServiceMind Agents

- **状态**：in-progress
- **创建时间**：2026-06-22
- **更新时间**：2026-06-22
- **计划依据**：`项目想法.md`、启动接入讨论、数据库设计讨论、Agent 运行时选型讨论、GitHub 模板调研

## 目标与完成定义

- 已证实事实：
  - 当前仓库处于新项目 Bootstrap 阶段，尚无业务代码和 Git 仓库。
  - 已存在 `.ai-spec/` 规范目录。
  - `项目想法.md` 明确项目方向为企业工单与知识库多 Agent 处理平台。
- 未证实假设：
  - 使用单 Git 仓库 monorepo 管理前端、后端、MCP 服务、评估包和基础设施。
  - 使用 PostgreSQL + pgvector 作为第一版数据底座。
  - 使用 FastAPI 全栈模板和 shadcn-admin 作为二开基线。
- 待用户确认问题：
  - 是否立即初始化 Git。
  - 是否实际 clone 外部模板，还是按模板思想从零搭建。
  - 是否第一阶段只做工程基线和数据库迁移，不写 Agent 业务逻辑。
- 已确认需求：
  - 项目要按完整项目规划，不按 Demo 处理。
  - 数据库是地基，必须先设计表结构、字段规范、迁移规范和扩展边界。
  - 前端需要现代化 UI，可全网/GitHub 搜索 UI 组件和模板。
  - Agent 主流程要考虑 LangGraph、Deep Agents 和后续扩展接口。
- 项目目标：
  - 构建企业级工单智能处理平台，覆盖工单接入、Agent 编排、RAG、MCP 工具、人工审批、AgentOps 观测和离线评估。
- 最终可交付结果：
  - 可本地一键启动的全栈系统。
  - 可创建工单、运行 Agent 流程、检索知识库、调用受控工具、触发审批、查看链路、运行评估。
  - 有数据库迁移、测试、文档、审计和回滚方案。
- 不在范围内：
  - 第一版不接真实 CRM、真实订单系统和真实退款/删除动作。
  - 第一版不做 Kubernetes 生产集群、多租户计费、自研大模型训练。
  - 第一版不允许 Agent 绕过审批直接执行高风险写操作。
- 项目级 Definition of Done：
  - 工程基线、数据库、核心 API、前端控制台、Agent 流程、RAG、MCP、审批、观测和评估均完成阶段验收。
  - 所有核心表通过 Alembic 迁移创建，关键索引和约束明确。
  - Agent run、step、tool call、approval、evaluation 均可审计和回放。
  - 前端主流程具备现代化工作台体验，支持链路图和评估看板。

## 现状与约束

- 当前状态：
  - 只有项目想法、规范目录和计划文档骨架。
- 技术/业务约束：
  - 数据库设计优先，业务代码实施前必须完成数据模型基线。
  - 模型输出默认不可信，高风险动作默认进入人工审批。
  - Agent 与业务系统通过受控 MCP 工具交互。
- 关键依赖：
  - PostgreSQL、pgvector、Redis、FastAPI、React、LangGraph、MCP Python SDK。

## 方案与关键决策

- 总体方案：
  - 单仓 monorepo，全栈工程；核心后端承载业务 API、Agent 编排、RAG、审批和观测；MCP 工具服务独立模块；前端做 AgentOps 管理控制台。
- 技术架构：
  - `apps/api`：FastAPI 主后端。
  - `apps/web`：React + TypeScript 现代化控制台。
  - `services/mcp-tools`：MCP 工具服务。
  - `packages/evals`：评估集与评测脚本。
  - `packages/shared-contracts`：共享契约、DTO、错误码。
  - `infra`：Docker Compose、初始化脚本和部署资产。
- 模块拆解与边界：
  - 工单模块：工单、消息、状态事件。
  - Agent 编排模块：图版本、运行、节点步骤、模型调用。
  - 知识库模块：空间、文档、版本、chunk、embedding、检索命中。
  - MCP 工具模块：server、tool、tool_call。
  - 审批模块：审批请求、决策、执行结果。
  - 评估模块：数据集、样本、评估运行、指标结果。
  - 审计模块：audit log、outbox event、background job。
- 模块职责与代码落点：
  - 详见 `docs/architecture/modules.md` 和 `docs/plans/database-design-plan.md`。
- 依赖方向与跨模块访问规则：
  - API 层调用应用服务；应用服务通过领域服务和 repository 访问数据。
  - Agent 模块不得直接操作外部业务系统，必须通过 MCP 工具模块。
  - 前端不得承载权限判断最终结果，权限必须在后端强制。
- 复用策略与新增模块理由：
  - 复用 FastAPI 全栈模板的工程、认证、配置、Docker、测试基线。
  - 复用 shadcn-admin 的现代控制台布局、侧边栏、暗色模式、表格和搜索模式。
  - 数据模型按 ServiceMind 领域重建，避免模板业务表污染。
- 接口/API：
  - 第一阶段先建立 OpenAPI 契约目录，不直接承诺最终路径。
- 数据模型：
  - 详见 `docs/plans/database-design-plan.md`。
- 前端页面/交互入口：
  - 工单工作台、工单详情、Agent 链路、知识库管理、审批中心、评估看板、系统设置。
- 进程管理/运行方式：
  - Docker Compose 管理 PostgreSQL、Redis、API、Web、MCP 工具服务。
- 权限策略：
  - RBAC + 租户隔离 + 工具级风险权限 + 审批权限。
- 安全审计策略：
  - 高风险工具调用、审批、状态变更、模型调用和数据导入均记录审计。
- 已确认决策：
  - 核心 Agent 主流程使用 LangGraph。
  - Deep Agents 作为后续高级任务插件，不进入第一版核心工单流程。
  - Agent runtime 抽象必须预留 `langgraph`、`deepagents`、`custom` 类型。
- 待确认事项：
  - 是否 clone 外部模板。
  - 是否启用真实第三方模型供应商。
  - 是否第一阶段初始化 Git。

## 关键决策记录

| 决策 | 原因 | 替代方案 | 影响范围 |
| --- | --- | --- | --- |
| PostgreSQL + pgvector 作为数据底座 | 关系数据强、事务审计强、向量能力足够支撑第一版 | Qdrant 单独向量库 | DB、RAG、部署 |
| LangGraph 作为主 Agent 运行时 | 显式状态机、可中断、可恢复、适合人工审批 | Deep Agents 直接做主流程 | Agent、审批、观测 |
| Deep Agents 作为扩展插件 | 适合复杂长任务、子 Agent 和上下文管理 | 完全不用 Deep Agents | 后续高级能力 |
| FastAPI 全栈模板作为工程参考 | 已覆盖 FastAPI、React、SQLModel、PostgreSQL、Docker、CI | 从零搭建 | 工程基线 |
| shadcn-admin 作为前端二开参考 | 现代化管理端、Vite、TanStack Router、响应式、暗色模式 | Ant Design Pro | 前端 UI |

## 变更影响矩阵

| 影响面 | 是否涉及 | 影响说明 | 同步文件/验证方式 |
| --- | --- | --- | --- |
| API/DTO | 是 | 后续需定义工单、Agent、知识库、审批、评估 API | `docs/contracts/` |
| DB/迁移 | 是 | 数据库为第一阶段核心地基 | `docs/plans/database-design-plan.md` |
| 权限/数据范围 | 是 | 租户、用户、角色、工具审批权限 | `docs/architecture/modules.md` |
| 页面/交互 | 是 | 管理端完整工作台 | 前端阶段验收 |
| 进程/定时任务/队列 | 是 | 文档解析、评估跑批、outbox、后台任务 | `infra/` |
| 外部系统/第三方 | 是 | 模型供应商、MCP、mock CRM/订单系统 | 契约和安全审计 |
| 模块契约 | 是 | 新项目需要建立模块边界 | `docs/architecture/modules.md` |
| 回归清单 | 是 | 核心链路涉及状态、审批、工具调用 | `docs/quality/regression-checklist.md` |

## 测试矩阵与验证命令

| 层级 | 是否执行 | 命令/步骤 | 跳过原因/预期结果 |
| --- | --- | --- | --- |
| typecheck | 后续执行 | `mypy`、`tsc --noEmit` | 当前尚无代码 |
| unit | 后续执行 | `pytest`、前端测试 | 当前尚无代码 |
| integration | 后续执行 | API + DB + Redis + MCP | 当前尚无代码 |
| e2e/browser | 后续执行 | Playwright | 当前尚无前端 |
| API smoke | 后续执行 | `/health`、工单主流程 | 当前尚无 API |
| manual verification | 是 | 检查计划、配置、目录和规范文件 | 本阶段可执行 |

## 阶段索引

| 阶段 | 状态 | 阶段文件 |
| --- | --- | --- |
| 00 接入与计划落盘 | completed | `phases/00-onboarding.md` |
| 01 数据库地基与迁移骨架 | completed | `phases/01-database-foundation.md` |
| 02 工程模板二开与基础服务 | completed | `phases/02-engineering-foundation.md` |
| 03 工单与状态流转 | completed | `phases/03-ticket-workflow.md` |
| 04 LangGraph Agent 主流程 | completed | `phases/04-langgraph-runtime.md` |
| 05 知识库 RAG | in-progress | `phases/05-knowledge-rag.md` |
| 06 MCP 工具与审批 | planned | `phases/06-mcp-approval.md` |
| 07 AgentOps 前端 | planned | `phases/07-agentops-ui.md` |
| 08 评估系统与项目收口 | planned | `phases/08-evaluation-release.md` |

## 阶段依赖

- 00 -> 01：接入计划确认后设计数据库迁移。
- 01 -> 02：数据库地基确认后初始化工程模板。
- 02 -> 03：工程骨架可运行后实现工单模块。
- 03 -> 04：工单状态稳定后接入 LangGraph。
- 04 -> 05：Agent run 记录稳定后接入 RAG。
- 05 -> 06：检索证据稳定后接入工具与审批。
- 06 -> 07：后端链路完整后做前端 AgentOps。
- 07 -> 08：主流程可观测后建立评估闭环。

## 总体验收标准

- [ ] 核心业务结果可验证。
- [ ] 代码按模块和分层落点实现，没有跨层混写或跨模块直读内部状态。
- [ ] 变更影响矩阵已同步，模块契约和回归清单按触发条件更新。
- [ ] 必要测试、构建和检查通过。
- [ ] 接口、数据、权限、安全和页面入口已按范围验证。
- [ ] 阶段计划、验收证据和 `current.md` 状态已同步。
- [ ] 风险、回滚和未完成项已记录。

## 总体风险与回滚

- 主要风险：
  - 过早 clone 大型模板导致项目结构被模板反向约束。
  - 数据模型过度 JSON 化，后续观测和评估不可查询。
  - Agent 高层抽象过早介入，审批和审计失控。
- 回滚/恢复策略：
  - 每阶段独立提交；模板二开前先保留计划和迁移基线。
  - 数据库破坏性变更必须走新字段、双写、切读、观察、删除流程。

## 范围变更规则

- 新增模块、调整阶段顺序、扩大能力边界或修改接口/数据/权限/安全策略时，必须同步更新本文件、当前阶段文件和 `current.md`。

## 计划变更记录

- 2026-06-22：创建计划；原因：用户确认做完整项目并开始接入；影响范围：项目计划、数据库设计、Agent 运行时、工程基线；同步文件：`current.md`、阶段文件、数据库计划、模块契约、回归清单。
- 2026-06-22：完成阶段 03 并启动阶段 04；原因：WSL PostgreSQL 冒烟通过，开始 LangGraph Agent 最小闭环；影响范围：API、Agent 模块、测试、阶段状态；同步文件：`current.md`、`phases/03-ticket-workflow.md`、`phases/04-langgraph-runtime.md`。
- 2026-06-22：完成阶段 04 并启动阶段 05；原因：Agent run 支持高风险暂停、审批恢复、step 审计写入，并已通过真实 PostgreSQL + pgvector smoke；影响范围：API、Agent 模块、测试、阶段状态；同步文件：`current.md`、`phases/04-langgraph-runtime.md`、`phases/05-knowledge-rag.md`。
- 2026-06-22：完成阶段 05 第一小步；原因：知识库空间、纯文本文档导入、版本和 chunk 持久化已形成最小闭环，并通过服务层、路由层和 PostgreSQL smoke；影响范围：API、Knowledge 模块、测试、阶段状态；同步文件：`current.md`、`phases/05-knowledge-rag.md`、`apps/api/README.md`。
- 2026-06-22：完成阶段 05 embedding 写入小步；原因：确定性本地 embedding provider 已可写入 `embedding_models` 和 `chunk_embeddings`，并通过 pgvector PostgreSQL smoke；影响范围：API、Knowledge 模块、测试、阶段状态；同步文件：`current.md`、`phases/05-knowledge-rag.md`、`apps/api/README.md`。
- 2026-06-22：完成阶段 05 检索审计小步；原因：知识库检索接口已基于确定性 embedding 返回 ranked chunk，并写入 `rag_queries` 与 `rag_retrieval_hits`；影响范围：API、Knowledge 模块、测试、阶段状态；同步文件：`current.md`、`phases/05-knowledge-rag.md`、`apps/api/README.md`。
