#!/usr/bin/env bash
# presentation-deck 스킬 준비. 파이썬 3.10+ 이 있어야 한다. PNG 로 뽑아 보는 단계는 PowerPoint(윈도) 가 있으면 쓴다.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python3 -c "import pptx, PIL, matplotlib; print('presentation-deck ready')" || python -c "import pptx, PIL, matplotlib; print('presentation-deck ready')"
