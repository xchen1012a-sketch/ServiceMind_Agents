[CmdletBinding()]
param(
    [string]$TargetRoot,
    [switch]$Apply,
    [string]$Repository = 'https://github.com/xchen1012a-sketch/SpecForge.git',
    [string]$SourceRoot,
    [string[]]$Tools = @('claude-code', 'codex', 'cursor', 'github-copilot', 'generic')
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    $installedSpecRoot = Split-Path -Parent $PSScriptRoot
    if ((Split-Path -Leaf $installedSpecRoot) -ne '.ai-spec') {
        throw 'TargetRoot is required when update.ps1 is not running from an installed .ai-spec/scripts directory.'
    }
    $TargetRoot = Split-Path -Parent $installedSpecRoot
}

$resolvedTarget = [System.IO.Path]::GetFullPath($TargetRoot)
if (-not (Test-Path -LiteralPath $resolvedTarget -PathType Container)) {
    throw "Target project does not exist: $resolvedTarget"
}

$temporarySource = $null
try {
    if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            throw 'git is required to pull the latest SpecForge rules.'
        }
        $temporarySource = Join-Path ([System.IO.Path]::GetTempPath()) ('SpecForge-update-' + [guid]::NewGuid().ToString('N'))
        & git clone --depth 1 $Repository $temporarySource
        if ($LASTEXITCODE -ne 0) {
            throw "git clone failed with exit code $LASTEXITCODE"
        }
        $SourceRoot = $temporarySource
    }

    $resolvedSource = [System.IO.Path]::GetFullPath($SourceRoot)
    $installer = Join-Path $resolvedSource 'scripts\install.ps1'
    if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
        throw "Latest installer not found: $installer"
    }

    $syncParameters = @{
        TargetRoot = $resolvedTarget
        Sync = $true
        Tools = $Tools
    }
    if ($Apply) { $syncParameters.Apply = $true }
    & $installer @syncParameters

    if ($Apply) {
        Write-Host 'SpecForge rules updated. Project-owned state was preserved.' -ForegroundColor Green
    }
    else {
        Write-Host 'Dry-run complete. Re-run with -Apply to update existing rules.' -ForegroundColor Yellow
    }
}
finally {
    if ($temporarySource -and (Test-Path -LiteralPath $temporarySource -PathType Container)) {
        $tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\')
        $resolvedTemporarySource = [System.IO.Path]::GetFullPath($temporarySource)
        if ($resolvedTemporarySource.StartsWith($tempBase + '\') -and (Split-Path -Leaf $resolvedTemporarySource).StartsWith('SpecForge-update-')) {
            Remove-Item -LiteralPath $resolvedTemporarySource -Recurse -Force
        }
    }
}
