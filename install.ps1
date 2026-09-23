<#
  agent-harness installer (Windows / PowerShell 5.1+)

  .\install.ps1 -List
  .\install.ps1 -Workflow supervisor-worker
  .\install.ps1 -Status
  .\install.ps1 -Workflow supervisor-worker -WithLinter
  .\install.ps1 -Pack documents,skillcraft
  .\install.ps1 -Project . -Workflow supervisor-worker   <- 권장
  .\install.ps1 -Project . -Workflow supervisor-worker -Topic implementation

  -Project <path>: RECOMMENDED. Installs into that folder's .claude\skills
  only, instead of the two global stores. The skills then belong to one
  project: what you adapt there stays there, and another project's harness is
  not rewritten by this one. Global install is for skills you want everywhere.

  The path is a required argument on purpose - there is no default. Installing
  into the wrong folder is easy to do and hard to notice, so even the current
  folder must be spelled out as `-Project .`.

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

  CLAUDE.md fragments: the chosen workflow, packs and topics also contribute
  CLAUDE.md fragments (the claude/ folder in this repo). They are assembled in a
  fixed order - _core, workflow, packs, topics - and written to
  <base>/harness-CLAUDE.md, which you then reference from your own CLAUDE.md.
  Your CLAUDE.md is NOT touched unless you pass -WithClaudeMd, which writes the
  same text into it inside an idempotent begin/end marker block.

  What gets assembled is not "the options you gave this time" but "what the
  markers say is installed". The markers are written first, so this run's
  options are already in them. Install -Pack documents today and -Pack
  skillcraft tomorrow and you get both fragments, because both packs' skills
  are in fact sitting in the store.

  -Topic <name>: picks claude/topics/<name>.md. Topics contribute a fragment
  only - they bring no skills - so they are given together with a workflow or a
  pack, not on their own.

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
  # CLAUDE.md 조각만 고르는 축. 워크플로우·팩과 무관하며 스킬을 끌고 오지 않는다.
  # claude/topics/<name>.md 를 가리킨다. 여러 개 줄 수 있다.
  [string[]]$Topic,
  [switch]$List,
  [switch]$Status,
  # 🔴 권장하지 않는다. 설치처 폴더를 지우고 레포 것으로 덮어쓴다.
  #    설치처에서 고친 내용이 사라지고, 복사본에는 이력이 없어 되돌릴 수 없다.
  #    갱신이 목적이면 skills/_core/harness-repo 의 가져오기 절차를 쓴다.
  [switch]$Force,
  # 선택 설치. 포터빌리티 린터(tools/check_skill.py)를 설치처에도 둔다.
  # 없어도 스킬은 정상 동작한다 — 스킬을 고칠 사람만 필요하다.
  [switch]$WithLinter,
  # 선택. 조립한 CLAUDE.md 조각을 대상 CLAUDE.md 끝의 마커 블록에 직접 반영한다.
  # 🔴 기본값은 사용자 파일을 건드리지 않는다 -- 별도 파일로 떨구고 참조를 안내만 한다.
  [switch]$WithClaudeMd,
  # 권장. 전역 두 스토어 대신 이 폴더의 .claude\skills 한 곳에만 설치한다.
  # 그 프로젝트에서 고친 스킬이 다른 프로젝트로 새지 않는다.
  # 🔴 경로는 필수다 — 기본값을 두면 엉뚱한 폴더에 까는 사고가 난다.
  #    현재 폴더에 깔 때도 '.' 를 명시해야 한다.
  [string]$Project,
  [string]$ClaudeDir = "$HOME\.claude\skills",
  [string]$AgentsDir = "$HOME\.agents\skills",
  [string]$ToolsDir  = "$HOME\.claude\tools"
)

$ErrorActionPreference = "Stop"
$Root   = $PSScriptRoot

# 설치처를 여기서 한 번만 정한다. 아래 코드는 $Stores 만 본다.
if ($PSBoundParameters.ContainsKey('Project')) {
  if ([string]::IsNullOrWhiteSpace($Project)) {
    throw "-Project 에 경로가 필요합니다. 현재 폴더라면 -Project . 로 명시하세요."
  }
  if ($PSBoundParameters.ContainsKey('ClaudeDir') -or $PSBoundParameters.ContainsKey('AgentsDir')) {
    throw "-Project 와 -ClaudeDir/-AgentsDir 는 함께 쓸 수 없습니다 — 설치처가 둘로 갈립니다."
  }
  # 🔴 없는 폴더를 만들어 주지 않는다. 오타면 빈 폴더가 생기고,
  #    사용자는 깔렸다고 믿은 채 아무 스킬도 없는 곳에서 일하게 된다.
  if (-not (Test-Path -LiteralPath $Project -PathType Container)) {
    throw "폴더가 없습니다: $Project  (경로를 확인하세요 — 만들어 주지 않습니다)"
  }
  $ProjectRoot = (Resolve-Path -LiteralPath $Project).Path
  $Stores      = @((Join-Path (Join-Path $ProjectRoot ".claude") "skills"))
  $MarkerDir   = $Stores[0]
  # 조각 산출물은 .claude/ 안에, 대상 CLAUDE.md 는 프로젝트 루트에 있다.
  $ClaudeMdBase   = Join-Path $ProjectRoot ".claude"
  $ClaudeMdTarget = Join-Path $ProjectRoot "CLAUDE.md"
  # 린터도 프로젝트 안으로. 명시로 준 경우는 그것을 존중한다.
  if (-not $PSBoundParameters.ContainsKey('ToolsDir')) {
    $ToolsDir = Join-Path (Join-Path $ProjectRoot ".claude") "tools"
  }
} else {
  $Stores    = @($ClaudeDir, $AgentsDir)
  # 🔴 전역 설치의 마커 위치는 건드리지 않는다. 옮기면 이미 깔려 있는 설치가
  #    -Status 에서 "설치 안 됨" 으로 보인다.
  $MarkerDir = $AgentsDir
  # 🔴 전역일 때의 CLAUDE.md 자리는 반드시 $ClaudeDir 에서 유도한다. $HOME 을 직접
  #    박으면 -ClaudeDir 로 임시 폴더를 줘도 실제 홈의 CLAUDE.md 를 건드리게 되어
  #    안전하게 시험할 방법이 없어진다. 기본값 기준으로는 ~/.claude/CLAUDE.md 다.
  $ClaudeMdBase   = Split-Path $ClaudeDir -Parent
  $ClaudeMdTarget = Join-Path $ClaudeMdBase "CLAUDE.md"
}
# 조립 결과를 떨구는 자리. 사용자 파일이 아니므로 설치기가 통째로 다시 쓴다.
$FragmentOut = Join-Path $ClaudeMdBase "harness-CLAUDE.md"
$Marker     = Join-Path $MarkerDir ".agent-harness-active"
$PackMarker = Join-Path $MarkerDir ".agent-harness-packs"
# 토픽 마커. 팩 마커와 같은 자리·같은 형식·같은 병합 규칙이다.
# 조립이 "무엇이 깔려 있는가"를 마커에서 읽으므로, 스킬을 끌고 오지 않는 토픽도
# 기록이 남아야 다음 설치에서 살아남는다. CLI 옵션이 아니라 내부 상태다.
$TopicMarker = Join-Path $MarkerDir ".agent-harness-topics"

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

# 조각의 첫 제목 줄을 목록에 보여줄 한 줄로 쓴다.
function Get-FragmentTitle($path) {
  foreach ($line in (Get-Content $path -Encoding UTF8)) {
    if ($line -match '^#+\s*(.+)$') { return $Matches[1] }
  }
  return ""
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
  $topicDir = Join-Path $Root "claude/topics"
  if (Test-Path $topicDir) {
    Write-Host "토픽 — CLAUDE.md 조각만 기여합니다. 스킬은 오지 않습니다"
    Write-Host ""
    foreach ($tf in (Get-ChildItem $topicDir -Filter *.md | Where-Object { $_.Name -ne "README.md" })) {
      Write-Host ("  {0,-20} {1}" -f $tf.BaseName, (Get-FragmentTitle $tf.FullName))
    }
    Write-Host ""
  }
  Write-Host "설치:  .\install.ps1 -Workflow <id>"
  Write-Host "       .\install.ps1 -Pack <id>[,<id>]"
  Write-Host "       .\install.ps1 -Workflow <id> -Topic <name>"
  Write-Host ""
  Write-Host "권장 — 프로젝트 한 곳에만:"
  Write-Host "       .\install.ps1 -Project <path> -Workflow <id>"
  Write-Host "       그 폴더의 .claude\skills 에만 깔립니다. 거기서 고친 스킬이"
  Write-Host "       다른 프로젝트로 새지 않습니다. 경로는 필수 — 현재 폴더도 '.' 로 씁니다."
  Write-Host "       전역(모든 프로젝트)에 두고 싶은 스킬만 -Project 없이 설치하세요."
  return
}

if ($Status) {
  Write-Host ("설치처: " + ($Stores -join " / "))
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
  if (Test-Path $TopicMarker) {
    Write-Host ("설치한 토픽: " + (Get-Content $TopicMarker -Raw).Trim())
  } else {
    Write-Host "설치한 토픽 없음"
  }
  return
}

if (-not $Workflow -and -not $Pack) {
  throw "-Workflow <id> 또는 -Pack <id> 를 지정하거나, -List 로 목록을 보세요. (-Topic 은 조각만 기여하므로 단독으로 쓸 수 없습니다)"
}

$targets  = @()
$chosen   = @()
$topicIds = @()
# 조각 목록은 여기서 만들지 않는다. 마커를 다 쓴 뒤 Get-FragmentsFromMarkers 가
# 마커를 보고 만든다 — 조립 순서는 _core -> 워크플로우 -> 팩 -> 토픽 으로 고정이다.
$fragments = @()

# 매니페스트가 조각을 가리키지 않아도, 가리킨 파일이 없어도 설치는 계속된다.
# 레포 쪽 어긋남은 CI(tools/check_manifests.py 의 M6·M7)가 잡을 일이지
# 설치를 막을 일이 아니다.
function Resolve-Fragment($rel) {
  if (-not $rel) { return $null }
  if (Test-Path -LiteralPath (Join-Path $Root $rel)) { return $rel }
  Write-Warning ("CLAUDE.md 조각을 찾지 못해 건너뜁니다: {0}" -f $rel)
  return $null
}

# 무엇을 조립할지는 **마커가** 정한다 — 이번에 준 옵션이 아니다.
#
# 🔴 옵션만 보면 설치처 상태와 배포된 규칙이 어긋난다. -Pack documents 로 깔고
#    다음에 -Pack skillcraft 로 깔면 documents 스킬은 폴더에 그대로 있는데
#    그 규칙만 조용히 사라졌다. 마커는 누적되는데 조각은 누적되지 않았기 때문이다.
#    그래서 조립의 근거를 "무엇이 깔려 있는가"(=마커)로 옮긴다.
# 마커는 이 함수를 부르기 전에 이미 갱신돼 있다. 이번에 준 것도 그래서 여기 들어 있다.
#
# 마커에 있는데 레포에 매니페스트나 조각이 없으면 경고 한 줄을 내고 그것만 건너뛴다.
# 설치를 실패시키지 않는다 — 조각 하나 때문에 스킬 설치까지 막을 일은 아니다.
function Get-FragmentsFromMarkers {
  $out = @()
  if (Test-Path -LiteralPath $Marker) {
    $wfid = @(Read-MarkerList $Marker)[0]
    # _core 조각은 _core 스킬과 같은 규칙이다 — 워크플로우가 깔려 있을 때만 따라온다.
    # 팩만 깐 설치처에는 붙지 않는다. 없는 스킬을 가리키는 규칙을 남기지 않는다.
    $f = Resolve-Fragment "claude/_core.md"; if ($f) { $out += $f }
    if ($wfid) {
      $w = Get-Workflows | Where-Object { $_.id -eq $wfid }
      if ($w) {
        # claude 필드가 없으면 $null 이 와서 조용히 건너뛴다 — 조각은 선택이다.
        $f = Resolve-Fragment $w.claude; if ($f) { $out += $f }
      } else {
        Write-Warning ("마커의 워크플로우 매니페스트가 없어 조각을 건너뜁니다: workflows/{0}.json" -f $wfid)
      }
    }
  }
  # 팩·토픽은 마커에 적힌 순서(정렬된 순서) 그대로 붙인다.
  foreach ($id in (Read-MarkerList $PackMarker)) {
    $pk = Get-Packs | Where-Object { $_.id -eq $id }
    if ($pk) {
      $f = Resolve-Fragment $pk.claude; if ($f) { $out += $f }
    } else {
      Write-Warning ("마커의 팩 매니페스트가 없어 조각을 건너뜁니다: packs/{0}.json" -f $id)
    }
  }
  foreach ($id in (Read-MarkerList $TopicMarker)) {
    # 토픽은 매니페스트가 없다 — 파일명이 곧 id 다. 없으면 Resolve-Fragment 가 경고한다.
    $f = Resolve-Fragment ("claude/topics/" + $id + ".md"); if ($f) { $out += $f }
  }
  return $out
}

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
  # 🔴 조각은 여기서 고르지 않는다. 마커를 쓴 뒤 Get-FragmentsFromMarkers 가 고른다.
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

# 토픽은 조각만 기여한다 — 스킬을 가져오지 않는다.
# 🔴 없는 이름은 거부한다. 오타를 조용히 넘기면 붙은 줄 알고 일하게 된다.
foreach ($topicId in $Topic) {
  if (-not $topicId) { continue }
  $rel = "claude/topics/" + $topicId + ".md"
  if (-not (Test-Path -LiteralPath (Join-Path $Root $rel))) {
    throw "알 수 없는 토픽: $topicId  ($rel 가 없습니다. -List 로 확인)"
  }
  $topicIds += $topicId
  $chosen   += ("토픽: " + $topicId)
}

foreach ($dir in $Stores) {
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
  foreach ($dir in $Stores) {
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

# 🔴 마커는 BOM 없이 쓴다. PowerShell 5.1 의 `Set-Content -Encoding utf8` 은 BOM 을
# 붙이는데, install.sh 는 그 파일을 cat 으로 읽어 `sort -u` 로 중복을 없앤다.
# BOM 이 붙으면 "documents" 와 "<BOM>documents" 가 서로 다른 항목으로 남아
# **두 설치기를 번갈아 쓸 때마다 팩 마커에 중복이 쌓인다.**
# 표시상의 문제가 아니라 기록이 망가지는 것이다. (2026-09-22 실측으로 확인)
# CLAUDE.md 조각 산출물도 같은 이유로 이 함수를 쓴다 — BOM 이 붙으면 두 설치기가
# 낸 결과가 바이트로 달라지고, 사용자 파일에 합칠 때 첫 줄에 보이지 않는 문자가 낀다.
function Write-Utf8NoBom($path, $text) {
  [IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))
}

# 마커 파일을 읽어 항목 배열로 낸다. 쉼표·공백은 털어낸다.
# 🔴 앞의 BOM 을 떼어낸다. 옛 버전이 BOM 을 붙여 쓴 마커가 남아 있을 수 있고,
#    그대로 읽으면 첫 항목이 "<BOM>documents" 가 되어 매니페스트도 조각도 못 찾는다.
function Read-MarkerList($path) {
  if (-not (Test-Path -LiteralPath $path)) { return @() }
  $raw = [IO.File]::ReadAllText($path, [Text.Encoding]::UTF8)
  if ($null -eq $raw) { return @() }
  $raw = $raw.Trim([char]0xFEFF + " `t`r`n")
  if (-not $raw) { return @() }
  return @($raw -split "\s*,\s*" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

# 이번에 준 것과 마커에 있던 것을 합쳐 다시 쓴다 — 쉼표+공백, 중복 제거, 정렬.
# 🔴 정렬은 Ordinal 이다. install.sh 는 LC_ALL=C sort 를 쓴다 — 문화권 정렬을 쓰면
#    하이픈이 든 id 에서 두 설치기의 순서가 갈리고 조립 결과가 바이트로 달라진다.
function Write-MarkerList($path, $ids) {
  $set = New-Object 'System.Collections.Generic.SortedSet[string]' ([System.StringComparer]::Ordinal)
  foreach ($x in (@(Read-MarkerList $path) + @($ids))) {
    $v = ([string]$x).Trim()
    if ($v) { [void]$set.Add($v) }
  }
  Write-Utf8NoBom $path (@($set) -join ", ")
}

$ClaudeMdBegin = "<!-- agent-harness:begin -->"
$ClaudeMdEnd   = "<!-- agent-harness:end -->"

# 조각을 정해진 순서로 잇는다. 각 조각 앞에 출처 한 줄을 남겨, 나중에 이 파일만 보고도
# 어느 파일에서 온 규칙인지 알 수 있게 한다.
function Build-ClaudeMd($relPaths) {
  $sb = New-Object System.Text.StringBuilder
  [void]$sb.Append("<!-- agent-harness 가 조립한 CLAUDE.md 조각입니다. 여기서 고치지 마십시오. -->`n")
  [void]$sb.Append("<!-- 고칠 곳은 <harness_repo>/claude/ 이고, 설치기를 다시 돌리면 통째로 다시 쓰입니다. -->`n")
  foreach ($rel in $relPaths) {
    $text = Get-Content -LiteralPath (Join-Path $Root $rel) -Raw -Encoding UTF8
    if ($null -eq $text) { $text = "" }
    $text = $text -replace "`r`n", "`n"
    [void]$sb.Append("`n<!-- from: $rel -->`n")
    [void]$sb.Append($text.TrimEnd("`n"))
    [void]$sb.Append("`n")
  }
  return $sb.ToString()
}

# 대상 CLAUDE.md 에 마커 블록으로 반영한다. 돌려주는 값은 무엇을 했는지 한 마디.
#
# 🔴 멱등이어야 한다. 두 번 돌리면 블록이 교체되지 쌓이면 안 된다.
# 🔴 블록 바깥은 한 글자도 바꾸지 않는다. BOM 이 있던 파일은 BOM 째로 돌려 놓는다 —
#    없애 버리는 것도 사용자 파일을 고친 것이다.
function Merge-ClaudeMdBlock($path, $body) {
  $block  = $ClaudeMdBegin + "`n" + $body + $ClaudeMdEnd + "`n"
  $hadBom = $false
  $old    = $null
  if (Test-Path -LiteralPath $path) {
    $bytes = [IO.File]::ReadAllBytes($path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
      $hadBom = $true
      $old = [Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
    } else {
      $old = [Text.Encoding]::UTF8.GetString($bytes)
    }
  }
  if ($null -eq $old) {
    $new = $block
    $how = "새로 만듦"
  } else {
    $s = $old.IndexOf($ClaudeMdBegin)
    $e = -1
    if ($s -ge 0) { $e = $old.IndexOf($ClaudeMdEnd, $s) }
    if ($s -ge 0 -and $e -gt $s) {
      $new = $old.Substring(0, $s) + $block.TrimEnd("`n") + $old.Substring($e + $ClaudeMdEnd.Length)
      $how = "블록 교체"
    } else {
      $sep = "`n`n"
      if ($old.EndsWith("`n")) { $sep = "`n" }
      $new = $old + $sep + $block
      $how = "끝에 덧붙임"
    }
  }
  [IO.File]::WriteAllText($path, $new, (New-Object System.Text.UTF8Encoding($hadBom)))
  return $how
}

# 마커는 복사가 끝난 직후에 적는다. 린터는 선택 설치라, 그쪽이 실패해도
# 스킬은 이미 놓였다. 뒤에 적으면 그 실패가 설치 기록까지 지워 -Status 가
# "설치하지 않았습니다" 라고 거짓말을 한다.
if ($Workflow) { Write-Utf8NoBom $Marker $wf.id }
# 이번에 설치한 것만 적지 않는다 — 전에 깔아 둔 것이 지워진 것처럼 보이므로 합친다.
if ($packIds.Count  -gt 0) { Write-MarkerList $PackMarker  $packIds }
if ($topicIds.Count -gt 0) { Write-MarkerList $TopicMarker $topicIds }

# 🔴 조립은 반드시 여기, 마커를 다 쓴 뒤다. 근거는 "이번에 준 옵션"이 아니라
#    "마커에 기록된 설치 상태"이므로, 마커가 최신이 아니면 조립도 틀린다.
$fragments = @(Get-FragmentsFromMarkers)

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

# CLAUDE.md 조각 — 스킬·린터와 달리 사용자가 읽는 파일 쪽 산출물이다.
# 🔴 기본은 사용자 파일을 건드리지 않는다. 별도 파일로 떨구고 참조를 안내할 뿐이며,
#    대상 CLAUDE.md 에 직접 넣는 것은 -WithClaudeMd 를 줬을 때뿐이다.
if ($fragments.Count -gt 0) {
  if (-not (Test-Path $ClaudeMdBase)) { New-Item -ItemType Directory -Path $ClaudeMdBase -Force | Out-Null }
  $body = Build-ClaudeMd $fragments
  Write-Utf8NoBom $FragmentOut $body
  Write-Host ""
  Write-Host ("CLAUDE.md 조각: {0}  (조각 {1}장)" -f $FragmentOut, $fragments.Count)
  foreach ($fr in $fragments) { Write-Host ("    {0}" -f $fr) -ForegroundColor DarkGray }
  if ($WithClaudeMd) {
    $how = Merge-ClaudeMdBlock $ClaudeMdTarget $body
    Write-Host ("  반영: {0}  ({1})" -f $ClaudeMdTarget, $how)
  } else {
    Write-Host "  이 파일은 설치기가 다시 씁니다 — 고칠 곳은 <harness_repo>/claude/ 입니다."
    Write-Host ("  당신의 CLAUDE.md 에서 이 파일을 참조하십시오: {0}" -f $ClaudeMdTarget)
    Write-Host "  -WithClaudeMd 를 주면 그 CLAUDE.md 의 마커 블록에 직접 반영합니다."
  }
}

# 훅 — 하네스 셋 중 "안 읽어도 막히는" 층. 스킬·조각처럼 파일만 떨구고,
# settings.json 은 사람이 합친다 (사용자 설정 파일은 자동으로 건드리지 않는다).
# 린터처럼 설치처에서 고칠 것이 아니라 그대로 쓰는 도구이므로 말없이 최신본으로 덮어쓴다.
$HooksSrc = Join-Path $Root "hooks"
$HooksOut = Join-Path $ClaudeMdBase "hooks"
if ((Test-Path $HooksSrc) -and (Get-ChildItem $HooksSrc -Filter *.py -File)) {
  if (-not (Test-Path $HooksOut)) { New-Item -ItemType Directory -Path $HooksOut -Force | Out-Null }
  $hooksN = 0
  $hookFiles = Get-ChildItem $HooksSrc -File | Where-Object { $_.Extension -eq ".py" -or $_.Name -eq "settings.fragment.json" }
  foreach ($hf in $hookFiles) {
    $dst = Join-Path $HooksOut $hf.Name
    if ($hf.Name -eq "settings.fragment.json" -and -not $PSBoundParameters.ContainsKey('Project')) {
      # 전역이면 훅 경로가 프로젝트 기준이 아니라 홈 기준이다
      $txt = Get-Content -LiteralPath $hf.FullName -Raw -Encoding UTF8
      $txt = $txt.Replace('$CLAUDE_PROJECT_DIR/.claude/hooks', '$HOME/.claude/hooks')
      Write-Utf8NoBom $dst $txt
    } else {
      Copy-Item -LiteralPath $hf.FullName -Destination $dst -Force
    }
    $hooksN++
  }
  Write-Host ""
  Write-Host ("훅: {0}  (파일 {1}개)" -f $HooksOut, $hooksN)
  $settingsPath = Join-Path $ClaudeMdBase "settings.json"
  $already = (Test-Path $settingsPath) -and ((Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8) -match 'agent-harness guard')
  if ($already) {
    Write-Host "  settings.json 에 이미 걸려 있습니다."
  } else {
    Write-Host ("  🔴 아직 켜지지 않았습니다. {0} 의 내용을" -f (Join-Path $HooksOut "settings.fragment.json")) -ForegroundColor Yellow
    Write-Host ("     {0} 에 합친 뒤 /hooks 를 열거나 세션을 다시 시작하십시오." -f $settingsPath) -ForegroundColor Yellow
  }
}

Write-Host ""
Write-Host ("설치: {0}" -f ($chosen -join " + "))
Write-Host ("  복사 {0}개, {1}개 건너뜀(같음 {2} · 변경됨 {3}), {4}개 실패" -f `
  $copied, $skipped, $same, $needMerge.Count, $failed.Count)
Write-Host ("  대상: {0}" -f ($Stores -join " / "))
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
