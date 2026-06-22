[CmdletBinding()]
param(
    [switch]$SelfTest
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$testScript = Join-Path $root 'tests\template.tests.ps1'
$installTestScript = Join-Path $root 'tests\install.tests.ps1'
$skillTestScript = Join-Path $root 'tests\skills.tests.ps1'
$script:doctorFailures = 0

function Get-SpecForgeTemplateVersion {
    param([string]$SpecRoot)

    $examplePath = Join-Path $SpecRoot 'ai-spec.example.yaml'
    if (-not (Test-Path -LiteralPath $examplePath -PathType Leaf)) { return $null }
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $examplePath
    $match = [regex]::Match($content, '(?m)^  templateVersion:\s*(\d+)')
    if ($match.Success) { return [int]$match.Groups[1].Value }
    return $null
}

function Get-InstalledTemplateVersion {
    param([string]$SpecRoot)

    $profilePath = Join-Path $SpecRoot 'ai-spec.yaml'
    if (-not (Test-Path -LiteralPath $profilePath -PathType Leaf)) { return $null }
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $profilePath
    $match = [regex]::Match($content, '(?m)^  templateVersion:\s*(\d+)')
    if ($match.Success) { return [int]$match.Groups[1].Value }
    return $null
}

function Write-DoctorLine {
    param(
        [ValidateSet('OK', 'WARN', 'FAIL')]
        [string]$Status,
        [string]$Message
    )

    $color = switch ($Status) {
        'OK' { 'Green' }
        'WARN' { 'Yellow' }
        'FAIL' { 'Red' }
    }
    if ($Status -eq 'FAIL') { $script:doctorFailures++ }
    Write-Host "[$Status] $Message" -ForegroundColor $color
}

function Test-GitDoctor {
    param([string]$ProjectRoot, [string]$Label)

    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot '.git') -PathType Container)) {
        Write-DoctorLine -Status 'WARN' -Message "$Label has no .git repository."
        return
    }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-DoctorLine -Status 'WARN' -Message 'git command is unavailable; skipped git status.'
        return
    }

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $status = @(& git -C $ProjectRoot status --porcelain 2>$null)
        $gitExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($gitExitCode -ne 0) {
        Write-DoctorLine -Status 'WARN' -Message "$Label git status failed or .git is invalid."
        return
    }
    if ($status.Count -gt 0) {
        Write-DoctorLine -Status 'WARN' -Message "$Label has uncommitted changes: $($status.Count)."
    }
    else {
        Write-DoctorLine -Status 'OK' -Message "$Label git working tree is clean."
    }
}

function Test-SpecBasics {
    param([string]$SpecRoot, [string]$Label, [int]$TemplateVersion)

    foreach ($requiredPath in @('AI-START.md', 'README.md')) {
        if (Test-Path -LiteralPath (Join-Path $SpecRoot $requiredPath) -PathType Leaf) {
            Write-DoctorLine -Status 'OK' -Message "$Label has $requiredPath."
        }
        else {
            Write-DoctorLine -Status 'FAIL' -Message "$Label missing $requiredPath."
        }
    }

    $installedVersion = Get-InstalledTemplateVersion -SpecRoot $SpecRoot
    if ($null -ne $installedVersion -and $null -ne $TemplateVersion) {
        if ($installedVersion -lt $TemplateVersion) {
            Write-DoctorLine -Status 'WARN' -Message "$Label templateVersion=$installedVersion, latest=$TemplateVersion; update recommended."
        }
        else {
            Write-DoctorLine -Status 'OK' -Message "$Label templateVersion=$installedVersion."
        }
    }
}

function Invoke-SpecForgeDoctor {
    param([string]$SpecRoot)

    $projectRoot = Split-Path -Parent $SpecRoot
    $templateVersion = Get-SpecForgeTemplateVersion -SpecRoot $SpecRoot
    Write-Host ''
    Write-Host 'SpecForge doctor:' -ForegroundColor Cyan
    Write-DoctorLine -Status 'OK' -Message "specRoot=$SpecRoot"
    Write-DoctorLine -Status 'OK' -Message "projectRoot=$projectRoot"

    $indexPath = Join-Path $projectRoot '.specforge.json'
    if (Test-Path -LiteralPath $indexPath -PathType Leaf) {
        Write-DoctorLine -Status 'OK' -Message 'multi-project index found: .specforge.json.'
        try {
            $index = Get-Content -Raw -Encoding UTF8 -LiteralPath $indexPath | ConvertFrom-Json
        }
        catch {
            Write-DoctorLine -Status 'FAIL' -Message '.specforge.json is not valid JSON.'
            return
        }

        if ($null -ne $templateVersion -and $index.PSObject.Properties.Name -contains 'templateVersion') {
            if ([int]$index.templateVersion -lt $templateVersion) {
                Write-DoctorLine -Status 'WARN' -Message "parent index templateVersion=$($index.templateVersion), latest=$templateVersion; update recommended."
            }
            else {
                Write-DoctorLine -Status 'OK' -Message "parent index templateVersion=$($index.templateVersion)."
            }
        }

        $entryPaths = @('AGENTS.md', 'CLAUDE.md', '.cursor\rules\ai-spec.mdc', '.github\copilot-instructions.md', 'START-PROMPT.md')
        $foundEntries = @($entryPaths | Where-Object { Test-Path -LiteralPath (Join-Path $projectRoot $_) -PathType Leaf })
        if ($foundEntries.Count -gt 0) {
            Write-DoctorLine -Status 'OK' -Message "parent lightweight entries: $($foundEntries -join ', ')."
        }
        else {
            Write-DoctorLine -Status 'WARN' -Message 'no parent lightweight AI entry found.'
        }

        foreach ($project in @($index.projects)) {
            $projectPath = [string]$project.path
            if ([string]::IsNullOrWhiteSpace($projectPath)) { continue }
            $childRoot = Join-Path $projectRoot $projectPath
            $childSpec = Join-Path $childRoot '.ai-spec'
            if (-not (Test-Path -LiteralPath $childRoot -PathType Container)) {
                Write-DoctorLine -Status 'FAIL' -Message "child project missing: $projectPath."
                continue
            }
            if (-not (Test-Path -LiteralPath $childSpec -PathType Container)) {
                Write-DoctorLine -Status 'FAIL' -Message "child spec missing: $projectPath/.ai-spec."
                continue
            }
            Test-SpecBasics -SpecRoot $childSpec -Label $projectPath -TemplateVersion $templateVersion
            Test-GitDoctor -ProjectRoot $childRoot -Label $projectPath
        }
    }
    else {
        Test-SpecBasics -SpecRoot $SpecRoot -Label 'current project' -TemplateVersion $templateVersion
        Test-GitDoctor -ProjectRoot $projectRoot -Label 'current project'
    }
}

$isTemplateRepository = (Test-Path -LiteralPath $testScript -PathType Leaf) -and
    (Test-Path -LiteralPath $installTestScript -PathType Leaf) -and
    (Test-Path -LiteralPath $skillTestScript -PathType Leaf)

if ($isTemplateRepository) {
    & $testScript
    if ($SelfTest) {
        & $installTestScript
        & $skillTestScript
    }
}
else {
    $projectRootForValidation = Split-Path -Parent $root
    $parentIndexPath = Join-Path $projectRootForValidation '.specforge.json'
    if (Test-Path -LiteralPath $parentIndexPath -PathType Leaf) {
        foreach ($requiredPath in @(
            'AI-START.md',
            'README.md',
            'scripts\update.ps1',
            'scripts\update.cmd',
            'scripts\update.sh',
            'scripts\validate.ps1'
        )) {
            if (-not (Test-Path -LiteralPath (Join-Path $root $requiredPath))) {
                throw "Missing parent update source file: $requiredPath"
            }
        }

        try {
            $parentIndex = Get-Content -Raw -Encoding UTF8 -LiteralPath $parentIndexPath | ConvertFrom-Json
        }
        catch {
            throw '.specforge.json is not valid JSON.'
        }

        if (-not $parentIndex.projects -or @($parentIndex.projects).Count -eq 0) {
            throw '.specforge.json has no projects.'
        }

        foreach ($project in @($parentIndex.projects)) {
            $projectPath = [string]$project.path
            if ([string]::IsNullOrWhiteSpace($projectPath)) {
                throw '.specforge.json contains a project without path.'
            }
            $childSpecRoot = Join-Path (Join-Path $projectRootForValidation $projectPath) '.ai-spec'
            foreach ($requiredPath in @(
                'AI-START.md',
                'ai-spec.yaml',
                'business\quick-ref.md',
                'scripts\validate.ps1'
            )) {
                if (-not (Test-Path -LiteralPath (Join-Path $childSpecRoot $requiredPath) -PathType Leaf)) {
                    throw "Missing child spec file: $projectPath/.ai-spec/$requiredPath"
                }
            }
        }

        Write-Host 'Multi-project parent validation passed.' -ForegroundColor Green
    }
    else {
    foreach ($requiredPath in @(
        'AI-START.md',
        'README.md',
        'ai-spec.yaml',
        'business\quick-ref.md',
        'core\architecture.md',
        'core\delivery-standard.md',
        'core\security-standard.md',
        'core-lite\delivery-lite.md',
        'core-lite\security-lite.md',
        'core-lite\testing-lite.md',
        'scripts\audit-global-context.ps1',
        'scripts\maintain-context.ps1',
        'scripts\maintain-context.sh',
        'scripts\update.sh',
        'scripts\validate.ps1'
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $root $requiredPath))) {
            throw "Missing installed spec file: $requiredPath"
        }
    }

    $aiSpecPath = Join-Path $root 'ai-spec.yaml'
    $aiSpecContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $aiSpecPath
    if (-not ($aiSpecContent -match '(?m)^  scope:\s*project-only\b')) {
        throw 'Missing spec.scope: project-only in ai-spec.yaml.'
    }
    if (-not ($aiSpecContent -match '(?m)^  skillPolicy:\s*$')) {
        throw 'Missing ai.skillPolicy in ai-spec.yaml. Installed specs must persist skillPolicy.mode so AI tools do not silently bypass project skills.'
    }
    if (-not ($aiSpecContent -match '(?m)^    mode:\s*(project-first|local-first|hybrid)\b')) {
        throw 'Invalid or missing ai.skillPolicy.mode in ai-spec.yaml. Expected project-first, local-first, or hybrid.'
    }
    if (-not ($aiSpecContent -match '(?m)^    reportSkillSource:\s*true\b')) {
        throw 'Missing ai.skillPolicy.reportSkillSource: true in ai-spec.yaml. AI tools must report whether project/local skills were used.'
    }
    if (-not ($aiSpecContent -match '(?m)^  outputLanguage:\s*$') -or -not ($aiSpecContent -match '(?m)^    default:\s*zh-CN\s*$')) {
        throw 'Missing ai.outputLanguage.default: zh-CN in ai-spec.yaml.'
    }
    if (-not ($aiSpecContent -match '(?m)^    locked:\s*true\b')) {
        throw 'Missing ai.outputLanguage.locked: true in ai-spec.yaml.'
    }
    if (-not ($aiSpecContent -match '(?m)^    overrideOnlyByExplicitUserRequest:\s*true\b')) {
        throw 'Missing ai.outputLanguage.overrideOnlyByExplicitUserRequest: true in ai-spec.yaml.'
    }
    if (-not ($aiSpecContent -match '(?m)^  maintenance:\s*$') -or -not ($aiSpecContent -match '(?m)^    strategy:\s*lazy\s*$')) {
        throw 'Missing context.maintenance.strategy: lazy in ai-spec.yaml.'
    }
    if (-not ($aiSpecContent -match '(?m)^    autoApply:\s*safe-only\s*$')) {
        throw 'Missing context.maintenance.autoApply: safe-only in ai-spec.yaml.'
    }
    if (-not ($aiSpecContent -match '(?m)^    singleReadMaxLines:\s*250\s*$')) {
        throw 'Missing context.maintenance.singleReadMaxLines: 250 in ai-spec.yaml.'
    }

    $quickRefPath = Join-Path $root 'business\quick-ref.md'
    $quickRefContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $quickRefPath
    $quickRefLines = @(Get-Content -Encoding UTF8 -LiteralPath $quickRefPath)
    if ($quickRefLines.Count -gt 40) {
        throw "Quick-ref exceeds 40 lines: $($quickRefLines.Count). Keep the daily entry lightweight."
    }
    if (-not $quickRefContent.Contains('outputLanguage: zh-CN')) {
        throw 'Quick-ref is missing outputLanguage: zh-CN.'
    }
    if ($quickRefContent -notmatch '(?m)^>\s*maintenanceDue:\s*(auto|\d{4}-\d{2}-\d{2})\s*$') {
        throw 'Quick-ref is missing a valid maintenanceDue marker.'
    }

    $quickRefStatusMatch = [regex]::Match($quickRefContent, '(?m)^>[^\r\n]*?[:\uFF1A]\s*(TEMPLATE_PLACEHOLDER|GENERATED)\b')
    $profileStatusMatch = [regex]::Match($aiSpecContent, '(?m)^\s{2}quickRefStatus:\s*(TEMPLATE_PLACEHOLDER|GENERATED)\s*(?:#.*)?$')
    if (-not $quickRefStatusMatch.Success -or -not $profileStatusMatch.Success -or $quickRefStatusMatch.Groups[1].Value -ne $profileStatusMatch.Groups[1].Value) {
        $quickValue = if ($quickRefStatusMatch.Success) { $quickRefStatusMatch.Groups[1].Value } else { '<missing>' }
        $profileValue = if ($profileStatusMatch.Success) { $profileStatusMatch.Groups[1].Value } else { '<missing>' }
        throw "Quick-ref status mismatch: quick-ref=$quickValue, ai-spec=$profileValue."
    }
    if ($quickRefStatusMatch.Success -and $quickRefStatusMatch.Groups[1].Value -eq 'GENERATED') {
        $pendingGenerate = -join (@(0x5F85, 0x751F, 0x6210) | ForEach-Object { [char]$_ })
        $pendingFill = -join (@(0x5F85, 0x586B, 0x5145) | ForEach-Object { [char]$_ })
        if ($quickRefContent.Contains($pendingGenerate) -or $quickRefContent.Contains($pendingFill) -or $quickRefContent -match '(?mi)^\s*-\s*TBD\b') {
            throw 'Generated quick-ref still contains placeholder content.'
        }

        $businessRulesPath = Join-Path $root 'business\business-rules.md'
        if (-not (Test-Path -LiteralPath $businessRulesPath -PathType Leaf)) {
            throw 'Generated business rules still contain placeholder content: file missing.'
        }
        $businessRulesContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $businessRulesPath
        if ($businessRulesContent.Contains($pendingGenerate) -or $businessRulesContent.Contains($pendingFill) -or $businessRulesContent -match '(?i)\bTBD\b') {
            throw 'Generated business rules still contain placeholder content.'
        }
        $sourceLabel = -join (@(0x6765, 0x6E90) | ForEach-Object { [char]$_ })
        $reliabilityLabel = -join (@(0x53EF, 0x9760, 0x5EA6) | ForEach-Object { [char]$_ })
        if ($businessRulesContent -notmatch ('\[' + [regex]::Escape($sourceLabel) + '[:\uFF1A]') -or
            $businessRulesContent -notmatch ('\[' + [regex]::Escape($reliabilityLabel) + '[:\uFF1A]')) {
            throw 'Generated business rules lack source/reliability evidence markers.'
        }

        $projectMapPath = Join-Path $root 'business\project-map.md'
        if (-not (Test-Path -LiteralPath $projectMapPath -PathType Leaf)) {
            throw 'Generated project map still contains placeholder content: file missing.'
        }
        $projectMapContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $projectMapPath
        if ($projectMapContent.Contains($pendingGenerate) -or $projectMapContent.Contains($pendingFill) -or $projectMapContent -match '(?i)\bTBD\b') {
            throw 'Generated project map still contains placeholder content.'
        }
    }
    if (-not $quickRefContent.Contains('.ai-spec/workflows/project-planning.md') -or -not $quickRefContent.Contains('docs/plans/current.md') -or -not $quickRefContent.Contains('docs/plans/project-plan.md')) {
        throw 'Quick-ref is missing the planning auto-trigger gate.'
    }
    if (-not $quickRefContent.Contains('module-contract-template.md') -or -not $quickRefContent.Contains('regression-checklist-template.md') -or -not $quickRefContent.Contains('影响矩阵')) {
        throw 'Quick-ref is missing maintainability implementation gates.'
    }

    $projectRoot = Split-Path -Parent $root
    foreach ($adapterRelativePath in @('CLAUDE.md', 'AGENTS.md', '.cursor\rules\ai-spec.mdc', '.github\copilot-instructions.md')) {
        $adapterPath = Join-Path $projectRoot $adapterRelativePath
        if (-not (Test-Path -LiteralPath $adapterPath -PathType Leaf)) { continue }
        $adapterContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $adapterPath
        if ($adapterContent.Contains('AI-START.md') -and -not $adapterContent.Contains('business/quick-ref.md')) {
            throw "Stale AI adapter forces full startup reads: $adapterRelativePath. Merge the dynamic quick-ref entry without overwriting project-owned instructions."
        }
    }

    $currentPlanPath = Join-Path $projectRoot 'docs\plans\current.md'
    if (Test-Path -LiteralPath $currentPlanPath -PathType Leaf) {
        $currentPlanLines = @(Get-Content -Encoding UTF8 -LiteralPath $currentPlanPath)
        if ($currentPlanLines.Count -gt 80) {
            throw "Current plan exceeds 80 lines: $($currentPlanLines.Count). Keep it as a lightweight phase pointer."
        }
    }

    $phaseRoot = Join-Path $projectRoot 'docs\plans\phases'
    if (Test-Path -LiteralPath $phaseRoot -PathType Container) {
        $completedStatusLabel = -join (@(0x5B8C, 0x6210, 0x72B6, 0x6001) | ForEach-Object { [char]$_ })
        $acceptanceEvidenceLabel = -join (@(0x9A8C, 0x6536, 0x8BC1, 0x636E) | ForEach-Object { [char]$_ })
        $completedPattern = '(?mi)^\s*-\s*\*\*(' + [regex]::Escape($completedStatusLabel) + '|status)\*\*\s*[:\uFF1A]\s*completed\s*$'
        $evidencePattern = '(?ms)^##\s+(' + [regex]::Escape($acceptanceEvidenceLabel) + '|Acceptance evidence)\s*\r?\n(?<body>.*?)(?=^##\s|\z)'
        foreach ($phaseFile in @(Get-ChildItem -LiteralPath $phaseRoot -File -Filter '*.md')) {
            $phaseContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $phaseFile.FullName
            if ($phaseContent -match $completedPattern) {
                $evidence = [regex]::Match($phaseContent, $evidencePattern)
                $concreteEvidence = @()
                if ($evidence.Success) {
                    $concreteEvidence = @($evidence.Groups['body'].Value -split '\r?\n' | ForEach-Object { $_.Trim() } | Where-Object {
                        $_ -and $_ -notmatch '^[-*]\s*$' -and $_ -notmatch '[:\uFF1A]\s*$' -and $_ -notmatch '(?i)\b(TBD|TODO|placeholder)\b'
                    })
                }
                if (-not $evidence.Success -or $concreteEvidence.Count -eq 0) {
                    throw "Completed phase lacks acceptance evidence: $($phaseFile.FullName)"
                }
            }
        }
    }
        Write-Host 'Installed spec structure validation passed.' -ForegroundColor Green
    }
}

$settingsPath = Join-Path $root 'adapters\claude-code\settings.json.template'
if (Test-Path -LiteralPath $settingsPath -PathType Leaf) {
    try {
        Get-Content -Raw -Encoding UTF8 -LiteralPath $settingsPath | ConvertFrom-Json | Out-Null
    }
    catch {
        Write-Host "Invalid JSON template: $settingsPath" -ForegroundColor Red
        throw
    }
}

$brokenLinks = [System.Collections.Generic.List[string]]::new()
$conflictMarkers = [System.Collections.Generic.List[string]]::new()
$markdownFiles = Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.md' |
    Where-Object { $_.FullName -notmatch '[\\/]docs[\\/]legacy[\\/]' }

foreach ($file in $markdownFiles) {
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName
    $lines = Get-Content -Encoding UTF8 -LiteralPath $file.FullName
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Contains('[') -and $lines[$i].Contains('冲突')) {
            $relativeFile = $file.FullName.Substring($root.Length + 1)
            $lineNumber = $i + 1
            $conflictMarkers.Add("${relativeFile}:$lineNumber $($lines[$i].Trim())")
        }
    }

    $matches = [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')
    foreach ($match in $matches) {
        $target = $match.Groups[1].Value.Trim('<', '>')
        if ($target -match '^(https?://|#|mailto:)' -or $target.Contains('{{')) { continue }
        $targetWithoutAnchor = $target.Split('#')[0]
        if ([string]::IsNullOrWhiteSpace($targetWithoutAnchor)) { continue }
        $resolved = Join-Path $file.DirectoryName $targetWithoutAnchor
        if (-not (Test-Path -LiteralPath $resolved)) {
            $relativeFile = $file.FullName.Substring($root.Length + 1)
            $brokenLinks.Add("$relativeFile -> $target")
        }
    }
}

if ($conflictMarkers.Count -gt 0) {
    Write-Host 'Conflict summary:' -ForegroundColor Yellow
    foreach ($marker in $conflictMarkers) { Write-Host "- $marker" -ForegroundColor Yellow }
}

if ($brokenLinks.Count -gt 0) {
    Write-Host 'Broken local Markdown links:' -ForegroundColor Red
    foreach ($link in $brokenLinks) { Write-Host "- $link" -ForegroundColor Red }
    exit 1
}

Invoke-SpecForgeDoctor -SpecRoot $root
if ($script:doctorFailures -gt 0) {
    throw "SpecForge doctor found $script:doctorFailures blocking issue(s)."
}

Write-Host 'Structure, policy, skill, JSON, and Markdown link validation passed.' -ForegroundColor Green
