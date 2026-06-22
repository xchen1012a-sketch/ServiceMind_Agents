# AI 工具适配器

`AI-START.md` 是唯一规范入口。适配器只解决不同工具的自动发现方式，不复制安全、架构、测试或交付规则。

## 当前适配

| 工具 | 模板 | 推荐落点 |
|---|---|---|
| Claude Code | `claude-code/CLAUDE.md.template` | 项目根 `CLAUDE.md` |
| Claude Code 权限 | `claude-code/settings.json.template` | `.claude/settings.json`，合并前逐项审查 |
| Codex | `codex/AGENTS.md.template` | 项目根 `AGENTS.md` |
| Cursor | `cursor/ai-spec.mdc.template` | `.cursor/rules/ai-spec.mdc` |
| GitHub Copilot | `github-copilot/copilot-instructions.md.template` | `.github/copilot-instructions.md` |
| 其它工具 | `generic/START-PROMPT.md` | 直接作为启动提示词 |

## 多项目父目录入口

多子仓接入时，父目录只保留轻量入口和 `.specforge.json`，完整规范落在各子项目 `.ai-spec/`：

| 工具 | 父目录入口 | 行为 |
|---|---|---|
| Claude Code | `CLAUDE.md` | 读取 `.specforge.json`，路由到子项目 `.ai-spec/` |
| Codex | `AGENTS.md` | 读取 `.specforge.json`，路由到子项目 `.ai-spec/` |
| Cursor | `.cursor/rules/ai-spec.mdc` | 读取 `.specforge.json`，路由到子项目 `.ai-spec/` |
| GitHub Copilot | `.github/copilot-instructions.md` | 读取 `.specforge.json`，路由到子项目 `.ai-spec/` |
| 其它工具 | `START-PROMPT.md` | 手动提示词，路由到子项目 `.ai-spec/` |

父目录 `.ai-spec/` 只允许作为安装/迁移期间的临时规则来源；必须等 `.specforge.json`、父级轻量入口和全部子项目 `.ai-spec/` 都配置好后再删除。若入口冲突或生成失败，保留父目录 `.ai-spec/` 并报告需要人工合并。

## 兼容规则

- 安装前检查目标文件是否存在；存在则语义合并，不覆盖。
- 工具版本改变自动发现格式时，只更新适配器，不修改规范内核。
- 未列出的工具日常先读 `business/quick-ref.md`；状态不是 `GENERATED` 或执行接入/完整审计时才读 `AI-START.md`。不得因为没有专用适配器而拒绝接入。
- Skills 的权威源是 `skills/<name>/SKILL.md`。按工具需要复制或链接到其项目级 Skill 目录。
- Skill 策略由 `ai-spec.yaml` 的 `ai.skillPolicy.mode` 决定：`project-first` 默认项目 Skill 优先；`local-first` 用户本地 Skill 优先；`hybrid` 两者兼顾但冲突时项目规则胜出。
- 用户可要求切换“本地优先”或“两者兼顾”，AI 应更新 `ai-spec.yaml`，并在输出中说明使用的 Skill 来源。
- 权限配置不得简单取并集；新增权限必须逐项说明能力和风险。
