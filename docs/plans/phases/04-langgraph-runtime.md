# 阶段计划：04 LangGraph Agent 主流程

- **所属总计划**：`../project-plan.md`
- **完成状态**：completed
- **更新时间**：2026-06-22

## 阶段目标

- 使用 LangGraph 实现核心工单处理状态机，并写入 `agent_runs` 与 `agent_run_steps`。

## 实施范围

- 包含：
  - 从工单触发 Agent run。
  - 使用 `LangGraphTicketRuntime` 编排分类、风险检查、审批门和摘要生成节点。
  - 写入 `agent_runs` 与 `agent_run_steps`。
  - 节点失败时记录 `error_code` 与 `error_message`。
  - 高风险工单进入 `waiting_approval` 暂停态。
  - `waiting_approval` Agent run 可通过人工审批恢复接口继续或拒绝结束，并写入恢复 step。
- 不包含：
  - 真实模型供应商调用。
  - RAG 检索。
  - MCP 工具调用。
  - 独立审批模块、RBAC 鉴权和真实高风险写动作执行。

## 模块落点与边界

- `apps/api/app/modules/agent/runtime.py`：LangGraph 状态机定义，不直接访问数据库。
- `apps/api/app/modules/agent/service.py`：Agent run 应用服务，负责编排运行、失败记录和持久化步骤。
- `apps/api/app/modules/agent/repository.py`：SQLAlchemy 数据访问。
- `apps/api/app/modules/agent/schemas.py`：Pydantic DTO。
- `apps/api/app/api/routes/agent.py`：HTTP 入口，只做请求、依赖注入和错误转换。
- `agent` 模块不得绕过 `approval` 模块执行高风险动作；当前仅记录暂停、人工决策和确定性后续占位节点。

## 验收标准

- [x] 工单可触发 Agent run。
- [x] 每个 LangGraph 节点有 step 记录。
- [x] 节点失败可定位错误原因。
- [x] 人工审批节点可暂停与恢复。

## 已实施内容

- 新增 `langgraph` 后端依赖。
- 新增 `POST /api/v1/tickets/{ticket_id}/agent-runs`。
- 低风险工单流程：
  - `classify_ticket`
  - `risk_review`
  - `generate_summary`
  - run 状态为 `completed`。
- 高风险工单流程：
  - `classify_ticket`
  - `risk_review`
  - `approval_gate`
  - run 状态为 `waiting_approval`，暂不继续执行写动作。
- 新增 `POST /api/v1/agent-runs/{agent_run_id}/resume`。
- 审批恢复流程：
  - `approval_gate` 从 `waiting_approval` 关闭为 `completed` 或 `rejected`。
  - 写入 `approval_decision` step，记录 `decision`、`decision_reason` 和 `decided_by_user_id`。
  - `approved` 时追加确定性 `generate_summary` step，并将 run 置为 `completed`。
  - `rejected` 时不继续后续节点，并将 run 置为 `rejected`。
- Runtime 失败时创建 `runtime_error` step，并在 `agent_runs` 写入错误码和错误信息。

## 验收证据

| 验证项 | 命令/方式 | 结果 |
| --- | --- | --- |
| Agent unit/route/runtime tests | `apps/api/.venv/Scripts/python -m pytest tests/agent` | 通过：13 passed，1 skipped；存在 FastAPI TestClient 上游弃用警告 |
| API all tests | `apps/api/.venv/Scripts/python -m pytest tests` | 通过：24 passed，2 skipped；存在 FastAPI TestClient 上游弃用警告 |
| API lint | `apps/api/.venv/Scripts/ruff check app tests alembic` | 通过 |
| Web typecheck | `pnpm --dir apps/web typecheck` | 通过 |
| Web lint | `pnpm --dir apps/web lint` | 通过 |
| Web build | `pnpm --dir apps/web build` | 通过 |
| PostgreSQL smoke | 临时 PostgreSQL 18 + pgvector 0.8.2，设置 `SERVICEMIND_RUN_POSTGRES_SMOKE=1` 后执行 `pytest tests/tickets/test_ticket_postgres_smoke.py tests/agent/test_agent_postgres_smoke.py` | 通过：2 passed |
| API all tests with PostgreSQL smoke | 同一真实 DB 环境执行 `apps/api/.venv/Scripts/python -m pytest tests` | 通过：26 passed；存在 FastAPI TestClient 上游弃用警告 |

## 未完成项与风险

- 暂未接入真实模型、RAG 和 MCP 工具，节点输出为确定性占位结果。
- 当前审批恢复是 Agent run 层的最小闭环，未实现独立审批请求、审批权限和真实高风险写动作执行；这些进入 Phase 06。
- Docker CLI 和 WSL 发行版在当前环境仍不可用；本轮使用临时便携 PostgreSQL 18 + pgvector 0.8.2 完成真实 DB smoke。后续若要长期本地开发，仍建议恢复 `infra/local/compose.db.yml` 对应的 Docker 环境。
