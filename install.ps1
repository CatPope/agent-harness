<#
  agent-harness installer (Windows / PowerShell 5.1+)

  .\install.ps1 -List
  .\install.ps1 -Workflow supervisor-worker
  .\install.ps1 -Status

  Copies the _core skills plus the chosen workflow's skills into both agent
  skill stores.

  Copies, not links. A link makes the install target and this repo the same
  files, so editing a skill while working on a project rewrites the shared
  original at once - project-specific notes leak into the repo and into every
  other project. Installing is one-way: repo -> install target. Sending work
  back is a separate step that generalises first.
#>
[CmdletBinding()]
param(
  [string]$Workflow,
  [switch]$List,
  [switch]$Status,
  [switch]$Force,
  [string]$ClaudeDir = "$HOME\.claude\skills",
  [string]$AgentsDir = "$HOME\.agents\skills"
)

$ErrorActionPreference = "Stop"
$Root   = $PSScriptRoot
$Marker = Join-Path $AgentsDir ".agent-harness-active"

function Get-Workflows {
  Get-ChildItem (Join-Path $Root "workflows") -Filter *.json | ForEach-Object {
    # -Encoding UTF8 필수: PowerShell 5.1 은 BOM 없는 파일을 ANSI 로 읽어 한글이 깨진다
    $w = Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $w | Add-Member -NotePropertyName _file -NotePropertyValue $_.Name -Force
    $w
  }
}

if ($List) {
  Write-Host ""
  Write-Host "사용 가능한 워크플로우"
  Write-Host ""
  foreach ($w in Get-Workflows) {
    Write-Host ("  {0,-20} [{1}] {2}" -f $w.id, $w.status, $w.name)
    Write-Host ("  {0,-20}   {1}" -f "", $w.summary)
    Write-Host ""
  }
  Write-Host "설치:  .\install.ps1 -Workflow <id>"
  return
}

if ($Status) {
  if (Test-Path $Marker) {
    Write-Host ("활성 워크플로우: " + (Get-Content $Marker -Raw).Trim())
  } else {
    Write-Host "활성 워크플로우 없음 (아직 설치하지 않았습니다)"
  }
  return
}

if (-not $Workflow) { throw "-Workflow <id> 를 지정하거나 -List 로 목록을 보세요." }

$wf = Get-Workflows | Where-Object { $_.id -eq $Workflow }
if (-not $wf) { throw "알 수 없는 워크플로우: $Workflow  (-List 로 확인)" }
if ($wf.status -ne "active") {
  throw "'$Workflow' 는 status=$($wf.status) 입니다. 아직 설치할 수 없습니다."
}

# 설치 대상 = _core 전부 + 워크플로우 고유 스킬
$targets = @()
Get-ChildItem (Join-Path $Root "skills\_core") -Directory | ForEach-Object { $targets += $_.FullName }
foreach ($s in $wf.skills) {
  $p = Join-Path $Root ("skills\" + $wf.id + "\" + $s)
  if (-not (Test-Path $p)) { throw "매니페스트에 있으나 폴더가 없습니다: $p" }
  $targets += $p
}

foreach ($dir in @($ClaudeDir, $AgentsDir)) {
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

$copied = 0; $skipped = 0; $failed = @()
foreach ($src in $targets) {
  $name = Split-Path $src -Leaf
  foreach ($dir in @($ClaudeDir, $AgentsDir)) {
    $link = Join-Path $dir $name
    if (Test-Path $link) {
      $item = Get-Item $link -Force
      # 예전 방식(정션·심링크)으로 깔려 있으면 끊고 복사본으로 바꾼다.
      # 링크를 지우는 것이지 대상 폴더의 내용을 지우는 것이 아니다.
      if ($item.LinkType -eq "Junction" -or $item.LinkType -eq "SymbolicLink") {
        cmd /c rd /q "$link" | Out-Null
        if (Test-Path $link) {
          $failed += "$link  (기존 링크 제거 실패)"
          continue
        }
      }
      elseif (-not $Force) {
        # 🔴 실제 폴더는 설치처에서 고쳤을 수 있다. 덮어쓰면 그 수정이 사라진다.
        Write-Warning "이미 있습니다(건너뜀): $link  -> 덮어쓰려면 -Force"
        $skipped++
        continue
      }
      else {
        Remove-Item $link -Recurse -Force
      }
    }
    Copy-Item -Path $src -Destination $link -Recurse -Force
    # 만들었다고 가정하지 않는다 — SKILL.md 가 실제로 놓였는지 확인하고 센다
    if (Test-Path (Join-Path $link "SKILL.md")) { $copied++ }
    else { $failed += "$link  (복사 실패)" }
  }
}

Set-Content -Path $Marker -Value $wf.id -Encoding utf8
Write-Host ""
Write-Host ("설치: {0}" -f $wf.name)
Write-Host ("  복사 {0}개, {1}개 건너뜀, {2}개 실패" -f $copied, $skipped, $failed.Count)
Write-Host ("  대상: {0} / {1}" -f $ClaudeDir, $AgentsDir)
Write-Host ("  스킬: {0}" -f (($targets | ForEach-Object { Split-Path $_ -Leaf }) -join ", "))

if ($failed.Count -gt 0) {
  Write-Host ""
  Write-Host "처리하지 못한 항목 — 이 경로들은 아직 저장소를 가리키지 않습니다:" -ForegroundColor Yellow
  foreach ($f in $failed) { Write-Host ("  - {0}" -f $f) -ForegroundColor Yellow }
  Write-Host ""
  Write-Host "실제 폴더는 자동으로 지우지 않습니다. 안에 있는 것이 유일본일 수 있기 때문입니다." -ForegroundColor Yellow
  Write-Host "내용을 확인해 저장소로 옮겼거나 더 필요 없다고 판단되면, 그 폴더를 직접 지운 뒤 다시 실행하세요." -ForegroundColor Yellow
  Write-Host ""
  exit 1
}
Write-Host ""
