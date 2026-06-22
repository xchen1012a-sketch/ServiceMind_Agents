param(
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $apiRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

.\.venv\Scripts\python -m pip install -e ".[dev]"

if ($DatabaseUrl -ne "") {
    $env:SERVICEMIND_DATABASE_URL = $DatabaseUrl
}

.\.venv\Scripts\python -m pytest tests/db
.\.venv\Scripts\ruff check app tests alembic
.\.venv\Scripts\alembic heads
.\.venv\Scripts\alembic upgrade head
