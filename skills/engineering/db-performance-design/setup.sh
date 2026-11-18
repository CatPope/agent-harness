#!/usr/bin/env bash
# db-performance-design 준비. 외부 패키지는 없다. 파이썬 3.11+ 과 SQLite FTS5 가 있는지만 본다.
set -e
cd "$(dirname "$0")"
python3 scripts/check_env.py || python scripts/check_env.py
