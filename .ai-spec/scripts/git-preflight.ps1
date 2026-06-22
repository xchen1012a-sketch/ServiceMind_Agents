[CmdletBinding()]
param(
    [string]$RepositoryRoot = '.',

    [switch]$StagedOnly,

    [switch]$AllowParentSpecForge,

    [int]$MaxScanBytes = 1048576
)

$ErrorActionPreference = 'Stop'

$repoRoot = [System.IO.Path]::GetFullPath($RepositoryRoot)
if (-not (Test-Path -LiteralPath $repoRoot -PathType Container)) {
    throw "Repository root does not exist: $repoRoot"
}

try {
    $insideWorkTree = (& git -C $repoRoot rev-parse --is-inside-work-tree 2>$null)
}
catch {
    throw "Not a git repository: $repoRoot"
}

if ($insideWorkTree -ne 'true') {
    throw "Not a git repository: $repoRoot"
}

function Normalize-GitPath {
    param([string]$Path)
    return ($Path -replace '\\', '/').Trim('"')
}

function Get-ChangedGitPath {
    param([string]$StatusLine)

    if ($StatusLine.Length -lt 4) { return $null }
    $path = $StatusLine.Substring(3).Trim()
    if ($path -match ' -> ') {
        $path = ($path -split ' -> ')[-1]
    }
    return (Normalize-GitPath -Path $path)
}

function Add-Issue {
    param(
        [System.Collections.Generic.List[hashtable]]$Issues,
        [string]$Level,
        [string]$Path,
        [string]$Reason
    )

    $Issues.Add(@{
        level = $Level
        path = $Path
        reason = $Reason
    })
}

$statusArgs = @('status', '--porcelain=v1')
if ($StagedOnly) {
    $statusArgs += @('--untracked-files=no')
}

$statusLines = @(& git -C $repoRoot @statusArgs)
if ($LASTEXITCODE -ne 0) {
    throw "git status failed for $repoRoot"
}

if ($StagedOnly) {
    $statusLines = @($statusLines | Where-Object {
        $_.Length -ge 2 -and $_[0] -ne ' ' -and $_[0] -ne '?'
    })
}

$changedPaths = @($statusLines | ForEach-Object { Get-ChangedGitPath -StatusLine $_ } | Where-Object { $_ } | Select-Object -Unique)
$blocked = [System.Collections.Generic.List[hashtable]]::new()
$warnings = [System.Collections.Generic.List[hashtable]]::new()

$blockedPathRules = @(
    @{ pattern = '(^|/)\.env($|[._-].*)'; reason = 'environment file' },
    @{ pattern = '(^|/)(\.idea|\.vscode)(/|$)'; reason = 'local IDE/editor configuration' },
    @{ pattern = '(^|/)(node_modules|vendor|dist|build|target|\.next|coverage|\.cache|tmp|temp|logs?)(/|$)'; reason = 'dependency/cache/build artifact' },
    @{ pattern = '\.(log|tmp|temp|bak|swp|swo)$'; reason = 'temporary or log file' },
    @{ pattern = '(^|/)(\.DS_Store|Thumbs\.db)$'; reason = 'local OS metadata' },
    @{ pattern = '(^|/)(\.npmrc|\.pypirc|\.netrc)$'; reason = 'credential-prone package manager config' },
    @{ pattern = '(^|/).*(credential|secret|private[-_]?key).*$'; reason = 'credential-prone file name' },
    @{ pattern = '\.(pem|key|p12|pfx|keystore)$'; reason = 'private key or certificate container' }
)

foreach ($path in $changedPaths) {
    foreach ($rule in $blockedPathRules) {
        if ($path -match $rule.pattern) {
            Add-Issue -Issues $blocked -Level 'BLOCK' -Path $path -Reason $rule.reason
        }
    }

    if (-not $AllowParentSpecForge -and $path -eq '.specforge.json') {
        Add-Issue -Issues $blocked -Level 'BLOCK' -Path $path -Reason 'parent SpecForge index is not part of the default child-repo code submission'
    }

    if ($path -match '(^|/)\.ai-spec(/|$)') {
        Add-Issue -Issues $warnings -Level 'WARN' -Path $path -Reason 'AI rules are versioned only after explicit project confirmation'
    }
}

$secretPatterns = @(
    @{ pattern = '-----BEGIN (RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----'; reason = 'private key material' },
    @{ pattern = 'AKIA[0-9A-Z]{16}'; reason = 'AWS access key id' },
    @{ pattern = '(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*["''][^"'']{12,}["'']'; reason = 'possible inline secret' },
    @{ pattern = '(?i)(authorization:\s*bearer\s+)[a-z0-9._~+/-]{20,}'; reason = 'possible bearer token' }
)

foreach ($path in $changedPaths) {
    $fullPath = Join-Path $repoRoot ($path -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        continue
    }

    $item = Get-Item -LiteralPath $fullPath
    if ($item.Length -gt $MaxScanBytes) {
        Add-Issue -Issues $warnings -Level 'WARN' -Path $path -Reason "file exceeds content scan limit ($MaxScanBytes bytes)"
        continue
    }

    try {
        $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $fullPath
    }
    catch {
        Add-Issue -Issues $warnings -Level 'WARN' -Path $path -Reason 'content scan skipped because file is not readable as UTF-8 text'
        continue
    }

    foreach ($rule in $secretPatterns) {
        if ($content -match $rule.pattern) {
            Add-Issue -Issues $blocked -Level 'BLOCK' -Path $path -Reason $rule.reason
        }
    }
}

Write-Host 'Git preflight scan' -ForegroundColor Cyan
Write-Host "Repository: $repoRoot"
Write-Host "Mode: $(if ($StagedOnly) { 'staged-only' } else { 'all changed files' })"
Write-Host "Changed files: $($changedPaths.Count)"

foreach ($path in $changedPaths) {
    Write-Host "- $path"
}

if ($warnings.Count -gt 0) {
    Write-Host "Warnings: $($warnings.Count)" -ForegroundColor Yellow
    foreach ($issue in $warnings) {
        Write-Host "- [$($issue.level)] $($issue.path): $($issue.reason)" -ForegroundColor Yellow
    }
}

if ($blocked.Count -gt 0) {
    Write-Host "Blocked: $($blocked.Count)" -ForegroundColor Red
    foreach ($issue in $blocked) {
        Write-Host "- [$($issue.level)] $($issue.path): $($issue.reason)" -ForegroundColor Red
    }
    exit 1
}

Write-Host 'Preflight passed: no blocked files or secret patterns found.' -ForegroundColor Green
