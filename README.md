# agent-harness

여러 PC·여러 프로젝트에서 그대로 쓰는 **에이전트 스킬 모음**입니다. 고르는 축은 둘입니다.

```
워크플로우   일하는 방식.  고르면 _core 공통 스킬이 함께 온다
팩           주제별 묶음.  자기 스킬만 온다. 여러 개를 함께 골라도 된다
```

포터빌리티 **규약과 린터** 모두 이 레포가 갖습니다 —
`skills/skillcraft/portable-skill-authoring` 이 정본입니다.

> 📦 **2026-09-21, [`CatPope/doc-skills`](https://github.com/CatPope/doc-skills) 를 이 레포로 병합했습니다.**
> 문서 편집 스킬은 `documents` 팩, 스킬 제작·수리 스킬은 `skillcraft` 팩으로 들어왔습니다.
> 스킬을 두 레포에 나눠 두니 **규약은 저쪽, 쓰는 쪽은 이쪽**이 되어 동기화 절차가 어느
> 쪽에도 없었습니다. 실제로 doc-skills 는 설치 스크립트가 없어 설치처 사본이 레포보다
> 하루 뒤진 채 방치돼 있었고, 린터는 **어느 레포의 CI 에서도 돌지 않았습니다.**

## 구조

```
agent-harness/
  workflows/          워크플로우 매니페스트 (어떤 스킬을 묶을지)
  packs/              팩 매니페스트 (주제별 묶음)
  claude/             CLAUDE.md 조각
  skills/
    _core/            워크플로우를 고르면 항상 함께 오는 공통 스킬
    <workflow-id>/    해당 워크플로우에서만 설치되는 고유 스킬
    <pack-id>/        해당 팩에서만 설치되는 스킬
  shared/             여러 스킬이 함께 쓰는 공용 레이어 (포맷 무관 유틸)
  hooks/              훅 설정
  tools/              레포에서 쓰는 도구. check_skill.py 는 린터로 넘기는 런처
  docs/workflows/     워크플로우별 다이어그램·설명
  install.ps1         Windows
  install.sh          macOS / Linux
```

🔴 **스킬은 `shared/` 를 하드코딩 경로 없이 참조합니다.** 레포 루트를 거슬러 올라가
찾습니다(`skills/skillcraft/portable-skill-authoring/templates/repo_root.py`).
그래서 **자기완결의 단위는 개별 폴더가 아니라 레포 전체**입니다 — 설치기가 스킬 폴더만
복사하므로, `shared/` 에 실제 코드를 올릴 때는 설치 경로도 함께 손봐야 합니다.
(지금 `shared/` 에는 README 뿐이라 깨지는 스킬은 없습니다.)

**하네스 = `CLAUDE.md` + 스킬 + 훅.** 세 가지를 묶어 부르는 말이다.

🔴 **설치는 복사다 — 링크가 아니다.** 예전에는 정션으로 묶여 있어 설치처에서 스킬을 고치면
이 레포의 원본이 즉시 바뀌었다. 그러면 그 스킬을 쓰는 **다른 프로젝트가 전부 영향을 받고**,
공개 레포라면 고치는 순간 올라갈 준비가 된다. 무엇보다 "올릴 때 일반화한다" 는 절차가
성립하지 않는다 — 일반화 전 상태가 남아 있지 않기 때문이다.

설치는 한 방향이다: **레포 → 설치처.** 반대 방향은 `skills/_core/harness-repo` 의
등록 절차(범용/전용 구분 → 일반화 → 병합 검토 → 릴리즈 → push)를 거친다.

## 설치

```powershell
# Windows
.\install.ps1 -List
.\install.ps1 -Project . -Workflow supervisor-worker          # 권장
.\install.ps1 -Project . -Workflow supervisor-worker -Pack documents -WithLinter
.\install.ps1 -Project . -Status
.\install.ps1 -Workflow supervisor-worker                     # 전역
```

```bash
# macOS / Linux
./install.sh --list
./install.sh --project . --workflow supervisor-worker          # 권장
./install.sh --project . --workflow supervisor-worker --pack documents --with-linter
./install.sh --project . --status
./install.sh --workflow supervisor-worker                      # 전역
```

**워크플로우와 팩은 함께 줘도 되고, 팩만 줘도 됩니다.** 팩만 고르면 `_core` 는 오지
않습니다 — 문서 편집만 하려는 사람에게 위임·검수 스킬 17개는 짐입니다.

### 🔵 `-Project` 를 권장합니다

설치처는 두 가지 중에 고릅니다.

| | 설치처 | 마커·린터 | 쓸 때 |
|---|---|---|---|
| **프로젝트** `-Project <path>` | `<path>/.claude/skills` **한 곳** | `<path>/.claude/` 안 | 권장 — 기본으로 이것을 쓰십시오 |
| 전역 (옵션 없음) | `~/.claude/skills` · `~/.agents/skills` **두 곳** | `~/.agents/skills` · `~/.claude/tools` | 모든 프로젝트에서 쓸 스킬만 |

**왜 프로젝트 쪽이 기본인가.** 설치처는 스킬을 이 일에 맞게 고치는 자리입니다(레포는
일반화된 것을 담습니다). 전역에 깔면 **그 수정이 모든 프로젝트에 퍼집니다** — A 프로젝트의
사건 기록을 B 프로젝트의 에이전트가 읽게 됩니다. 정션을 걷어낸 이유가 레포 오염이었는데,
전역 설치는 같은 문제를 설치처 층에서 되풀이합니다. 프로젝트에 깔면 고친 것이 거기 머뭅니다.

덤으로, 프로젝트에 깔면 **그 폴더만 보고 어떤 하네스로 일했는지 알 수 있습니다.** 전역이면
기계 상태에 달려 있어, 같은 폴더를 다른 기계에서 열면 스킬이 없습니다.

🔴 **경로는 필수 인자입니다. 기본값이 없습니다.** 현재 폴더에 깔 때도 `-Project .` 로
명시해야 합니다. 엉뚱한 폴더에 까는 사고는 일어나기는 쉽고 알아채기는 어렵기 때문에,
어디에 까는지를 매번 손으로 적게 했습니다. 없는 폴더를 주면 **만들지 않고 거부합니다** —
오타로 빈 폴더가 생기면 깔렸다고 믿은 채 스킬 없는 곳에서 일하게 됩니다.

전역 설치의 마커 위치(`~/.agents/skills`)는 그대로입니다. 이미 깔아 둔 것은 영향받지 않습니다.

### 복사이지 링크가 아니다

스킬을 설치처에 **복사**합니다. 링크가 아니므로 레포에서 고친 것이 저절로 오지
않습니다 — 그것이 대가입니다. 대신 설치처에서 무엇을 고쳐도 레포가 오염되지 않습니다.

설치기는 명령을 부른 것으로 성공을 세지 않고, **`SKILL.md` 가 실제로 놓였는지 확인한 뒤**
셉니다. 수가 맞지 않으면 어느 경로가 왜 실패했는지 함께 출력합니다.

### 이미 설치돼 있으면

위 표의 "설치처"는 `-Project` 를 줬으면 그 프로젝트 폴더 하나, 안 줬으면 전역 두 곳입니다.

| 설치처 상태 | 기본 | `-Force` / `--force` |
|---|---|---|
| 없음 | 복사 | 복사 |
| 폴더가 있음 | **건너뜀** | `install.ps1` → **지우고 덮어씀**<br>`install.sh` → 지우지 않고 실패로 보고 |
| 예전 정션·심링크 | **끊고 복사** | 끊고 복사 |

⚠️ **두 설치기의 `--force` 동작이 다릅니다.** `install.sh` 에는 링크 시절 로직이 남아 있어,
실제 폴더를 만나면 `--force` 를 줘도 지우지 않고 실패로 셉니다. 고치기 전까지는
플랫폼마다 결과가 다르다는 것을 알고 쓰십시오.

### 🔴 `-Force` 는 권장하지 않습니다

`install.ps1 -Force` 는 **이미 있는 스킬 폴더를 지우고** 레포 것으로 덮어씁니다.

- 설치처에서 고친 내용이 **사라집니다.**
- 복사본에는 이력이 없어 **되돌릴 방법이 없습니다.** git 에 있는 것은 레포 쪽뿐입니다.
- 설치처는 이 기계에 맞춰 구체화된 자리이고, 레포는 일반화된 것을 담습니다.
  덮어쓰는 것은 **맞춰 둔 것을 버리고 일반형을 되가져오는 일**입니다.

**레포의 새 내용을 받고 싶다면 `-Force` 가 아니라 가져오기 절차를 쓰십시오.**
`skills/_core/harness-repo` 에 있으며, 스킬마다 **새것 / 다름 / 로컬 전용** 으로 갈라
필요한 것만 병합합니다.

`-Force` 가 맞는 때는 **설치처에 지킬 것이 없다고 확신할 때**뿐입니다 — 새 기계이거나,
로컬에서 한 번도 건드리지 않은 스킬입니다.

### 왜 링크를 쓰지 않는가

Windows에서 심볼릭 링크는 관리자 권한을 요구하지만 디렉터리 정션(`mklink /J`)은
일반 권한으로 만들어집니다. 그래서 예전에는 정션을 썼습니다.

**그것이 문제였습니다.** 정션이면 설치처와 레포가 같은 파일이라, 프로젝트를 하면서
스킬을 고치는 순간 공유 원본이 바뀝니다. 그 스킬을 쓰는 다른 프로젝트가 전부 영향을
받고, "올릴 때 일반화한다" 는 절차도 성립하지 않습니다 — 일반화 전 상태가 남지 않으니까요.
2026-09-17 에 정션 34개를 끊고 복사로 바꿨습니다.

## 워크플로우

| id | 상태 | 내용 |
|----|------|------|
| `supervisor-worker` | active | Claude가 명세·역할배분·검수, Codex가 정밀 구현. 같은 Codex 세션을 유지하며 구조화 완료보고(JSON)를 받는다. |
| `codex-review` | planned | 역할이 뒤집힌 구성. Claude가 설계·개발, Codex가 적대적 검토. `openai/codex-plugin-cc` 경유. |

`status`가 `active`가 아니면 설치되지 않습니다.

## 팩

| id | 상태 | 내용 |
|----|------|------|
| `documents` | active | 한글 `.hwpx` 문서를 실제로 만들고 고치는 스킬. 편집 가능한 OWPML 표 삽입, 이미지로 박힌 표의 복원 |
| `skillcraft` | active | 스킬을 만들고 고치는 메타 도구. 포터빌리티 규약·린터·템플릿, OPC/ZIP 진단기 |

둘 다 `CatPope/doc-skills` 에서 왔습니다. **본문은 영어입니다** — 들여온 그대로 두었고,
번역하면 규약 문장이 뭉개질 위험이 커서 손대지 않았습니다.

## 스킬

### `_core` — 항상 설치

| 스킬 | 역할 |
|------|------|
| `task-brief` | 넘길 작업지시서를 쓴다. 완료 기준·금지사항·권한 경계를 갖춰 받는 쪽이 추측하지 않게 한다 |
| `work-review` | 받은 결과를 검증한다. "완료했습니다"를 믿지 않고 증거와 대조한다 |
| `verification-route` | **무엇으로** 검증할지 고른다. 화면 직접 조작은 사다리의 맨 아래 칸이다 |
| `progress-log` | 결정·정정을 진행상황 문서에 반영한다. 요청을 기다리지 않는다 |
| `compact-checkpoint` | 대화 압축 예고를 받으면 그 전에 문서·스킬을 먼저 갱신한다 |
| `bottleneck-review` | 여러 세션을 누적해 무엇이 시간을 먹었는지 가른다. **없애면 안 되는 것**부터 분리한다 |
| `background-task-watchdog` | 백그라운드 작업은 알림 없이 끝나거나 무한 루프에 빠진다. 시간 기준으로 직접 확인한다 |
| `test-documentation` | 테스트 실행마다 날짜가 붙은 보고서를 남긴다. 캡처가 나왔으면 첨부가 필수 |
| `daily-report` | 회사 제출용 일일 업무보고. **행동이 아니라 결과물** 기준으로 개괄식 |
| `agent-operations` | 서브에이전트 운영 규칙을 정본 스킬에 기록해 세션 후에도 복구되게 한다 |
| `skill-generalize` | 프로젝트에서 자란 스킬을 다른 곳에서도 쓰게 일반화한다. 노하우는 남기고 그때의 결정만 걷어낸다 |
| `result-record` | 실험·테스트 결과를 **재현·비교 가능하게** 남긴다 |
| `adoption-proposal` | 근거를 갖춰 **채택을 요청**한다. 읽는 사람은 결정권자 |
| `docs-append` | 공유 Google 문서 끝에 덧붙인다. 외부 쓰기라 명시적 지시에만 동작 |
| `implementation-conduct` | 지시서를 받아 **구현할 때** 지키는 수칙. 원본 보존·주석·단계별 실행·로그·완료 기록·권한 경계 |
| `refactor` | 동작을 바꾸지 않는 구조 개선. 읽기 우선 → 계획 승인 → 한 덩어리씩 → 커밋 |

`implementation-conduct` 와 `refactor` 만 `audience: shared` 다. 나머지 `_core` 는 관리자용이다 —
이 둘은 **"누가"가 아니라 "무엇을 하는가"에 붙는** 규칙이라, 워크플로우에 따라 구현자가
바뀌어도 그대로 적용된다.

> `refactor` 는 이 저장소에서 **유일하게 본문이 영어인 스킬**이다. 다른 곳에서 만들어진
> 것을 그대로 들여왔고, 번역하면 문장이 뭉개질 위험이 커서 원문을 유지했다.

`result-record` 와 `adoption-proposal` 은 둘 다 "보고서"지만 **목적이 다르다** —
전자는 우리가 나중에 다시 보려는 기록이고, 후자는 남에게 판단을 요청하는 문서다.
요구되는 내용도 다르므로 섞지 않는다.

일을 넘기고, 검증하고, 기록하는 일은 상대가 Codex든 사람이든 서브에이전트든 같기 때문에
공통입니다.

### `supervisor-worker` — 선택 시 설치

| 스킬 | 역할 |
|------|------|
| `role-split` | 무엇을 Claude가 직접 하고 무엇을 넘길지 가른다. 가장 되돌리기 비싼 분기 |
| `codex-delegate` | 같은 Codex 세션을 유지하며 위임하고 구조화 완료보고를 받는 메커니즘 |
| `codex-completion-report` | 실행자가 남기는 완료 보고서 형식 |
| `codex-plugin-flow` | 같은 워크플로우를 `openai/codex-plugin-cc` 로 도는 **대안 메커니즘**. ⏸ 시범 보류 중 |

넷 다 **"Codex가 실행자"라는 전제**에 묶여 있어 공통이 아닙니다.

`codex-delegate` 와 `codex-plugin-flow` 는 **같은 자리를 두고 겨루는 두 메커니즘**입니다.
기본은 `codex-delegate` 이고, 어느 쪽을 쓰는지는 프로젝트 지침(`CLAUDE.md` 등)의 스위치가
정합니다. 플러그인 쪽은 2026-09-11 부터 보류 상태이며, 스킬 맨 앞의 **재개 체크리스트
4항목**을 통과하기 전에는 켜지 않습니다.

### `documents` — 팩 선택 시 설치

| 스킬 | 역할 |
|------|------|
| `hwpx-table-kit` | 기존 한글 `.hwpx` 를 손상시키지 않고 편집 가능한 OWPML 표를 넣는다. 재사용 엔진 |
| `hwpx-image-table-to-table` | `.hwpx` 안에 **이미지로 박힌 표**를 진짜 표로 되돌린다. 필요하면 `.xlsx` 에서 데이터를 뽑는다 |

뒤엣것은 레시피이고 앞엣것을 엔진으로 씁니다. **따로 설치하지 말고 팩째 설치하세요.**

### `skillcraft` — 팩 선택 시 설치

| 스킬 | 역할 |
|------|------|
| `portable-skill-authoring` | 노 베이스 에이전트가 clone 만으로 쓸 수 있는 스킬을 쓰는 규칙 + 린터(`check_skill.py`) + 템플릿 |
| `skill-repair` | 스킬대로 했는데 깨졌을 때 진단·수정하고 그 수정을 스킬에 되먹인다. OPC/ZIP 진단기 포함 |

🔴 **포터빌리티 린터의 정본이 여기 있습니다** —
`skills/skillcraft/portable-skill-authoring/scripts/check_skill.py`.
사본을 따로 두지 않습니다. 스킬은 자기 스크립트를 함께 지녀야 홀로 쓸 수 있으므로
그 자리가 정본이고, `tools/check_skill.py` 는 **검사 로직이 전혀 없는 런처**입니다.

## 규약

- `audience:` — `manager` / `executor` / `shared`. 누가 쓰는 스킬인지 프론트매터에 명시합니다.
- `## 이력 (필수 기록)` — 생성일·업데이트 횟수·사용 이력. **왜 그렇게 바뀌었는지**를 남깁니다.
- 스킬끼리는 `[[skill-name]]` 로 참조합니다. 함수 호출이 아니라 "이 시점에 저걸 읽어라"입니다.
- 특정 프로젝트의 경로·인명·문서 ID를 스킬 본문에 적지 않습니다. 프로젝트 문서로 넘깁니다.

## 검증

커밋 전에 포터빌리티 린터를 돌립니다. **린터는 이 레포 안에 있습니다** —
다른 레포를 받아 둘 필요가 없습니다.

```bash
python tools/check_skill.py skills/_core
python tools/check_skill.py skills/supervisor-worker
python tools/check_skill.py skills/documents
python tools/check_skill.py skills/skillcraft
```

`tools/check_skill.py` 는 `skills/skillcraft/portable-skill-authoring/scripts/check_skill.py`
로 넘기는 런처입니다. 정본을 직접 불러도 결과는 같습니다.

### 검사는 두 층입니다

린터는 **스킬 안쪽**만 봅니다. 스킬을 만들어 놓고 매니페스트에 넣지 않으면 린터는
통과하는데 **설치기가 나르지 않아 설치처에는 그냥 없습니다.** 그래서 바깥 층을 따로 봅니다.

```bash
python tools/check_manifests.py
```

| 항목 | 보는 것 |
|---|---|
| M1 | 매니페스트의 `id` 가 파일명과 같은가 |
| M2 | 매니페스트가 부르는 스킬이 실제로 있는가 |
| M3 | `skills/<묶음>/` 의 폴더가 전부 매니페스트에 올라 있는가 (`_core` 는 면제) |
| M4 | `skills/<묶음>/` 에 대응하는 매니페스트가 있는가 |
| M5 | 린터 런처가 가리키는 정본이 실제로 있는가 |

## CI

| 워크플로 | 언제 | 하는 일 |
|---|---|---|
| `harness-lint` | `skills/` · `shared/` · `workflows/` · `packs/` · `tools/` · 설치기 변경 시 | ① 포터빌리티 린터 ② 매니페스트 정합성 ③ 두 설치기가 같은 옵션을 받는가 |
| `PR Template Check` | PR 열림·수정 | 필수 절·변경 유형 체크·개요 비어 있지 않음(error) / 선언한 유형과 실제로 손댄 폴더 대조(notice) |

**PR 템플릿의 '변경 유형'은 폴더에 맞춰 나뉩니다** — 스킬 / 훅 / CLAUDE.md 조각 /
워크플로우·팩 매니페스트 / 공용 레이어 / 설치기·도구 / 문서 / CI·레포 설정.
이 레포가 스킬 모음이 아니라 **하네스와 그 배포 장치**를 함께 담기 때문입니다.

🔴 **설치기는 둘이 짝입니다.** `install.ps1` 과 `install.sh` 중 한쪽만 바뀌면 CI 가
경고합니다. 실제로 2026-09 에 `install.sh` 의 `--force` 만 옛 로직으로 남아
**두 번째 실행부터 전 항목이 실패**한 적이 있습니다.

**설치처에도 두고 싶으면 `-WithLinter` / `--with-linter`** 를 붙입니다. 선택입니다 —
없어도 스킬은 정상 동작하고, 스킬을 **고칠** 사람만 필요합니다.

```powershell
.\install.ps1 -Pack skillcraft -WithLinter   # -> %USERPROFILE%\.claude\tools\check_skill.py
```
```bash
./install.sh --pack skillcraft --with-linter  # -> ~/.claude/tools/check_skill.py
```

린터는 스킬과 달리 **설치처에서 고칠 것이 아니라 그대로 쓰는 도구**이므로,
이미 있으면 말없이 최신본으로 덮어씁니다. 설치되는 것은 **정본 파일 자체**라
설치처에서 레포 없이도 단독으로 돌아갑니다.

`FAIL`이 하나라도 있으면 커밋하지 않습니다.
