# report-writing 스킬 준비. 파이썬 3.10+ 이 있어야 한다.
$ErrorActionPreference = "Stop"
python -m pip install --quiet --disable-pip-version-check -r (Join-Path $PSScriptRoot "requirements.txt")
python -c "import docx; print('report-writing ready')"
