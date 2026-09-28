# 파이썬이 만든 xlsx 에 VBA 를 붙여 .xlsm 으로 저장한다. 결과는 실행 폴더의 out\ (또는 -OutDir).
param([string]$Ver = "2.1.0", [string]$OutDir = (Join-Path (Get-Location) "out"))
$tmp = "$env:TEMP\wbs_v${Ver}_nomacro.xlsx"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$out = Join-Path $OutDir "[1차] WBS_일정관리_v$Ver.xlsm"
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($tmp)
    $vbp = $wb.VBProject
    $mod = $vbp.VBComponents.Add(1)      # 표준 모듈
    $mod.Name = "WbsSync"
    $mod.CodeModule.AddFromString((Get-Content "$PSScriptRoot\WbsSync.bas" -Raw -Encoding utf8))
    $codeName = $wb.Worksheets.Item("인원별").CodeName
    $sheetComp = $vbp.VBComponents.Item($codeName)
    $sheetComp.CodeModule.AddFromString((Get-Content "$PSScriptRoot\SheetPeople.bas" -Raw -Encoding utf8))
    # Excel 은 파일 이름에 [ ] 가 있으면 저장을 거부한다 → 임시 이름으로 저장한 뒤 옮긴다
    $stage = "$env:TEMP\wbs_v${Ver}_macro.xlsm"
    $wb.SaveAs($stage, 52)               # xlOpenXMLWorkbookMacroEnabled
} finally {
    if ($wb) { $wb.Close($false) }
    $xl.Quit()
}
Move-Item -LiteralPath $stage -Destination $out -Force
"saved $out"
