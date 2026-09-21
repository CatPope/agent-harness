# Self-bootstrap this skill's environment (Windows / PowerShell). Safe to re-run.
# Requires: python (>=3.9). Node is optional and only for verification.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[my-skill] installing Python deps ..."
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

if (Test-Path package.json) {
    if (Get-Command node -ErrorAction SilentlyContinue) {
        Write-Host "[my-skill] installing Node deps ..."
        npm install --silent --no-audit --no-fund
    } else {
        Write-Host "[my-skill] node not found -> skipping optional Node deps."
    }
}

Write-Host "[my-skill] ready."
