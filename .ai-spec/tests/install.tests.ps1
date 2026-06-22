$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $root 'scripts\install.ps1'
$tempRoot = [System.IO.Path]::GetFullPath((Join-Path $env:TEMP ("ai-spec-v2-test-" + [guid]::NewGuid().ToString('N'))))

function Assert-Test {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    $fakeGlobalRules = Join-Path $tempRoot 'global-rules'
    New-Item -ItemType Directory -Force -Path (Join-Path $fakeGlobalRules 'common'), (Join-Path $fakeGlobalRules 'zh') | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $fakeGlobalRules 'common\agents.md'), "# Immediate Agent Usage`nUse code-reviewer after every edit.`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $fakeGlobalRules 'zh\agents.md'), "# 立即使用代理`n80% coverage`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $fakeGlobalRules 'python.md'), "---`npaths:`n  - '**/*.py'`n---`n# Python`n", [System.Text.UTF8Encoding]::new($false))
    $globalAuditOutput = & (Join-Path $root 'scripts\audit-global-context.ps1') -RulesRoot $fakeGlobalRules -MaxAlwaysOnFiles 1 -MaxAlwaysOnBytes 1 6>&1
    $globalAuditText = [string]::Join("`n", @($globalAuditOutput))
    Assert-Test ($globalAuditText.Contains('GLOBAL_CONTEXT_WARNING')) 'Global context audit did not flag oversized always-on rules'
    Assert-Test ($globalAuditText.Contains('alwaysOn=2')) 'Global context audit misclassified path-scoped rules'
    Assert-Test (Test-Path -LiteralPath (Join-Path $fakeGlobalRules 'common\agents.md')) 'Global context audit modified user rules'

    $safeRoot = Join-Path $tempRoot 'safe-copy'
    New-Item -ItemType Directory -Force -Path $safeRoot | Out-Null
    $ownedClaude = Join-Path $safeRoot 'CLAUDE.md'
    [System.IO.File]::WriteAllText($ownedClaude, 'user-owned', [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $safeRoot 'package.json'), '{"scripts":{"build":"vite build","test":"vitest run","lint":"biome check .","dev":"vite --host 0.0.0.0"},"dependencies":{"react":"latest","vite":"latest"}}', [System.Text.UTF8Encoding]::new($false))

    & $installer -TargetRoot $safeRoot -Mode existing -Tools 'claude-code,codex,cursor,github-copilot' -Apply *> $null

    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.ai-spec\AI-START.md')) 'Installer did not copy AI-START.md'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.ai-spec\ai-spec.yaml')) 'Installer did not create ai-spec.yaml'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot 'AGENTS.md')) 'Installer did not create AGENTS.md'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.cursor\rules\ai-spec.mdc')) 'Installer did not create Cursor rules'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.github\copilot-instructions.md')) 'Installer did not create Copilot instructions'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.claude\settings.json')) 'Installer did not create Claude settings'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.agents\skills\product-architect\SKILL.md')) 'Installer did not create Codex skill'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.claude\skills\dev-implementation\SKILL.md')) 'Installer did not create Claude skill'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.agents\skills\code-reviewer\SKILL.md')) 'Installer did not create Codex code-reviewer skill'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.agents\skills\debugger\SKILL.md')) 'Installer did not create Codex debugger skill'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.agents\skills\spec-evaluator\SKILL.md')) 'Installer did not create Codex spec-evaluator skill'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.claude\skills\code-reviewer\SKILL.md')) 'Installer did not create Claude code-reviewer skill'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.claude\skills\debugger\SKILL.md')) 'Installer did not create Claude debugger skill'
    Assert-Test (Test-Path -LiteralPath (Join-Path $safeRoot '.claude\skills\spec-evaluator\SKILL.md')) 'Installer did not create Claude spec-evaluator skill'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath $ownedClaude) -eq 'user-owned') 'Installer overwrote an existing CLAUDE.md'

    $agents = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $safeRoot 'AGENTS.md')
    Assert-Test (-not $agents.Contains('{{')) 'Installer left placeholders in AGENTS.md'

    $profile = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $safeRoot '.ai-spec\ai-spec.yaml')
    Assert-Test ($profile.Contains('stage: existing')) 'Installer did not write the selected project stage'
    Assert-Test ($profile.Contains('languages: [javascript]')) 'Installer did not infer JavaScript stack'
    Assert-Test ($profile.Contains('frameworks: [react, vite]')) 'Installer did not infer frontend frameworks'
    Assert-Test ($profile.Contains('packageManagers: [npm]')) 'Installer did not infer npm package manager'
    Assert-Test ($profile.Contains('build: npm run build')) 'Installer did not infer build command'
    Assert-Test ($profile.Contains('test: npm run test')) 'Installer did not infer test command'
    Assert-Test ($profile.Contains('lint: npm run lint')) 'Installer did not infer lint command'
    Assert-Test ($profile.Contains('run: npm run dev')) 'Installer did not infer run command'
    Assert-Test ($profile.Contains('skillPolicy:')) 'Installer did not write default skill policy'
    Assert-Test ($profile.Contains('mode: project-first')) 'Installer did not write project-first skill mode'
    Assert-Test ($profile.Contains('allowLocalSkills: true')) 'Installer did not allow local skills as explicit policy'
    Assert-Test ($profile.Contains('reportSkillSource: true')) 'Installer did not require skill source reporting'
    Assert-Test ($profile.Contains('outputLanguage:')) 'Installer did not persist output language policy'
    Assert-Test ($profile.Contains('default: zh-CN')) 'Installer did not default output language to Simplified Chinese'
    Assert-Test ($profile.Contains('locked: true')) 'Installer did not lock the default output language'
    Assert-Test ($profile.Contains('strategy: lazy')) 'Installer did not persist lazy context maintenance'
    Assert-Test ($profile.Contains('autoApply: safe-only')) 'Installer maintenance is not stability-first'
    Assert-Test ($profile.Contains('scope: project-only')) 'Installer did not persist project-only scope'

    & $installer -TargetRoot $safeRoot -Mode existing -Tools 'generic' -Apply *> $null
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $safeRoot '.ai-spec\ai-spec.yaml.draft'))) 'Installer should not create ai-spec.yaml.draft by default'

    & (Join-Path $safeRoot '.ai-spec\tests\template.tests.ps1') *> $null

    $gitPlan = & $installer -TargetRoot $safeRoot -Mode existing -Tools 'generic' -Onboard -ManageGit 6>&1
    $gitPlanText = [string]::Join("`n", @($gitPlan))
    Assert-Test ($gitPlanText.Contains('GIT init/add/initial-commit')) 'ManageGit dry-run did not plan the controlled initial commit'
    Assert-Test ($gitPlanText.Contains('GIT create branch chore/specforge-onboard')) 'ManageGit dry-run did not plan onboarding branch creation'

    $newRoot = Join-Path $tempRoot 'new-project'
    New-Item -ItemType Directory -Force -Path $newRoot | Out-Null
    & $installer -TargetRoot $newRoot -Mode new -Tools 'generic' -Onboard -Apply *> $null
    Assert-Test (Test-Path -LiteralPath (Join-Path $newRoot '.ai-spec\tests')) 'New project without project-plan should keep full rules before slimming'
    Assert-Test (Test-Path -LiteralPath (Join-Path $newRoot '.ai-spec\scripts\install.ps1')) 'New project without project-plan should keep the installer before slimming'

    $plannedNewRoot = Join-Path $tempRoot 'planned-new-project'
    New-Item -ItemType Directory -Force -Path (Join-Path $plannedNewRoot 'docs\plans') | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $plannedNewRoot 'docs\plans\project-plan.md'), "# Project plan`n", [System.Text.UTF8Encoding]::new($false))
    & $installer -TargetRoot $plannedNewRoot -Mode new -Tools 'generic' -Onboard -Apply *> $null
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $plannedNewRoot '.ai-spec\tests'))) 'New project with project-plan should slim template self-tests'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $plannedNewRoot '.ai-spec\scripts\install.ps1'))) 'New project with project-plan should slim the one-time installer'

    $monoRoot = Join-Path $tempRoot 'multi-project'
    $frontend = Join-Path $monoRoot 'frontend'
    $backend = Join-Path $monoRoot 'backend'
    New-Item -ItemType Directory -Force -Path $frontend | Out-Null
    New-Item -ItemType Directory -Force -Path $backend | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $frontend 'package.json'), '{"scripts":{"build":"vite build","test":"vitest run","dev":"vite"},"dependencies":{"react":"latest","vite":"latest"}}', [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $backend 'go.mod'), "module example.com/backend`n", [System.Text.UTF8Encoding]::new($false))

    $multiGitPlan = & $installer -TargetRoot $monoRoot -Mode auto -Tools 'codex' -Onboard -ManageGit 6>&1
    $multiGitPlanText = [string]::Join("`n", @($multiGitPlan))
    Assert-Test ($multiGitPlanText.Contains("GIT init/add/initial-commit $frontend (controlled")) 'ManageGit auto should plan frontend Git onboarding inside the child project'
    Assert-Test ($multiGitPlanText.Contains("GIT init/add/initial-commit $backend (controlled")) 'ManageGit auto should plan backend Git onboarding inside the child project'
    Assert-Test (-not $multiGitPlanText.Contains("GIT init/add/initial-commit $monoRoot (controlled")) 'ManageGit auto should not initialize Git at a plain multi-project parent'

    $parentGitPlan = & $installer -TargetRoot $monoRoot -Mode auto -Tools 'codex' -Onboard -ManageGit -GitScope parent 6>&1
    $parentGitPlanText = [string]::Join("`n", @($parentGitPlan))
    Assert-Test ($parentGitPlanText.Contains("GIT init/add/initial-commit $monoRoot (controlled")) 'ManageGit -GitScope parent should explicitly plan Git onboarding at the parent'

    New-Item -ItemType Directory -Force -Path (Join-Path $monoRoot '.ai-spec') | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $monoRoot '.ai-spec\legacy-parent-rule.txt'), 'legacy parent spec', [System.Text.UTF8Encoding]::new($false))

    & $installer -TargetRoot $monoRoot -Mode auto -Tools 'claude-code,codex,cursor,github-copilot,generic' -Onboard -Apply *> $null

    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $monoRoot '.ai-spec'))) 'Onboard mode installed a parent .ai-spec for a multi-project root'
    Assert-Test (Test-Path -LiteralPath (Join-Path $monoRoot '.specforge.json')) 'Onboard mode did not create parent .specforge.json'
    Assert-Test (Test-Path -LiteralPath (Join-Path $monoRoot 'AGENTS.md')) 'Onboard mode did not create parent lightweight Codex entry'
    Assert-Test (Test-Path -LiteralPath (Join-Path $monoRoot 'CLAUDE.md')) 'Onboard mode did not create parent lightweight Claude entry'
    Assert-Test (Test-Path -LiteralPath (Join-Path $monoRoot '.cursor\rules\ai-spec.mdc')) 'Onboard mode did not create parent lightweight Cursor entry'
    Assert-Test (Test-Path -LiteralPath (Join-Path $monoRoot '.github\copilot-instructions.md')) 'Onboard mode did not create parent lightweight Copilot entry'
    Assert-Test (Test-Path -LiteralPath (Join-Path $monoRoot 'START-PROMPT.md')) 'Onboard mode did not create parent generic start prompt'
    $parentAgents = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $monoRoot 'AGENTS.md')
    Assert-Test ($parentAgents.Contains('.specforge.json')) 'Parent lightweight entry does not point to the multi-project index'
    Assert-Test ($parentAgents.Contains('child project')) 'Parent lightweight entry does not route to child projects'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $monoRoot '.agents'))) 'Parent lightweight entry should not install parent Codex skills'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $monoRoot '.claude\skills'))) 'Parent lightweight entry should not install parent Claude skills'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\AI-START.md')) 'Onboard mode did not install frontend .ai-spec'
    Assert-Test (Test-Path -LiteralPath (Join-Path $backend '.ai-spec\AI-START.md')) 'Onboard mode did not install backend .ai-spec'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend 'AGENTS.md')) 'Onboard mode did not create frontend Codex entry'
    Assert-Test (Test-Path -LiteralPath (Join-Path $backend 'AGENTS.md')) 'Onboard mode did not create backend Codex entry'

    $index = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $monoRoot '.specforge.json') | ConvertFrom-Json
    Assert-Test ($index.templateVersion -eq 2) 'Parent .specforge.json missing templateVersion'
    Assert-Test ($index.templateSource -eq 'SpecForge') 'Parent .specforge.json missing templateSource'
    Assert-Test (-not [string]::IsNullOrWhiteSpace([string]$index.multiProjectId)) 'Parent .specforge.json missing multiProjectId'
    Assert-Test ($index.projects.Count -eq 2) 'Parent .specforge.json should contain two projects'
    Assert-Test (@($index.projects.path) -contains 'frontend') 'Parent .specforge.json missing frontend project'
    Assert-Test (@($index.projects.path) -contains 'backend') 'Parent .specforge.json missing backend project'

    $frontendProfile = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\ai-spec.yaml')
    Assert-Test ($frontendProfile.Contains('templateVersion: 2')) 'Frontend profile did not record templateVersion'
    Assert-Test ($frontendProfile.Contains('type: frontend')) 'Frontend profile did not record frontend type'
    Assert-Test ($frontendProfile.Contains('languages: [javascript]')) 'Frontend profile did not infer language'
    Assert-Test ($frontendProfile.Contains('frameworks: [react, vite]')) 'Frontend profile did not infer frameworks'
    Assert-Test ($frontendProfile.Contains('build: npm run build')) 'Frontend profile did not infer build command'
    Assert-Test ($frontendProfile.Contains('test: npm run test')) 'Frontend profile did not infer test command'
    Assert-Test ($frontendProfile.Contains('run: npm run dev')) 'Frontend profile did not infer run command'
    Assert-Test ($frontendProfile.Contains("multiProjectId: $($index.multiProjectId)")) 'Frontend profile did not receive shared multiProjectId'
    Assert-Test ($frontendProfile.Contains('quickRefStatus: TEMPLATE_PLACEHOLDER')) 'Frontend profile missing quick-ref placeholder status'
    Assert-Test ($frontendProfile.Contains('projectSize: tiny')) 'Frontend profile did not record tiny project size'
    Assert-Test ($frontendProfile.Contains('fileCount: 1')) 'Frontend profile did not record project file count'
    Assert-Test ($frontendProfile.Contains('hasApi: false')) 'Frontend profile did not record API signal'
    Assert-Test ($frontendProfile.Contains('hasAuth: false')) 'Frontend profile did not record auth signal'
    Assert-Test ($frontendProfile.Contains('skillPolicy:')) 'Frontend profile missing default skill policy'
    Assert-Test ($frontendProfile.Contains('mode: project-first')) 'Frontend profile missing project-first skill mode'
    $frontendQuickRef = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\business\quick-ref.md')
    Assert-Test ($frontendQuickRef.Contains('status: TEMPLATE_PLACEHOLDER')) 'Installed quick-ref status marker does not match the startup protocol'
    Assert-Test ($frontendQuickRef.Contains('dailyEntry: true')) 'Installed quick-ref is not the daily startup entry'
    Assert-Test ($frontendQuickRef.Contains('dynamicContextGate: true')) 'Installed quick-ref missing dynamic context gate'
    Assert-Test ($frontendQuickRef.Contains('projectSize: tiny')) 'Installed quick-ref missing project size'
    Assert-Test ($frontendQuickRef.Contains('sizeStrategy: ultra-lite')) 'Installed quick-ref missing tiny size strategy'
    Assert-Test ($frontendQuickRef.Contains('outputLanguage: zh-CN')) 'Installed quick-ref missing Simplified Chinese output lock'
    Assert-Test ($frontendQuickRef -match 'maintenanceDue: \d{4}-\d{2}-\d{2}') 'Installed quick-ref missing concrete maintenance due date'
    Assert-Test ($frontendQuickRef.Contains('250')) 'Installed quick-ref missing large-file chunk budget'
    Assert-Test ($frontendQuickRef.Contains('计划自动触发门禁')) 'Installed quick-ref missing automatic planning gate'
    Assert-Test ($frontendQuickRef.Contains('.ai-spec/workflows/project-planning.md')) 'Installed quick-ref missing project planning workflow route'
    Assert-Test ($frontendQuickRef.Contains('docs/plans/project-plan.md')) 'Installed quick-ref missing persisted project plan gate'
    Assert-Test ($frontendQuickRef.Contains('docs/plans/current.md')) 'Installed quick-ref missing current plan resume route'
    Assert-Test ($frontendQuickRef.Contains('module-contract-template.md')) 'Installed quick-ref missing module contract gate'
    Assert-Test ($frontendQuickRef.Contains('regression-checklist-template.md')) 'Installed quick-ref missing regression checklist gate'
    Assert-Test ($frontendQuickRef.Contains('影响矩阵')) 'Installed quick-ref missing impact matrix gate'
    Assert-Test ($frontendQuickRef.Contains('待填充')) 'Installed quick-ref should use Chinese placeholders'
    Assert-Test (-not $frontendQuickRef.Contains('Planning auto-trigger gate')) 'Installed quick-ref should not generate English planning headings'
    Assert-Test (@($frontendQuickRef -split "`r?`n").Count -le 40) 'Installed quick-ref exceeds the 40-line token budget'

    $frontendRules = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\business\business-rules.md')
    Assert-Test ($frontendRules.Contains('omittedSections:')) 'Installed business-rules should record omitted sections'
    Assert-Test ($frontendRules.Contains('section: business-positioning')) 'Installed business-rules missing required positioning section'
    Assert-Test ($frontendRules.Contains('section: business-domains')) 'Installed business-rules missing required domain section'
    Assert-Test ($frontendRules.Contains('section: data-write-rules')) 'Installed business-rules missing required write-rules section'
    Assert-Test ($frontendRules.Contains('section: business-invariants')) 'Installed business-rules missing required invariants section'
    Assert-Test (-not $frontendRules.Contains('section: organization-identity')) 'Business-rules kept organization section without auth signal'
    Assert-Test (-not $frontendRules.Contains('section: kpi-metrics')) 'Business-rules kept KPI section without analytics signal'
    Assert-Test (-not $frontendRules.Contains('section: state-machines')) 'Business-rules kept state-machine section without state signal'
    Assert-Test (-not $frontendRules.Contains('section: menu-permissions')) 'Business-rules kept permission menu section without admin/auth signal'
    Assert-Test (-not $frontendRules.Contains('section: external-integrations')) 'Business-rules kept external integration section without integration signal'

    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\stacks\frontend-general.md')) 'Frontend stack was not retained'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\stacks\backend-general.md'))) 'Frontend stack slimming kept backend rules'
    Assert-Test (Test-Path -LiteralPath (Join-Path $backend '.ai-spec\stacks\backend-general.md')) 'Backend stack was not retained'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $backend '.ai-spec\stacks\frontend-general.md'))) 'Backend stack slimming kept frontend rules'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\core-lite\delivery-lite.md')) 'Onboard mode did not keep delivery-lite'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\core-lite\security-lite.md')) 'Onboard mode did not keep security-lite'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\core-lite\testing-lite.md')) 'Onboard mode did not keep testing-lite'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\tests'))) 'Onboard mode did not remove template self-tests'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\scripts\install.ps1'))) 'Onboard mode did not remove one-time installer'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\scripts\validate.ps1')) 'Onboard mode removed validate.ps1'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\scripts\update.ps1')) 'Onboard mode removed update.ps1'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\scripts\update.cmd')) 'Onboard mode removed update.cmd'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\scripts\maintain-context.ps1')) 'Onboard mode removed maintain-context.ps1'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\scripts\audit-global-context.ps1')) 'Onboard mode removed audit-global-context.ps1'
    Assert-Test (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\adapters\codex')) 'Onboard mode did not retain selected adapter'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $frontend '.ai-spec\adapters\cursor'))) 'Onboard mode kept unused adapter'
    & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null

    $frontendProfilePath = Join-Path $frontend '.ai-spec\ai-spec.yaml'
    $profileWithSkillPolicy = Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendProfilePath
    $profileWithoutSkillPolicy = $profileWithSkillPolicy -replace '(?ms)\r?\n  skillPolicy:\r?\n    mode:.*?\r?\n    allowLocalSkills:.*?\r?\n    reportSkillSource:.*?$', ''
    [System.IO.File]::WriteAllText($frontendProfilePath, $profileWithoutSkillPolicy, [System.Text.UTF8Encoding]::new($false))
    $missingSkillPolicyFailed = $false
    try {
        & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null
    }
    catch {
        $missingSkillPolicyFailed = $true
    }
    Assert-Test $missingSkillPolicyFailed 'Installed validate.ps1 did not fail when ai.skillPolicy was missing'
    [System.IO.File]::WriteAllText($frontendProfilePath, $profileWithSkillPolicy, [System.Text.UTF8Encoding]::new($false))

    $profileWithoutLanguageLock = $profileWithSkillPolicy -replace '(?ms)\r?\n  outputLanguage:\r?\n    default:.*?\r?\n    locked:.*?(?=\r?\n  skillPolicy:)', ''
    [System.IO.File]::WriteAllText($frontendProfilePath, $profileWithoutLanguageLock, [System.Text.UTF8Encoding]::new($false))
    $missingLanguageLockFailed = $false
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $missingLanguageLockFailed = $true }
    Assert-Test $missingLanguageLockFailed 'Installed validate.ps1 did not reject a missing Simplified Chinese language lock'
    [System.IO.File]::WriteAllText($frontendProfilePath, $profileWithSkillPolicy, [System.Text.UTF8Encoding]::new($false))

    $frontendQuickRefPath = Join-Path $frontend '.ai-spec\business\quick-ref.md'
    $validQuickRef = Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendQuickRefPath
    $quickRefWithoutLanguageLock = $validQuickRef -replace '(?m)^> outputLanguage: zh-CN\r?\n', ''
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $quickRefWithoutLanguageLock, [System.Text.UTF8Encoding]::new($false))
    $missingQuickRefLanguageFailed = $false
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $missingQuickRefLanguageFailed = $true }
    Assert-Test $missingQuickRefLanguageFailed 'Installed validate.ps1 did not reject a quick-ref without outputLanguage: zh-CN'
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $validQuickRef, [System.Text.UTF8Encoding]::new($false))

    $semanticProfile = $profileWithSkillPolicy -replace 'quickRefStatus: TEMPLATE_PLACEHOLDER', 'quickRefStatus: GENERATED'
    $semanticQuickRef = $validQuickRef -replace 'status: TEMPLATE_PLACEHOLDER', 'status: GENERATED'
    [System.IO.File]::WriteAllText($frontendProfilePath, $semanticProfile, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $semanticQuickRef, [System.Text.UTF8Encoding]::new($false))
    $semanticQuickRefFailed = $false
    $semanticQuickRefError = ''
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $semanticQuickRefFailed = $true; $semanticQuickRefError = $_.Exception.Message }
    Assert-Test ($semanticQuickRefFailed -and $semanticQuickRefError.Contains('Generated quick-ref still contains placeholder content')) 'Generated quick-ref accepted placeholder facts'

    $semanticQuickRef = $semanticQuickRef -replace '(?m)^- 待填充.*$', '- provider-routing: confirmed'
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $semanticQuickRef, [System.Text.UTF8Encoding]::new($false))
    $semanticRulesFailed = $false
    $semanticRulesError = ''
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $semanticRulesFailed = $true; $semanticRulesError = $_.Exception.Message }
    Assert-Test ($semanticRulesFailed -and $semanticRulesError.Contains('Generated business rules still contain placeholder content')) 'Generated status accepted placeholder business rules'

    $semanticRulesPath = Join-Path $frontend '.ai-spec\business\business-rules.md'
    $semanticMapPath = Join-Path $frontend '.ai-spec\business\project-map.md'
    $semanticRulesOriginal = Get-Content -Raw -Encoding UTF8 -LiteralPath $semanticRulesPath
    $semanticMapOriginal = Get-Content -Raw -Encoding UTF8 -LiteralPath $semanticMapPath
    [System.IO.File]::WriteAllText($semanticRulesPath, $semanticRulesOriginal.Replace('待填充', '已确认'), [System.Text.UTF8Encoding]::new($false))
    $semanticEvidenceFailed = $false
    $semanticEvidenceError = ''
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $semanticEvidenceFailed = $true; $semanticEvidenceError = $_.Exception.Message }
    Assert-Test ($semanticEvidenceFailed -and $semanticEvidenceError.Contains('Generated business rules lack source/reliability evidence markers')) 'Generated business rules accepted content without source/reliability evidence'

    $sourceMarker = -join (@(0x6765, 0x6E90) | ForEach-Object { [char]$_ })
    $reliabilityMarker = -join (@(0x53EF, 0x9760, 0x5EA6) | ForEach-Object { [char]$_ })
    [System.IO.File]::WriteAllText($semanticRulesPath, ($semanticRulesOriginal.Replace('待填充', '已确认') + "`n- Provider routing is explicit. [$sourceMarker`: code] [$reliabilityMarker`: high]`n"), [System.Text.UTF8Encoding]::new($false))
    $semanticMapFailed = $false
    $semanticMapError = ''
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $semanticMapFailed = $true; $semanticMapError = $_.Exception.Message }
    Assert-Test ($semanticMapFailed -and $semanticMapError.Contains('Generated project map still contains placeholder content')) 'Generated status accepted placeholder project map'

    [System.IO.File]::WriteAllText($semanticMapPath, "# Project map`n`n## Position`nOrbitAI provider orchestration.`n`n## Domains`n- Provider routing`n", [System.Text.UTF8Encoding]::new($false))
    & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null
    [System.IO.File]::WriteAllText($semanticRulesPath, $semanticRulesOriginal, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($semanticMapPath, $semanticMapOriginal, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($frontendProfilePath, $profileWithSkillPolicy, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $validQuickRef, [System.Text.UTF8Encoding]::new($false))
    Add-Content -Encoding UTF8 -LiteralPath $frontendQuickRefPath -Value @('overflow-1', 'overflow-2', 'overflow-3', 'overflow-4', 'overflow-5')
    $oversizedQuickRefFailed = $false
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $oversizedQuickRefFailed = $true }
    Assert-Test $oversizedQuickRefFailed 'Installed validate.ps1 did not reject a quick-ref over 40 lines'
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $validQuickRef, [System.Text.UTF8Encoding]::new($false))

    $mismatchedQuickRef = $validQuickRef -replace '(?m)^(>[^\r\n]*?)TEMPLATE_PLACEHOLDER', '${1}GENERATED'
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $mismatchedQuickRef, [System.Text.UTF8Encoding]::new($false))
    $statusMismatchFailed = $false
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $statusMismatchFailed = $true }
    Assert-Test $statusMismatchFailed 'Installed validate.ps1 did not reject quick-ref/ai-spec status drift'
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $validQuickRef, [System.Text.UTF8Encoding]::new($false))

    $quickRefWithoutPlanningGate = $validQuickRef -replace '(?ms)\r?\n## 实施硬门禁.*?(?=\r?\n## 业务事实)', ''
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $quickRefWithoutPlanningGate, [System.Text.UTF8Encoding]::new($false))
    $missingPlanningGateFailed = $false
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $missingPlanningGateFailed = $true }
    Assert-Test $missingPlanningGateFailed 'Installed validate.ps1 did not reject a removed planning gate'
    [System.IO.File]::WriteAllText($frontendQuickRefPath, $validQuickRef, [System.Text.UTF8Encoding]::new($false))

    $frontendAgentsPath = Join-Path $frontend 'AGENTS.md'
    $validAgentsContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendAgentsPath
    [System.IO.File]::WriteAllText($frontendAgentsPath, 'Before any task, read .ai-spec/AI-START.md.', [System.Text.UTF8Encoding]::new($false))
    $staleAdapterFailed = $false
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $staleAdapterFailed = $true }
    Assert-Test $staleAdapterFailed 'Installed validate.ps1 did not reject a stale full-read AI adapter'
    [System.IO.File]::WriteAllText($frontendAgentsPath, $validAgentsContent, [System.Text.UTF8Encoding]::new($false))

    $plansRoot = Join-Path $frontend 'docs\plans'
    New-Item -ItemType Directory -Force -Path $plansRoot | Out-Null
    [System.IO.File]::WriteAllLines((Join-Path $plansRoot 'current.md'), @(1..81 | ForEach-Object { "line-$_" }), [System.Text.UTF8Encoding]::new($false))
    $oversizedCurrentPlanFailed = $false
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $oversizedCurrentPlanFailed = $true }
    Assert-Test $oversizedCurrentPlanFailed 'Installed validate.ps1 did not reject current.md over 80 lines'
    Remove-Item -LiteralPath (Join-Path $plansRoot 'current.md') -Force

    $phaseRoot = Join-Path $plansRoot 'phases'
    New-Item -ItemType Directory -Force -Path $phaseRoot | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $phaseRoot '01-test.md'), "# Phase`n`n- **status**: completed`n`n## Acceptance evidence`n`n- command and result:`n- completion time:`n", [System.Text.UTF8Encoding]::new($false))
    $missingPhaseEvidenceFailed = $false
    try { & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') *> $null } catch { $missingPhaseEvidenceFailed = $true }
    Assert-Test $missingPhaseEvidenceFailed 'Installed validate.ps1 did not reject a completed phase without evidence'
    Remove-Item -LiteralPath $plansRoot -Recurse -Force

    $profileBeforeUpdater = Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendProfilePath
    $rulesBeforeUpdater = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\business\business-rules.md')
    $startBeforeUpdater = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\AI-START.md')
    [System.IO.File]::WriteAllText((Join-Path $frontend '.ai-spec\AI-START.md'), 'stale-before-updater', [System.Text.UTF8Encoding]::new($false))
    & (Join-Path $frontend '.ai-spec\scripts\update.ps1') -TargetRoot $frontend -SourceRoot $root -Apply *> $null
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\AI-START.md')) -eq $startBeforeUpdater) 'PowerShell updater did not refresh existing rules'
    $profileAfterUpdater = Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendProfilePath
    Assert-Test ($profileAfterUpdater.Contains('name: frontend')) 'PowerShell updater changed project identity in ai-spec.yaml'
    Assert-Test ($profileAfterUpdater.Contains('overrideOnlyByExplicitUserRequest: true')) 'PowerShell updater did not add language compatibility default'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\business\business-rules.md')) -eq $rulesBeforeUpdater) 'PowerShell updater overwrote business rules'

    $maintenanceQuickRefPath = Join-Path $frontend '.ai-spec\business\quick-ref.md'
    $maintenanceProfilePath = Join-Path $frontend '.ai-spec\ai-spec.yaml'
    $quickRefBeforeMaintenance = Get-Content -Raw -Encoding UTF8 -LiteralPath $maintenanceQuickRefPath
    $profileBeforeMaintenance = Get-Content -Raw -Encoding UTF8 -LiteralPath $maintenanceProfilePath
    $maintenanceQuickRef = $quickRefBeforeMaintenance -replace 'status: TEMPLATE_PLACEHOLDER', 'status: GENERATED' -replace 'maintenanceDue: \d{4}-\d{2}-\d{2}', 'maintenanceDue: 2026-06-18'
    $maintenanceProfile = $profileBeforeMaintenance -replace 'quickRefStatus: TEMPLATE_PLACEHOLDER', 'quickRefStatus: GENERATED'
    [System.IO.File]::WriteAllText($maintenanceQuickRefPath, $maintenanceQuickRef, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($maintenanceProfilePath, $maintenanceProfile, [System.Text.UTF8Encoding]::new($false))

    $sessionsRoot = Join-Path $frontend '.ai-spec\sessions'
    $handoffsRoot = Join-Path $frontend 'docs\handoffs'
    New-Item -ItemType Directory -Force -Path $sessionsRoot, $handoffsRoot | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $sessionsRoot 'completed.md'), "# Session`n- status: completed`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $sessionsRoot 'active.md'), "# Session`n- status: active`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $handoffsRoot 'completed.md'), "# Handoff`n- status: completed`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $handoffsRoot 'active.md'), "# Handoff`n- status: active`n", [System.Text.UTF8Encoding]::new($false))

    $maintenancePlansRoot = Join-Path $frontend 'docs\plans'
    $maintenancePhasesRoot = Join-Path $maintenancePlansRoot 'phases'
    New-Item -ItemType Directory -Force -Path $maintenancePhasesRoot | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $maintenancePlansRoot 'current.md'), "# Current`n- phase: phases/current-completed.md`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $maintenancePhasesRoot 'current-completed.md'), "# Current phase`n- status: completed`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $maintenancePhasesRoot 'old-completed.md'), "# Old phase`n- status: completed`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $maintenancePlansRoot 'project-plan.md'), "# Plan`n- phases/current-completed.md`n- phases/old-completed.md`n", [System.Text.UTF8Encoding]::new($false))

    & (Join-Path $frontend '.ai-spec\scripts\maintain-context.ps1') -TargetRoot $frontend -Now ([datetime]'2026-06-19') *> $null
    Assert-Test (Test-Path -LiteralPath (Join-Path $sessionsRoot 'completed.md')) 'Maintenance dry-run moved a completed session'
    Assert-Test (Test-Path -LiteralPath (Join-Path $handoffsRoot 'completed.md')) 'Maintenance dry-run moved a completed handoff'
    Assert-Test (Test-Path -LiteralPath (Join-Path $maintenancePhasesRoot 'old-completed.md')) 'Maintenance dry-run moved a completed phase'

    & (Join-Path $frontend '.ai-spec\scripts\maintain-context.ps1') -TargetRoot $frontend -Now ([datetime]'2026-06-19') -Apply *> $null
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $sessionsRoot 'completed.md'))) 'Maintenance apply did not archive completed session'
    Assert-Test (Test-Path -LiteralPath (Join-Path $sessionsRoot 'active.md')) 'Maintenance apply touched active session'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $handoffsRoot 'completed.md'))) 'Maintenance apply did not archive completed handoff'
    Assert-Test (Test-Path -LiteralPath (Join-Path $handoffsRoot 'active.md')) 'Maintenance apply touched active handoff'
    Assert-Test ((Get-ChildItem -LiteralPath (Join-Path $sessionsRoot 'archive') -Recurse -File).Count -eq 1) 'Completed session archive count is incorrect'
    Assert-Test ((Get-ChildItem -LiteralPath (Join-Path $handoffsRoot 'archive') -Recurse -File).Count -eq 1) 'Completed handoff archive count is incorrect'
    Assert-Test (Test-Path -LiteralPath (Join-Path $maintenancePhasesRoot 'current-completed.md')) 'Maintenance archived the phase referenced by current.md'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $maintenancePhasesRoot 'old-completed.md'))) 'Maintenance did not archive an unreferenced completed phase'
    Assert-Test (Test-Path -LiteralPath (Join-Path $maintenancePlansRoot 'archive\2026-06\old-completed.md')) 'Completed phase archive is missing'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $maintenancePlansRoot 'project-plan.md')).Contains('archive/2026-06/old-completed.md')) 'Project plan link was not updated after phase archive'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath $maintenanceQuickRefPath) -match 'maintenanceDue: 2026-07-19') 'Maintenance apply did not advance tiny-project due date by 30 days'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\business\business-rules.md')) -eq $rulesBeforeUpdater) 'Maintenance apply changed business rules'

    $businessRulesPathForMaintenance = Join-Path $frontend '.ai-spec\business\business-rules.md'
    $oversizedRules = $rulesBeforeUpdater + "`n" + ([string]::Join("`n", @(1..210 | ForEach-Object { "- retained-rule-$_" })))
    [System.IO.File]::WriteAllText($businessRulesPathForMaintenance, $oversizedRules, [System.Text.UTF8Encoding]::new($false))
    $maintenanceIssueOutput = & (Join-Path $frontend '.ai-spec\scripts\maintain-context.ps1') -TargetRoot $frontend -Now ([datetime]'2026-06-19') -Force -Apply 6>&1
    $maintenanceIssueText = [string]::Join("`n", @($maintenanceIssueOutput))
    Assert-Test ($maintenanceIssueText.Contains('COMPACT_REQUIRED business/business-rules.md')) 'Maintenance did not report oversized business rules'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath $businessRulesPathForMaintenance) -eq $oversizedRules) 'Maintenance mechanically truncated business rules'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath $maintenanceQuickRefPath) -match 'maintenanceDue: 2026-06-20') 'Unresolved compaction did not schedule a next-day reminder'
    [System.IO.File]::WriteAllText($businessRulesPathForMaintenance, $rulesBeforeUpdater, [System.Text.UTF8Encoding]::new($false))

    [System.IO.File]::WriteAllText($maintenanceQuickRefPath, $quickRefBeforeMaintenance, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($maintenanceProfilePath, $profileBeforeMaintenance, [System.Text.UTF8Encoding]::new($false))

    Add-Content -Encoding UTF8 -LiteralPath (Join-Path $frontend '.ai-spec\business\business-rules.md') -Value '[⚠️ 冲突 2026-06-19] code says A, rule says B'
    $conflictValidation = & (Join-Path $frontend '.ai-spec\scripts\validate.ps1') 6>&1
    $conflictValidationText = [string]::Join("`n", @($conflictValidation))
    Assert-Test ($conflictValidationText.Contains('Conflict summary')) 'Installed validate.ps1 did not report conflict summary'
    Assert-Test ($conflictValidationText.Contains('business\business-rules.md')) 'Conflict summary did not include conflict file path'

    $frontendStart = Join-Path $frontend '.ai-spec\AI-START.md'
    $frontendRulesPath = Join-Path $frontend '.ai-spec\business\business-rules.md'
    [System.IO.File]::WriteAllText($frontendStart, 'old-start', [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($frontendRulesPath, 'project-owned-business-rules', [System.Text.UTF8Encoding]::new($false))
    $profileBeforeSync = Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendProfilePath

    $syncPlan = & $installer -TargetRoot $monoRoot -Sync 6>&1
    $syncPlanText = [string]::Join("`n", @($syncPlan))
    Assert-Test ($syncPlanText.Contains('SYNC')) 'Sync dry-run did not report planned core-file updates'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendStart) -eq 'old-start') 'Sync dry-run modified AI-START.md'

    & $installer -TargetRoot $monoRoot -Sync -Apply *> $null

    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendStart).Contains('Startup Protocol')) 'Sync did not refresh AI-START.md'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendRulesPath) -eq 'project-owned-business-rules') 'Sync overwrote project-owned business rules'
    $profileAfterSync = Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendProfilePath
    Assert-Test ($profileAfterSync.Contains('name: frontend')) 'Sync changed project identity in ai-spec.yaml'
    Assert-Test ($profileAfterSync.Contains('overrideOnlyByExplicitUserRequest: true')) 'Sync did not preserve/add language compatibility default'

    $legacyProfile = $profileBeforeSync `
        -replace '(?m)^  scope: project-only.*\r?\n', '' `
        -replace '(?ms)\r?\n  maintenance:\r?\n    enabled:.*?\r?\n    strategy:.*?\r?\n    autoApply:.*?\r?\n    intervalDaysBySize:.*?\r?\n    quickRefMaxLines:.*?\r?\n    currentPlanMaxLines:.*?\r?\n    singleReadMaxLines:.*?(?=\r?\n  projectSizeSignals:)', '' `
        -replace '(?ms)\r?\n  outputLanguage:\r?\n    default:.*?\r?\n    locked:.*?(?=\r?\n  skillPolicy:)', ''
    $legacyQuickRefPath = Join-Path $frontend '.ai-spec\business\quick-ref.md'
    $legacyQuickRef = (Get-Content -Raw -Encoding UTF8 -LiteralPath $legacyQuickRefPath) `
        -replace '(?m)^> outputLanguage: zh-CN\r?\n', '' `
        -replace '(?m)^> maintenanceDue:.*\r?\n', ''
    [System.IO.File]::WriteAllText($frontendProfilePath, $legacyProfile, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($legacyQuickRefPath, $legacyQuickRef, [System.Text.UTF8Encoding]::new($false))
    & $installer -TargetRoot $frontend -Sync -Apply *> $null
    $migratedProfile = Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendProfilePath
    $migratedQuickRef = Get-Content -Raw -Encoding UTF8 -LiteralPath $legacyQuickRefPath
    Assert-Test ($migratedProfile.Contains('scope: project-only')) 'Sync did not add project-only scope to a legacy profile'
    Assert-Test ($migratedProfile.Contains('strategy: lazy')) 'Sync did not add maintenance defaults to a legacy profile'
    Assert-Test ($migratedProfile.Contains('default: zh-CN')) 'Sync did not add language defaults to a legacy profile'
    Assert-Test ($migratedProfile.Contains('overrideOnlyByExplicitUserRequest: true')) 'Sync did not add explicit language override default to a legacy profile'
    Assert-Test ($migratedProfile.Contains('name: frontend')) 'Compatibility migration changed project identity'
    Assert-Test ($migratedQuickRef.Contains('outputLanguage: zh-CN')) 'Sync did not add the language marker to a legacy quick-ref'
    Assert-Test ($migratedQuickRef -match 'maintenanceDue: \d{4}-\d{2}-\d{2}') 'Sync did not add a due date to a legacy quick-ref'
    Assert-Test ((Get-Content -Encoding UTF8 -LiteralPath $legacyQuickRefPath).Count -le 40) 'Compatibility migration made quick-ref exceed 40 lines'
    Assert-Test ((Get-Content -Raw -Encoding UTF8 -LiteralPath $frontendRulesPath) -eq 'project-owned-business-rules') 'Compatibility migration overwrote project business rules'

    Write-Host 'Installer integration tests passed.' -ForegroundColor Green
}
finally {
    $resolvedTempBase = [System.IO.Path]::GetFullPath($env:TEMP)
    if ($tempRoot.StartsWith($resolvedTempBase) -and (Split-Path -Leaf $tempRoot).StartsWith('ai-spec-v2-test-')) {
        if (Test-Path -LiteralPath $tempRoot) {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force
        }
    }
}
