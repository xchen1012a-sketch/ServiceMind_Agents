# 阶段计划：00 接入与计划落盘

- **所属总计划**：`../project-plan.md`
- **完成状态**：completed
- **更新时间**：2026-06-22

## 阶段目标

- 形成可审计的项目接入基线。
- 保留完整项目计划、数据库设计计划和 Agent 运行时决策。
- 建立 `.ai-spec/ai-spec.yaml`、`AGENTS.md`、`business/quick-ref.md` 快速入口。

## 实施范围

- 包含：
  - 项目计划文档。
  - 数据库设计计划。
  - Agent 运行时决策。
  - 模块契约和回归清单。
  - SpecForge 项目画像。
- 不包含：
  - 业务代码。
  - 数据库迁移脚本。
  - 外部模板 clone。
  - Git 初始化。
- 依赖与前置条件：
  - 用户已确认“保留计划书并开始接入项目”。
- 预计修改文件/模块：
  - `docs/plans/`
  - `docs/architecture/`
  - `docs/quality/`
  - `.ai-spec/`
  - `AGENTS.md`
- 模块归属与分层落点：
  - 项目治理与计划层。
- 新增模块/包理由：
  - 需要为后续完整项目实施建立可恢复状态。
- 停止条件：
  - 用户要求停止或撤回接入。
  - 外部模板 clone、Git 初始化或业务代码修改需要另行确认。

## 实施细节

- 架构/模块：
  - 暂只定义文档和目录边界。
- 代码落点与职责边界：
  - 无业务代码修改。
- 依赖方向与跨模块访问：
  - 通过 `docs/architecture/modules.md` 记录。
- 接口/API：
  - 本阶段不定义具体 OpenAPI。
- 数据/权限/安全：
  - 通过数据库计划定义字段、迁移和审计规范。
- 前端页面/交互：
  - 只记录页面规划，不实现。
- 进程管理/运行方式：
  - 只记录 Docker Compose 方向，不启动服务。

## 变更影响矩阵

| 影响面 | 是否涉及 | 本阶段影响 | 验证/同步结果 |
| --- | --- | --- | --- |
| API/DTO | 否 | 仅规划 | 后续阶段定义 |
| DB/迁移 | 是 | 设计计划，不执行迁移 | `database-design-plan.md` |
| 权限/数据范围 | 是 | 设计 RBAC 和租户边界 | `modules.md` |
| 页面/交互 | 是 | 规划页面 | 总计划记录 |
| 进程/定时任务/队列 | 是 | 规划队列和后台任务 | 总计划记录 |
| 外部系统/第三方 | 是 | 记录模板和 MCP 选型 | Agent 决策记录 |
| 模块契约 | 是 | 建立最小模块契约 | `docs/architecture/modules.md` |
| 回归清单 | 是 | 建立最小回归清单 | `docs/quality/regression-checklist.md` |

## 安全评审点

- 是否涉及进程启动/终止、工作区路径、shell/PTY、文件监听、日志保存、AI 自动执行、权限边界、数据存储路径或外部资源访问：涉及工作区文件写入，不涉及进程和外部资源执行。
- 安全边界：
  - 不写业务代码。
  - 不初始化 Git。
  - 不 clone 外部模板。
  - 不写密钥、Token、真实客户数据。
- 验证方法：
  - 检查文件结构和规范状态。

## 测试层级矩阵

| 层级 | 是否执行 | 命令/步骤 | 跳过原因/预期结果 |
| --- | --- | --- | --- |
| typecheck | 否 | 无 | 当前无代码 |
| unit | 否 | 无 | 当前无代码 |
| integration | 否 | 无 | 当前无服务 |
| e2e/browser | 否 | 无 | 当前无前端 |
| API smoke | 否 | 无 | 当前无 API |
| manual verification | 是 | `Get-ChildItem`、`validate.ps1` | 验证文档和规范状态 |

## UI/人工验收

- 页面地址：不适用。
- 关键操作路径：不适用。
- 回归清单路径：`docs/quality/regression-checklist.md`
- 截图或手动验证说明：不适用。
- 错误态验证：不适用。
- 不涉及 UI 时说明：本阶段为项目接入和计划落盘。

## 任务顺序

1. [x] 创建计划目录和项目骨架目录。
2. [x] 保存总计划、数据库计划和 Agent 决策。
3. [x] 生成 SpecForge 项目画像和 Codex 入口。
4. [x] 运行规范验证。
5. [x] 切入数据库地基阶段。

## 验收标准

- [x] 所有计划文件存在且能打开。
- [x] `.ai-spec/ai-spec.yaml` 存在并标识项目画像。
- [x] `quick-ref.md` 变为 `GENERATED` 且内容不是占位。
- [x] `AGENTS.md` 指向项目内 `.ai-spec`。
- [x] 本阶段未写业务代码。

## 验证命令

```text
$files = @(
  'docs/plans/project-plan.md',
  'docs/plans/current.md',
  'docs/plans/database-design-plan.md',
  'docs/plans/agent-runtime-decision.md',
  '.ai-spec/ai-spec.yaml',
  'AGENTS.md'
)
$files | ForEach-Object { Test-Path $_ }
```

## 风险与回滚

- 风险：
  - 计划文档过早固化，需要后续根据模板和真实代码调整。
- 回滚/恢复方式：
  - 删除本阶段新增文档和配置，恢复 `.ai-spec/business/quick-ref.md` 到占位状态。

## 验收证据

- 执行命令或人工验证步骤：`powershell -ExecutionPolicy Bypass -File .ai-spec/scripts/validate.ps1`
- 命令结果或观察结果：`V2 template tests passed.`；`Structure, policy, skill, JSON, and Markdown link validation passed.`
- 关键接口/页面/数据/进程验证：不适用。
- 模块化自检结果：已建立 `docs/architecture/modules.md`，本阶段无业务代码。
- 变更影响矩阵结果：已在本阶段文件记录。
- 回归清单验证结果：已建立 `docs/quality/regression-checklist.md`，本阶段无业务链路可跑。
- 未完成项：Git 初始化、外部模板 clone、ORM 选择留到后续确认。
- 未验证项和原因：当前无业务代码可验证。
- 残余风险：外部模板和 Git 策略尚未确认。
- current.md 推进结果：已推进到 `phases/01-database-foundation.md`。
- 完成时间：2026-06-22。
