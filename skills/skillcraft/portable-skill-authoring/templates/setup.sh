#!/usr/bin/env bash
# Self-bootstrap this skill's environment. Safe to re-run (idempotent).
# Requires: python3 (>=3.9). Node is optional and only for verification.
set -e
cd "$(dirname "$0")"

echo "[my-skill] installing Python deps ..."
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt

if [ -f package.json ]; then
  if command -v node >/dev/null 2>&1; then
    echo "[my-skill] installing Node deps ..."
    npm install --silent --no-audit --no-fund
  else
    echo "[my-skill] node not found -> skipping optional Node deps."
  fi
fi

echo "[my-skill] ready."
