#!/usr/bin/env bash
# figma-mcp 스킬 준비. 파이썬 3.9+ 이 있어야 한다. 모아 보기 스크립트(deck_contact.py)에만 필요하다.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python3 -c "import PIL; print('figma-mcp ready')" || python -c "import PIL; print('figma-mcp ready')"
