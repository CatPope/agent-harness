---
id: test-documentation
name: test-documentation
description: Record every test run as a durable, dated report. Whenever you execute tests in a repo — unit, build/vet/lint, integration/smoke, or visual/UI — write a report under docs/test-reports/. When the test produced capture images (screenshots of a UI, a rendered chart, a diff), attaching those images to the report is MANDATORY — a visual test with no attached capture is an incomplete report. Standalone and project-agnostic; not tied to any document-governance suite.
triggers:
  - "/test-documentation"
  - "test-documentation"
  - "테스트 문서화"
  - "테스트 보고서"
  - "테스트 결과 남겨"
  - "테스트 기록"
  - "test report"
tags:
  - testing
  - documentation
source: manual
---

# test-documentation — 테스트 문서화 (필수, 캡처 있으면 첨부 필수)

**테스트를 실행하면 반드시 보고서를 남긴다. 그 테스트가 캡처 이미지(스크린샷·렌더 결과)를 만들었으면 그 이미지를 반드시 보고서에 첨부한다.** 문서 없는 테스트, 또는 캡처가 있는데 첨부 없는 시각 테스트는 미완으로 간주한다.

프로젝트 무관 글로벌 규약이다. 특정 문서 거버넌스 체계(SRS/PRD/ADR 등)에 속하지 않는, 테스트 증거 기록만을 위한 독립 스킬이다.

## 적용 대상 (하나라도 실행했으면)

- 단위 테스트 / 빌드·vet·lint
- 통합·smoke (실제 스택 위 시나리오)
- **시각/UI 테스트 (스크린샷·렌더 캡처)** → **이미지 첨부 의무**
- 성능·부하, 보안 점검(있을 경우)

## 위치·명명 (기본값)

```
docs/test-reports/
  README.md                      # 인덱스 (한 줄/보고서)
  YYYY-MM-DD-<slug>.md           # 보고서
  assets/<slug>/*.png            # 그 보고서의 캡처 이미지
```

- `<slug>`: 대상 기능 kebab-case (예: `login-flow`, `dashboard-viz`).
- 자산 이미지는 `assets/<slug>/`에 두고 보고서에서 **상대경로**로 임베드(`![](assets/<slug>/x.png)`) — 폴더를 통째로 옮겨도 링크가 살아 있도록.
- 같은 날 같은 기능을 다시 테스트하면 같은 파일에 **회차 섹션 추가**(덮어쓰지 않음). 날짜가 다르면 새 파일.
- 프로젝트가 다른 위치를 정했으면(예: 그 repo의 CLAUDE.md/ops 규칙) 그걸 따른다. 없으면 위 기본값.

## 보고서 양식

```markdown
# 테스트 보고서 — <기능명>

- **날짜:** YYYY-MM-DD
- **대상 변경:** <커밋 sha 또는 브랜치/설명>
- **범위:** <바뀐 파일·기능 한 줄>

## 1. 자동 검증 (빌드/vet/test)
<실행 명령> → 결과. 신규/영향 테스트를 PASS/FAIL로 나열. 실패했다면 그대로 기록(숨기지 않음).

## 2. 시각 검증 — 캡처 첨부 (해당 시 필수)
각 화면/폭 캡처를 임베드하고, 장마다 확인한 것(레이아웃 붕괴·오버플로 없음 등)을 캡션으로.

![설명](assets/<slug>/shot.png)
*캡션 — 무엇을 확인했는지.*

## 3. 데이터/환경 조건
테스트에 쓴 데이터·시드·환경.

## 4. 결과 / 미결
green/red 요약 + 남은 리스크·후속.
```

## 절차

1. 테스트를 돌린다(단위/빌드/스모크/시각).
2. **캡처가 나오는 테스트면** 이미지를 `docs/test-reports/assets/<slug>/`로 옮긴다.
3. `docs/test-reports/YYYY-MM-DD-<slug>.md`를 작성 — 실행 명령·결과·(있으면) 캡처 임베드.
4. `docs/test-reports/README.md` 인덱스에 한 줄 추가.
5. 보고서 + 자산을 그 작업의 커밋에 포함(중간 상태 커밋 금지).

## 원칙

- **캡처 첨부는 협상 불가**: UI/화면 테스트를 돌렸으면 그 스크린샷이 보고서에 있어야 한다. "잘 나왔다"는 서술만으로는 미완.
- **실패도 그대로**: 실패한 테스트는 출력을 포함해 그대로 남긴다 — "대체로 통과" 같은 요약으로 숨기지 않는다.
- **가볍게**: 테스트를 안 돌린 턴, 문서/설정만 바꾼 변경엔 보고서를 강요하지 않는다. 실제로 테스트를 실행했을 때만.
