# 사용자가 직접 고친 .xlsm 을 다시 만들지 않고, 안의 VBA(WbsSync · 인원별 시트 모듈)만 이 폴더의 .bas 로 갈아끼운다.
# 값·서식·행 배치는 그대로 남는다. 파일 이름에 [ ] 가 있어도 되게 임시 이름으로 저장한 뒤 옮긴다.
#   .\update_vba.ps1 -In "<원본 xlsm>" -Out "<저장할 xlsm>"
param([Parameter(Mandatory)][string]$In, [Parameter(Mandatory)][string]$Out)
$In = (Resolve-Path -LiteralPath $In).Path
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
$xl.AutomationSecurity = 3                      # 매크로를 끄고 연다 — 여는 동안 옛 RebuildPeople 이 돌지 않게
try {
    $wb = $xl.Workbooks.Open($In)
    $vbp = $wb.VBProject
    $old = $null
    try { $old = $vbp.VBComponents.Item("WbsSync") } catch {}
    if ($old) { $vbp.VBComponents.Remove($old) }
    $mod = $vbp.VBComponents.Add(1)
    $mod.Name = "WbsSync"
    $mod.CodeModule.AddFromString((Get-Content "$PSScriptRoot\WbsSync.bas" -Raw -Encoding utf8))
    $codeName = $wb.Worksheets.Item("인원별").CodeName
    $sheetComp = $vbp.VBComponents.Item($codeName)
    $cm = $sheetComp.CodeModule
    if ($cm.CountOfLines -gt 0) { $cm.DeleteLines(1, $cm.CountOfLines) }
    $cm.AddFromString((Get-Content "$PSScriptRoot\SheetPeople.bas" -Raw -Encoding utf8))
    $stage = Join-Path $env:TEMP ("wbs_update_" + [guid]::NewGuid().ToString("N") + ".xlsm")
    $wb.SaveAs($stage, 52)
} finally {
    if ($wb) { $wb.Close($false) }
    $xl.Quit()
}
Move-Item -LiteralPath $stage -Destination $Out -Force
"saved $Out"
