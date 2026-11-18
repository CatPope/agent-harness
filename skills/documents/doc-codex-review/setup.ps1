# doc-codex-review 스킬 준비. 파이썬 3.9+ 이 있어야 한다. codex CLI 도 있어야 검토가 돈다.
$ErrorActionPreference = "Stop"
python -m pip install --quiet --disable-pip-version-check -r (Join-Path $PSScriptRoot "requirements.txt")
python -c "import olefile; print('doc-codex-review ready')"
