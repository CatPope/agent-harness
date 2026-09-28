#!/usr/bin/env bash
# report-writing 스킬 준비. 파이썬 3.10+ 이 있어야 한다.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python3 -c "import docx; print('report-writing ready')" || python -c "import docx; print('report-writing ready')"
