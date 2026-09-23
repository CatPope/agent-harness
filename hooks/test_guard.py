#!/usr/bin/env python3
"""guard.py 자가 테스트. 표준 라이브러리만. CI 와 설치 전 확인에서 돌린다.

    python hooks/test_guard.py

막아야 할 것이 막히고, 통과해야 할 것이 통과하는지 본다. 후자가 더 중요하다 —
가드가 멀쩡한 명령을 막기 시작하면 사람이 훅을 꺼 버리고, 그러면 아무것도 안 막힌다.

🔴 명령 문자열은 전부 raw 문자열(r"...")이다. 백슬래시가 든 경로를 일반 문자열로 쓰면
   "C:\t\a" 의 \t 가 탭이 된다 — 이 레포에서 세 번 터진 버그다.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guard  # noqa: E402

# (도구, 명령, 막혀야 하는가, 기대 규칙)
CASES = [
    # ---- R1 삭제: 막힌다
    ("Bash", r"rm -rf /tmp/x", True, "R1"),
    ("Bash", r"cd a && rm foo.txt", True, "R1"),
    ("Bash", r"rmdir build", True, "R1"),
    ("Bash", r"git clean -fdx", True, "R1"),
    ("Bash", r"git rm --cached a.py", True, "R1"),
    ("Bash", r"X=1 rm a", True, "R1"),
    ("PowerShell", r"Remove-Item -Recurse -Force .\out", True, "R1"),
    ("PowerShell", r"remove-item x.txt", True, "R1"),
    ("PowerShell", r"del *.log", True, "R1"),
    ("PowerShell", r"rd /s /q build", True, "R1"),
    ("PowerShell", r"Get-ChildItem | Remove-Item", True, "R1"),
    ("Bash", "python - <<'EOF'\nimport shutil\nshutil.rmtree('x')\nEOF", True, "R1"),
    # ---- R1 오탐이면 안 되는 것: 통과
    ("Bash", r"grep -n form README.md", False, None),
    ("Bash", r"echo harm", False, None),
    ("Bash", r"ls -la; wc -l a.txt", False, None),
    ("Bash", r"git rm-not-a-thing", False, None),
    ("Bash", r"mv old.txt old.txt.bak", False, None),
    ("Bash", r"cat model.txt", False, None),
    ("Bash", r"git commit -m 'remove the delete path'", False, None),
    ("Bash", r"echo 'rm -rf' > note.txt", False, None),      # 첫 낱말이 echo
    ("PowerShell", r"Get-ChildItem -Recurse", False, None),
    ("PowerShell", r"Write-Output 'rd'", False, None),
    ("PowerShell", r"Get-Content .\erase.log", False, None),
    # ---- R2 설치기 실행: 막힌다
    ("Bash", r"./install.sh --workflow supervisor-worker", True, "R2"),
    ("Bash", r"~/Documents/GitHub/agent-harness/install.sh --pack documents --workflow x", True, "R2"),
    ("Bash", r"cd repo && ./install.sh --pack documents", True, "R2"),
    ("Bash", r"bash install.sh --workflow supervisor-worker", True, "R2"),
    ("PowerShell", r'& "$HOME\Documents\GitHub\agent-harness\install.ps1" -Workflow supervisor-worker', True, "R2"),
    ("PowerShell", r".\install.ps1 -Pack documents -WithClaudeMd", True, "R2"),
    ("PowerShell", r"powershell -File .\install.ps1 -Workflow x", True, "R2"),
    # ---- R2 허용: -Project / 읽기 전용 / 설치처 돌려 놓음 / 언급만
    ("Bash", r"./install.sh --project . --workflow supervisor-worker", False, None),
    ("PowerShell", r".\install.ps1 -Project . -Workflow supervisor-worker", False, None),
    ("Bash", r"./install.sh --list", False, None),
    ("Bash", r"./install.sh --status", False, None),
    ("PowerShell", r".\install.ps1 -Status", False, None),
    ("Bash", r"CLAUDE_SKILLS_DIR=/tmp/a AGENTS_SKILLS_DIR=/tmp/b ./install.sh --workflow supervisor-worker", False, None),
    ("PowerShell", r".\install.ps1 -ClaudeDir C:\t\a -AgentsDir C:\t\b -Workflow supervisor-worker", False, None),
    ("Bash", r"bash -n install.sh", False, None),
    ("Bash", r"cat install.sh | head", False, None),
    ("Bash", r"grep -n Project install.ps1 install.sh", False, None),
    ("Bash", r"git diff install.sh", False, None),
    ("Bash", r"sed -n '1,20p' install.ps1", False, None),
    ("Bash", r"python tools/check_installers.py install.sh", False, None),
    # ---- R3 전역 CLAUDE.md 쓰기: 막힌다
    ("Bash", r"echo x >> ~/.claude/CLAUDE.md", True, "R3"),
    ("Bash", r"cp a.md ~/.claude/CLAUDE.md", True, "R3"),
    ("PowerShell", r"Set-Content -Path $HOME\.claude\CLAUDE.md -Value x", True, "R3"),
    ("Bash", r"sed -i 's/a/b/' /c/Users/me/.claude/CLAUDE.md", True, "R3"),
    ("Bash", r"cat a.md > ~/.claude/CLAUDE.md", True, "R3"),
    ("Bash", r'echo x >"$HOME/.claude/CLAUDE.md"', True, "R3"),
    ("PowerShell", r"[IO.File]::WriteAllText(\"$HOME\.claude\CLAUDE.md\", $t)", True, "R3"),
    # ---- R3 허용: 읽기, 프로젝트 CLAUDE.md, 조각 파일, "언급 + 무관한 >"
    ("Bash", r"cat ~/.claude/CLAUDE.md", False, None),
    # 커밋 메시지 히어독 — 경로를 말로 언급하고 다른 줄에 '>' 가 있다. 실제로 커밋을 막았던 케이스.
    ("Bash", "git commit -q -F - <<'MSGEOF'\nR3  전역 CLAUDE.md 보호  ~/.claude/CLAUDE.md 에 셸로 쓰기\n설치기는 <설치처>/.claude/hooks/ 로 복사한다\nMSGEOF", False, None),
    ("Bash", r"grep -n CLAUDE ~/.claude/CLAUDE.md > /tmp/out.txt", False, None),   # 읽고 다른 곳에 쓴다
    ("Bash", r"diff ~/.claude/CLAUDE.md ./CLAUDE.md", False, None),
    ("Bash", r"md5sum ~/.claude/CLAUDE.md", False, None),
    ("Bash", r"echo x >> ./CLAUDE.md", False, None),
    ("Bash", r"grep -c begin ~/.claude/CLAUDE.md", False, None),
    ("Bash", r"cat ~/.claude/harness-CLAUDE.md > x", False, None),
    ("Bash", r"echo x >> ~/.claude/CLAUDE.md.bak", False, None),
    # ---- 히어독 본문은 명령이 아니다 — 커밋 메시지가 R2·R1 에 걸려 커밋을 막았던 케이스
    ("Bash", "git commit -F - <<'MSG'\ninstall.ps1 Get-DirFingerprint 를 고친다\nrm 은 막힌다고 적는다\nMSG", False, None),
    ("Bash", "cat > note.txt <<EOF\n./install.sh --workflow x 를 돌리지 마라\nEOF", False, None),
    ("Bash", "cat <<EOF\nrm -rf /\nEOF\nrm x", True, "R1"),                      # 종료자 뒤는 다시 명령
    ("Bash", "python - <<'PY'\nprint('rm')\nPY\n./install.sh --workflow x", True, "R2"),
    ("Bash", "rm x <<EOF\nbody\nEOF", True, "R1"),                               # 히어독 앞의 명령은 명령
    # ---- 다른 도구는 무시
    ("Write", r"rm -rf /", False, None),
]

# R4: Agent 도구 — (subagent_type, 막혀야 하는가)
AGENT_CASES = [
    ("codex:codex-rescue", True),
    ("codex:rescue", True),
    ("Codex:Codex-Rescue", True),
    ("oh-my-claudecode:executor", False),
    ("oh-my-claudecode:code-reviewer", False),
    ("general-purpose", False),
    ("", False),
]


def run_subprocess(tool, command):
    """실제 훅 호출 경로(stdin JSON → stdout JSON)로도 검증한다."""
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}}, ensure_ascii=False)
    # 🔴 훅 런타임과 같은 환경으로 돌린다. 테스트를 PYTHONIOENCODING=utf-8 로 띄우면 그것이
    #    자식에 새어 들어가, 실제 훅에서는 죽는 cp949 인코딩 오류를 테스트가 못 본다 (실측).
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONLEGACYWINDOWSSTDIO")}
    p = subprocess.run([sys.executable, os.path.join(HERE, "guard.py")],
                       input=payload.encode("utf-8"), capture_output=True, env=env)
    if p.returncode != 0:
        return "ERROR exit {}".format(p.returncode)
    if not p.stdout.strip():
        return None
    out = json.loads(p.stdout.decode("utf-8"))
    return out["hookSpecificOutput"]["permissionDecisionReason"]


def main():
    fails = []
    for tool, cmd, should_block, rule in CASES:
        reason = guard.check(tool, cmd) if tool in ("Bash", "PowerShell") else None
        blocked = reason is not None
        if blocked != should_block:
            fails.append(("check()", tool, cmd, "block" if should_block else "pass", reason))
            continue
        if should_block and rule and not reason.startswith(rule):
            fails.append(("rule", tool, cmd, rule, reason))
    for sub_type, should_block in AGENT_CASES:
        reason = guard.check_agent(sub_type)
        if (reason is not None) != should_block:
            fails.append(("check_agent()", "Agent", sub_type, "block" if should_block else "pass", reason))
        elif should_block and not reason.startswith("R4"):
            fails.append(("rule", "Agent", sub_type, "R4", reason))

    # 서브프로세스 경로: 대표 케이스만 (전부 돌리면 느리다)
    sub = [
        ("Bash", r"rm -rf /tmp/x", True),
        ("Bash", r"ls", False),
        ("PowerShell", r".\install.ps1 -Workflow supervisor-worker", True),
        ("Write", r"rm -rf /", False),
        # 한글이 든 명령 — stdin 을 텍스트로 읽으면 cp949 디코드로 깨진다. 바이트로 읽어야 한다.
        ("Bash", r"echo '한글 경로 시험' && rm 파일.txt", True),
        ("Bash", r"grep -n '삭제 금지' README.md", False),
    ]
    for tool, cmd, should_block in sub:
        r = run_subprocess(tool, cmd)
        if isinstance(r, str) and r.startswith("ERROR"):
            fails.append(("subprocess", tool, cmd, should_block, r))
        elif (r is not None) != should_block:
            fails.append(("subprocess", tool, cmd, should_block, r))
    # Agent 도구는 stdin 모양이 다르다(subagent_type). 실제 경로로 한 번 본다.
    for sub_type, should_block in [("codex:codex-rescue", True), ("oh-my-claudecode:executor", False)]:
        payload = json.dumps({"tool_name": "Agent", "tool_input": {"subagent_type": sub_type, "prompt": "x"}})
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
        p = subprocess.run([sys.executable, os.path.join(HERE, "guard.py")],
                           input=payload.encode("utf-8"), capture_output=True, env=env)
        blocked = p.returncode == 0 and bool(p.stdout.strip())
        if p.returncode != 0 or blocked != should_block:
            fails.append(("subprocess", "Agent", sub_type, should_block, p.stdout[:80], p.stderr[:80]))

    # 탭 검사: 이 파일과 guard.py 에 리터럴 탭이 없어야 한다 (\t 접힘 사고 감시)
    for fn in ("guard.py", "test_guard.py"):
        with open(os.path.join(HERE, fn), "rb") as f:
            if b"\t" in f.read():
                fails.append(("literal-tab", fn, "", "", ""))

    total = len(CASES) + len(AGENT_CASES) + len(sub) + 2
    if fails:
        print("FAIL {}/{}".format(len(fails), total))
        for f in fails:
            print("  ", f)
        return 1
    print("guard: {} cases pass".format(total))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
