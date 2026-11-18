#!/usr/bin/env bash
# doc-codex-review 스킬 준비. 파이썬 3.9+ 이 있어야 한다. codex CLI 도 있어야 검토가 돈다.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python3 -c "import olefile; print('doc-codex-review ready')" || python -c "import olefile; print('doc-codex-review ready')"
