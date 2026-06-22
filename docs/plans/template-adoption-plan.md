# 二开模板采用计划：ServiceMind Agents

## 目标

在不覆盖本项目规范、数据库设计和模块边界的前提下，选择成熟模板做工程底座参考，提升简历项目的完整度、现代化 UI 质量和可维护性。

## 已调研模板

### 后端：fastapi/full-stack-fastapi-template

- 来源：https://github.com/fastapi/full-stack-fastapi-template
- 采用：
  - FastAPI 工程组织、配置管理、Docker Compose、本地开发脚本、健康检查和测试组织思路。
  - Alembic 迁移目录组织和 pyproject 工具链配置思路。
  - API 分层方式：router 入口、core 配置、db/session、tests。
- 不采用：
  - 不直接采用 SQLModel 业务模型。本项目数据库层采用 SQLAlchemy 2.0 declarative。
  - 不照搬 demo users/items 业务表。
  - 不直接照搬模板鉴权流程，后续按多租户 RBAC 和审批审计要求设计。

### 前端：satnaing/shadcn-admin

- 来源：https://github.com/satnaing/shadcn-admin
- 采用：
  - Vite + React + TypeScript + shadcn/ui + Tailwind 的现代管理端底座。
  - 侧边栏、主题切换、表格、筛选、弹窗、设置页和数据表组件模式。
  - TanStack Router、TanStack Query、React Table、Zod 表单校验组合。
- 不采用：
  - 不直接采用 Clerk 作为第一版强绑定鉴权。
  - 不保留示例用户、任务、帮助中心等与本业务无关的演示页面。
  - 不让前端承载权限判断；权限、租户隔离和高风险审批必须由后端强制。

### Agent 参考：fastapi-langgraph-agent-production-ready-template

- 来源：https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template
- 采用：
  - LangGraph 运行时组织、prompts、observability、metrics、evals 和 Docker 观测配置思路。
  - LLM service registry、运行时配置、限流和结构化日志思路。
- 不采用：
  - 不直接复制聊天机器人业务模型。
  - 不直接采用 SQLModel、Supabase 或模板内置会话模型。
  - 不让 Agent 直接修改核心业务表。Agent 与业务系统通过受控 MCP 工具和审批链路交互。

## 本项目落地结构

```text
apps/
  api/        # FastAPI 后端，SQLAlchemy 2.0 + Alembic
  web/        # 后续从 shadcn-admin 选择性二开
packages/
  shared/     # 后续放共享契约、类型、常量
services/
  agent/      # 后续 LangGraph runtime 独立服务或包
infra/
  local/      # 本地 PostgreSQL/pgvector/Redis/observability
docs/
  architecture/
  plans/
```

## 二开顺序

1. 数据库地基：先完成 PostgreSQL + pgvector + Alembic schema 和迁移。
2. 后端工程底座：补齐 FastAPI app、配置、DB session、健康检查、测试命令。
3. 前端管理端：引入 shadcn-admin 的布局、表格和主题模式，替换为本项目页面。
4. Agent runtime：用 LangGraph 落地工单处理图，预留 Deep Agents 插件接口。
5. 观测与评估：补齐 agent_runs、agent_run_steps、model_invocations、evals 的 UI 与 API。

## 约束

- 外部模板只能提供工程模式参考，不能覆盖 `docs/plans/database-design-plan.md` 和 `docs/architecture/modules.md`。
- 业务表、状态、权限、审计和审批链路必须以本项目数据库设计为准。
- 每次引入模板代码前必须做模块归属判断，删除演示业务，保留必要许可证说明。
- 前端组件可复用，但业务状态、权限和数据范围不能由前端单独决定。

## 变更影响矩阵

| 影响面 | 当前阶段影响 | 说明 |
|---|---|---|
| API/DTO | 暂无 | 本阶段不实现业务 API |
| DB/迁移 | 有 | 建立首批 SQLAlchemy 模型和 Alembic 迁移 |
| 权限 | 设计级 | 表结构预留 RBAC，不实现鉴权入口 |
| 页面 | 暂无 | 前端二开留到后续阶段 |
| 进程/任务 | 轻微 | 增加本地数据库 compose，不启动长期服务 |
| 外部系统 | 暂无 | 只调研 GitHub 模板 |
| 测试 | 有 | 先做 Python 编译和 SpecForge 校验 |
| 回归 | 设计级 | 对照核心链路回归清单确保表结构可承载 |
