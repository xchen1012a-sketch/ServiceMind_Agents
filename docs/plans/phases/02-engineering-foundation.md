# 阶段计划：02 工程模板二开与基础服务

- **所属总计划**：`../project-plan.md`
- **完成状态**：completed
- **更新时间**：2026-06-22

## 阶段目标

- 建立可运行的 FastAPI + React + PostgreSQL + Redis + Docker Compose 工程基线。

## 实施范围

- 包含：
  - `apps/api`、`apps/web`、`services/mcp-tools`、`packages/evals`、`packages/shared-contracts`。
  - `/health` API。
  - 前端基础布局。
  - Docker Compose。
- 不包含：
  - 完整业务流程。
  - 真实模型调用。

## 验收标准

- [x] 后端 `/health` 返回正常。
- [x] 前端能访问后端健康状态。
- [ ] Docker Compose 能启动依赖服务。
- [x] 基础 lint/typecheck/test 命令可执行。

## 已实施内容

- `apps/api`：
  - 新增 FastAPI 应用入口 `app/main.py`。
  - 新增路由层 `app/api/router.py` 与 `/health`。
  - 扩展基础配置：应用名、版本、环境、CORS origin。
  - 新增 `/health` 单元测试。
- `apps/web`：
  - 新增 Vite + React + TypeScript 前端骨架。
  - 新增 ServiceMind 控制台基础布局。
  - 通过 `VITE_API_BASE_URL` 调用后端 `/health`。
- `infra/local/compose.db.yml`：
  - 保留 PostgreSQL + pgvector。
  - 新增 Redis 本地依赖服务。
- `services/mcp-tools`、`packages/evals`、`packages/shared-contracts`：
  - 新增阶段 02 占位说明，明确后续阶段归属。

## 模块边界自检

- 本阶段只新增工程入口和健康检查，不实现工单、Agent、RAG、MCP、审批、评估业务逻辑。
- 前端只展示 `/health` 结果，不承载权限、租户隔离或业务状态判断。
- 后端 `/health` 不访问数据库写路径，不触发审计、审批或外部系统动作。

## 验收证据

| 验证项 | 命令/方式 | 结果 |
| --- | --- | --- |
| API unit/smoke | `apps/api/.venv/Scripts/python -m pytest tests` | 通过：6 passed；存在 FastAPI TestClient 上游弃用警告 |
| API lint | `apps/api/.venv/Scripts/ruff check app tests alembic` | 通过 |
| Web typecheck | `pnpm --dir apps/web typecheck` | 通过 |
| Web lint | `pnpm --dir apps/web lint` | 通过 |
| Web build | `pnpm --dir apps/web build` | 通过，产物生成到 `apps/web/dist` |
| API + Web 短启动冒烟 | 短暂启动 `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` 与 `pnpm --dir apps/web exec vite preview --host 127.0.0.1 --port 4173 --strictPort`，用 `curl` 访问 | 通过：`/health` 返回 `status=ok`；前端预览页 HTTP 200 |
| Docker 可用性 | `docker --version`、`docker compose version` | 未通过：当前 Windows 环境未安装 Docker 命令 |

## 未完成项与风险

- Docker Compose 文件已补齐 PostgreSQL/pgvector 与 Redis，但当前机器没有 Docker，未执行真实启动验收。
- FastAPI CLI 在 Windows GBK 重定向下会因输出特殊字符报编码错误；本阶段统一使用 `python -m uvicorn app.main:app` 启动 API。
- 短启动冒烟已完成并清理进程；未保留长期 dev server。
- 阶段 02 已按用户确认以“Docker 未本机验证”作为残余风险收口；后续在具备 Docker 的环境补验 `infra/local/compose.db.yml`。
