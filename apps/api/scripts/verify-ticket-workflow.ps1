param(
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$CommandArguments = @()
    )

    & $FilePath @CommandArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($CommandArguments -join ' ')"
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $apiRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

Invoke-NativeChecked ".\.venv\Scripts\python" @("-m", "pip", "install", "-e", ".[dev]")

if ($DatabaseUrl -ne "") {
    $env:SERVICEMIND_DATABASE_URL = $DatabaseUrl
}

$env:SERVICEMIND_RUN_POSTGRES_SMOKE = "1"

Invoke-NativeChecked ".\.venv\Scripts\alembic" @("upgrade", "head")
Invoke-NativeChecked ".\.venv\Scripts\python" @("-m", "pytest", "tests/tickets/test_ticket_postgres_smoke.py")
Invoke-NativeChecked ".\.venv\Scripts\python" @("-m", "pytest", "tests")
Invoke-NativeChecked ".\.venv\Scripts\ruff" @("check", "app", "tests", "alembic")
