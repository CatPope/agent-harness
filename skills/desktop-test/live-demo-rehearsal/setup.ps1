# Self-bootstrap live-demo-rehearsal (Windows / PowerShell). Safe to re-run. Requires: python (>=3.9).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "[live-demo-rehearsal] installing Python deps (openpyxl) ..."
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
Write-Host "[live-demo-rehearsal] ready."
