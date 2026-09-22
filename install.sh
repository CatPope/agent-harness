#!/usr/bin/env bash
# agent-harness installer (macOS / Linux)
#
#   ./install.sh --list
#   ./install.sh --workflow supervisor-worker
#   ./install.sh --status
#   ./install.sh --workflow supervisor-worker --with-linter
#   ./install.sh --pack documents --pack skillcraft
#   ./install.sh --project . --workflow supervisor-worker   <- 권장
#
# --project <path>: RECOMMENDED. Installs into that folder's .claude/skills
# only, instead of the two global stores. The skills then belong to one
# project: what you adapt there stays there. The path is a required argument
# on purpose - even the current folder must be spelled out as `--project .`.
#
# Copies the _core skills plus the chosen workflow's skills into both agent
# skill stores. On Windows use install.ps1 instead.
#
# A pack (--pack) is a topic bundle installed on its own: it brings only its own
# skills, not _core. Workflow and packs can be given together.
#
# Copies, not links. A link makes the install target and this repo the same
# files, so editing a skill while working on a project rewrites the shared
# original at once. Installing is one-way: repo -> install target.
set -euo pipefail
# 🔴 --project 의 상대 경로는 사용자가 이 스크립트를 부른 자리를 기준으로 읽어야 한다.
#    아래 cd 가 기준을 레포로 바꿔 버리므로, 그 전에 붙잡아 둔다.
INVOKE_CWD="$PWD"
cd "$(dirname "$0")"
ROOT="$(pwd)"

CLAUDE_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
AGENTS_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
TOOLS_DIR="${CLAUDE_TOOLS_DIR:-$HOME/.claude/tools}"
# 환경변수로 준 것은 --project 가 있어도 존중한다
TOOLS_DIR_SET=0; [ -n "${CLAUDE_TOOLS_DIR:-}" ] && TOOLS_DIR_SET=1
DIRS_SET=0
{ [ -n "${CLAUDE_SKILLS_DIR:-}" ] || [ -n "${AGENTS_SKILLS_DIR:-}" ]; } && DIRS_SET=1

WORKFLOW=""; DO_LIST=0; DO_STATUS=0; FORCE=0; WITH_LINTER=0
PROJECT=""; PROJECT_GIVEN=0
PACKS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --list)     DO_LIST=1 ;;
    --status)   DO_STATUS=1 ;;
    # 🔴 권장하지 않는다. 자세한 것은 README 의 "설치" 절과
    #    skills/_core/harness-repo 의 가져오기 절차를 보라.
    --force)    FORCE=1 ;;
    # 선택 설치. 포터빌리티 린터를 설치처에도 둔다.
    # 없어도 스킬은 정상 동작한다 — 스킬을 고칠 사람만 필요하다.
    --with-linter) WITH_LINTER=1 ;;
    --workflow) shift; WORKFLOW="${1:-}" ;;
    # 권장. 전역 두 스토어 대신 그 폴더의 .claude/skills 한 곳에만 설치한다.
    # 🔴 경로는 필수 — 기본값을 두면 엉뚱한 폴더에 까는 사고가 난다.
    --project)  shift; PROJECT="${1:-}"; PROJECT_GIVEN=1
                # 값을 빠뜨리면 다음 옵션을 경로로 삼켜 엉뚱한 곳에 깔릴 뻔한다
                case "$PROJECT" in --*) echo "--project 뒤에 경로가 와야 합니다 (받은 것: $PROJECT)" >&2; exit 2 ;; esac ;;
    # 주제별 묶음. 여러 번 주거나 쉼표로 이어 줄 수 있다.
    --pack)     shift; IFS=, read -r -a _p <<< "${1:-}"; PACKS+=("${_p[@]}") ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
  # 🔴 `|| true` 가 필요하다. 값을 받는 플래그가 맨 끝에 오면(--project 로 끝나는 등)
  #    case 안의 shift 가 이미 인자를 다 써서 여기서 shift 가 실패한다.
  #    set -e 가 그것을 잡아 **메시지 한 줄 없이 exit 1** 로 죽인다 —
  #    아래에 있는 "경로가 필요합니다" 같은 안내에 닿지도 못한다.
  #    (2026-09-22 Codex 검수가 찾았다. --project 만이 아니라 기존 플래그 전부 해당)
  shift || true
done

# 설치처를 여기서 한 번만 정한다. 아래 코드는 STORES 만 본다.
STORES=()
if [ "$PROJECT_GIVEN" = 1 ]; then
  [ -n "$PROJECT" ] || { echo "--project 에 경로가 필요합니다. 현재 폴더라면 --project . 로 명시하세요." >&2; exit 2; }
  [ "$DIRS_SET" = 0 ] || { echo "--project 와 CLAUDE_SKILLS_DIR/AGENTS_SKILLS_DIR 는 함께 쓸 수 없습니다 — 설치처가 둘로 갈립니다." >&2; exit 2; }
  case "$PROJECT" in
    /*) PROJECT_ROOT="$PROJECT" ;;
    *)  PROJECT_ROOT="$INVOKE_CWD/$PROJECT" ;;
  esac
  # 🔴 없는 폴더를 만들어 주지 않는다. 오타면 빈 폴더가 생기고,
  #    사용자는 깔렸다고 믿은 채 아무 스킬도 없는 곳에서 일하게 된다.
  [ -d "$PROJECT_ROOT" ] || { echo "폴더가 없습니다: $PROJECT_ROOT  (경로를 확인하세요 — 만들어 주지 않습니다)" >&2; exit 2; }
  PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
  STORES=("$PROJECT_ROOT/.claude/skills")
  MARKER_DIR="${STORES[0]}"
  [ "$TOOLS_DIR_SET" = 1 ] || TOOLS_DIR="$PROJECT_ROOT/.claude/tools"
else
  STORES=("$CLAUDE_DIR" "$AGENTS_DIR")
  # 🔴 전역 설치의 마커 위치는 건드리지 않는다. 옮기면 이미 깔려 있는 설치가
  #    --status 에서 "설치 안 됨" 으로 보인다.
  MARKER_DIR="$AGENTS_DIR"
fi
# 설치처가 하나일 수도 둘일 수도 있어, 보여 줄 때만 한 줄로 잇는다
stores_str () { printf '%s / ' "${STORES[@]}" | sed 's| / $||'; }
MARKER="$MARKER_DIR/.agent-harness-active"
PACK_MARKER="$MARKER_DIR/.agent-harness-packs"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

field () {  # field <json-file> <key>
  PYTHONIOENCODING=utf-8 "$PY" - "$1" "$2" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
v = d.get(sys.argv[2], "")
print(" ".join(v) if isinstance(v, list) else (v if v is not None else ""))
PYEOF
}

# 설치처가 레포와 실제로 다른지 본다. 같으면 DELTA 가 빈 문자열이다.
#
# 비교에서 빼는 것 — 파이썬 캐시, 수정 전 안전 사본, 설치처가 남기는 로컬 기록.
# 이것까지 세면 멀쩡한 설치처가 전부 "변경됨"으로 잡힌다.
DELTA=""
skill_delta () {  # skill_delta <레포 원본> <설치된 것>
  local out changed only_repo only_local total names bits
  out="$(diff -rq \
    --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='*.bak_*'     --exclude='기록' \
    "$1" "$2" 2>/dev/null || true)"
  if [ -z "$out" ]; then DELTA=""; return 0; fi

  total="$(printf '%s\n' "$out" | grep -c . || true)"
  changed="$(printf '%s\n' "$out" | grep -cE '^Files .* differ$' || true)"
  only_repo="$(printf '%s\n' "$out" | grep -cF "Only in $1" || true)"
  only_local=$(( total - changed - only_repo ))

  bits=""
  [ "$changed"    -gt 0 ] && bits="내용 다름 $changed"
  [ "$only_repo"  -gt 0 ] && bits="${bits:+$bits · }레포에만 $only_repo"
  [ "$only_local" -gt 0 ] && bits="${bits:+$bits · }설치처에만 $only_local"

  # 어느 파일인지 앞의 셋만 이름으로 보여준다
  names="$(printf '%s\n' "$out" \
    | sed -n 's/^Files \(.*\) and .* differ$/\1/p; s/^Only in .*: \(.*\)$/\1/p' \
    | sed 's#.*/##' | head -3 | tr '\n' ',' | sed 's/,$//; s/,/, /g')"
  DELTA="$bits  ($names)"
}

if [ "$DO_LIST" = 1 ]; then
  echo; echo "워크플로우 — _core 공통 스킬과 함께 설치됩니다"; echo
  for f in workflows/*.json; do
    printf "  %-20s [%s] %s\n" "$(field "$f" id)" "$(field "$f" status)" "$(field "$f" name)"
    printf "  %-20s   %s\n\n" "" "$(field "$f" summary)"
  done
  echo "팩 — 주제별 묶음. 자기 스킬만 설치합니다"; echo
  for f in packs/*.json; do
    [ -e "$f" ] || continue
    printf "  %-20s [%s] %s\n" "$(field "$f" id)" "$(field "$f" status)" "$(field "$f" name)"
    printf "  %-20s   %s\n\n" "" "$(field "$f" summary)"
  done
  echo "설치:  ./install.sh --workflow <id>"
  echo "       ./install.sh --pack <id> [--pack <id>]"; echo
  echo "권장 — 프로젝트 한 곳에만:"
  echo "       ./install.sh --project <path> --workflow <id>"
  echo "       그 폴더의 .claude/skills 에만 깔립니다. 거기서 고친 스킬이"
  echo "       다른 프로젝트로 새지 않습니다. 경로는 필수 — 현재 폴더도 '.' 로 씁니다."
  echo "       전역(모든 프로젝트)에 두고 싶은 스킬만 --project 없이 설치하세요."; echo
  exit 0
fi

if [ "$DO_STATUS" = 1 ]; then
  echo "설치처: $(stores_str)"
  if [ -f "$MARKER" ]; then echo "활성 워크플로우: $(cat "$MARKER")"
  else echo "활성 워크플로우 없음 (아직 설치하지 않았습니다)"; fi
  if [ -f "$PACK_MARKER" ]; then echo "설치한 팩: $(cat "$PACK_MARKER")"
  else echo "설치한 팩 없음"; fi
  exit 0
fi

if [ -z "$WORKFLOW" ] && [ "${#PACKS[@]}" -eq 0 ]; then
  echo "--workflow <id> 또는 --pack <id> 를 지정하거나, --list 로 목록을 보세요." >&2
  exit 2
fi

TARGETS=(); CHOSEN=()

# 워크플로우를 고르면 _core 공통 스킬이 함께 온다.
if [ -n "$WORKFLOW" ]; then
  MF="workflows/$WORKFLOW.json"
  [ -f "$MF" ] || { echo "알 수 없는 워크플로우: $WORKFLOW  (--list 로 확인)" >&2; exit 2; }
  ST="$(field "$MF" status)"
  [ "$ST" = "active" ] || { echo "'$WORKFLOW' 는 status=$ST 입니다. 아직 설치할 수 없습니다." >&2; exit 2; }
  for d in skills/_core/*/; do TARGETS+=("$ROOT/${d%/}"); done
  for s in $(field "$MF" skills); do
    p="$ROOT/skills/$WORKFLOW/$s"
    [ -d "$p" ] || { echo "매니페스트에 있으나 폴더가 없습니다: $p" >&2; exit 1; }
    TARGETS+=("$p")
  done
  CHOSEN+=("$(field "$MF" name)")
fi

# 팩은 자기 스킬만 가져온다. _core 를 끌고 오지 않는다.
PACK_IDS=()
for pk in "${PACKS[@]:-}"; do
  [ -n "$pk" ] || continue
  PF="packs/$pk.json"
  [ -f "$PF" ] || { echo "알 수 없는 팩: $pk  (--list 로 확인)" >&2; exit 2; }
  PST="$(field "$PF" status)"
  [ "$PST" = "active" ] || { echo "'$pk' 는 status=$PST 입니다. 아직 설치할 수 없습니다." >&2; exit 2; }
  for s in $(field "$PF" skills); do
    p="$ROOT/skills/$pk/$s"
    [ -d "$p" ] || { echo "매니페스트에 있으나 폴더가 없습니다: $p" >&2; exit 1; }
    TARGETS+=("$p")
  done
  PACK_IDS+=("$pk")
  CHOSEN+=("$(field "$PF" name)")
done

mkdir -p "${STORES[@]}"

if [ "$FORCE" = 1 ]; then
  echo
  echo "경고 --force: 이미 있는 스킬 폴더를 지우고 레포 것으로 덮어씁니다." >&2
  echo "             설치처에서 고친 내용은 사라지며 되돌릴 수 없습니다." >&2
  echo "             갱신이 목적이라면 skills/_core/harness-repo 의" >&2
  echo "             가져오기 절차를 쓰십시오 — 필요한 것만 골라 병합합니다." >&2
  echo
fi

linked=0; skipped=0; same=0; failed=(); NEED_MERGE=()
for src in "${TARGETS[@]}"; do
  name="$(basename "$src")"
  for dir in "${STORES[@]}"; do
    link="$dir/$name"
    if [ -e "$link" ] || [ -L "$link" ]; then
      # 예전 방식(심링크)으로 깔려 있으면 끊고 복사본으로 바꾼다.
      # 링크를 끊는 것이지 가리키던 폴더의 내용을 없애는 것이 아니다.
      if [ -L "$link" ]; then
        unlink "$link" 2>/dev/null || true
        if [ -e "$link" ] || [ -L "$link" ]; then
          failed+=("$link  (기존 링크 제거 실패)"); continue
        fi
      elif [ "$FORCE" != 1 ]; then
        # 실제 디렉터리는 설치처에서 고쳤을 수 있다. 덮어쓰면 그 수정이 사라진다.
        # 그래서 지나치기 전에 "정말 같은가"를 본다. 같으면 알릴 것이 없고,
        # 다르면 덮어쓰기가 아니라 병합이 필요한 상태다.
        skill_delta "$src" "$link"
        if [ -z "$DELTA" ]; then
          same=$((same+1))
        else
          NEED_MERGE+=("$name|$DELTA|$link")
        fi
        skipped=$((skipped+1)); continue
      else
        rm -rf "$link"
      fi
    fi
    cp -r "$src" "$link" 2>/dev/null || true
    # 만들었다고 가정하지 않는다 — SKILL.md 가 실제로 놓였는지 확인하고 센다
    if [ -f "$link/SKILL.md" ]; then
      linked=$((linked+1))
    else
      failed+=("$link  (복사 실패)")
    fi
  done
done

# 마커는 복사가 끝난 직후에 적는다. 린터는 선택 설치라, 그쪽이 실패해도
# 스킬은 이미 놓였다. 뒤에 적으면 그 실패가 설치 기록까지 지워 --status 가
# "설치하지 않았습니다" 라고 거짓말을 한다.
[ -n "$WORKFLOW" ] && printf '%s' "$WORKFLOW" > "$MARKER"
if [ "${#PACK_IDS[@]}" -gt 0 ]; then
  # 이번에 설치한 것만 적지 않는다 — 전에 깔아 둔 팩이 지워진 것처럼 보이므로 합친다.
  prev=""
  [ -f "$PACK_MARKER" ] && prev="$(cat "$PACK_MARKER")"
  printf '%s\n' "$prev" "${PACK_IDS[@]}" \
    | tr ',' '\n' | sed 's/^ *//; s/ *$//' | grep -v '^$' | sort -u \
    | paste -sd',' - | sed 's/,/, /g' > "$PACK_MARKER"
fi

# 린터는 선택 설치다. 스킬과 달리 설치처에서 고칠 것이 아니라 그대로 쓰는
# 도구이므로, 이미 있으면 말없이 최신본으로 덮어쓴다.
if [ "$WITH_LINTER" = 1 ]; then
  mkdir -p "$TOOLS_DIR"
  # 정본은 스킬 안에 있다. tools/check_skill.py 는 그리로 넘기는 런처라
  # 그것을 복사하면 설치처에서 경로를 못 찾는다.
  LINTER="$ROOT/skills/skillcraft/portable-skill-authoring/scripts/check_skill.py"
  [ -f "$LINTER" ] || { echo "린터를 찾을 수 없습니다: $LINTER" >&2; exit 1; }
  cp -f "$LINTER" "$TOOLS_DIR/check_skill.py"
  if [ -f "$TOOLS_DIR/check_skill.py" ]; then
    echo "린터 설치: $TOOLS_DIR/check_skill.py"
  else
    failed+=("$TOOLS_DIR/check_skill.py  (린터 복사 실패)")
  fi
fi

echo
joined=""
for c in "${CHOSEN[@]}"; do
  if [ -z "$joined" ]; then joined="$c"; else joined="$joined + $c"; fi
done
echo "설치: $joined"
echo "  복사 ${linked}개, ${skipped}개 건너뜀(같음 ${same} · 변경됨 ${#NEED_MERGE[@]}), ${#failed[@]}개 실패"
echo "  대상: $(stores_str)"
echo "  스킬: $(for t in "${TARGETS[@]}"; do printf '%s ' "$(basename "$t")"; done)"

if [ "${#NEED_MERGE[@]}" -gt 0 ]; then
  echo
  echo "🔴 병합이 필요합니다 — 설치처 내용이 레포와 다릅니다:" >&2
  for m in "${NEED_MERGE[@]}"; do
    echo "  - ${m%%|*}" >&2
    rest="${m#*|}"
    echo "      ${rest%%|*}" >&2
    echo "      ${rest#*|}" >&2
  done
  echo >&2
  echo "설치처에서 고친 것일 수도, 레포가 앞서 나간 것일 수도 있습니다." >&2
  echo "🔴 --force 로 덮어쓰지 마십시오 — 설치처의 수정이 사라지고 되돌릴 수 없습니다." >&2
  echo "   skills/_core/harness-repo 의 가져오기 절차를 쓰십시오. 새 것 / 다른 것 /" >&2
  echo "   설치처에만 있는 것으로 갈라 필요한 것만 병합합니다." >&2
  echo >&2
fi

if [ "${#failed[@]}" -gt 0 ]; then
  echo
  echo "처리하지 못한 항목 — 이 경로들은 아직 저장소를 가리키지 않습니다:" >&2
  for f in "${failed[@]}"; do echo "  - $f" >&2; done
  echo >&2
  echo "복사 자체가 실패한 항목입니다. 권한·디스크·경로를 확인하고 다시 실행하세요." >&2
  echo >&2
  exit 1
fi
echo
