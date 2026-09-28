#!/usr/bin/env bash
# planning-docs 스킬 준비. 파이썬 3.10+ 이 있어야 한다. 목차 쪽 번호(fill_toc.ps1)는 윈도의 Word 가 있어야 한다.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python3 -c "import docx, lxml, matplotlib; print('planning-docs ready')" || python -c "import docx, lxml, matplotlib; print('planning-docs ready')"
