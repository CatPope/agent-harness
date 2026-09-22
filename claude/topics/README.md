# claude/topics/

**워크플로우·팩과 무관하게 따로 골라 붙이는 조각**을 둔다.

다른 세 축(`_core.md` · `workflows/` · `packs/`)은 **무엇을 설치했는가**에 따라 자동으로
따라온다. 토픽은 그 축에 걸리지 않는다 — 어떤 워크플로우를 쓰든, 팩을 하나도 안 깔았든
필요하면 붙이는 규칙이다. 그래서 선택은 설치 옵션으로 한다.

```powershell
.\install.ps1 -Project . -Workflow supervisor-worker -Topic implementation
```
```bash
./install.sh --project . --workflow supervisor-worker --topic implementation
```

## 규약

- 파일 하나가 토픽 하나다. **파일명(확장자 제외)이 곧 토픽 id** 다 —
  `implementation.md` → `-Topic implementation`. 매니페스트가 따로 없다.
- **토픽은 조각만 기여한다. 스킬을 끌고 오지 않는다.** 스킬이 필요하면 그것은
  워크플로우나 팩의 일이다.
- 없는 이름을 주면 설치기가 **거부한다.** 오타를 조용히 넘기면 붙은 줄 알고 일하게 된다.
- 토픽은 워크플로우·팩과 **함께** 고른다. 토픽만 주는 설치는 받지 않는다 —
  설치할 스킬이 없기 때문이다.
- 내용 규약은 상위 `claude/README.md` 와 같다: 어느 프로젝트에서나 통하는 규칙만,
  경로는 대명사로.

## 무엇을 토픽으로 두는가

어떤 스킬의 **"항상 켜져 있어야 하는 부분"** 인데 그 스킬이 특정 워크플로우·팩에
묶이지 않을 때다. 예: `implementation` 은 [[implementation-conduct]] 에서 추린 것으로,
구현자가 사람이든 실행자 에이전트든 관리자 자신이든 같이 적용되므로 어느 축에도 속하지 않는다.
