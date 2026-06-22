$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$failures = [System.Collections.Generic.List[string]]::new()

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { $script:failures.Add($Message) }
}

function Read-ProjectFile {
    param([string]$RelativePath)
    $path = Join-Path $root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $script:failures.Add("Missing file: $RelativePath")
        return ''
    }
    return Get-Content -Raw -Encoding UTF8 -LiteralPath $path
}

$requiredFiles = @(
    'AI-START.md',
    'README.md',
    '.gitattributes',
    'ai-spec.example.yaml',
    'adapters/README.md',
    'adapters/claude-code/CLAUDE.md.template',
    'adapters/claude-code/settings.json.template',
    'adapters/codex/AGENTS.md.template',
    'adapters/cursor/ai-spec.mdc.template',
    'adapters/github-copilot/copilot-instructions.md.template',
    'adapters/generic/START-PROMPT.md',
    'adapters/multi-project/AGENTS.md.template',
    'adapters/multi-project/CLAUDE.md.template',
    'adapters/multi-project/START-PROMPT.md.template',
    'adapters/multi-project/ai-spec.mdc.template',
    'adapters/multi-project/copilot-instructions.md.template',
    'business/quick-ref.md',
    'core-lite/delivery-lite.md',
    'core-lite/security-lite.md',
    'core-lite/testing-lite.md',
    'core/command-standard.md',
    'workflows/multi-project-onboard.md',
    'workflows/output-protocol.md',
    'workflows/project-planning.md',
    'workflows/context-maintenance.md',
    'workflows/new-project.md',
    'workflows/existing-project.md',
    'workflows/in-progress-project.md',
    'governance/policy-levels.md',
    'governance/exception-template.md',
    'governance/adr-template.md',
    'governance/rfc-template.md',
    'governance/risk-register-template.md',
    'governance/handoff-template.md',
    'governance/project-plan-template.md',
    'governance/phase-plan-template.md',
    'governance/module-contract-template.md',
    'governance/regression-checklist-template.md',
    'governance/ownership-template.md',
    'skills/product-architect/SKILL.md',
    'skills/dev-implementation/SKILL.md',
    'skills/code-reviewer/SKILL.md',
    'skills/debugger/SKILL.md',
    'skills/spec-evaluator/SKILL.md',
    'scripts/install.sh',
    'scripts/install.ps1',
    'scripts/update.ps1',
    'scripts/update.cmd',
    'scripts/update.sh',
    'scripts/maintain-context.ps1',
    'scripts/maintain-context.sh',
    'scripts/audit-global-context.ps1',
    'scripts/git-preflight.ps1',
    'scripts/validate.ps1'
)

foreach ($relativePath in $requiredFiles) {
    Assert-True (Test-Path -LiteralPath (Join-Path $root $relativePath) -PathType Leaf) "Missing file: $relativePath"
}

# Root .md whitelist: AI-START.md, README.md, and any manual with prefix "AI"
$rootMarkdown = @(Get-ChildItem -LiteralPath $root -File -Filter '*.md' | Select-Object -ExpandProperty Name)
$allowedRootMarkdown = @('AI-START.md', 'README.md')
$unexpectedRootMarkdown = @($rootMarkdown | Where-Object {
    $_ -notin $allowedRootMarkdown -and $_ -notmatch '^AI.*\.md$'
})
Assert-True ($unexpectedRootMarkdown.Count -eq 0) "Unexpected root Markdown: $($unexpectedRootMarkdown -join ', ')"

$start = Read-ProjectFile 'AI-START.md'
foreach ($section in @('Startup Protocol', 'Project Stage Detection', 'AI Tool Detection', 'Security Baseline', 'Context Routing', 'Delivery Protocol')) {
    Assert-True ($start.Contains($section)) "AI-START.md missing section marker: $section"
}
Assert-True ($start.Contains('new-project')) 'AI-START.md does not route new projects'
Assert-True ($start.Contains('existing-project')) 'AI-START.md does not route existing projects'
Assert-True ($start.Contains('in-progress-project')) 'AI-START.md does not route in-progress projects'
Assert-True ($start.Contains('generic')) 'AI-START.md has no generic fallback'
Assert-True ($start.Contains('上下文预算')) 'AI-START.md missing context budget protocol'
Assert-True ($start.Contains('status: GENERATED')) 'AI-START.md quick recovery does not require generated quick-ref status'
Assert-True ($start.Contains('上下文使用报告')) 'AI-START.md does not require context usage reporting'
Assert-True ($start.Contains('受控例外')) 'AI-START.md does not define controlled exceptions'
Assert-True ($start.Contains('初始基线 commit')) 'AI-START.md does not clarify the no-Git initial commit exception'
Assert-True ($start.Contains('quick-ref.md 是日常启动唯一入口')) 'AI-START.md does not make quick-ref the daily startup entry'
Assert-True ($start.Contains('core-lite/delivery-lite.md')) 'AI-START.md does not route simple tasks to core-lite'
Assert-True ($start.Contains('projectSize')) 'AI-START.md missing project size routing'
Assert-True ($start.Contains('tiny | small | medium | large | enterprise')) 'AI-START.md missing project size levels'
Assert-True ($start.Contains('Git 提交硬性门禁')) 'AI-START.md missing hard git commit gate'
Assert-True ($start.Contains('只提交纯代码')) 'AI-START.md missing pure-code commit rule'
Assert-True ($start.Contains('暂存区必须检查')) 'AI-START.md missing staging-area check rule'
Assert-True ($start.Contains('git-preflight.ps1')) 'AI-START.md missing git preflight scan rule'
Assert-True ($start.Contains('先澄清假设')) 'AI-START.md missing clarify-assumptions coding discipline'
Assert-True ($start.Contains('模块化硬门禁')) 'AI-START.md missing mandatory modular coding gate'
Assert-True ($start.Contains('维护扩展门禁')) 'AI-START.md missing maintainability extension gate'
Assert-True ($start.Contains('简单优先')) 'AI-START.md missing simplicity-first coding discipline'
Assert-True ($start.Contains('外科式改动')) 'AI-START.md missing surgical-change coding discipline'
Assert-True ($start.Contains('目标驱动验证')) 'AI-START.md missing goal-driven verification discipline'
Assert-True ($start.Contains('执行任何实施任务前')) 'AI-START.md missing mandatory pre-implementation planning gate'
Assert-True ($start.Contains('无需用户额外提醒')) 'AI-START.md does not require automatic planning activation'
Assert-True ($start.Contains('workflows/multi-project-onboard.md')) 'AI-START.md missing lazy multi-project workflow route'
Assert-True ($start.Contains('workflows/output-protocol.md')) 'AI-START.md missing output protocol route'
Assert-True ($start.Contains('workflows/session-coordination.md')) 'AI-START.md missing session coordination workflow route'
Assert-True ($start.Contains('workflows/project-planning.md')) 'AI-START.md missing project planning workflow route'
Assert-True ($start.Contains('workflows/context-maintenance.md')) 'AI-START.md missing lazy context maintenance route'
Assert-True ($start.Contains('单次读取上限为 250 行')) 'AI-START.md missing large-file chunk read gate'
Assert-True ($start.Contains('SpecForge 仅允许安装到项目目录')) 'AI-START.md missing project-only installation boundary'
Assert-True ($start.Contains('三层约束模型')) 'AI-START.md missing constraint model boundary'
Assert-True ($start.Contains('证据不足') -and $start.Contains('未证实')) 'AI-START.md missing insufficient-evidence reporting rule'
Assert-True ($start.Contains('项目存在 API/数据库不构成升级理由')) 'AI-START.md still escalates every backend task to L3'
Assert-True ($start.Contains('公开 API 契约')) 'AI-START.md missing concrete API escalation trigger'
Assert-True ($start.Contains('Skill 使用策略')) 'AI-START.md missing skill policy section'
Assert-True ($start.Contains('project-first')) 'AI-START.md missing project-first skill mode'
Assert-True ($start.Contains('local-first')) 'AI-START.md missing local-first skill mode'
Assert-True ($start.Contains('hybrid')) 'AI-START.md missing hybrid skill mode'
foreach ($skillName in @('product-architect', 'dev-implementation', 'code-reviewer', 'debugger', 'spec-evaluator')) {
    Assert-True ($start.Contains("skills/$skillName/SKILL.md")) "AI-START.md missing skill route: $skillName"
}
foreach ($mode in @('L0 快速恢复', 'L1 机械改动', 'L2 标准改动', 'L3 高风险改动', 'L4 接入/审计')) {
    Assert-True ($start.Contains($mode)) "AI-START.md missing context budget mode: $mode"
}

$quickRef = Read-ProjectFile 'business/quick-ref.md'
$quickRefLines = @($quickRef.TrimEnd() -split "`r?`n")
Assert-True ($quickRef.Contains('status: TEMPLATE_PLACEHOLDER')) 'quick-ref.md missing placeholder status marker'
Assert-True ($quickRef.Contains('生成后改为 GENERATED')) 'quick-ref.md does not explain generated status transition'
Assert-True ($quickRef.Contains('动态上下文门禁')) 'quick-ref.md missing dynamic context gate'
Assert-True ($quickRef.Contains('日常启动唯一入口')) 'quick-ref.md is not documented as the daily startup entry'
Assert-True ($quickRef.Contains('projectSize:')) 'quick-ref.md missing project size marker'
Assert-True ($quickRef.Contains('sizeStrategy:')) 'quick-ref.md missing size-based loading strategy marker'
Assert-True ($quickRef.Contains('计划自动触发门禁')) 'quick-ref.md missing automatic planning gate'
Assert-True ($quickRef.Contains('workflows/project-planning.md')) 'quick-ref.md missing lazy planning workflow route'
Assert-True ($quickRef.Contains('无需用户额外提醒')) 'quick-ref.md does not automatically activate planning'
Assert-True ($quickRef.Contains('docs/plans/current.md')) 'quick-ref.md missing existing plan resume route'
Assert-True ($quickRef.Contains('module-contract-template.md')) 'quick-ref.md missing module contract gate'
Assert-True ($quickRef.Contains('regression-checklist-template.md')) 'quick-ref.md missing regression checklist gate'
Assert-True ($quickRef.Contains('影响矩阵')) 'quick-ref.md missing impact matrix gate'
Assert-True ($quickRef.Contains('outputLanguage: zh-CN')) 'quick-ref.md missing the lightweight language lock'
Assert-True ($quickRef.Contains('maintenanceDue:')) 'quick-ref.md missing lightweight maintenance due marker'
Assert-True ($quickRef.Contains('250')) 'quick-ref.md missing large-file chunk budget'
Assert-True ($quickRefLines.Count -le 40) "quick-ref.md exceeds the 40-line token budget: $($quickRefLines.Count) lines"
Assert-True ($start.Contains('计划自动触发门禁') -and $start.Contains('模块契约门禁') -and $start.Contains('回归清单门禁')) 'AI-START.md does not preserve implementation gates when quick-ref is generated'
Assert-True ($start.Contains('先搜索并只读取命中的相关章节')) 'AI-START.md does not route business rules at section level'
Assert-True ($start.Contains('按需读取不等于跳过适用规则')) 'AI-START.md allows token saving to weaken quality gates'
Assert-True ($start.Contains('默认输出语言强制为简体中文')) 'AI-START.md missing the Simplified Chinese output lock'
Assert-True ($start.Contains('不得因代码、日志、依赖、框架或原始文档为英文而切换')) 'AI-START.md allows silent language switching'
Assert-True ($start.Contains('模板占位说明') -and $start.Contains('无法判断时使用简体中文')) 'AI-START.md does not force Chinese for maintained docs and new comments'
Assert-True ($start.Contains('outputLanguage: zh-CN') -and $start.Contains('语言门禁不得删除')) 'AI-START.md does not preserve the language lock when regenerating quick-ref'

foreach ($lite in @('core-lite/delivery-lite.md', 'core-lite/security-lite.md', 'core-lite/testing-lite.md')) {
    $liteContent = Read-ProjectFile $lite
    Assert-True ($liteContent.Contains('appliesTo:')) "$lite missing appliesTo frontmatter"
    Assert-True ($liteContent.Contains('loadWhen:')) "$lite missing loadWhen frontmatter"
}

$deliveryLite = Read-ProjectFile 'core-lite/delivery-lite.md'
Assert-True ($deliveryLite.Contains('短版输出')) 'delivery-lite missing short output rule'
Assert-True ($deliveryLite.Contains('禁止流水账')) 'delivery-lite missing no-process-log rule'
Assert-True ($deliveryLite.Contains('表格最多 3 列')) 'delivery-lite missing narrow-table rule'

$outputProtocol = Read-ProjectFile 'workflows/output-protocol.md'
Assert-True ($outputProtocol.Contains('默认短版')) 'output protocol missing short-by-default rule'
Assert-True ($outputProtocol.Contains('L0')) 'output protocol missing level-based output rules'
Assert-True ($outputProtocol.Contains('终端友好表格')) 'output protocol missing terminal-friendly table rules'
Assert-True ($outputProtocol.Contains('表格最多 3 列')) 'output protocol missing max table column rule'
Assert-True ($outputProtocol.Contains('风险清单优先用编号列表')) 'output protocol missing numbered risk list rule'
Assert-True ($outputProtocol.Contains('默认使用简体中文')) 'output protocol missing Simplified Chinese default'
Assert-True ($outputProtocol.Contains('实际修改公开契约')) 'output protocol still escalates based on project capabilities instead of task changes'
Assert-True ($outputProtocol.Contains('输出给用户必须抓重点')) 'output protocol missing lightweight user-facing report rule'
Assert-True ($outputProtocol.Contains('未证实：')) 'output protocol missing unverified evidence line'

$sessionWorkflow = Read-ProjectFile 'workflows/session-coordination.md'
Assert-True ($sessionWorkflow.Contains('工具不会自动执行锁')) 'session workflow missing non-automatic-lock warning'
Assert-True ($sessionWorkflow.Contains('workflows/session-coordination.md')) 'session workflow missing self route marker'

$aiWorkflow = Read-ProjectFile 'core/ai-workflow.md'
Assert-True ($aiWorkflow.Contains('business/quick-ref.md')) 'AI handoff workflow bypasses the lightweight daily entry'
Assert-True ($aiWorkflow.Contains('status: GENERATED')) 'AI handoff workflow does not check quick-ref readiness'
Assert-True ($aiWorkflow.Contains('AI-START.md')) 'AI handoff workflow missing onboarding/audit fallback'
Assert-True ($aiWorkflow.Contains('docs/plans/current.md')) 'AI handoff workflow missing current plan recovery'

$architectureStandard = Read-ProjectFile 'core/architecture.md'
foreach ($rule in @('模块化代码是实施硬门禁', '代码落点（强约束）', '新增文件必须落到项目既有模块结构', '入口层只处理协议', '基础设施/适配器层', '模块契约触发', 'docs/architecture/modules.md')) {
    Assert-True ($architectureStandard.Contains($rule)) "architecture standard missing modular gate: $rule"
}

$planningWorkflow = Read-ProjectFile 'workflows/project-planning.md'
Assert-True ($planningWorkflow.Contains('docs/plans/project-plan.md')) 'planning workflow missing persistent project plan path'
Assert-True ($planningWorkflow.Contains('docs/plans/current.md')) 'planning workflow missing lightweight current plan entry'
Assert-True ($planningWorkflow.Contains('docs/plans/phases/')) 'planning workflow missing phase plan directory'
Assert-True ($planningWorkflow.Contains('超过 200 行')) 'planning workflow missing long-plan split threshold'
Assert-True ($planningWorkflow.Contains('3 个以上阶段')) 'planning workflow missing multi-phase split threshold'
Assert-True ($planningWorkflow.Contains('用户确认执行')) 'planning workflow missing confirmation-to-persist transition'
Assert-True ($planningWorkflow.Contains('只读取 `docs/plans/current.md`')) 'planning workflow does not protect daily token usage'
Assert-True ($planningWorkflow.Contains('实施前自动判定')) 'planning workflow missing mandatory automatic trigger'
Assert-True ($planningWorkflow.Contains('无需用户额外提醒')) 'planning workflow relies on the user to request planning'
foreach ($rule in @('计划分层', '已证实事实', '未证实假设', '模块职责、代码落点、依赖方向', '模块化自检结果', '变更影响矩阵', 'docs/quality/regression-checklist.md', 'docs/plans/decisions.md', '安全评审点', '测试层级矩阵', '页面地址', '停止条件', 'Definition of Done', '计划变更记录')) {
    Assert-True ($planningWorkflow.Contains($rule)) "planning workflow missing quality gate: $rule"
}

$maintenanceWorkflow = Read-ProjectFile 'workflows/context-maintenance.md'
foreach ($rule in @('惰性触发', 'safe-only', '先检查行数、状态和修改时间', '禁止机械截断', 'active', 'blocked', '验收证据', '250 行', '可回滚')) {
    Assert-True ($maintenanceWorkflow.Contains($rule)) "context maintenance workflow missing safety rule: $rule"
}
Assert-True ($maintenanceWorkflow.Contains('自动执行 dry-run')) 'context maintenance workflow does not auto-trigger its safe inspection'
Assert-True ($maintenanceWorkflow.Contains('自动执行 `-Apply`')) 'safe-only maintenance is configured but never auto-applied'

$projectPlanTemplate = Read-ProjectFile 'governance/project-plan-template.md'
Assert-True ($projectPlanTemplate.Contains('项目总计划')) 'project plan template missing title'
Assert-True ($projectPlanTemplate.Contains('阶段索引')) 'project plan template missing phase index'
Assert-True ($projectPlanTemplate.Contains('总体验收标准')) 'project plan template missing overall acceptance criteria'
foreach ($section in @('已证实事实', '未证实假设', '待用户确认问题', '模块职责与代码落点', '依赖方向与跨模块访问规则', '关键决策记录', '变更影响矩阵', '测试矩阵与验证命令', '项目级 Definition of Done', '计划变更记录')) {
    Assert-True ($projectPlanTemplate.Contains($section)) "project plan template missing section: $section"
}

$phasePlanTemplate = Read-ProjectFile 'governance/phase-plan-template.md'
foreach ($section in @('阶段目标', '实施范围', '依赖与前置条件', '模块归属与分层落点', '代码落点与职责边界', '依赖方向与跨模块访问', '模块化自检结果', '变更影响矩阵', '回归清单验证结果', '安全评审点', '测试层级矩阵', 'UI/人工验收', '任务顺序', '验收标准', '验证命令', '风险与回滚', '完成状态', 'current.md 推进结果')) {
    Assert-True ($phasePlanTemplate.Contains($section)) "phase plan template missing section: $section"
}

$moduleContractTemplate = Read-ProjectFile 'governance/module-contract-template.md'
foreach ($section in @('模块契约清单', '职责', '对外能力/API', '拥有数据', '禁止访问', '跨模块访问')) {
    Assert-True ($moduleContractTemplate.Contains($section)) "module contract template missing section: $section"
}

$regressionChecklistTemplate = Read-ProjectFile 'governance/regression-checklist-template.md'
foreach ($section in @('项目回归清单', '核心链路', '边界与错误态', '权限不足', '重复提交/并发')) {
    Assert-True ($regressionChecklistTemplate.Contains($section)) "regression checklist template missing section: $section"
}

$multiProjectWorkflow = Read-ProjectFile 'workflows/multi-project-onboard.md'
Assert-True ($multiProjectWorkflow.Contains('同项目多副本')) 'multi-project workflow missing duplicate-copy guard'
Assert-True ($multiProjectWorkflow.Contains('AI 首次接入直接生成')) 'multi-project workflow missing direct ai-spec generation guidance'
Assert-True ($multiProjectWorkflow.Contains('templateVersion')) 'multi-project workflow missing template version consistency rule'
Assert-True ($multiProjectWorkflow.Contains('install.ps1 -TargetRoot')) 'multi-project workflow missing sync command rule'
Assert-True ($multiProjectWorkflow.Contains('禁止同步覆盖')) 'multi-project workflow missing no-automatic-sync-overwrite rule'

$validateScript = Read-ProjectFile 'scripts/validate.ps1'
Assert-True ($validateScript.Contains('Conflict summary')) 'validate.ps1 missing conflict summary output'
Assert-True ($validateScript.Contains('SpecForge doctor')) 'validate.ps1 missing doctor summary'
Assert-True ($validateScript.Contains('[switch]$SelfTest')) 'validate.ps1 missing explicit full self-test gate'
Assert-True ($validateScript.Contains('.specforge.json')) 'validate.ps1 missing multi-project parent checks'
Assert-True ($validateScript.Contains('status --porcelain')) 'validate.ps1 missing git status doctor check'
Assert-True ($validateScript.Contains('templateVersion')) 'validate.ps1 missing template version doctor check'

$specExample = Read-ProjectFile 'ai-spec.example.yaml'
Assert-True ($specExample.Contains('context:')) 'ai-spec.example.yaml missing context configuration'
Assert-True ($specExample.Contains('projectSize: auto')) 'ai-spec.example.yaml missing project size default'
Assert-True ($specExample.Contains('projectSizeSignals:')) 'ai-spec.example.yaml missing project size signals'
Assert-True ($specExample.Contains('generated by installer')) 'ai-spec.example.yaml does not mark generated signals'
Assert-True ($specExample.Contains('quickRefStatus: TEMPLATE_PLACEHOLDER')) 'ai-spec.example.yaml missing quick-ref status default'
Assert-True ($specExample.Contains('skillPolicy:')) 'ai-spec.example.yaml missing skill policy'
Assert-True ($specExample.Contains('mode: project-first')) 'ai-spec.example.yaml missing default project-first skill policy'
Assert-True ($specExample.Contains('outputLanguage:')) 'ai-spec.example.yaml missing output language policy'
Assert-True ($specExample.Contains('default: zh-CN')) 'ai-spec.example.yaml does not default to Simplified Chinese'
Assert-True ($specExample.Contains('locked: true')) 'ai-spec.example.yaml does not lock the default language'
Assert-True ($specExample.Contains('overrideOnlyByExplicitUserRequest: true')) 'ai-spec.example.yaml does not allow only explicit user language override'
Assert-True ($specExample.Contains('maintenance:')) 'ai-spec.example.yaml missing context maintenance configuration'
Assert-True ($specExample.Contains('strategy: lazy')) 'ai-spec.example.yaml does not use lazy maintenance'
Assert-True ($specExample.Contains('autoApply: safe-only')) 'ai-spec.example.yaml maintenance is not stability-first'
Assert-True ($specExample.Contains('singleReadMaxLines: 250')) 'ai-spec.example.yaml missing large-file read budget'
Assert-True ($specExample.Contains('scope: project-only')) 'ai-spec.example.yaml missing project-only scope lock'

$readme = Read-ProjectFile 'README.md'
Assert-True ($readme.Contains('轻量入口、省 token、保质量')) 'README missing the lightweight/token/quality core'
Assert-True (-not $readme.Contains('安装器能力差异')) 'README should not expose installer capability matrix'
Assert-True (-not $readme.Contains('scripts\install.ps1')) 'README should not expose install.ps1 as the user entry'
Assert-True ($readme.Contains('## 项目亮点')) 'README missing project highlights section'
Assert-True ($readme.Contains('## 使用逻辑')) 'README missing usage flow section'
Assert-True ($readme.Contains('完整规范落到子仓 `.ai-spec/`')) 'README missing child-repo spec placement summary'
Assert-True ($readme.Contains('从父目录一键同步到子仓')) 'README missing parent-to-child update flow'
Assert-True ($readme.Contains('快速安装')) 'README missing quick install section'
Assert-True ($readme.Contains('Claude Code、Codex、Cursor、Copilot')) 'README missing mainstream AI editor scope'
Assert-True ($readme.Contains('切换 AI')) 'README missing AI switch guidance'
Assert-True ($readme.Contains('不要重新安装、重新接入或全量扫描')) 'README does not prevent repeated onboarding after AI switch'
Assert-True ($readme.Contains('docs/plans/current.md')) 'README AI switch prompt missing current phase plan'
Assert-True ($readme.Contains('最新 Handoff')) 'README AI switch prompt missing handoff state'
Assert-True ($readme.Contains('active session')) 'README AI switch prompt missing active session check'
Assert-True ($readme.Contains('首次接入')) 'README missing first-use prompt'
Assert-True ($readme.Contains('更新规范')) 'README missing rule-refresh section'
Assert-True ($readme.Contains('不是首次接入')) 'README rule-refresh prompt can trigger repeated onboarding'
Assert-True ($readme.Contains('不要重新全量扫描项目')) 'README rule-refresh prompt does not prevent a full rescan'
Assert-True ($readme.Contains('只更新当前子仓')) 'README missing child-repo update shortcut'
Assert-True ($readme.Contains('.ai-spec\scripts\update.cmd -TargetRoot . -Apply')) 'README missing CMD parent update command'
Assert-True ($readme.Contains('.ai-spec\scripts\update.ps1 -Apply')) 'README missing PowerShell update command'
Assert-True ($readme.Contains('.ai-spec\scripts\update.cmd -Apply')) 'README missing CMD update command'
Assert-True ($readme.Contains('.ai-spec/scripts/update.sh --apply')) 'README missing Bash update command'
Assert-True ($readme.Contains('检查远端更新')) 'README missing remote update check section'
Assert-True ($readme.Contains('.ai-spec\scripts\update.ps1 -TargetRoot .')) 'README missing PowerShell remote dry-run check'
Assert-True ($readme.Contains('.ai-spec\scripts\update.cmd -TargetRoot .')) 'README missing CMD remote dry-run check'
Assert-True ($readme.Contains('.ai-spec/scripts/update.sh --target .')) 'README missing Bash remote dry-run check'
Assert-True (-not $readme.Contains('## 一键检查')) 'README should keep validate out of the lightweight entry'
Assert-True ($readme.Contains('只安装到当前项目')) 'README does not state the project-only boundary'
Assert-True ($readme.Contains('不写入 `~/.claude/rules/`')) 'README does not reject global rule installation'

$adapterReadme = Read-ProjectFile 'adapters/README.md'
Assert-True ($adapterReadme.Contains('project-first')) 'adapters README missing project-first skill policy'
Assert-True ($adapterReadme.Contains('local-first')) 'adapters README missing local-first skill policy'
Assert-True ($adapterReadme.Contains('hybrid')) 'adapters README missing hybrid skill policy'

foreach ($adapterPath in @(
    'adapters/claude-code/CLAUDE.md.template',
    'adapters/codex/AGENTS.md.template',
    'adapters/cursor/ai-spec.mdc.template',
    'adapters/github-copilot/copilot-instructions.md.template',
    'adapters/generic/START-PROMPT.md'
)) {
    $adapterContent = Read-ProjectFile $adapterPath
    Assert-True ($adapterContent.Contains('business/quick-ref.md')) "$adapterPath missing lightweight daily entry"
    Assert-True ($adapterContent.Contains('GENERATED')) "$adapterPath does not gate quick-ref readiness"
    Assert-True ($adapterContent.Contains('AI-START.md')) "$adapterPath missing onboarding/audit fallback"
    Assert-True ($adapterContent.Contains('简体中文') -or $adapterContent.Contains('Simplified Chinese')) "$adapterPath missing the Simplified Chinese output lock"
}

$installSh = Read-ProjectFile 'scripts/install.sh'
Assert-True ($installSh.Contains('--onboard')) 'install.sh missing onboard option'
Assert-True ($installSh.Contains('--sync')) 'install.sh missing sync option'
Assert-True ($installSh.Contains('intentionally lightweight')) 'install.sh missing lightweight scope warning'
Assert-True ($installSh.Contains('Full onboarding/sync remains implemented in scripts/install.ps1')) 'install.sh missing full installer guidance'

$updatePs1 = Read-ProjectFile 'scripts/update.ps1'
Assert-True ($updatePs1.Contains('git') -and $updatePs1.Contains('clone') -and $updatePs1.Contains('SpecForge.git')) 'update.ps1 does not pull the latest SpecForge source'
Assert-True ($updatePs1.Contains('Sync = $true')) 'update.ps1 does not use the safe sync path'
Assert-True ($updatePs1.Contains('SourceRoot')) 'update.ps1 missing local source injection for deterministic testing/recovery'
Assert-True ($updatePs1.Contains('claude-code') -and $updatePs1.Contains('github-copilot') -and $updatePs1.Contains('Tools = $Tools')) 'update.ps1 does not pass mainstream AI editor adapters into sync'
Assert-True ($updatePs1.Contains('finally')) 'update.ps1 does not guarantee temporary clone cleanup'
Assert-True ($updatePs1.Contains('Apply')) 'update.ps1 missing explicit apply gate'

$updateCmd = Read-ProjectFile 'scripts/update.cmd'
Assert-True ($updateCmd.Contains('update.ps1')) 'update.cmd does not delegate to the PowerShell updater'
Assert-True ($updateCmd.Contains('%*')) 'update.cmd does not forward update arguments'

$updateSh = Read-ProjectFile 'scripts/update.sh'
Assert-True ($updateSh.Contains('git clone') -and $updateSh.Contains('SpecForge.git')) 'update.sh does not pull the latest SpecForge source'
Assert-True ($updateSh.Contains('--sync')) 'update.sh does not use the safe sync path'
Assert-True ($updateSh.Contains('--apply')) 'update.sh missing explicit apply gate'
Assert-True ($updateSh.Contains('mktemp')) 'update.sh does not isolate temporary clone'

$installPs1 = Read-ProjectFile 'scripts/install.ps1'
Assert-True ($installPs1.Contains("'scripts\update.ps1'")) 'install.ps1 sync does not refresh update.ps1'
Assert-True ($installPs1.Contains("'scripts\update.cmd'")) 'install.ps1 sync does not refresh update.cmd'
Assert-True ($installPs1.Contains("'scripts\update.sh'")) 'install.ps1 sync does not refresh update.sh'
Assert-True ($installPs1.Contains("'scripts\maintain-context.ps1'")) 'install.ps1 sync does not refresh maintain-context.ps1'
Assert-True ($installPs1.Contains("'scripts\maintain-context.sh'")) 'install.ps1 sync does not refresh maintain-context.sh'
Assert-True ($installPs1.Contains("'scripts\audit-global-context.ps1'")) 'install.ps1 sync does not refresh audit-global-context.ps1'
Assert-True ($installPs1.Contains('Add-ParentEntrypoints -RootDir $RootDir')) 'install.ps1 sync does not refresh missing parent lightweight entries'
Assert-True ($installPs1.Contains('forbiddenGlobalRoots')) 'install.ps1 does not reject global AI configuration targets'

$newProjectSmokeRoot = [System.IO.Path]::GetFullPath((Join-Path ([System.IO.Path]::GetTempPath()) ('specforge-new-project-smoke-' + [guid]::NewGuid().ToString('N'))))
try {
    $emptyProjectRoot = Join-Path $newProjectSmokeRoot 'empty'
    New-Item -ItemType Directory -Force -Path $emptyProjectRoot | Out-Null
    & (Join-Path $root 'scripts\install.ps1') -TargetRoot $emptyProjectRoot -Mode new -Tools 'generic' -Onboard -Apply *> $null
    Assert-True (Test-Path -LiteralPath (Join-Path $emptyProjectRoot '.ai-spec\tests') -PathType Container) 'Empty new project slimmed rules before project-plan.md exists'
    Assert-True (Test-Path -LiteralPath (Join-Path $emptyProjectRoot '.ai-spec\scripts\install.ps1') -PathType Leaf) 'Empty new project removed installer before project-plan.md exists'

    $plannedProjectRoot = Join-Path $newProjectSmokeRoot 'planned'
    New-Item -ItemType Directory -Force -Path (Join-Path $plannedProjectRoot 'docs\plans') | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $plannedProjectRoot 'docs\plans\project-plan.md'), "# Project plan`n", [System.Text.UTF8Encoding]::new($false))
    & (Join-Path $root 'scripts\install.ps1') -TargetRoot $plannedProjectRoot -Mode new -Tools 'generic' -Onboard -Apply *> $null
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $plannedProjectRoot '.ai-spec\tests') -PathType Container)) 'Planned new project did not slim template self-tests'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $plannedProjectRoot '.ai-spec\scripts\install.ps1') -PathType Leaf)) 'Planned new project did not slim one-time installer'
}
finally {
    if ($newProjectSmokeRoot.StartsWith([System.IO.Path]::GetTempPath(), [System.StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $newProjectSmokeRoot)) {
        Remove-Item -LiteralPath $newProjectSmokeRoot -Recurse -Force
    }
}

$maintainContext = Read-ProjectFile 'scripts/maintain-context.ps1'
Assert-True ($maintainContext.Contains('maintenanceDue')) 'maintain-context.ps1 does not use the lazy due marker'
Assert-True ($maintainContext.Contains('[switch]$Apply')) 'maintain-context.ps1 missing dry-run/apply gate'
Assert-True ($maintainContext.Contains('COMPACT_REQUIRED')) 'maintain-context.ps1 does not report oversized semantic files'
Assert-True ($maintainContext.Contains('status: completed')) 'maintain-context.ps1 does not identify safe archive candidates'
Assert-True ($maintainContext.Contains('archive')) 'maintain-context.ps1 does not archive completed runtime files'
Assert-True (-not $maintainContext.Contains('business-rules.md -Force')) 'maintain-context.ps1 can destructively remove business rules'

$maintainContextSh = Read-ProjectFile 'scripts/maintain-context.sh'
Assert-True ($maintainContextSh.Contains('maintenanceDue')) 'maintain-context.sh does not use the lazy due marker'
Assert-True ($maintainContextSh.Contains('--apply')) 'maintain-context.sh missing dry-run/apply gate'
Assert-True ($maintainContextSh.Contains('COMPACT_REQUIRED')) 'maintain-context.sh does not report oversized semantic files'
Assert-True ($maintainContextSh.Contains('completed')) 'maintain-context.sh does not identify safe archive candidates'
Assert-True ($maintainContextSh.Contains('archive')) 'maintain-context.sh does not archive completed runtime files'

$globalAudit = Read-ProjectFile 'scripts/audit-global-context.ps1'
Assert-True ($globalAudit.Contains('GLOBAL_CONTEXT_WARNING')) 'global context audit missing concise warning marker'
Assert-True ($globalAudit.Contains('paths:')) 'global context audit does not distinguish path-scoped rules'
Assert-True ($globalAudit.Contains('Immediate Agent Usage') -and $globalAudit.Contains('80%')) 'global context audit misses broad agent/coverage triggers'
Assert-True (-not ($globalAudit -match '(?m)^\s*(Remove-Item|Move-Item|Set-Content)\b')) 'global context audit mutates user-level rules'

$gitAttributes = Read-ProjectFile '.gitattributes'
Assert-True ($gitAttributes.Contains('*.sh text eol=lf')) '.gitattributes does not force LF for shell scripts'
Assert-True ($gitAttributes.Contains('*.cmd text eol=crlf')) '.gitattributes does not force CRLF for CMD scripts'
Assert-True ($gitAttributes.Contains('*.ps1 text eol=crlf')) '.gitattributes does not force CRLF for PowerShell scripts'

Assert-True ($start.Contains('AI 首次接入必须') -and $start.Contains('ai-spec.yaml')) 'AI-START.md does not allow AI to generate ai-spec.yaml on onboarding'
Assert-True ($start.Contains('后续修改需用户明确授权')) 'AI-START.md missing explicit authorization rule for later ai-spec edits'

foreach ($routedFile in @(
    'core/delivery-standard.md',
    'core/security-standard.md',
    'core/testing-standard.md',
    'contracts/api-contract-standard.md',
    'contracts/integration-standard.md',
    'stacks/frontend-general.md',
    'stacks/backend-general.md'
)) {
    $routedContent = Read-ProjectFile $routedFile
    $normalizedRoutedContent = $routedContent.TrimStart([char]0xFEFF, [char]0x200B, " ", "`r", "`n", "`t")
    Assert-True ($normalizedRoutedContent.StartsWith('---')) "$routedFile missing routing frontmatter"
    Assert-True ($routedContent.Contains('appliesTo:')) "$routedFile missing appliesTo frontmatter"
    Assert-True ($routedContent.Contains('loadWhen:')) "$routedFile missing loadWhen frontmatter"
    Assert-True (([regex]::Matches($routedContent, '(?m)^appliesTo:')).Count -eq 1) "$routedFile has duplicate appliesTo frontmatter"
    Assert-True (([regex]::Matches($routedContent, '(?m)^loadWhen:')).Count -eq 1) "$routedFile has duplicate loadWhen frontmatter"
    Assert-True (([regex]::Matches($routedContent, '(?m)^fallbackTo:')).Count -eq 1) "$routedFile has duplicate fallbackTo frontmatter"
}

$securityStandard = Read-ProjectFile 'core/security-standard.md'
Assert-True ($securityStandard.Contains('Git 提交硬性门禁')) 'security standard missing hard git commit gate'
Assert-True ($securityStandard.Contains('暂存区必须检查')) 'security standard missing staging-area check'
Assert-True ($securityStandard.Contains('只提交纯代码')) 'security standard missing pure-code commit rule'
Assert-True ($securityStandard.Contains('.env')) 'security standard missing env-file filter'
Assert-True ($securityStandard.Contains('IDE 配置')) 'security standard missing IDE config filter'
Assert-True ($securityStandard.Contains('构建产物')) 'security standard missing build artifact filter'
Assert-True ($securityStandard.Contains('提交前扫描')) 'security standard missing pre-commit scan rule'

$gitPreflight = Read-ProjectFile 'scripts/git-preflight.ps1'
Assert-True ($gitPreflight.Contains('Git preflight scan')) 'git-preflight.ps1 missing scan banner'
Assert-True ($gitPreflight.Contains('.env')) 'git-preflight.ps1 missing env path block'
Assert-True ($gitPreflight.Contains('PRIVATE KEY')) 'git-preflight.ps1 missing private key scan'
Assert-True ($gitPreflight.Contains('.specforge.json')) 'git-preflight.ps1 missing parent SpecForge index gate'

foreach ($skill in @('product-architect', 'dev-implementation', 'code-reviewer', 'debugger', 'spec-evaluator')) {
    $relativePath = "skills/$skill/SKILL.md"
    $content = Read-ProjectFile $relativePath
    Assert-True ($content -match "(?ms)^---\s*\nname:\s*$skill\s*\ndescription:") "$relativePath has invalid frontmatter"
    Assert-True (-not ($content -match '(?m)^trigger:')) "$relativePath uses non-standard trigger field"
}

$devImplementationSkill = Read-ProjectFile 'skills/dev-implementation/SKILL.md'
Assert-True ($devImplementationSkill.Contains('workflows/project-planning.md')) 'dev implementation skill missing project planning workflow route'
Assert-True ($devImplementationSkill.Contains('计划自动触发门禁')) 'dev implementation skill can bypass the automatic planning gate'
Assert-True ($devImplementationSkill.Contains('business/quick-ref.md')) 'dev implementation skill forces the full startup document'
Assert-True ($devImplementationSkill.Contains('docs/plans/current.md')) 'dev implementation skill does not follow the active development plan'
Assert-True ($devImplementationSkill.Contains('相关章节')) 'dev implementation skill loads all business rules instead of relevant sections'
Assert-True ($devImplementationSkill.Contains('模块落点') -and $devImplementationSkill.Contains('跨模块直接读写')) 'dev implementation skill missing modular implementation gate'
Assert-True ($devImplementationSkill.Contains('module-contract-template.md') -and $devImplementationSkill.Contains('regression-checklist-template.md')) 'dev implementation skill missing maintainability templates'

$specEvaluatorSkill = Read-ProjectFile 'skills/spec-evaluator/SKILL.md'
Assert-True ($specEvaluatorSkill.Contains('证据不足封顶')) 'spec evaluator missing insufficient-evidence score caps'
Assert-True ($specEvaluatorSkill.Contains('最高 6 分')) 'spec evaluator does not cap score when evidence is missing'
Assert-True ($specEvaluatorSkill.Contains('未证实')) 'spec evaluator does not require unverified findings'
Assert-True ($specEvaluatorSkill.Contains('最多列 3 个关键问题')) 'spec evaluator output can become too verbose'

$productArchitectSkill = Read-ProjectFile 'skills/product-architect/SKILL.md'
Assert-True ($productArchitectSkill.Contains('business/quick-ref.md')) 'product architect skill forces the full startup document'
Assert-True ($productArchitectSkill.Contains('GENERATED')) 'product architect skill does not use the lightweight readiness gate'

foreach ($validatorRule in @('Missing spec.scope: project-only', 'Generated quick-ref still contains placeholder content', 'Generated business rules still contain placeholder content', 'Generated business rules lack source/reliability evidence markers', 'Generated project map still contains placeholder content', 'Missing ai.outputLanguage.default: zh-CN', 'Missing ai.outputLanguage.locked: true', 'Quick-ref exceeds 40 lines', 'Quick-ref status mismatch', 'planning auto-trigger gate', 'maintainability implementation gates', 'Stale AI adapter', 'Current plan exceeds 80 lines', 'Completed phase lacks acceptance evidence')) {
    Assert-True ($validateScript.Contains($validatorRule)) "validate.ps1 missing runtime drift check: $validatorRule"
}

$claudeAdapter = Read-ProjectFile 'adapters/claude-code/CLAUDE.md.template'
Assert-True (@($claudeAdapter.TrimEnd() -split "`r?`n").Count -le 15) 'Claude adapter is too large for an always-loaded project entry'
Assert-True (-not $claudeAdapter.Contains('状态机图')) 'Claude adapter duplicates project-specific business knowledge'

$securityStandard = Read-ProjectFile 'core/security-standard.md'
Assert-True ($securityStandard.Contains('仅 Cookie/浏览器会话')) 'security standard applies CSRF controls to every API'
Assert-True ($securityStandard.Contains('Bearer Token')) 'security standard does not distinguish token APIs from cookie sessions'
Assert-True ($securityStandard.Contains('JSON Schema')) 'security standard missing AI structured-output boundary'
Assert-True ($securityStandard.Contains('不可信用户输入')) 'security standard missing AI untrusted-input boundary'

$aiLlmStack = Read-ProjectFile 'stacks/ai-llm-app.md'
Assert-True ($aiLlmStack.Contains('JSON Schema')) 'AI/LLM stack missing structured output rule'
Assert-True ($aiLlmStack.Contains('不可信')) 'AI/LLM stack missing untrusted-input rule'

$settings = Read-ProjectFile 'adapters/claude-code/settings.json.template'
foreach ($dangerousRule in @(
    'Bash(npm *)', 'Bash(pip *)', 'Bash(python *)', 'Bash(docker *)',
    'Bash(curl *)', 'Bash(redis-cli *)', 'Bash(git checkout *)'
)) {
    Assert-True (-not $settings.Contains($dangerousRule)) "Unsafe default Claude permission: $dangerousRule"
}

$activeTextFiles = Get-ChildItem -LiteralPath $root -Recurse -File |
    Where-Object {
        $_.Extension -in @('.md', '.template', '.json', '.yaml', '.yml') -and
        $_.FullName -notmatch '[\\/]docs[\\/]legacy[\\/]'
    }

foreach ($file in $activeTextFiles) {
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName
    $relativePath = $file.FullName.Substring($root.Length + 1)
    Assert-True (-not $content.Contains('USAGE.md')) "$relativePath references missing USAGE.md"
    Assert-True (-not ($content -match '\.claude/skills/[^/\s`]+\.md')) "$relativePath uses a flat skill path"
    if ($relativePath -notmatch '^adapters[\\/]' -and $relativePath -notmatch '^(scripts|tests)[\\/]') {
        Assert-True (-not ($content -match '\{\{[A-Z_][A-Z0-9_]*\}\}')) "$relativePath contains an unresolved runtime placeholder"
    }
}

$integration = Read-ProjectFile 'contracts/integration-standard.md'
$passwordCodePoints = @(23494, 30721)
$passwordWord = -join ($passwordCodePoints | ForEach-Object { [char]$_ })
Assert-True (-not ($integration.Contains($passwordWord))) 'Integration standard asks for a plaintext password'

if ($failures.Count -gt 0) {
    Write-Host "V2 template tests failed: $($failures.Count)" -ForegroundColor Red
    foreach ($failure in $failures) { Write-Host "- $failure" -ForegroundColor Red }
    exit 1
}

Write-Host 'V2 template tests passed.' -ForegroundColor Green
