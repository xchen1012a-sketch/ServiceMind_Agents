# 多项目接入工作流

仅当 `PROJECT_ROOT` 下检测到 2+ 个真实项目目录时读取本文件。父目录通常不是代码项目，不放完整 `.ai-spec/`。

## 1. 先排除同项目多副本

检测到多个候选项目时，不要立即按多项目安装。先判断是否为同项目多副本：

- 子目录名称表达版本/用途：`全版工程代码`、`授课工程代码`、`demo`、`backup`、`copy`、`archive`
- 多个子目录存在同名包结构、同名主入口、相同 `src/` 层级
- 构建文件类型相同，依赖高度相似
- Java/Eclipse 项目出现相同 `.project` / `.classpath` / 包名

命中上述信号时，输出“疑似同项目多副本”，询问用户选择：

1. 按单项目处理，选择一个主目录接入。
2. 按多项目处理，每个子项目独立 `.ai-spec/`。
3. 只生成分析报告，不安装。

未确认前不得批量写入多个 `.ai-spec/`。

## 2. 安装规则

1. 每个真实子项目各安装一份 `.ai-spec/`。
2. 所有实例共享一个 `multiProjectId`，写入各自 `ai-spec.yaml`。
3. 父目录只创建 `.specforge.json` 轻量索引，以及所选 AI 工具的轻量入口（如 `CLAUDE.md`、`AGENTS.md`、`.cursor/rules/ai-spec.mdc`、`.github/copilot-instructions.md`、`START-PROMPT.md`）。父入口只读取 `.specforge.json` 并路由到子项目 `.ai-spec/`，不复制规范正文：

```json
{
  "templateSource": "SpecForge",
  "templateVersion": 2,
  "multiProjectId": "<uuid>",
  "projects": [
    {
      "path": "frontend",
      "type": "frontend",
      "buildFiles": ["package.json"],
      "installedAt": "<ISO timestamp>"
    }
  ]
}
```

若父目录存在误装或临时使用的 `.ai-spec/`，必须等 `.specforge.json`、父级轻量入口和全部子项目 `.ai-spec/` 都配置成功后再删除父目录 `.ai-spec/`。如果父入口冲突、缺失或生成失败，先保留父目录 `.ai-spec/` 并报告需要人工合并；每个真实子项目保留自己的完整 `.ai-spec/`。

## 2.1 Git 归属

多项目接入时，父目录默认不生成 Git 仓库。`-ManageGit` 的自动策略应先完成子项目识别，再按以下规则决定：

- 父目录已有 `.git`，或存在 monorepo / 聚合工程信号（如 `pnpm-workspace.yaml`、`go.work`、根 `package.json`、根 `pom.xml` 等）时，在父目录管理 Git。
- 父目录只是多个独立项目的容器时，在各子项目目录分别管理 Git。
- 只有用户显式指定父级策略时，才允许在普通父目录创建 Git；只有用户显式指定项目策略时，才允许在已有父级 Git 的目录内创建子仓。

## 3. 一致文件与差异文件

所有实例中应保持一致：

- `AI-START.md`
- `README.md`
- `core/`
- `core-lite/`
- `governance/`
- `skills/`
- `workflows/`
- `contracts/`
- `scripts/validate.ps1`

每个项目独立维护，禁止同步覆盖：

- `ai-spec.yaml`
- `business/`
- `stacks/`
- `adapters/`

## 4. ai-spec.yaml

AI 首次接入直接生成每个子项目的正式 `ai-spec.yaml`，不用让用户从零填写。

必须从以下来源推断并落盘：

- 代码目录和文件类型
- 构建文件和依赖
- 包结构、入口文件、配置文件
- README / docs 中的项目说明

`type`、`stage`、`stack`、`commands`、`projectSize` 都应直接写入正式文件。后续用户明确要求时，AI 可以继续修改 `ai-spec.yaml`，但交付时必须列出 diff。模板 `-Sync` 仍然禁止同步覆盖 `ai-spec.yaml`。

## 5. 项目类型判定

| 信号 | 类型 |
| --- | --- |
| `package.json` 且依赖含 React / Vue / Next.js 等前端框架 | `frontend` |
| `pom.xml` / `go.mod` / `requirements.txt` / `.project` / `.classpath` 且无前端框架依赖 | `backend` |
| `package.json` 同时含前端框架和后端框架依赖 | `fullstack` |
| `pubspec.yaml` / 含 `android/` 或 `ios/` 目录 | `mobile` |
| `Cargo.toml` / `go.mod` 且无 Web 服务框架 | `library-sdk` |
| `pyproject.toml` 且含 AI/LLM 框架依赖 | `ai-llm` |
| 含 `main.go` / `main.rs` / `__main__.py` / `bin/` 目录，且无 Web 框架依赖 | `cli` |
| 含 `dbt_project.yml` / `airflow.cfg` / `dagster` / 大量 SQL 文件，且无 Web 入口 | `data-platform` |
| 无法判定 | `generic` |

L4 接入允许检查深度 ≤ 2 的候选目录，但必须排除 `node_modules`、`vendor`、`.git`、`dist`、`build`、`target`、`out`。

## 6. 后续会话

- 子项目目录启动：按普通启动协议执行，使用 `multiProjectId` 识别兄弟项目。
- 父目录启动：读取 `.specforge.json` 后询问本次处理哪个子项目或全部。
- 版本不一致：提示执行 `scripts/install.ps1 -TargetRoot <父目录或项目目录> -Sync`；实际覆盖必须由用户确认并追加 `-Apply`。
