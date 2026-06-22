# SpecForge

SpecForge 是项目级 AI 协作规范。核心目标：**轻量入口、省 token、保质量**。

它只安装到当前项目，不写入 `~/.claude/rules/`、`~/.codex/` 等全局配置；Claude Code、Codex、Cursor、Copilot 可用，其它 AI 使用通用入口。

## 项目亮点

- **轻量入口**：父目录只放 AI 可识别的入口文件，完整规范落到子仓 `.ai-spec/`。
- **省 token**：日常优先读 `business/quick-ref.md`，复杂任务才逐级加载更多规范。
- **质量兜底**：保留计划、交付、安全、Git、提交前扫描和多子仓更新规则。

## 使用逻辑

首次接入时，让 AI 读取 `.ai-spec/AI-START.md` 建立项目画像；接入完成后，新会话只从 `quick-ref.md` 恢复上下文。多子仓项目由父目录轻入口指向各子仓规范；规范升级时从父目录一键同步到子仓。

## 快速安装

在目标项目根目录执行一行命令：

PowerShell：

```powershell
git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec; Remove-Item -Recurse -Force .ai-spec/.git
```

CMD：

```bat
git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec && rmdir /s /q .ai-spec\.git
```

Bash：

```bash
git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec && rm -rf .ai-spec/.git
```

## 首次接入

把这句发给 AI：

```text
请读取 .ai-spec/AI-START.md，并严格按启动协议接入当前项目。先完成只读识别和启动报告，不要直接修改业务代码。
```

空的新项目会先进入计划阶段，确认 `docs/plans/project-plan.md` 后再创建子仓、初始化 Git 和执行规范瘦身。

## 切换 AI

```text
当前项目已经完成 SpecForge 接入，不要重新安装、重新接入或全量扫描。请先读取 .ai-spec/business/quick-ref.md，按动态上下文门禁加载必要文件；检查 git status、docs/plans/current.md、最新 Handoff 和 active session。先简要报告当前阶段、未完成事项、工作区状态和下一步，确认没有文件冲突后继续。
```

## 更新规范

父目录一行拉取远端最新规范并同步到子仓：

PowerShell：

```powershell
if (-not (Test-Path .ai-spec\scripts\update.ps1)) { git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec }; .\.ai-spec\scripts\update.ps1 -TargetRoot . -Apply
```

CMD：

```bat
if exist .ai-spec\scripts\update.cmd (.ai-spec\scripts\update.cmd -TargetRoot . -Apply) else (git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec && .ai-spec\scripts\update.cmd -TargetRoot . -Apply)
```

Bash：

```bash
if [ ! -f .ai-spec/scripts/update.sh ]; then git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec; fi; bash .ai-spec/scripts/update.sh --target . --apply
```

只更新当前子仓：

PowerShell：`.\.ai-spec\scripts\update.ps1 -Apply`  
CMD：`.ai-spec\scripts\update.cmd -Apply`  
Bash：`bash .ai-spec/scripts/update.sh --apply`

更新提示词：

```text
请读取当前目录 .ai-spec/AI-START.md，执行规范更新。这不是首次接入，不要重新全量扫描项目。只更新模板规范和缺失入口，保留项目事实、计划、交接、业务代码和已有 AI 入口。完成后报告更新、保留和冲突项。
```

## 检查远端更新

只拉取远端最新规范做 dry-run，不应用更新：

PowerShell：

```powershell
if (-not (Test-Path .ai-spec\scripts\update.ps1)) { git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec }; .\.ai-spec\scripts\update.ps1 -TargetRoot .
```

CMD：

```bat
if exist .ai-spec\scripts\update.cmd (.ai-spec\scripts\update.cmd -TargetRoot .) else (git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec && .ai-spec\scripts\update.cmd -TargetRoot .)
```

Bash：

```bash
if [ ! -f .ai-spec/scripts/update.sh ]; then git clone https://github.com/xchen1012a-sketch/SpecForge.git .ai-spec; fi; bash .ai-spec/scripts/update.sh --target .
```

## 详细文档

- [AI-START.md](AI-START.md)
- [使用指南](docs/使用指南.md)
- [配置示例](ai-spec.example.yaml)
