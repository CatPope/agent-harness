#!/usr/bin/env sh
# Self-bootstrap live-demo-rehearsal. Safe to re-run. Requires: python3 (>=3.9).
set -e
cd "$(dirname "$0")"
echo "[live-demo-rehearsal] installing Python deps (openpyxl) ..."
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt
echo "[live-demo-rehearsal] ready."
