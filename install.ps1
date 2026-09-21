<#
  agent-harness installer (Windows / PowerShell 5.1+)

  .\install.ps1 -List
  .\install.ps1 -Workflow supervisor-worker
  .\install.ps1 -Status
  .\install.ps1 -Workflow supervisor-worker -WithLinter
  .\install.ps1 -Pack documents,skillcraft

  Copies the _core skills plus the chosen workflow's skills into both agent
  skill stores. A pack (-Pack) is a topic bundle installed on its own: it brings
  only its own skills, not _core. Workflow and packs can be given together.

  Copies, not links. A link makes the install target and this repo the same
  files, so editing a skill while working on a project rewrites the shared
  original at once - project-specific notes leak into the repo and into every
  other project. Installing is one-way: repo -> install target. Sending work
  back is a separate step that generalises first.

  -Force: NOT RECOMMENDED.
  Without it, a skill folder that already exists is left alone. With it, that
  folder is DELETED and replaced by the repo copy - anything you changed at the
  install target is gone, and copies keep no history, so there is nothing to
  undo from. The install target is where a skill is adapted to this machine;
  the repo holds the generalised version. Overwriting throws away the adapted
  one to get the generic one back.

  Want the newer repo version? Use the pull procedure in
  skills/_core/harness-repo instead. It sorts each skill into new / differing /
  local-only and merges only what you pick.

  Use -Force only when you know the install target has nothing worth keeping -
  a fresh machine, or a skill you never touched locally.
#>
[CmdletBinding()]
param(
  [string]$Workflow,
  # 주제별 묶음. 워크플로우와 달리 _core 를 끌고 오지 않는다. 여러 개 줄 수 있다.
  [string[]]$Pack,
  [switch]$List,
  [switch]$Status,
  # 🔴 권장하지 않는다. 설치처 폴더를 지우고 레포 것으로 덮어쓴다.
  #    설치처에서 고친 내용이 사라지고, 복사본에는 이력이 없어 되돌릴 수 없다.
  #    갱신이 목적이면 skills/_core/harness-repo 의 가져오기 절차를 쓴다.
  [switch]$Force,
  # 선택 설치. 포터빌리티 린터(tools/check_skill.py)를 설치처에도 둔다.
  # 없어도 스킬은 정상 동작한다 — 스킬을 고칠 사람만 필요하다.
  [switch]$WithLinter,
  [string]$ClaudeDir = "$HOME\.claude\skills",
  [string]$AgentsDir = "$HOME\.agents\skills",
  [string]$ToolsDir  = "$HOME\.claude\tools"
)

$ErrorActionPreference = "Stop"
$Root   = $PSScriptRoot
$Marker     = Join-Path $AgentsDir ".agent-harness-active"
$PackMarker = Join-Path $AgentsDir ".agent-harness-packs"

function Get-Manifests($sub) {
  $dir = Join-Path $Root $sub
  if (-not (Test-Path $dir)) { return @() }
  Get-ChildItem $dir -Filter *.json | ForEach-Object {
    # -Encoding UTF8 필수: PowerShell 5.1 은 BOM 없는 파일을 ANSI 로 읽어 한글이 깨진다
    $w = Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $w | Add-Member -NotePropertyName _file -NotePropertyValue $_.Name -Force
    $w
  }
}
function Get-Workflows { Get-Manifests "workflows" }
function Get-Packs     { Get-Manifests "packs" }

# 비교에서 뺄 것 — 파이썬 캐시, 수정 전 안전 사본, 설치처가 남기는 로컬 기록.
# 이것까지 세면 멀쩡한 설치처가 전부 "변경됨"으로 잡힌다.
function Test-Ignorable($rel, $leaf) {
  if ($rel -match '(^|[\\/])__pycache__([\\/]|$)') { return $true }
  if ($rel -match '(^|[\\/])기록([\\/]|$)')        { return $true }
  if ($rel -match '\.pyc$')                          { return $true }
  if ($leaf -like '*.bak_*')                          { return $true }
  return $false
}

function Get-DirFingerprint($dir) {
  $map = @{}
  if (-not (Test-Path $dir)) { return $map }
  $base = (Resolve-Path $dir).Path.TrimEnd('\')
  Get-ChildItem $dir -Recurse -File -Force | ForEach-Object {
    $rel = $_.FullName.Substring($base.Length).TrimStart('\')
    if (Test-Ignorable $rel $_.Name) { return }
    $map[$rel] = (Get-FileHash $_.FullName -Algorithm MD5).Hash
  }
  return $map
}

# 같으면 $null, 다르면 사람이 읽을 요약 문자열을 돌려준다.
function Compare-SkillDir($src, $dst) {
  $a = Get-DirFingerprint $src
  $b = Get-DirFingerprint $dst
  $onlyRepo  = @($a.Keys | Where-Object { -not $b.ContainsKey($_) })
  $onlyLocal = @($b.Keys | Where-Object { -not $a.ContainsKey($_) })
  $changed   = @($a.Keys | Where-Object { $b.ContainsKey($_) -and $a[$_] -ne $b[$_] })
  if ($onlyRepo.Count -eq 0 -and $onlyLocal.Count -eq 0 -and $changed.Count -eq 0) { return $null }
  $bits = @()
  if ($changed.Count   -gt 0) { $bits += "내용 다름 {0}" -f $changed.Count }
  if ($onlyRepo.Count  -gt 0) { $bits += "레포에만 {0}"  -f $onlyRepo.Count }
  if ($onlyLocal.Count -gt 0) { $bits += "설치처에만 {0}" -f $onlyLocal.Count }
  $names = @($changed + $onlyRepo + $onlyLocal) | Select-Object -First 3
  return ("{0}  ({1})" -f ($bits -join " · "), ($names -join ", "))
}

if ($List) {
  Write-Host ""
  Write-Host "워크플로우 — _core 공통 스킬과 함께 설치됩니다"
  Write-Host ""
  foreach ($w in Get-Workflows) {
    Write-Host ("  {0,-20} [{1}] {2}" -f $w.id, $w.status, $w.name)
    Write-Host ("  {0,-20}   {1}" -f "", $w.summary)
    Write-Host ""
  }
  Write-Host "팩 — 주제별 묶음. 자기 스킬만 설치합니다"
  Write-Host ""
  foreach ($p in Get-Packs) {
    Write-Host ("  {0,-20} [{1}] {2}" -f $p.id, $p.status, $p.name)
    Write-Host ("  {0,-20}   {1}" -f "", $p.summary)
    Write-Host ""
  }
  Write-Host "설치:  .\install.ps1 -Workflow <id>"
  Write-Host "       .\install.ps1 -Pack <id>[,<id>]"
  return
}

if ($Status) {
  if (Test-Path $Marker) {
    Write-Host ("활성 워크플로우: " + (Get-Content $Marker -Raw).Trim())
  } else {
    Write-Host "활성 워크플로우 없음 (아직 설치하지 않았습니다)"
  }
  if (Test-Path $PackMarker) {
    Write-Host ("설치한 팩: " + (Get-Content $PackMarker -Raw).Trim())
  } else {
    Write-Host "설치한 팩 없음"
  }
  return
}

if (-not $Workflow -and -not $Pack) {
  throw "-Workflow <id> 또는 -Pack <id> 를 지정하거나, -List 로 목록을 보세요."
}

$targets = @()
$chosen  = @()

# 워크플로우를 고르면 _core 공통 스킬이 함께 온다.
if ($Workflow) {
  $wf = Get-Workflows | Where-Object { $_.id -eq $Workflow }
  if (-not $wf) { throw "알 수 없는 워크플로우: $Workflow  (-List 로 확인)" }
  if ($wf.status -ne "active") {
    throw "'$Workflow' 는 status=$($wf.status) 입니다. 아직 설치할 수 없습니다."
  }
  Get-ChildItem (Join-Path $Root "skills\_core") -Directory | ForEach-Object { $targets += $_.FullName }
  foreach ($s in $wf.skills) {
    $p = Join-Path $Root ("skills\" + $wf.id + "\" + $s)
    if (-not (Test-Path $p)) { throw "매니페스트에 있으나 폴더가 없습니다: $p" }
    $targets += $p
  }
  $chosen += $wf.name
}

# 팩은 자기 스킬만 가져온다. _core 를 끌고 오지 않는다.
$packIds = @()
foreach ($packId in $Pack) {
  $pk = Get-Packs | Where-Object { $_.id -eq $packId }
  if (-not $pk) { throw "알 수 없는 팩: $packId  (-List 로 확인)" }
  if ($pk.status -ne "active") {
    throw "'$packId' 는 status=$($pk.status) 입니다. 아직 설치할 수 없습니다."
  }
  foreach ($s in $pk.skills) {
    $p = Join-Path $Root ("skills\" + $pk.id + "\" + $s)
    if (-not (Test-Path $p)) { throw "매니페스트에 있으나 폴더가 없습니다: $p" }
    $targets += $p
  }
  $packIds += $pk.id
  $chosen  += $pk.name
}

foreach ($dir in @($ClaudeDir, $AgentsDir)) {
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

if ($Force) {
  Write-Host ""
  Write-Warning "-Force: 이미 있는 스킬 폴더를 지우고 레포 것으로 덮어씁니다."
  Write-Warning "         설치처에서 고친 내용은 사라지며 되돌릴 수 없습니다."
  Write-Warning "         갱신이 목적이라면 skills/_core/harness-repo 의"
  Write-Warning "         가져오기 절차를 쓰십시오 — 필요한 것만 골라 병합합니다."
  Write-Host ""
}

$copied = 0; $skipped = 0; $same = 0; $failed = @(); $needMerge = @()
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
        # 그래서 지나치기 전에 "정말 같은가"를 본다. 같으면 알릴 것이 없고,
        # 다르면 덮어쓰기가 아니라 병합이 필요한 상태다.
        $delta = Compare-SkillDir $src $link
        if ($null -eq $delta) {
          $same++
        } else {
          $needMerge += [pscustomobject]@{ Skill = $name; Path = $link; Delta = $delta }
        }
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

# 린터는 선택 설치다. 스킬과 달리 설치처에서 고칠 것이 아니라 그대로 쓰는
# 도구이므로, 이미 있으면 말없이 최신본으로 덮어쓴다.
if ($WithLinter) {
  if (-not (Test-Path $ToolsDir)) { New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null }
  # 정본은 스킬 안에 있다. tools\check_skill.py 는 그리로 넘기는 런처라
  # 그것을 복사하면 설치처에서 경로를 못 찾는다.
  $linter = Join-Path $Root "skills\skillcraft\portable-skill-authoring\scripts\check_skill.py"
  if (-not (Test-Path $linter)) { throw "린터를 찾을 수 없습니다: $linter" }
  Copy-Item -Path $linter -Destination (Join-Path $ToolsDir "check_skill.py") -Force
  if (Test-Path (Join-Path $ToolsDir "check_skill.py")) {
    Write-Host ("린터 설치: {0}\check_skill.py" -f $ToolsDir)
  } else {
    $failed += "$ToolsDir\check_skill.py  (린터 복사 실패)"
  }
}

if ($Workflow) { Set-Content -Path $Marker -Value $wf.id -Encoding utf8 }
if ($packIds.Count -gt 0) {
  # 이번에 설치한 것만 적지 않는다 — 전에 깔아 둔 팩이 지워진 것처럼 보이므로 합친다.
  $prev = @()
  if (Test-Path $PackMarker) { $prev = (Get-Content $PackMarker -Raw).Trim() -split "\s*,\s*" }
  $all = @($prev + $packIds | Where-Object { $_ } | Sort-Object -Unique)
  Set-Content -Path $PackMarker -Value ($all -join ", ") -Encoding utf8
}
Write-Host ""
Write-Host ("설치: {0}" -f ($chosen -join " + "))
Write-Host ("  복사 {0}개, {1}개 건너뜀(같음 {2} · 변경됨 {3}), {4}개 실패" -f `
  $copied, $skipped, $same, $needMerge.Count, $failed.Count)
Write-Host ("  대상: {0} / {1}" -f $ClaudeDir, $AgentsDir)
Write-Host ("  스킬: {0}" -f (($targets | ForEach-Object { Split-Path $_ -Leaf }) -join ", "))

if ($needMerge.Count -gt 0) {
  Write-Host ""
  Write-Host "🔴 병합이 필요합니다 — 설치처 내용이 레포와 다릅니다:" -ForegroundColor Yellow
  foreach ($m in $needMerge) {
    Write-Host ("  - {0}" -f $m.Skill) -ForegroundColor Yellow
    Write-Host ("      {0}" -f $m.Delta)
    Write-Host ("      {0}" -f $m.Path) -ForegroundColor DarkGray
  }
  Write-Host ""
  Write-Host "설치처에서 고친 것일 수도, 레포가 앞서 나간 것일 수도 있습니다." -ForegroundColor Yellow
  Write-Host "🔴 -Force 로 덮어쓰지 마십시오 — 설치처의 수정이 사라지고 되돌릴 수 없습니다." -ForegroundColor Yellow
  Write-Host "   skills/_core/harness-repo 의 가져오기 절차를 쓰십시오. 새 것 / 다른 것 /" -ForegroundColor Yellow
  Write-Host "   설치처에만 있는 것으로 갈라 필요한 것만 병합합니다." -ForegroundColor Yellow
  Write-Host ""
}

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
