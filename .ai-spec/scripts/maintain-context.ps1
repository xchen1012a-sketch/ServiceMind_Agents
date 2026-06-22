[CmdletBinding()]
param(
    [string]$TargetRoot,
    [switch]$Apply,
    [switch]$Force,
    [datetime]$Now = (Get-Date)
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    $candidateSpecRoot = Split-Path -Parent $PSScriptRoot
    if ((Split-Path -Leaf $candidateSpecRoot) -ne '.ai-spec') {
        throw 'TargetRoot is required outside an installed .ai-spec/scripts directory.'
    }
    $TargetRoot = Split-Path -Parent $candidateSpecRoot
}

$projectRoot = [System.IO.Path]::GetFullPath($TargetRoot)
$specRoot = Join-Path $projectRoot '.ai-spec'
if (-not (Test-Path -LiteralPath $specRoot -PathType Container)) {
    throw "Installed .ai-spec not found under: $projectRoot"
}

$quickRefPath = Join-Path $specRoot 'business\quick-ref.md'
$profilePath = Join-Path $specRoot 'ai-spec.yaml'
if (-not (Test-Path -LiteralPath $quickRefPath -PathType Leaf) -or -not (Test-Path -LiteralPath $profilePath -PathType Leaf)) {
    throw 'Context maintenance requires business/quick-ref.md and ai-spec.yaml.'
}

function Get-LineCount {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return 0 }
    return @(Get-Content -Encoding UTF8 -LiteralPath $Path).Count
}

function Test-Completed {
    param([string]$Path)
    # Safe archive candidates must explicitly contain: status: completed
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $Path
    $completedStatusLabel = -join (@(0x5B8C, 0x6210, 0x72B6, 0x6001) | ForEach-Object { [char]$_ })
    $pattern = '(?mi)^\s*-\s*(?:\*\*)?(' + [regex]::Escape($completedStatusLabel) + '|status)(?:\*\*)?\s*[:\uFF1A]\s*completed\s*$'
    return $content -match $pattern
}

function Assert-SafeSource {
    param([string]$Path, [string]$AllowedRoot)
    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $resolvedRoot = [System.IO.Path]::GetFullPath($AllowedRoot).TrimEnd('\')
    if (-not $resolvedPath.StartsWith($resolvedRoot + '\')) {
        throw "Maintenance source is outside its allowed root: $resolvedPath"
    }
}

function New-ArchiveAction {
    param([string]$Source, [string]$ArchiveRoot, [string]$Type)
    $month = $Now.ToString('yyyy-MM')
    $destinationDirectory = Join-Path $ArchiveRoot $month
    $destination = Join-Path $destinationDirectory (Split-Path -Leaf $Source)
    if (Test-Path -LiteralPath $destination) {
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($destination)
        $extension = [System.IO.Path]::GetExtension($destination)
        $destination = Join-Path $destinationDirectory ($baseName + '-' + $Now.ToString('yyyyMMddHHmmss') + $extension)
    }
    return [pscustomobject]@{ Type = $Type; Source = $Source; Destination = $destination }
}

$quickRefContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $quickRefPath
$profileContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $profilePath
if (-not $Force -and $quickRefContent -notmatch '(?m)^>\s*status:\s*GENERATED\s*$') {
    Write-Host 'Maintenance skipped: quick-ref is not GENERATED.' -ForegroundColor Yellow
    return
}

$projectSizeMatch = [regex]::Match($profileContent, '(?m)^\s{2}projectSize:\s*(tiny|small|medium|large|enterprise|auto)\b')
$projectSize = if ($projectSizeMatch.Success) { $projectSizeMatch.Groups[1].Value } else { 'auto' }
$intervalDays = switch ($projectSize) {
    { $_ -in @('tiny', 'small') } { 30; break }
    'medium' { 14; break }
    { $_ -in @('large', 'enterprise') } { 7; break }
    default { 14 }
}
$businessRulesBudget = switch ($projectSize) {
    'tiny' { 200; break }
    'small' { 300; break }
    'medium' { 500; break }
    'large' { 800; break }
    'enterprise' { 1200; break }
    default { 300 }
}
$projectMapBudget = switch ($projectSize) {
    'tiny' { 80; break }
    'small' { 120; break }
    'medium' { 180; break }
    'large' { 250; break }
    'enterprise' { 350; break }
    default { 120 }
}

$dueMatch = [regex]::Match($quickRefContent, '(?m)^>\s*maintenanceDue:\s*(auto|\d{4}-\d{2}-\d{2})\s*$')
$isDue = $Force -or -not $dueMatch.Success -or $dueMatch.Groups[1].Value -eq 'auto'
if (-not $isDue) {
    $dueDate = [datetime]::ParseExact($dueMatch.Groups[1].Value, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
    $isDue = $dueDate.Date -le $Now.Date
}

$issues = [System.Collections.Generic.List[string]]::new()
$quickRefLines = Get-LineCount $quickRefPath
if ($quickRefLines -gt 40) { $issues.Add("COMPACT_REQUIRED quick-ref.md lines=$quickRefLines budget=40") }
$currentPlanPath = Join-Path $projectRoot 'docs\plans\current.md'
$currentPlanLines = Get-LineCount $currentPlanPath
if ($currentPlanLines -gt 80) { $issues.Add("COMPACT_REQUIRED docs/plans/current.md lines=$currentPlanLines budget=80") }
$businessRulesPath = Join-Path $specRoot 'business\business-rules.md'
$businessRulesLines = Get-LineCount $businessRulesPath
if ($businessRulesLines -gt $businessRulesBudget) { $issues.Add("COMPACT_REQUIRED business/business-rules.md lines=$businessRulesLines budget=$businessRulesBudget") }
$projectMapPath = Join-Path $specRoot 'business\project-map.md'
$projectMapLines = Get-LineCount $projectMapPath
if ($projectMapLines -gt $projectMapBudget) { $issues.Add("COMPACT_REQUIRED business/project-map.md lines=$projectMapLines budget=$projectMapBudget") }

if (-not $isDue -and $issues.Count -eq 0) {
    Write-Host "Maintenance not due. projectSize=$projectSize due=$($dueMatch.Groups[1].Value)" -ForegroundColor Green
    return
}

$actions = [System.Collections.Generic.List[object]]::new()
$sessionsRoot = Join-Path $specRoot 'sessions'
if (Test-Path -LiteralPath $sessionsRoot -PathType Container) {
    foreach ($file in @(Get-ChildItem -LiteralPath $sessionsRoot -File -Filter '*.md')) {
        if (Test-Completed $file.FullName) {
            $actions.Add((New-ArchiveAction -Source $file.FullName -ArchiveRoot (Join-Path $sessionsRoot 'archive') -Type 'session'))
        }
    }
}

$handoffsRoot = Join-Path $projectRoot 'docs\handoffs'
if (Test-Path -LiteralPath $handoffsRoot -PathType Container) {
    foreach ($file in @(Get-ChildItem -LiteralPath $handoffsRoot -File -Filter '*.md')) {
        if (Test-Completed $file.FullName) {
            $actions.Add((New-ArchiveAction -Source $file.FullName -ArchiveRoot (Join-Path $handoffsRoot 'archive') -Type 'handoff'))
        }
    }
}

$phasesRoot = Join-Path $projectRoot 'docs\plans\phases'
$currentPlanContent = if (Test-Path -LiteralPath $currentPlanPath -PathType Leaf) { Get-Content -Raw -Encoding UTF8 -LiteralPath $currentPlanPath } else { '' }
if (Test-Path -LiteralPath $phasesRoot -PathType Container) {
    foreach ($file in @(Get-ChildItem -LiteralPath $phasesRoot -File -Filter '*.md')) {
        if ((Test-Completed $file.FullName) -and -not $currentPlanContent.Contains($file.Name)) {
            $actions.Add((New-ArchiveAction -Source $file.FullName -ArchiveRoot (Join-Path $projectRoot 'docs\plans\archive') -Type 'phase'))
        }
    }
}

foreach ($issue in $issues) { Write-Host $issue -ForegroundColor Yellow }
foreach ($action in $actions) { Write-Host "ARCHIVE $($action.Type) $($action.Source) -> $($action.Destination)" }

if (-not $Apply) {
    Write-Host "Maintenance dry-run complete. actions=$($actions.Count) issues=$($issues.Count)" -ForegroundColor Yellow
    return
}

foreach ($action in $actions) {
    $allowedRoot = switch ($action.Type) {
        'session' { $sessionsRoot }
        'handoff' { $handoffsRoot }
        'phase' { $phasesRoot }
    }
    Assert-SafeSource -Path $action.Source -AllowedRoot $allowedRoot
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $action.Destination) | Out-Null
    Move-Item -LiteralPath $action.Source -Destination $action.Destination

    if ($action.Type -eq 'phase') {
        $projectPlanPath = Join-Path $projectRoot 'docs\plans\project-plan.md'
        if (Test-Path -LiteralPath $projectPlanPath -PathType Leaf) {
            $projectPlanContent = Get-Content -Raw -Encoding UTF8 -LiteralPath $projectPlanPath
            $oldReference = 'phases/' + (Split-Path -Leaf $action.Source)
            $newReference = 'archive/' + $Now.ToString('yyyy-MM') + '/' + (Split-Path -Leaf $action.Destination)
            if ($projectPlanContent.Contains($oldReference)) {
                $projectPlanContent = $projectPlanContent.Replace($oldReference, $newReference)
                [System.IO.File]::WriteAllText($projectPlanPath, $projectPlanContent, [System.Text.UTF8Encoding]::new($false))
            }
        }
    }
}

$nextDays = if ($issues.Count -gt 0) { 1 } else { $intervalDays }
$nextDue = $Now.Date.AddDays($nextDays).ToString('yyyy-MM-dd')
if ($dueMatch.Success) {
    $quickRefContent = [regex]::Replace($quickRefContent, '(?m)^>\s*maintenanceDue:\s*(auto|\d{4}-\d{2}-\d{2})\s*$', "> maintenanceDue: $nextDue")
}
else {
    throw 'maintenanceDue marker is missing; refusing to rewrite quick-ref structure.'
}
[System.IO.File]::WriteAllText($quickRefPath, $quickRefContent, [System.Text.UTF8Encoding]::new($false))
Write-Host "Maintenance applied. archived=$($actions.Count) issues=$($issues.Count) nextDue=$nextDue" -ForegroundColor Green
