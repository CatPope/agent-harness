#!/usr/bin/env python3
"""skill_usage.py 자가 테스트. 표준 라이브러리만. 임시 폴더에서만 쓴다.

    python hooks/test_skill_usage.py
"""
import datetime
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skill_usage  # noqa: E402


def make_skill(root, name, with_history=True):
    d = os.path.join(root, '.claude', 'skills', name)
    os.makedirs(d, exist_ok=True)
    body = '---\nname: {}\n---\n# {}\n'.format(name, name)
    if with_history:
        body += '\n## 이력 (필수 기록)\n\n- 생성일: 2026-09-17\n- 업데이트 횟수: 1\n'
    with io.open(os.path.join(d, 'SKILL.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(body)
    return d


def read_usage(d):
    p = os.path.join(d, '기록', '사용.md')
    return io.open(p, encoding='utf-8').read() if os.path.isfile(p) else None


def main():
    fails = []
    tmp = tempfile.mkdtemp(prefix='agent-harness-usage-')
    os.environ['CLAUDE_PROJECT_DIR'] = tmp
    ours = make_skill(tmp, 'work-review')
    theirs = make_skill(tmp, 'foreign-skill', with_history=False)

    # 1) 우리 스킬을 찾는다 / 이력 절 없는 폴더는 무시한다 / 플러그인 이름은 무시한다
    if skill_usage.find_skill_dir('work-review') != ours:
        fails.append(('find', 'work-review', skill_usage.find_skill_dir('work-review')))
    if skill_usage.find_skill_dir('foreign-skill') is not None:
        fails.append(('find-foreign', 'foreign-skill'))
    for bad in ('oh-my-claudecode:executor', '', '../work-review', 'a/b'):
        if skill_usage.find_skill_dir(bad) is not None:
            fails.append(('find-bad', bad))

    # 2) 첫 기록: 횟수 1, 최근 사용, 로그 한 줄
    t1 = datetime.datetime(2026, 9, 23, 10, 0)
    n = skill_usage.record(ours, 'args one', now=t1)
    u = read_usage(ours)
    if n != 1 or '사용 횟수: 1' not in u or '최근 사용: 2026-09-23 10:00' not in u or 'args one' not in u:
        fails.append(('record-1', n, u))

    # 3) 두 번째 기록: 횟수 2, 로그 두 줄 누적, 첫 줄 유지
    t2 = datetime.datetime(2026, 9, 23, 11, 30)
    n = skill_usage.record(ours, 'args two', now=t2)
    u = read_usage(ours)
    if n != 2 or '사용 횟수: 2' not in u or '최근 사용: 2026-09-23 11:30' not in u \
            or 'args one' not in u or 'args two' not in u:
        fails.append(('record-2', n, u))

    # 4) 긴 args 는 잘린다, 줄바꿈은 한 줄로
    skill_usage.record(ours, 'x' * 200 + '\n' + 'y' * 50, now=t2)
    u = read_usage(ours)
    if any(len(ln) > 120 for ln in u.splitlines()):
        fails.append(('truncate', max(len(ln) for ln in u.splitlines())))

    # 5) 로그 상한: 250번 기록해도 200줄만 남고 횟수는 계속 센다
    for i in range(250):
        skill_usage.record(ours, 'bulk {}'.format(i), now=t2)
    u = read_usage(ours)
    log_lines = [ln for ln in u.split('\n---\n', 1)[1].splitlines() if ln.strip()]
    if len(log_lines) != skill_usage.MAX_LOG_LINES or '사용 횟수: 253' not in u:
        fails.append(('cap', len(log_lines), u.splitlines()[0]))

    # 6) SKILL.md 는 건드리지 않는다
    sk = io.open(os.path.join(ours, 'SKILL.md'), encoding='utf-8').read()
    if '업데이트 횟수: 1' not in sk or '사용 횟수' in sk:
        fails.append(('skillmd-touched', sk))

    # 7) 실제 훅 경로: stdin JSON → 파일 갱신, stdout 없음, exit 0. 환경은 훅 런타임과 같게.
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONIOENCODING', 'PYTHONUTF8')}
    env['CLAUDE_PROJECT_DIR'] = tmp
    before = read_usage(ours)
    # 🔴 한글 args. 훅 런타임은 UTF-8 JSON 을 주는데 텍스트 모드 stdin 은 cp949 로 풀어 서로게이트가
    #    되고, 파일에 쓰다 죽었다(실측). ensure_ascii=False 로 실제 UTF-8 바이트를 먹인다.
    payload = json.dumps({'tool_name': 'Skill', 'tool_input': {'skill': 'work-review', 'args': 'via hook 훅 발동 시험'}},
                         ensure_ascii=False)
    p = subprocess.run([sys.executable, os.path.join(HERE, 'skill_usage.py')],
                       input=payload.encode('utf-8'), capture_output=True, env=env)
    after = read_usage(ours)
    err_file = os.path.join(ours, '기록', '사용.err')
    if p.returncode != 0 or p.stdout.strip() or after is None or '훅 발동 시험' not in after \
            or after == before or os.path.exists(err_file):
        fails.append(('subprocess', p.returncode, p.stdout[:80], p.stderr[:200],
                      io.open(err_file, encoding='utf-8').read()[-300:] if os.path.exists(err_file) else ''))
    # 다른 도구의 호출은 무시
    payload = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'ls'}})
    p = subprocess.run([sys.executable, os.path.join(HERE, 'skill_usage.py')],
                       input=payload.encode('utf-8'), capture_output=True, env=env)
    if p.returncode != 0 or read_usage(ours) != after:
        fails.append(('subprocess-other-tool', p.returncode))

    # 8) 리터럴 탭 없음
    for fn in ('skill_usage.py', 'test_skill_usage.py'):
        with open(os.path.join(HERE, fn), 'rb') as f:
            if b'\t' in f.read():
                fails.append(('literal-tab', fn))

    if fails:
        print('FAIL {}'.format(len(fails)))
        for f in fails:
            print('  ', f)
        return 1
    print('skill_usage: 8 groups pass')
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
