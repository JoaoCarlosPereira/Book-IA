# Run unit and integration tests for Book-IA.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> Book-IA test suite"
Write-Host "    Root: $Root"

if (Get-Command docker -ErrorAction SilentlyContinue) {
    if (Test-Path "docker-compose.test.yml") {
        Write-Host "==> Optional: docker compose -f docker-compose.test.yml up -d (postgres:5433, redis:6380)"
    }
}

$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    $Python = "python3"
}

Write-Host "==> Unit tests (services/schemas — coverage >= 80%)"
& $Python -m pytest tests/test_services tests/test_schemas -v --cov-fail-under=80 @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Remaining unit/API/Celery tests"
& $Python -m pytest tests --ignore=tests/test_integration --ignore=tests/test_services --ignore=tests/test_schemas -v @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Integration tests (tests/test_integration)"
& $Python -m pytest tests/test_integration -v --cov-fail-under=0 @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> All tests passed."
