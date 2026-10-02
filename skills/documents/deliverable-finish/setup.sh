#!/usr/bin/env bash
# deliverable-finish 준비. 외부 패키지는 없다. 파이썬 3.9+ 만 본다.
set -e
cd "$(dirname "$0")"
PY="$(command -v python3 || command -v python)"
"$PY" -c "import sys; assert sys.version_info >= (3, 9), sys.version; print('python', sys.version.split()[0], 'OK')"
