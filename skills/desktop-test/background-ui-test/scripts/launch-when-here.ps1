param(
  [Parameter(Mandatory)][string]$Target,   # 켤 것. 시작 메뉴 바로 가기(.lnk)나 실행 파일. 사용자가 실제로 켜는 경로와 같게 한다
  [long]$RefHwnd = 0,                      # 시험 데스크톱에 있는 기준 창
  [string]$RefProcess = "",
  [string]$LogFile = "",                   # 켠 시각을 남길 파일(증거)
  [int]$Minutes = 30
)
# 사용자가 시험 데스크톱으로 오면 그때 $Target 을 켜고 켠 시각을 남긴다.
# 켜질 때 자기 창을 앞으로 가져오는 앱은 사용자가 있는 데스크톱에 뜬다. 다른 데스크톱에서 켜면 사용자의 작업 화면을 덮는다.
$sp = Split-Path $MyInvocation.MyCommand.Path
$ref = @{}; if ($RefHwnd) { $ref.RefHwnd = $RefHwnd } else { $ref.RefProcess = $RefProcess }
$deadline = (Get-Date).AddMinutes($Minutes)
while ((Get-Date) -lt $deadline) {
  if ((& "$sp\vmove.ps1" -Check @ref) -eq "here") {
    $t = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Start-Process $Target
    if ($LogFile) { "켠 시각: $t" | Out-File -Encoding utf8 $LogFile }
    "LAUNCHED $t"
    exit 0
  }
  Start-Sleep -Seconds 2
}
"TIMEOUT"
