# screen-design-doc 스킬 준비. 파이썬 3.10+ 이 있어야 한다. 캡처에 Chromium 을 쓴다.
$ErrorActionPreference = "Stop"
python -m pip install --quiet --disable-pip-version-check -r (Join-Path $PSScriptRoot "requirements.txt")
python -m playwright install chromium
python -c "import pptx, PIL, playwright; print('screen-design-doc ready')"
