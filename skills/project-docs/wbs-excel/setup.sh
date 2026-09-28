#!/usr/bin/env bash
# wbs-excel 스킬 준비. 생성(wbs_build.py)은 어디서나 되지만, VBA 주입(inject_vba.ps1)은 윈도의 데스크톱 Excel 이 있어야 한다.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python3 -c "import openpyxl; print(\"openpyxl\", openpyxl.__version__)" || python -c "import openpyxl; print(\"openpyxl\", openpyxl.__version__)"
echo "[wbs-excel] VBA 를 붙이려면 윈도에서 setup.ps1 과 inject_vba.ps1 을 쓴다."
