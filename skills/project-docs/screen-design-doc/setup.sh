#!/usr/bin/env bash
# screen-design-doc 스킬 준비. 파이썬 3.10+ 이 있어야 한다. 캡처에 Chromium 을 쓴다.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python3 -m playwright install chromium || python -m playwright install chromium
python3 -c "import pptx, PIL, playwright; print('screen-design-doc ready')" || python -c "import pptx, PIL, playwright; print('screen-design-doc ready')"
