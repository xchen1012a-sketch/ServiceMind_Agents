[CmdletBinding()]
param(
    [string]$RulesRoot = (Join-Path $HOME '.claude\rules'),
    [int]$MaxAlwaysOnFiles = 5,
    [int]$MaxAlwaysOnBytes = 12288
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $RulesRoot -PathType Container)) {
    Write-Host 'Global Claude rules not found. SpecForge remains project-only.'
    return
}

$files = @(Get-ChildItem -LiteralPath $RulesRoot -Recurse -File -Filter '*.md')
$alwaysOn = [System.Collections.Generic.List[object]]::new()
$broadAgentFiles = [System.Collections.Generic.List[string]]::new()
$fixedCoverageFiles = [System.Collections.Generic.List[string]]::new()

foreach ($file in $files) {
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName
    if ($content -notmatch '(?m)^paths:\s*$') {
        $alwaysOn.Add($file)
    }
    if ($content -match '(?i)Immediate Agent Usage|code-reviewer.{0,80}(every|after writing)|tdd-guide.{0,80}(new feature|bug fix)') {
        $broadAgentFiles.Add($file.FullName)
    }
    if ($content.Contains('80%')) {
        $fixedCoverageFiles.Add($file.FullName)
    }
}

$alwaysOnBytes = if ($alwaysOn.Count -gt 0) { [long](($alwaysOn | Measure-Object Length -Sum).Sum) } else { 0 }
$mirrorCount = 0
$commonRoot = Join-Path $RulesRoot 'common'
$zhRoot = Join-Path $RulesRoot 'zh'
if ((Test-Path -LiteralPath $commonRoot -PathType Container) -and (Test-Path -LiteralPath $zhRoot -PathType Container)) {
    foreach ($commonFile in @(Get-ChildItem -LiteralPath $commonRoot -File -Filter '*.md')) {
        if (Test-Path -LiteralPath (Join-Path $zhRoot $commonFile.Name) -PathType Leaf) {
            $mirrorCount++
        }
    }
}

$summary = "files=$($files.Count) alwaysOn=$($alwaysOn.Count) alwaysOnBytes=$alwaysOnBytes mirrors=$mirrorCount broadAgent=$($broadAgentFiles.Count) fixed80=$($fixedCoverageFiles.Count)"
if ($alwaysOn.Count -gt $MaxAlwaysOnFiles -or $alwaysOnBytes -gt $MaxAlwaysOnBytes) {
    Write-Host "GLOBAL_CONTEXT_WARNING $summary" -ForegroundColor Yellow
    Write-Host 'SpecForge will not modify user-level rules. Back up and reduce or path-scope them separately.' -ForegroundColor Yellow
}
else {
    Write-Host "Global context audit OK $summary" -ForegroundColor Green
}
