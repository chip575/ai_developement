$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'Docker was not found.'
    exit 1
}
docker compose down
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host 'PNU Assistant stopped. Demo data and model caches are retained.'
