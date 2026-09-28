# wbs-excel 스킬 준비. 파이썬 3.10+ 과 Excel(데스크톱) 이 있어야 한다.
$ErrorActionPreference = "Stop"
python -m pip install --quiet -r (Join-Path $PSScriptRoot "requirements.txt")
python -c "import openpyxl; print('openpyxl', openpyxl.__version__)"
$vbom = (Get-ItemProperty "HKCU:\Software\Microsoft\Office\16.0\Excel\Security" -ErrorAction SilentlyContinue).AccessVBOM
if ($vbom -ne 1) { Write-Warning "Excel 의 'VBA 프로젝트 개체 모델에 대한 액세스 신뢰' 가 꺼져 있다. inject_vba.ps1 이 실패한다. 사용자에게 먼저 묻고 켠다." }
else { "AccessVBOM=1 확인" }
