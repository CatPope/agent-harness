$ErrorActionPreference = "Stop"

# 🔴 bash 는 UTF-8 로 출력하고, PowerShell 은 그것을 콘솔 코드페이지(한국어 Windows 는 cp949)로
#    디코드한다. 그러면 "복사 2개" 가 깨진 채 비교돼 sh 쪽 단정이 전부 실패한다 — 코드페이지가
#    다른 콘솔에서는 통과하므로(2026-09-22 Codex 실행) 환경에 따라 결과가 갈리는 테스트였다.
#    디코딩을 여기서 고정해 어느 콘솔에서든 같은 결과가 나오게 한다.
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8

$root = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { (Get-Location).Path }
Set-Location $root

$tempUnix = (& bash -lc 'mktemp -d -t agent-harness-verify.XXXXXX').Trim()
if (-not $tempUnix) { throw "Git Bash did not create a system temp directory." }
$tempRoot = (& bash -lc "cygpath -w '$tempUnix'").Trim()
if (-not $tempRoot) { throw "Could not resolve the Windows temp path: $tempUnix" }

Write-Output "TEMP_ROOT=$tempRoot ($tempUnix)"

function New-TestProject([string]$name) {
  $path = Join-Path $tempRoot $name
  New-Item -ItemType Directory -Path $path -Force | Out-Null
  return $path
}

function Get-BashPath([string]$path) {
  return "$tempUnix/$(Split-Path $path -Leaf)"
}

function Assert-True([bool]$condition, [string]$message) {
  if (-not $condition) { throw "ASSERTION FAILED: $message" }
}

function Invoke-Checked([string]$name, [scriptblock]$command) {
  $oldPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $output = @(& $command 2>&1 | ForEach-Object { $_.ToString() })
  $code = $LASTEXITCODE
  $ErrorActionPreference = $oldPreference
  Write-Host "COMMAND[$name] exit=$code"
  $output |
    Where-Object { $_ -match 'CLAUDE.md|[0-9]+.*[0-9]+|WARNING:|ghost-|implementation' } |
    ForEach-Object { Write-Host "  $_" }
  if ($code -ne 0) { throw "COMMAND FAILED [$name]`n$($output -join "`n")" }
  return ,$output
}

function Write-Utf8NoBom([string]$path, [string]$text) {
  $parent = Split-Path $path -Parent
  if (-not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
  [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
}

function Get-FromLines([string]$path) {
  return @((Get-Content -Encoding UTF8 $path) | Where-Object { $_ -like '<!-- from: *' })
}

function Assert-NoBom([string]$path, [string]$label) {
  $bytes = [IO.File]::ReadAllBytes($path)
  $hasBom = $bytes.Length -ge 3 -and
    $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
  Assert-True (-not $hasBom) "$label has a UTF-8 BOM"
}

function Assert-MergedClaudeMd([string]$project, [string]$label) {
  $path = Join-Path $project "CLAUDE.md"
  $bytes = [IO.File]::ReadAllBytes($path)
  $hasBom = $bytes.Length -ge 3 -and
    $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
  Assert-True $hasBom "$label did not preserve the original BOM"
  $text = [Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
  Assert-True (([regex]::Matches($text, '<!-- agent-harness:begin -->')).Count -eq 1) "$label begin marker count"
  Assert-True (([regex]::Matches($text, '<!-- agent-harness:end -->')).Count -eq 1) "$label end marker count"
  Assert-True ($text.StartsWith("BEFORE`n")) "$label changed text before the block"
  Assert-True ($text.EndsWith("`nAFTER`n")) "$label changed text after the block"
  Assert-NoBom (Join-Path $project ".claude/harness-CLAUDE.md") "$label fragment output"
}

function Invoke-ShInstall([string]$name, [string[]]$arguments) {
  return Invoke-Checked $name { & bash ./install.sh @arguments }
}

function Invoke-PsInstall([string]$name, [string[]]$arguments) {
  return Invoke-Checked $name {
    & powershell -NoProfile -ExecutionPolicy Bypass -File ./install.ps1 @arguments
  }
}

# 1, 7: pack accumulation and no _core for a pack-only installation.
$shPack = New-TestProject "sh-pack"
$psPack = New-TestProject "ps-pack"
Invoke-ShInstall "sh pack documents" @("--project", (Get-BashPath $shPack), "--pack", "documents") | Out-Null
Invoke-ShInstall "sh pack skillcraft" @("--project", (Get-BashPath $shPack), "--pack", "skillcraft") | Out-Null
Invoke-PsInstall "ps pack documents" @("-Project", $psPack, "-Pack", "documents") | Out-Null
Invoke-PsInstall "ps pack skillcraft" @("-Project", $psPack, "-Pack", "skillcraft") | Out-Null
$expectedPack = @(
  '<!-- from: claude/packs/documents.md -->',
  '<!-- from: claude/packs/skillcraft.md -->'
)
foreach ($pair in @(@("sh", $shPack), @("ps", $psPack))) {
  $from = Get-FromLines (Join-Path $pair[1] ".claude/harness-CLAUDE.md")
  Assert-True (($from -join "|") -eq ($expectedPack -join "|")) "$($pair[0]) pack accumulation/order"
  Assert-True (-not (($from -join "|") -match 'claude/_core.md')) "$($pair[0]) pack-only included _core"
  $marker = Join-Path $pair[1] ".claude/skills/.agent-harness-packs"
  Assert-True ((Get-Content -Raw $marker).Trim() -eq "documents, skillcraft") "$($pair[0]) pack marker format"
  Assert-NoBom $marker "$($pair[0]) pack marker"
}
Write-Output "PASS[1] sh/ps from-lines=$($expectedPack -join ', ')"
Write-Output "PASS[7] pack-only outputs omit claude/_core.md"

# 2, 3: topics accumulate, deduplicate, and remain BOM-free.
$shTopic = New-TestProject "sh-topic"
$psTopic = New-TestProject "ps-topic"
Write-Utf8NoBom (Join-Path $shTopic ".claude/skills/.agent-harness-active") "supervisor-worker"
Write-Utf8NoBom (Join-Path $psTopic ".claude/skills/.agent-harness-active") "supervisor-worker"
Invoke-ShInstall "sh topic first" @("--project", (Get-BashPath $shTopic), "--pack", "skillcraft", "--topic", "implementation") | Out-Null
Invoke-ShInstall "sh topic duplicate" @("--project", (Get-BashPath $shTopic), "--pack", "skillcraft", "--topic", "implementation") | Out-Null
Invoke-ShInstall "sh topic omitted" @("--project", (Get-BashPath $shTopic), "--pack", "skillcraft") | Out-Null
Invoke-PsInstall "ps topic first" @("-Project", $psTopic, "-Pack", "skillcraft", "-Topic", "implementation") | Out-Null
Invoke-PsInstall "ps topic duplicate" @("-Project", $psTopic, "-Pack", "skillcraft", "-Topic", "implementation") | Out-Null
Invoke-PsInstall "ps topic omitted" @("-Project", $psTopic, "-Pack", "skillcraft") | Out-Null
foreach ($pair in @(@("sh", $shTopic), @("ps", $psTopic))) {
  $marker = Join-Path $pair[1] ".claude/skills/.agent-harness-topics"
  Assert-True ((Get-Content -Raw $marker).Trim() -eq "implementation") "$($pair[0]) topic marker format/deduplication"
  Assert-NoBom $marker "$($pair[0]) topic marker"
  $from = Get-FromLines (Join-Path $pair[1] ".claude/harness-CLAUDE.md")
  Assert-True ($from[-1] -eq '<!-- from: claude/topics/implementation.md -->') "$($pair[0]) topic persistence"
}
Write-Output "PASS[2] topic survived rerun without topic option (sh/ps)"
Write-Output "PASS[3] topic marker=implementation; no duplicate; no BOM; pack marker=documents, skillcraft"

# 4: project and overridden-global status both expose the topic marker.
$shProjectStatus = Invoke-ShInstall "sh project status" @("--project", (Get-BashPath $shTopic), "--status")
$psProjectStatus = Invoke-PsInstall "ps project status" @("-Project", $psTopic, "-Status")
Assert-True (($shProjectStatus -join "`n") -match 'implementation') "sh project status topic"
Assert-True (($psProjectStatus -join "`n") -match 'implementation') "ps project status topic"

$shGlobal = New-TestProject "sh-global"
$env:CLAUDE_SKILLS_DIR = Join-Path $shGlobal "claude/skills"
$env:AGENTS_SKILLS_DIR = Join-Path $shGlobal "agents/skills"
$env:CLAUDE_TOOLS_DIR = Join-Path $shGlobal "claude/tools"
Write-Utf8NoBom (Join-Path $env:AGENTS_SKILLS_DIR ".agent-harness-topics") "implementation"
$shGlobalStatus = Invoke-ShInstall "sh global status overridden" @("--status")
Remove-Item Env:CLAUDE_SKILLS_DIR -ErrorAction SilentlyContinue
Remove-Item Env:AGENTS_SKILLS_DIR -ErrorAction SilentlyContinue
Remove-Item Env:CLAUDE_TOOLS_DIR -ErrorAction SilentlyContinue

$psGlobal = New-TestProject "ps-global"
$psClaude = Join-Path $psGlobal "claude/skills"
$psAgents = Join-Path $psGlobal "agents/skills"
Write-Utf8NoBom (Join-Path $psAgents ".agent-harness-topics") "implementation"
$psGlobalStatus = Invoke-PsInstall "ps global status overridden" @(
  "-ClaudeDir", $psClaude, "-AgentsDir", $psAgents, "-Status"
)
Assert-True (($shGlobalStatus -join "`n") -match 'implementation') "sh global status topic"
Assert-True (($psGlobalStatus -join "`n") -match 'implementation') "ps global status topic"
Write-Output "PASS[4] project/global status prints topic for sh/ps (global dirs overridden)"

# 5: identical marker state produces byte-identical assembled output.
$shParity = New-TestProject "sh-parity"
$psParity = New-TestProject "ps-parity"
Write-Utf8NoBom (Join-Path $shParity ".claude/skills/.agent-harness-active") "supervisor-worker"
Write-Utf8NoBom (Join-Path $psParity ".claude/skills/.agent-harness-active") "supervisor-worker"
Invoke-ShInstall "sh parity base" @("--project", (Get-BashPath $shParity), "--pack", "skillcraft", "--topic", "implementation") | Out-Null
Invoke-ShInstall "sh parity add pack" @("--project", (Get-BashPath $shParity), "--pack", "documents") | Out-Null
Invoke-PsInstall "ps parity base" @("-Project", $psParity, "-Pack", "skillcraft", "-Topic", "implementation") | Out-Null
Invoke-PsInstall "ps parity add pack" @("-Project", $psParity, "-Pack", "documents") | Out-Null
$shMd5 = (Get-FileHash -Algorithm MD5 (Join-Path $shParity ".claude/harness-CLAUDE.md")).Hash
$psMd5 = (Get-FileHash -Algorithm MD5 (Join-Path $psParity ".claude/harness-CLAUDE.md")).Hash
Assert-True ($shMd5 -eq $psMd5) "MD5 differs: sh=$shMd5 ps=$psMd5"
Write-Output "PASS[5] MD5 sh=$shMd5 ps=$psMd5"

# 6: merging three times remains idempotent and preserves outside text/BOM.
$shMerge = New-TestProject "sh-merge"
$psMerge = New-TestProject "ps-merge"
Write-Utf8NoBom (Join-Path $shMerge ".claude/skills/.agent-harness-active") "supervisor-worker"
Write-Utf8NoBom (Join-Path $psMerge ".claude/skills/.agent-harness-active") "supervisor-worker"
foreach ($project in @($shMerge, $psMerge)) {
  $initial = "BEFORE`n<!-- agent-harness:begin -->`nstale`n<!-- agent-harness:end -->`nAFTER`n"
  $bytes = [byte[]](0xEF, 0xBB, 0xBF) + [Text.Encoding]::UTF8.GetBytes($initial)
  [IO.File]::WriteAllBytes((Join-Path $project "CLAUDE.md"), $bytes)
}
1..3 | ForEach-Object {
  Invoke-ShInstall "sh merge run $_" @("--project", (Get-BashPath $shMerge), "--pack", "documents", "--with-claude-md") | Out-Null
}
1..3 | ForEach-Object {
  Invoke-PsInstall "ps merge run $_" @("-Project", $psMerge, "-Pack", "documents", "-WithClaudeMd") | Out-Null
}
Assert-MergedClaudeMd $shMerge "sh"
Assert-MergedClaudeMd $psMerge "ps"
Write-Output "PASS[6] sh/ps: 3 runs, one block, outside preserved, original BOM preserved, output no BOM"

# 8: stale marker ids warn but do not abort installation.
$shFake = New-TestProject "sh-fake"
$psFake = New-TestProject "ps-fake"
foreach ($project in @($shFake, $psFake)) {
  Write-Utf8NoBom (Join-Path $project ".claude/skills/.agent-harness-packs") "ghost-pack"
  Write-Utf8NoBom (Join-Path $project ".claude/skills/.agent-harness-topics") "ghost-topic"
}
$shFakeOutput = Invoke-ShInstall "sh fake marker ids" @("--project", (Get-BashPath $shFake), "--pack", "documents")
$psFakeOutput = Invoke-PsInstall "ps fake marker ids" @("-Project", $psFake, "-Pack", "documents")
Assert-True (($shFakeOutput -join "`n") -match 'ghost-pack' -and ($shFakeOutput -join "`n") -match 'ghost-topic') "sh fake marker warnings"
Assert-True (($psFakeOutput -join "`n") -match 'ghost-pack' -and ($psFakeOutput -join "`n") -match 'ghost-topic') "ps fake marker warnings"
Write-Output "PASS[8] sh/ps warned for ghost-pack and ghost-topic and exited 0"

# 9: a manifest whose claude field is null contributes no fragment and no warning.
$shNull = New-TestProject "sh-null"
$psNull = New-TestProject "ps-null"
Write-Utf8NoBom (Join-Path $shNull ".claude/skills/.agent-harness-active") "codex-review"
Write-Utf8NoBom (Join-Path $psNull ".claude/skills/.agent-harness-active") "codex-review"
$shNullOutput = Invoke-ShInstall "sh null claude marker" @("--project", (Get-BashPath $shNull), "--pack", "documents")
$psNullOutput = Invoke-PsInstall "ps null claude marker" @("-Project", $psNull, "-Pack", "documents")
foreach ($case in @(@("sh", $shNull, $shNullOutput), @("ps", $psNull, $psNullOutput))) {
  $from = Get-FromLines (Join-Path $case[1] ".claude/harness-CLAUDE.md")
  $expected = '<!-- from: claude/_core.md -->|<!-- from: claude/packs/documents.md -->'
  Assert-True (($from -join "|") -eq $expected) "$($case[0]) null fragment result"
}
Write-Output "PASS[9] claude:null skipped quietly for sh/ps"

# 10: copy counts, identical rerun skipping, and list output remain intact.
$shRegression = New-TestProject "sh-regression"
$psRegression = New-TestProject "ps-regression"
$shFirst = Invoke-ShInstall "sh regression first" @("--project", (Get-BashPath $shRegression), "--pack", "documents")
$shAgain = Invoke-ShInstall "sh regression rerun" @("--project", (Get-BashPath $shRegression), "--pack", "documents")
$psFirst = Invoke-PsInstall "ps regression first" @("-Project", $psRegression, "-Pack", "documents")
$psAgain = Invoke-PsInstall "ps regression rerun" @("-Project", $psRegression, "-Pack", "documents")
$shListProject = New-TestProject "sh-list"
$psListProject = New-TestProject "ps-list"
$shList = Invoke-ShInstall "sh list" @("--project", (Get-BashPath $shListProject), "--list")
$psList = Invoke-PsInstall "ps list" @("-Project", $psListProject, "-List")
$firstCopyPattern = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('67O17IKsIDLqsJw='))
$sameSkipPattern = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('67O17IKsIDDqsJwsIDLqsJwg6rG064SI65yAKOqwmeydjCAy'))
Assert-True (($shFirst -join "`n").Contains($firstCopyPattern)) "sh first copy count"
Assert-True (($psFirst -join "`n").Contains($firstCopyPattern)) "ps first copy count"
Assert-True (($shAgain -join "`n").Contains($sameSkipPattern)) "sh identical rerun"
Assert-True (($psAgain -join "`n").Contains($sameSkipPattern)) "ps identical rerun"
foreach ($output in @($shList, $psList)) {
  $joined = $output -join "`n"
  Assert-True ($joined -match 'supervisor-worker' -and $joined -match 'documents' -and $joined -match 'implementation') "list output"
}
Write-Output "PASS[10] sh/ps first copy=2; rerun copy=0 skip=2 same=2; list includes workflow/pack/topic"

Write-Output "FUNCTIONAL_TESTS_PASS temp=$tempRoot"
