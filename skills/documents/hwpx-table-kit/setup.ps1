# Self-bootstrap the hwpx-table-kit environment (Windows / PowerShell).
# Safe to re-run. Requires: python (>=3.9) and node (>=18, only for verification).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[hwpx-table-kit] installing Python deps (Pillow, openpyxl) ..."
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "[hwpx-table-kit] installing kordoc (verification) ..."
    npm install --silent --no-audit --no-fund
} else {
    Write-Host "[hwpx-table-kit] node not found -> skipping kordoc. Generation still works;"
    Write-Host "                 roundtrip verification (verify_hwpx.mjs) will be unavailable."
}

Write-Host "[hwpx-table-kit] ready."
