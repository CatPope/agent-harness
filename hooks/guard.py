#!/usr/bin/env python3
"""agent-harness 가드 훅 — Claude Code PreToolUse (Bash · PowerShell)

스킬과 CLAUDE.md 는 "읽고 따르는" 층이다. 이 파일은 "안 읽어도 막히는" 층이다.
2026-09-22 한 세션에서 텍스트 규칙 위반이 다섯 번 났고, 막은 것은 하나도 없었다 —
사용자가 지적하거나 에이전트가 자진 신고했다. 그중 셋을 여기서 코드로 막는다.

  R1  삭제 금지          rm / rmdir / del / Remove-Item / git clean / git rm
                         (프로젝트 규칙: 읽기·쓰기만 허용. 덮어쓰거나 옮겨라)
  R2  전역 설치 금지      install.sh / install.ps1 을 -Project 없이 "실행"하면
                         실제 ~/.claude/skills · ~/.agents/skills 에 쓰인다.
                         설치처 인자(-ClaudeDir / CLAUDE_SKILLS_DIR)로 돌려 놓은 경우는 허용 —
                         그것이 시험용으로 열어 둔 길이다. 언급(cat, bash -n, grep)은 실행이 아니다.
  R3  전역 CLAUDE.md 보호  ~/.claude/CLAUDE.md 에 셸로 쓰지 마라. 설치기(-WithClaudeMd)나
                         편집 도구로만.

동작: stdin 의 JSON 을 읽고, 막을 것이면 permissionDecision=deny 를 stdout 에 낸다.
      아니면 아무것도 내지 않고 0 으로 끝난다. 판단이 안 되면 통과시킨다 — 가드가
      죽어서 모든 명령이 막히면 사람이 훅을 꺼 버리고, 그러면 아무것도 안 막힌다.
      오탐(멀쩡한 명령을 막음)이 미탐보다 위험한 이유가 그것이다.

설치: 설치기가 <설치처>/.claude/hooks/ 로 복사한다. settings.json 에는
      hooks/settings.fragment.json 의 내용을 사람이 합친다 (사용자 설정 파일은 자동으로
      건드리지 않는다 — CLAUDE.md 조각과 같은 원칙).

이 파일은 정규식이 많다. 백슬래시를 접는 경로(히어독 등)로 고치지 말고 편집기로 고쳐라.
표준 라이브러리만 쓴다. 테스트: python hooks/test_guard.py
"""
import json
import re
import sys

# 명령을 세그먼트로 가른다: ; & | 줄바꿈. 각 세그먼트의 첫 낱말이 "무엇을 실행하는가"다.
_SEG_SPLIT = re.compile(r'[;&|]+|\r?\n')
_TOKEN = re.compile(r'"[^"]*"|\'[^\']*\'|\S+')
_ENV_ASSIGN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')


def _segments(cmd):
    for seg in _SEG_SPLIT.split(cmd):
        seg = seg.strip()
        while seg.startswith('('):
            seg = seg[1:].strip()
        if seg:
            yield seg


def _words(seg):
    return [t.strip('"\'') for t in _TOKEN.findall(seg)]


def _basename(word):
    return re.split(r'[\\/]', word)[-1].lower()


# ---- R1 삭제 -------------------------------------------------------------
# 세그먼트의 첫 낱말(env 대입은 건너뜀)이 삭제 명령인가. 단어 안의 rm/del 은 안 잡힌다.
_DELETE_FIRST = {
    'rm': 'rm', 'rmdir': 'rmdir', 'del': 'del', 'erase': 'erase',
    'remove-item': 'Remove-Item', 'ri': 'ri (Remove-Item 별칭)', 'rd': 'rd (rmdir 별칭)',
}
_GIT_DELETE = {'clean': 'git clean', 'rm': 'git rm'}
# 히어독·인라인 파이썬 안의 삭제 호출. 첫 낱말이 아니므로 따로 본다.
_PY_DELETE = re.compile(r'\b(shutil\.rmtree|os\.remove|os\.unlink|os\.rmdir)\s*\(')


def _check_delete(cmd):
    if _PY_DELETE.search(cmd):
        return '파이썬 삭제 호출'
    for seg in _segments(cmd):
        words = _words(seg)
        while words and _ENV_ASSIGN.match(words[0]):
            words = words[1:]
        if not words:
            continue
        first = _basename(words[0])
        if first in _DELETE_FIRST and (len(words) > 1 or first not in ('ri', 'rd')):
            return _DELETE_FIRST[first]
        if first == 'git' and len(words) > 1 and words[1].lower() in _GIT_DELETE:
            return _GIT_DELETE[words[1].lower()]
    return None


# ---- R2 설치기 ------------------------------------------------------------
_INSTALLER_NAMES = ('install.sh', 'install.ps1')
_READ_ONLY = re.compile(r'(--list|--status|--help|-List\b|-Status\b)', re.I)
_PROJECT = re.compile(r'(--project\b|-Project\b)', re.I)
# 설치처를 다른 곳으로 돌려 놓은 경우. 시험용으로 일부러 열어 둔 길이다.
_REDIRECTED = re.compile(
    r'(CLAUDE_SKILLS_DIR\s*=|AGENTS_SKILLS_DIR\s*=|-ClaudeDir\b|-AgentsDir\b)', re.I)


def _installer_executed(cmd):
    """설치기가 '실행 위치'에 있는 세그먼트가 있는가. 언급만 있으면 False."""
    for seg in _segments(cmd):
        if not any(n in seg.lower() for n in _INSTALLER_NAMES):
            continue
        words = _words(seg)
        while words and _ENV_ASSIGN.match(words[0]):
            words = words[1:]
        if words and words[0] == '&':          # PowerShell 호출 연산자: & "path\install.ps1"
            words = words[1:]
        if not words:
            continue
        first = _basename(words[0])
        if first in _INSTALLER_NAMES:
            return True
        if first in ('bash', 'sh', 'zsh'):
            # bash -n install.sh 는 문법 검사다. 플래그 없이 바로 파일이 오면 실행이다.
            rest = words[1:]
            if rest and not rest[0].startswith('-') and _basename(rest[0]) in _INSTALLER_NAMES:
                return True
            if rest and rest[0] in ('-x', '-e', '-u', '-eu', '-ex', '-xe') and len(rest) > 1 \
                    and _basename(rest[1]) in _INSTALLER_NAMES:
                return True
        if first in ('powershell', 'powershell.exe', 'pwsh', 'pwsh.exe'):
            if re.search(r'-File\s+"?[^\s"]*install\.ps1', seg, re.I):
                return True
    return False


def _check_installer(cmd):
    if not _installer_executed(cmd):
        return None
    if _READ_ONLY.search(cmd):
        return None
    if _PROJECT.search(cmd) or _REDIRECTED.search(cmd):
        return None
    return ('install.sh / install.ps1 을 -Project 없이 실행하면 실제 ~/.claude/skills 와 '
            '~/.agents/skills 에 씁니다. -Project <path> 를 주거나, 시험이면 '
            '-ClaudeDir/-AgentsDir (sh: CLAUDE_SKILLS_DIR/AGENTS_SKILLS_DIR) 을 임시 폴더로 돌리십시오.')


# ---- R3 전역 CLAUDE.md ------------------------------------------------------
# <구분자>.claude<구분자>CLAUDE.md — 프로젝트 루트의 CLAUDE.md 는 .claude 폴더 밖이라 안 걸린다.
_GLOBAL_CLAUDE_MD = re.compile(r'[\\/]\.claude[\\/]CLAUDE\.md(?![\w.])', re.I)
# 리다이렉트가 그 경로를 "직접" 가리킬 때만. 명령 어딘가의 '>' 는 증거가 아니다 —
# 커밋 메시지 히어독의 '<설치처>' 한 글자에 걸려 커밋을 막은 적이 있다 (2026-09-23 실측).
_REDIRECT_TO_GLOBAL = re.compile(
    r'>>?\s*["\']?[^\s"\'|;&]*[\\/]\.claude[\\/]CLAUDE\.md(?![\w.])', re.I)
# 세그먼트의 첫 낱말이 쓰기 동사이고 같은 세그먼트에 그 경로가 있을 때.
_WRITE_VERBS = {
    'cp', 'mv', 'tee', 'copy-item', 'move-item', 'set-content', 'out-file', 'add-content',
    'copy', 'move', 'sc', 'ac',
}
_SED_INPLACE = re.compile(r'^sed\s+(-[a-zA-Z]*i|--in-place)', re.I)
_DOTNET_WRITE = re.compile(r'WriteAll(Text|Bytes|Lines)\s*\(', re.I)


def _check_global_claude_md(cmd):
    if not _GLOBAL_CLAUDE_MD.search(cmd):
        return None
    msg = '~/.claude/CLAUDE.md 에 셸로 쓰지 마십시오. 설치기의 -WithClaudeMd 나 편집 도구를 쓰십시오.'
    for seg in _segments(cmd):
        if not _GLOBAL_CLAUDE_MD.search(seg):
            continue
        if _REDIRECT_TO_GLOBAL.search(seg):
            return msg
        words = _words(seg)
        while words and _ENV_ASSIGN.match(words[0]):
            words = words[1:]
        if not words:
            continue
        first = _basename(words[0])
        if first in _WRITE_VERBS:
            return msg
        if _SED_INPLACE.match(seg.strip()):
            return msg
        if _DOTNET_WRITE.search(seg):
            return msg
    return None


# ---- R4 Codex 를 안 부르는 "Codex" 서브에이전트 --------------------------------
# codex:codex-rescue 는 Claude Sonnet 래퍼다. 역할은 요청을 codex-companion 으로 한 번 넘기는
# 것뿐인데, 상세한 지시서를 주면 전달 대신 자기가 수행한다. 한 세션에서 세 번 다 그랬고
# codex-companion 호출은 0건이었다(2026-09-22 실측). Codex 위임은 codex-delegate 스킬로만 한다.
_BLOCKED_AGENT_PREFIXES = ('codex:',)


def check_agent(subagent_type):
    if not subagent_type:
        return None
    if subagent_type.lower().startswith(_BLOCKED_AGENT_PREFIXES):
        return ('R4 codex:* 서브에이전트 금지 — {} 는 Codex 가 아니라 Claude 래퍼이고, 실제로 Codex 를 '
                '부르지 않은 채 자기가 일합니다(실측 3/3). Codex 위임은 codex-delegate 스킬'
                '(codex_task.py start/send/status/report)로만 하십시오.').format(subagent_type)
    return None


def check(tool_name, command):
    """막을 이유가 있으면 'R1 ...' 꼴 문자열, 없으면 None."""
    if not command:
        return None
    r = _check_delete(command)
    if r:
        return 'R1 삭제 금지 — {} 가 들어 있습니다. 이 환경은 읽기/쓰기만 허용합니다. 지우는 대신 덮어쓰거나 다른 이름으로 옮기십시오.'.format(r)
    r = _check_installer(command)
    if r:
        return 'R2 전역 설치 금지 — ' + r
    r = _check_global_claude_md(command)
    if r:
        return 'R3 전역 CLAUDE.md 보호 — ' + r
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        # 입력을 못 읽으면 통과 — 가드가 모든 것을 막는 사고를 내지 않는다.
        # 다만 흔적은 남긴다. 조용히 통과하면 "훅이 안 도는 것"과 구분이 안 된다.
        sys.stderr.write('[agent-harness guard] input not parsed, passing through: {}\n'.format(e))
        return 0
    tool = data.get('tool_name', '')
    tool_input = data.get('tool_input') or {}
    if tool == 'Agent':
        reason = check_agent(tool_input.get('subagent_type', ''))
    elif tool in ('Bash', 'PowerShell'):
        reason = check(tool, tool_input.get('command', ''))
    else:
        return 0
    if reason is None:
        return 0
    out = {
        'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': '[agent-harness guard] ' + reason,
        }
    }
    # 🔴 ensure_ascii=True + 바이트 쓰기. Windows 의 훅 런타임은 stdout 이 cp949 라
    #    한글 사유를 그대로 쓰면 UnicodeEncodeError 로 죽고, 그러면 아무것도 안 막힌다.
    #    Claude Code 는 JSON 을 파싱하므로 \uXXXX 이스케이프여도 사유는 한글로 보인다.
    payload = json.dumps(out, ensure_ascii=True).encode('ascii')
    try:
        sys.stdout.buffer.write(payload)
    except AttributeError:
        sys.stdout.write(payload.decode('ascii'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
