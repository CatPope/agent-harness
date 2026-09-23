#!/usr/bin/env python3
"""agent-harness 사용 기록 훅 — Claude Code PostToolUse (Skill)

규칙: "skills 내부에 업데이트 횟수·일자·사용 횟수를 기록하고, 매 사용 시마다 갱신한다."
이 규칙은 사람과 모델이 지키지 않았다 — 한 세션에서 쓴 스킬 6개 중 갱신된 것 1개(2026-09-23 실측).
그래서 훅이 한다. 안 읽어도, 잊어도 기록된다.

어디에 적는가: <스킬 폴더>/기록/사용.md
  - SKILL.md 를 고치면 설치기가 매번 "변경됨" 으로 잡아 병합 소음이 난다.
  - 기록/ 은 설치기 비교에서 빠지고(.gitignore 에도 있다) "설치처가 남기는 로컬 기록" 자리다.
  - SKILL.md 의 "이력" 절은 본문을 고칠 때만 사람이 갱신한다 (업데이트 횟수·일자).

무엇을 적는가:
    사용 횟수: N
    최근 사용: YYYY-MM-DD HH:MM
    ---
    YYYY-MM-DD HH:MM  <args 요약>        ← 한 줄씩 누적 (최근 200줄만 유지)

스킬 폴더를 찾는 순서: $CLAUDE_PROJECT_DIR/.claude/skills/<이름> → ~/.claude/skills/<이름>.
플러그인 스킬(이름에 ':' 이 있음)과 우리 것이 아닌 폴더(SKILL.md 에 "## 이력" 이 없음)는 건드리지 않는다.
실패하면 조용히 통과한다 — 기록 훅이 스킬 호출을 막아서는 안 된다. 표준 라이브러리만.
"""
import datetime
import io
import json
import os
import re
import sys

MAX_LOG_LINES = 200


def _candidates(name):
    dirs = []
    proj = os.environ.get('CLAUDE_PROJECT_DIR')
    if proj:
        dirs.append(os.path.join(proj, '.claude', 'skills', name))
    dirs.append(os.path.join(os.path.expanduser('~'), '.claude', 'skills', name))
    return dirs


def find_skill_dir(name):
    if not name or ':' in name or '/' in name or '\\' in name or name.startswith('.'):
        return None
    for d in _candidates(name):
        skill_md = os.path.join(d, 'SKILL.md')
        if not os.path.isfile(skill_md):
            continue
        try:
            text = io.open(skill_md, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        if re.search(r'^## 이력', text, re.M):
            return d
    return None


def record(skill_dir, args, now=None):
    """기록/사용.md 를 갱신하고 새 사용 횟수를 돌려준다."""
    now = now or datetime.datetime.now()
    stamp = now.strftime('%Y-%m-%d %H:%M')
    rec_dir = os.path.join(skill_dir, '기록')
    path = os.path.join(rec_dir, '사용.md')
    count = 0
    log = []
    if os.path.isfile(path):
        old = io.open(path, encoding='utf-8', errors='replace').read()
        m = re.search(r'^사용 횟수:\s*(\d+)', old, re.M)
        if m:
            count = int(m.group(1))
        if '\n---\n' in old:
            log = [ln for ln in old.split('\n---\n', 1)[1].splitlines() if ln.strip()]
    count += 1
    summary = (args or '').strip().replace('\n', ' ')
    if len(summary) > 80:
        summary = summary[:77] + '...'
    log.append('{}  {}'.format(stamp, summary).rstrip())
    log = log[-MAX_LOG_LINES:]
    body = '사용 횟수: {}\n최근 사용: {}\n---\n{}\n'.format(count, stamp, '\n'.join(log))
    os.makedirs(rec_dir, exist_ok=True)
    # 원자적으로 쓴다. 훅 런타임에서 쓰기 도중 실패하면 0 바이트 파일이 남았다(2026-09-23 실측) —
    # 그러면 다음 호출이 횟수를 0 에서 다시 센다. 임시 파일에 다 쓴 뒤 바꿔치기한다.
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return count


def read_stdin_json():
    """stdin 을 바이트로 읽어 UTF-8 로 푼다. 텍스트 모드로 읽으면 Windows 훅 런타임이
    cp949 로 디코드해 한글이 서로게이트로 들어오고, 그것을 파일에 쓰다 죽는다(2026-09-23 실측:
    args '훅 발동 시험 2' → UnicodeEncodeError surrogates not allowed)."""
    raw = sys.stdin.buffer.read() if hasattr(sys.stdin, 'buffer') else sys.stdin.read().encode('utf-8', 'replace')
    return json.loads(raw.decode('utf-8', errors='replace'))


def main():
    try:
        data = read_stdin_json()
    except Exception:
        return 0
    if data.get('tool_name') != 'Skill':
        return 0
    tool_input = data.get('tool_input') or {}
    name = (tool_input.get('skill') or '').strip()
    skill_dir = find_skill_dir(name)
    if not skill_dir:
        return 0
    try:
        record(skill_dir, tool_input.get('args', ''))
    except Exception as e:
        # exit 0 을 유지하므로(기록 훅이 스킬 호출을 막으면 안 된다) stderr 는 사람에게 안 보인다.
        # 흔적을 파일로 남긴다 — 이것이 없으면 "왜 안 적혔는지" 를 알 길이 없다.
        sys.stderr.write('[agent-harness skill_usage] record failed, ignoring: {}\n'.format(e))
        try:
            import traceback
            err_path = os.path.join(skill_dir, '기록', '사용.err')
            os.makedirs(os.path.dirname(err_path), exist_ok=True)
            with io.open(err_path, 'a', encoding='utf-8', newline='\n') as f:
                f.write('{}\n{}\n'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                          traceback.format_exc()))
        except Exception:
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
