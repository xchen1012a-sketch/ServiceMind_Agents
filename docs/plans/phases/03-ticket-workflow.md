# 阶段计划：03 工单与状态流转

- **所属总计划**：`../project-plan.md`
- **完成状态**：completed
- **更新时间**：2026-06-22

## 阶段目标

- 实现工单主对象、消息、状态事件和基础工作台。

## 实施范围

- 包含：
  - 工单创建 API。
  - 工单列表与详情 API。
  - 工单状态流转 API。
  - 创建工单时写入初始状态事件。
  - 非法状态流转拦截。
- 不包含：
  - 鉴权、RBAC 和真实租户上下文解析。
  - Agent 自动处理、RAG、MCP 工具调用和审批。
  - 多角色完整前端工作台交互。

## 模块落点与边界

- `apps/api/app/api/routes/tickets.py`：HTTP 入口，只做请求/响应与错误转换。
- `apps/api/app/modules/tickets/service.py`：工单应用服务，承载状态流转规则和事务编排。
- `apps/api/app/modules/tickets/repository.py`：SQLAlchemy 数据访问。
- `apps/api/app/modules/tickets/schemas.py`：Pydantic DTO。
- `ticket` 模块不得直接调用模型、MCP 工具或向量数据库。

## 验收标准

- [x] 可创建工单。
- [x] 可查看工单详情和消息。
- [x] 工单状态变更写入状态事件。
- [x] 状态流转不允许非法跳转。
- [x] 基础前端工作台可创建、刷新、查看和流转工单。

## 已实施内容

- 新增 `/api/v1/tickets` 路由：
  - `POST /api/v1/tickets`
  - `GET /api/v1/tickets?tenant_id=<uuid>`
  - `GET /api/v1/tickets/{ticket_id}?tenant_id=<uuid>`
  - `POST /api/v1/tickets/{ticket_id}/status`
- 新增 `tickets` 应用模块：
  - `schemas.py` 定义请求/响应 DTO。
  - `repository.py` 封装 SQLAlchemy 访问。
  - `service.py` 实现创建工单、查询详情、状态流转和非法流转拦截。
- 创建工单时写入：
  - `tickets` 主记录，初始状态为 `new`。
  - `ticket_messages` 初始消息。
  - `ticket_status_events` 初始状态事件。
- 新增基础前端工单工作台：
  - `apps/web/src/App.tsx` 接入 `/health` 与 `/api/v1/tickets`。
  - 支持显式 `tenant_id`、创建工单、刷新列表、查看详情和触发允许的状态流转。
  - `apps/web/src/styles.css` 补齐三栏工作台、表单、列表、详情和提示状态样式。
- 新增真实 PostgreSQL 冒烟验证入口：
  - `apps/api/tests/tickets/test_ticket_postgres_smoke.py` 使用真实 API 和数据库连接验证创建、状态流转与落库。
  - `apps/api/scripts/verify-ticket-workflow.ps1` 串联依赖安装、迁移、PostgreSQL 冒烟、全量测试和 lint。
  - 默认测试跳过该冒烟；需设置 `SERVICEMIND_RUN_POSTGRES_SMOKE=1` 并提供可连接的 `SERVICEMIND_DATABASE_URL`。

## 状态流转规则

| 当前状态 | 允许目标状态 |
| --- | --- |
| `new` | `triaged`、`cancelled` |
| `triaged` | `in_progress`、`cancelled` |
| `in_progress` | `waiting_customer`、`resolved`、`cancelled` |
| `waiting_customer` | `in_progress`、`resolved`、`cancelled` |
| `resolved` | `closed`、`reopened` |
| `reopened` | `in_progress`、`cancelled` |
| `closed` | 无 |
| `cancelled` | 无 |

## 模块边界自检

- 路由层只做 HTTP 参数、依赖注入和异常转换。
- 状态流转规则集中在 `TicketService`，未放入前端或 repository。
- `ticket` 模块未调用 Agent、RAG、MCP 或审批模块。
- 当前未实现鉴权，API 暂用显式 `tenant_id`，后续必须替换为后端认证上下文。

## 验收证据

| 验证项 | 命令/方式 | 结果 |
| --- | --- | --- |
| API unit/route tests | `apps/api/.venv/Scripts/python -m pytest tests` | 通过：19 passed，2 skipped；存在 FastAPI TestClient 上游弃用警告 |
| API lint | `apps/api/.venv/Scripts/ruff check app tests alembic` | 通过 |
| Web typecheck | `pnpm --dir apps/web typecheck` | 通过 |
| Web lint | `pnpm --dir apps/web lint` | 通过 |
| Web build | `pnpm --dir apps/web build` | 通过 |
| 回归清单：工单主流程 | 服务层与路由层测试覆盖创建、初始状态事件、非法流转拒绝 | 通过 |
| PostgreSQL 冒烟 | WSL Ubuntu-26.04 内设置 `SERVICEMIND_RUN_POSTGRES_SMOKE=1` 后执行 `alembic upgrade head`、`pytest tests/tickets/test_ticket_postgres_smoke.py tests/agent/test_agent_postgres_smoke.py`、`pytest tests`、`ruff check app tests alembic` | 通过：2 个真实 DB smoke passed；全量后端 21 passed；Ruff 通过 |

## 未完成项与风险

- Windows 原生环境仍无法连接 `localhost:5432`，真实 PostgreSQL 验证通过 WSL Ubuntu-26.04 完成。
- 未实现鉴权、RBAC 和后端租户上下文；当前 API 与前端工作台仍使用显式 `tenant_id`。
- 前端工作台创建工单需要数据库中已存在对应租户；测试冒烟会自行创建临时租户，但真实 UI 联调需要准备有效租户。
- 未实现工单消息追加接口；本轮只覆盖创建时的初始消息。
- 阶段 03 后端最小闭环、基础前端工作台和真实 PostgreSQL 冒烟均已完成。
