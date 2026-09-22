# claude/

`CLAUDE.md` 조각을 둔다. **설치기가 이것을 조립해 설치처에 떨군다.**

- 여기 있는 것은 **어느 프로젝트에서나 통하는 규칙**이다
- 프로젝트 고유의 사실(경로·서버·사람·일정)은 설치처 `CLAUDE.md` 에 남기고 여기 올리지 않는다
- 경로는 대명사로 적는다 — `<project_root>`, `<harness_repo>`

## 왜 조각을 나르는가

스킬은 **불러야 열린다.** 매니페스트는 설치기만 읽는다. 그래서 워크플로우가 전제하는
규칙(예: "코드 구현은 Codex 에 위임한다")이 **세션 시작에 자동으로 읽히는 파일 어디에도
없는** 상태가 된다. 조각은 그 빈 자리를 메운다.

## 네 축

```
claude/_core.md              워크플로우를 고르면 항상 따라온다 (skills/_core 와 같은 성격)
claude/workflows/<id>.md     그 워크플로우를 고르면 따라온다
claude/packs/<id>.md         그 팩을 고르면 따라온다
claude/topics/<name>.md      워크플로우·팩과 무관하게 -Topic / --topic 으로 따로 고른다
```

앞의 셋은 **무엇을 설치했는가**에 따라오고, 토픽만 따로 고른다. 토픽 규약은
`claude/topics/README.md` 에 있다.

🔴 **`_core.md` 는 워크플로우를 골랐을 때만 따라온다.** 팩만 설치하면 `skills/_core` 가
오지 않는 것과 같은 이유다 — 없는 스킬을 가리키는 규칙을 남기지 않는다.

## 매니페스트 연결

워크플로우·팩 매니페스트의 **`claude` 필드**가 자기 조각을 가리킨다. 레포 루트 기준
상대 경로이며, 조각이 없으면 `null` 이거나 필드 자체가 없다(`doc` 필드와 같은 꼴).

```json
{
  "id": "supervisor-worker",
  "skills": ["role-split", "codex-delegate"],
  "doc": "docs/workflows/supervisor-worker.md",
  "claude": "claude/workflows/supervisor-worker.md"
}
```

- 조각이 **없어도 설치는 깨지지 않는다.** 그 워크플로우·팩은 조각을 기여하지 않을 뿐이다.
- 가리켰는데 **파일이 없으면** 설치기가 경고하고 그것만 건너뛴다. CI 는 `tools/check_manifests.py`
  의 **M6** 으로 잡는다.
- 반대로 `claude/workflows/` · `claude/packs/` 에 두고 **아무 매니페스트도 가리키지 않으면**
  영영 배포되지 않는다. **M7** 이 잡는다. (`_core.md` · `topics/*.md` · `README.md` 는 면제)

## 조립과 설치

조립 순서는 고정이다.

```
_core.md  →  워크플로우  →  팩(고른 순)  →  토픽(고른 순)
```

각 조각 앞에 `<!-- from: claude/... -->` 한 줄이 붙어 **나중에 어느 파일에서 왔는지** 보인다.

| | 기본 (옵션 없음) | `-WithClaudeMd` / `--with-claude-md` |
|---|---|---|
| 프로젝트 설치 | `<project_root>/.claude/harness-CLAUDE.md` 를 쓴다 | 위에 더해 `<project_root>/CLAUDE.md` 에 반영 |
| 전역 설치 | `<claude_dir>/../harness-CLAUDE.md` 를 쓴다 | 위에 더해 그 옆 `CLAUDE.md` 에 반영 |

기본값에서 전역 설치처는 `~/.claude/skills` 이므로 산출물은 `~/.claude/harness-CLAUDE.md`,
대상은 `~/.claude/CLAUDE.md` 다. **경로는 설치처 인자에서 유도한다** — `-ClaudeDir` /
`CLAUDE_SKILLS_DIR` 을 바꾸면 조각의 자리도 함께 옮겨 간다(시험할 때 이 점이 필요하다).

🔴 **기본값은 사용자 파일을 건드리지 않는다.** 별도 파일을 떨구고, 그것을 참조하라고
안내만 한다. 직접 이어붙이는 것은 옵션을 줬을 때뿐이다.

### 마커 블록

`-WithClaudeMd` 를 주면 대상 `CLAUDE.md` 에 이 블록으로 들어간다.

```
<!-- agent-harness:begin -->
...조립된 내용...
<!-- agent-harness:end -->
```

- **멱등이다.** 두 번 실행하면 블록이 **교체**되지 쌓이지 않는다.
- **블록 바깥은 한 글자도 바꾸지 않는다.** BOM 이 있던 파일은 BOM 을 그대로 둔다.
- 마커가 없는 파일이면 **끝에 새로 붙이고**, 파일이 아예 없으면 새로 만든다.
- 산출물(`harness-CLAUDE.md`)과 블록 안쪽은 **설치기가 다시 쓴다.** 거기서 고치지 말고
  이 폴더의 조각을 고친 뒤 다시 설치한다.

### 다시 실행하면

조립의 근거는 **그때 준 옵션이 아니라 마커에 기록된 설치 상태**다. 전에 `-Pack documents`
로 깔았다면, 이번에 안 줘도 그 마커가 남아 있는 한 조각은 결과에 그대로 있다. 토픽도
같은 자리에 자기 마커(`.agent-harness-topics`)를 두고 팩 마커와 같은 규칙으로 누적된다.
`-Status` / `--status` 로 설치한 팩·토픽을 확인할 수 있다.

## 올리고 내리기

- 설치처에서 자란 것을 레포로 **올리는** 절차는 `skills/_core/harness-repo` 의 등록 절차
- 레포의 새 조각을 설치처로 **내리는** 것은 설치기가 한다 (같은 스킬의 가져오기 절차 참고)
