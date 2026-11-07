$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path -LiteralPath '.env')) {
    Write-Host 'Missing .env. Copy .env.example to .env and enter PICKLE_API_KEY.'
    exit 1
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'Docker was not found. Install and start Docker Desktop, then try again.'
    exit 1
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Docker Desktop is not running. Start it, wait until ready, then try again.'
    exit 1
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Docker Compose is unavailable. Update Docker Desktop and try again.'
    exit 1
}

Write-Host 'Building and starting PNU Assistant. First run downloads dependencies and an embedding model.'
docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Build or startup failed. Check Docker Desktop, internet access, and port conflicts.'
    exit 1
}

$appPort = '8771'
foreach ($line in Get-Content -LiteralPath '.env') {
    if ($line -match '^\s*APP_PORT\s*=\s*(\d+)\s*$') { $appPort = $Matches[1] }
}
if ($env:APP_PORT) { $appPort = $env:APP_PORT }
if ($appPort -notmatch '^\d+$' -or [int]$appPort -lt 1 -or [int]$appPort -gt 65535) {
    Write-Host 'Invalid APP_PORT in .env.'
    exit 1
}
$url = "http://127.0.0.1:$appPort/"
Write-Host "Waiting for the application at $url (first run can take several minutes)..."
$deadline = (Get-Date).AddMinutes(15)
while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            Write-Host "Ready: $url"
            Start-Process $url
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 3
}
Write-Host 'The application did not become ready. Recent application logs:'
docker compose logs --tail 40 app
exit 1
