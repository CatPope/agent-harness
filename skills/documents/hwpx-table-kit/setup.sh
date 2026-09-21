#!/usr/bin/env bash
# Self-bootstrap the hwpx-table-kit environment.
# Safe to re-run. Requires: python3 (>=3.9) and node (>=18, only for verification).
set -e
cd "$(dirname "$0")"

echo "[hwpx-table-kit] installing Python deps (Pillow, openpyxl) ..."
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt

if command -v node >/dev/null 2>&1; then
  echo "[hwpx-table-kit] installing kordoc (verification) ..."
  npm install --silent --no-audit --no-fund
else
  echo "[hwpx-table-kit] node not found -> skipping kordoc. Generation still works;"
  echo "                 roundtrip verification (verify_hwpx.mjs) will be unavailable."
fi

echo "[hwpx-table-kit] ready."
