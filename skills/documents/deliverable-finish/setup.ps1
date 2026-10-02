# deliverable-finish 준비. 외부 패키지는 없다. 파이썬 3.9+ 만 본다.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -c "import sys; assert sys.version_info >= (3, 9), sys.version; print('python', sys.version.split()[0], 'OK')"
