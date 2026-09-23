# hooks/

훅 설정을 둔다. **스킬과 `CLAUDE.md` 는 "읽고 따르는" 층이고, 훅은 "안 읽어도 막히는" 층이다.**
그 점이 나머지 둘과 다르다 — 에이전트가 규칙을 안 읽어도, 읽고 무시해도 작동한다.

2026-09-22 한 세션에서 텍스트 규칙 위반이 다섯 번 났고, 막은 것은 하나도 없었다.
사용자가 지적하거나 에이전트가 자진 신고했다. 이 폴더가 그 자리를 메운다.

## 무엇이 있는가

| 파일 | 역할 |
|---|---|
| `guard.py` | `PreToolUse` 훅 (Bash · PowerShell). 세 규칙을 코드로 막는다 |
| `test_guard.py` | 자가 테스트. 막을 것이 막히고 **멀쩡한 것이 통과하는지** 본다. CI 가 돌린다 |
| `settings.fragment.json` | 설치처 `.claude/settings.json` 에 합칠 조각 — `permissions.deny` + `hooks` |

**`guard.py` 의 세 규칙**

```
R1  삭제 금지          rm / rmdir / del / Remove-Item / git clean / git rm / shutil.rmtree …
                       세그먼트(; & | 줄바꿈)의 첫 낱말로 판단한다 — "echo 'rm -rf'" 는 안 막힌다
R2  전역 설치 금지      install.sh / install.ps1 을 -Project 없이 "실행" 하면 막는다.
                       설치처를 -ClaudeDir / CLAUDE_SKILLS_DIR 로 돌려 놓았으면 허용 (시험용 길).
                       cat / bash -n / grep 같은 "언급" 은 실행이 아니다
R3  전역 CLAUDE.md 보호  ~/.claude/CLAUDE.md 에 셸로 쓰면 막는다 (>, cp, Set-Content …).
                       프로젝트 루트의 CLAUDE.md 와 harness-CLAUDE.md 는 대상이 아니다
```

**오탐이 미탐보다 위험하다.** 가드가 멀쩡한 명령을 막기 시작하면 사람이 훅을 꺼 버리고,
그러면 아무것도 안 막힌다. 그래서 판단이 안 되면 통과시키고, 테스트의 절반이 "통과해야 하는 것"이다.

## 어떻게 설치되는가

설치기가 `guard.py` · `test_guard.py` · `settings.fragment.json` 을 **`<설치처>/.claude/hooks/`** 로
복사한다 (프로젝트 설치면 `<project>/.claude/hooks/`, 전역이면 `~/.claude/hooks/` — 전역일 때는
조각 안의 훅 경로도 `$HOME/.claude/hooks` 로 바꿔 준다).
`CLAUDE.md` 조각과 같은 원칙이다 — 파일을 떨구고, **사용자 설정 파일은 건드리지 않는다.**

`settings.json` 에 합치는 것은 사람이 한다. 설치 끝에 안내가 나온다.

```jsonc
// <project>/.claude/settings.json  ← settings.fragment.json 의 내용을 합친다
{
  "permissions": { "deny": [ "Bash(rm *)", ... ] },
  "hooks": { "PreToolUse": [ { "matcher": "Bash|PowerShell", "hooks": [
      { "type": "command", "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard.py\"" }
  ] } ] }
}
```

- `permissions.deny` 는 **접두 매칭**이라 `cd x && rm` 같은 복합 명령을 못 잡는다.
  본 검사는 `guard.py` 가 하고, deny 는 이중 방어다.
- 훅 명령은 Git Bash 로 실행된다(Windows 포함). `python` 이 PATH 에 있어야 한다.
- 합친 뒤 `/hooks` 를 한 번 열거나 세션을 다시 시작해야 반영된다.

**확인**: 훅이 걸린 세션에서 `rm x` 같은 명령을 내 보면 `[agent-harness guard] R1 …` 로 막힌다.

## 고칠 때

- 규칙을 더하면 `test_guard.py` 에 **막히는 케이스와 통과하는 케이스를 둘 다** 넣는다.
- 🔴 이 폴더의 파이썬 파일은 정규식과 백슬래시 경로가 많다. **백슬래시를 접는 경로(셸 히어독 등)로
  고치지 마라.** 이 레포에서 `"\t"` 가 탭이 된 사고가 세 번 있었다. `test_guard.py` 가 리터럴 탭을 검사한다.
- 올리는 절차는 `skills/_core/harness-repo` 를 따른다. 경로가 들어가면 대명사로 적는다.
