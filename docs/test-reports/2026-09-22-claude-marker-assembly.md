# 테스트 보고서 — CLAUDE.md 마커 기반 조립

- **날짜:** 2026-09-22
- **대상:** `main` 브랜치의 커밋되지 않은 CLAUDE.md 조각 배포 변경
- **범위:** `install.ps1`, `install.sh`, 매니페스트·조각·문서, 설치기 회귀 검증
- **환경:** Windows PowerShell 5, Git for Windows Bash, Python; 설치 대상은 Git Bash가 만든 시스템 임시 폴더만 사용
- **최종 결과:** PASS

## 기능 검증 1~10

실행:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/verify_installers.ps1
```

최종 임시 루트:

```text
C:\Users\qwer\AppData\Local\Temp\agent-harness-verify.021Xgg
```

1. **재현 시나리오 소멸 — PASS.** 두 설치기에서 `documents` 다음 `skillcraft`를 설치했다. 최종 `<!-- from: -->` 줄은 아래 두 줄이며 순서도 같았다.

   ```text
   <!-- from: claude/packs/documents.md -->
   <!-- from: claude/packs/skillcraft.md -->
   ```

2. **토픽 누적 — PASS.** 두 설치기 모두 `implementation` 토픽을 설치한 뒤 토픽 옵션 없이 `skillcraft`를 다시 설치해도 마지막 조각이 `claude/topics/implementation.md`였다.
3. **토픽 마커 형식 — PASS.** 토픽을 두 번 줘도 마커는 `implementation` 한 항목이었다. 팩 마커는 `documents, skillcraft`였고 두 마커 모두 BOM이 없었다.
4. **상태 출력 — PASS.** 프로젝트·전역, sh·PowerShell 네 경우 모두 `설치한 토픽: implementation`을 출력했다. 전역 검사는 `CLAUDE_SKILLS_DIR`/`AGENTS_SKILLS_DIR`/`CLAUDE_TOOLS_DIR` 또는 `-ClaudeDir`/`-AgentsDir`를 임시 폴더로 덮어썼다.
5. **두 설치기 산출물 동일 — PASS.** 동일 설치 상태의 `harness-CLAUDE.md` MD5는 둘 다 `4B05EDA3876F3E4E2E664614EC9AB4CA`였다.
6. **멱등성 — PASS.** 두 설치기에서 `--with-claude-md`/`-WithClaudeMd`를 각각 3회 실행했다. begin/end 블록은 각 1개였고, 블록 앞 `BEFORE`와 뒤 `AFTER`가 보존됐으며 원본 BOM도 보존됐다. 별도 산출물에는 BOM이 없었다. 최종 회귀 실행의 2·3회차는 `복사 0개, 2개 건너뜀(같음 2 · 변경됨 0), 0개 실패`였다.
7. **팩 전용 설치의 `_core` 배제 — PASS.** 팩만 설치한 결과의 출처 줄에 `claude/_core.md`가 없었다.
8. **가짜 마커 id — PASS.** 두 설치기 모두 `ghost-pack`과 `ghost-topic`을 경고하고 정상 종료(exit 0)했으며 documents 조각을 계속 만들었다.
9. **`claude: null` — PASS.** 워크플로우 마커를 `codex-review`로 두고 팩 설치를 실행했다. 두 설치기 모두 `_core`와 documents만 조립하고 결측 조각 경고 없이 종료했다.
10. **기존 기능 무회귀 — PASS.** documents 최초 설치는 두 설치기 모두 `복사 2개`, 재실행은 `복사 0개, 2개 건너뜀(같음 2 · 변경됨 0), 0개 실패`였다. 목록에는 `supervisor-worker`, `documents`, `implementation`이 모두 나왔다.

## 로컬 CI 11

- 허용된 스킬 24개에 `python tools/check_skill.py <skill-dir>` 실행: `CHECK_SKILL_SUMMARY count=24 failed=0`.
- 사용자 지시에 따라 `skills/_core/task-brief`와 `skills/_core/delegation-retro`는 열거나 검사하지 않았다.
- `python tools/check_manifests.py`: `18 check(s), 0 failing, 1 warning(s)`. 경고는 `codex-review`가 `status=planned`이고 스킬 목록이 비었다는 기존 경고다. M6·M7 포함 모두 통과했다.
- 옵션 짝 9쌍: `OPTION_PAIRS_PASS count=9`.
- `grep -n "$(printf '\t')" install.ps1 install.sh`: 출력 없음, exit 1(매치 없음).
- `bash -n install.sh`: `BASH_N_PASS`.
- `git diff --check`(금지 경로 제외): exit 0.

## 실행 중 하네스 오류

제품 실패와 구분해 기록한다.

- 첫 인라인 시도: 존재하지 않는 프로젝트 경로와 Git Bash 경로 변환 오류로 시작 전 실패.
- 둘째 시도: PowerShell이 만든 임시 폴더를 Git Bash가 쓰지 못해 시작 전 실패.
- 셋째 시도: 압축한 인라인 PowerShell의 파서 오류로 시작 전 실패.
- 최초 파일 실행: Windows PowerShell 5가 BOM 없는 UTF-8의 한글 리터럴을 ANSI로 읽어 시작 전 실패. 회귀 스크립트를 ASCII 안전 리터럴로 고쳐 직접 실행 가능하게 했다.
- 한 차례 기능 실행: 전역 상태 검사용 환경변수가 후속 프로젝트 설치에 남아 하네스가 중단됐다. 상태 검사 직후 환경변수를 제거하도록 수정했다.
- 옵션·탭의 첫 CI 명령: PowerShell→Bash 인용 오류. 옵션 검사는 PowerShell 리터럴 검색으로, 탭 grep은 환경변수를 통한 `eval`로 정확한 명령을 전달해 재실행했다.

초기 회귀 실행은 워크플로우 옵션을 사용해 `_core` 전체를 임시 설치처로 복사했다. 이 과정에서 금지된 다른 세션의 두 디렉터리도 설치기의 자동 복사 대상이 됐지만, 내용을 직접 열거나 수정하지는 않았다. 최종 회귀 스크립트는 워크플로우 마커를 임시로 시드하고 팩만 설치하도록 바꿔 두 경로를 파일 I/O 대상으로 삼지 않는다.

## 미결

없음. 시각 테스트가 아니므로 첨부 이미지가 없다.
