$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Python = Join-Path $Root "upload\.venv\Scripts\python.exe"
$Script = Join-Path $Root "upload\scripts\rebuild_ptm_catalog.py"

if (-not (Test-Path $Python)) {
    throw "Python venv not found: $Python"
}
if (-not (Test-Path $Script)) {
    throw "PTM catalog rebuild script not found: $Script"
}

Write-Host "=== REBUILD PTM SORTAMENT ==="
& $Python $Script
if ($LASTEXITCODE -ne 0) {
    throw "PTM catalog rebuild failed with exit code $LASTEXITCODE"
}
Write-Host "PTM catalog rebuild completed."
