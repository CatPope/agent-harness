# SQLite 물리 설계

규칙마다 근거(공식 문서 또는 실측)를 붙였다. 실측은 SQLite 3.50.4(파이썬 3.14 번들), 윈도 11 에서 했다.

## 1. 행 크기

레코드는 머리(열마다 형 코드 varint) + 값이다(https://www.sqlite.org/fileformat2.html).

| 값 | 저장 크기 |
|---|---|
| 정수 0, 1 | 0 B (형 코드만) |
| 작은 정수 | 1~2 B. 유닉스 초는 4~6 B |
| TEXT | UTF-8 바이트 그대로. 한글 한 글자 3 B |
| sha1 hex 글자 | 40 B. BLOB 으로 두면 20 B |
| `'YYYY-MM-DD HH:MM:SS'` | 19 B. INTEGER 초면 4~6 B |

- 표 잎 페이지 한 칸에 들어가는 최대 크기는 `U - 35`(4 KB 페이지면 4,061 B). 넘으면 넘침(overflow) 페이지로 이어진다.
- **실측**: 본문 평균 44 B 인 메시지 한 건이 표에서 145 B, UNIQUE 색인에서 59 B, 시각 색인에서 33 B 를 썼다.
  FTS 까지 합치면 약 320 B, 본문의 7배다. 40자 hex 해시와 19자 시각 글자 두 개가 행의 절반을 넘었다.

## 2. rowid 표와 WITHOUT ROWID

- `INTEGER PRIMARY KEY` 는 rowid 의 별칭이다. 표 B-tree 가 이 값으로 정렬된다.
- 시간순으로 늘어나는 rowid 는 트리 오른쪽 끝에만 붙는다. 페이지가 꽉 찬다(실측 잎 채움률 97.7%).
  무작위 키(UUIDv4 같은)는 중간에 끼어들어 페이지를 쪼갠다. 채움률이 떨어지고 쓰기가 흩어진다.
- WITHOUT ROWID 는 PK 가 곧 표의 정렬 키다. B-tree 가 하나 준다.
  행 평균이 페이지의 1/20(4 KB 면 약 200 B)보다 작을 때 좋다. 정수 하나짜리 PK 에는 쓰지 않는다(https://www.sqlite.org/withoutrowid.html).
  **연결표**(`(a_id, b_id)` PK)와 **키-값 표**에 맞다.

## 3. 형과 시각

- 선언형 이름으로 친화도가 정해진다. `DATETIME` 은 NUMERIC 친화도다(https://www.sqlite.org/datatype3.html).
  실측: `DATETIME` 열에 `'2026'` 을 넣으면 정수 2026 이 된다.
- STRICT 표(3.37.0 부터)는 선언한 형만 받는다(https://www.sqlite.org/stricttables.html).
- **시각은 한 형식으로 둔다.** INTEGER UTC 초를 권한다. 작고, 비교가 맞고, 시간대가 모호하지 않다.
  글자는 API·화면 경계에서만 만든다.
- 실측: `'2026-09-30 10:00:00' < '2026-09-30T09:00:00Z'` 가 참이다. 공백(0x20)이 `T`(0x54)보다 작아서다.
  두 형식이 섞인 표끼리 비교하면 순서가 틀린다.

## 4. 색인

| 규칙 | 근거 |
|---|---|
| 질의마다 쓸 색인을 정한다. 받는 질의가 없는 색인은 두지 않는다 | 색인마다 쓰기 비용 |
| 복합 색인의 열 순서는 **등호 열 → 범위 열 → ORDER BY 열** | 범위 조건 뒤의 열은 좁히는 데 못 쓴다 |
| 한 색인이 다른 색인의 앞부분이면 짧은 쪽을 지운다. UNIQUE 제약이 만든 색인도 해당한다 | https://www.sqlite.org/queryplanner.html |
| 목록·통계 질의는 덮는 색인으로 표를 안 가게 한다 | 약 2배 |
| 부분 색인 `WHERE x IS NOT NULL` 은 `x = ?` 질의에 쓰인다 | https://www.sqlite.org/partialindex.html. 실측: `SEARCH link USING COVERING INDEX ux_item (item=?)` |
| 작은 부분집합(`WHERE synced = 0`, `WHERE deleted = 0`)은 부분 색인으로 | 색인이 작고 쓰기가 싸다 |
| FK 자식 열은 어떤 색인의 앞 열이어야 한다 | 없으면 부모를 지우거나 바꿀 때 자식 표를 다 훑는다 |
| OR 로 묶인 조건은 항마다 색인이 있어야 색인을 쓴다 | 하나라도 없으면 전체 훑기 |

질의 계획은 `EXPLAIN QUERY PLAN` 으로 본다(https://www.sqlite.org/eqp.html).

| 계획에 뜨는 말 | 뜻 |
|---|---|
| `SEARCH t USING INDEX i (a=?)` | 색인으로 좁혔다 |
| `SEARCH t USING COVERING INDEX i` | 표를 안 갔다 |
| `SCAN t` | 전체 훑기. 작은 표면 괜찮다 |
| `USE TEMP B-TREE FOR ORDER BY` | 맞는 행을 전부 모아 정렬했다. LIMIT 이 있어도 비용은 맞는 행 수 |
| `AUTOMATIC ... INDEX` | 실행마다 임시 색인을 만든다. 색인이 빠졌다는 신호 |

### 질의 모양 규칙 (실측)

색인이 있어도 플래너가 조인 순서를 고르면서 정렬을 색인에 맡기지 않을 수 있다.
180만 건 표에 `(source_id, ts)` 복합 색인을 더하고 통계를 돌리자, 전체 타임라인(`ORDER BY ts DESC LIMIT 20`)이
0.06 ms 에서 549 ms 가 됐다. 플래너가 작은 표(27행)를 바깥에 두고 행마다 복합 색인으로 읽은 뒤 전부 정렬했다.

| 질의 | 고친 모양 | 180만 건 |
|---|---|---|
| 전체 타임라인 | `FROM (SELECT … FROM 큰표 ORDER BY ts DESC LIMIT :n) x JOIN 작은표 …` | 0.04 ms |
| 전체 타임라인 | `FROM 큰표 CROSS JOIN 작은표 ON …` (SQLite 는 CROSS JOIN 의 왼쪽을 바깥에 고정한다) | 0.03 ms |
| 한 채팅방 | 번호를 먼저 구해 `WHERE source_id = ? ORDER BY ts DESC LIMIT n` | 0.03 ms |
| 여러 채팅방(프로젝트) | `FROM 큰표 INDEXED BY ix_ts CROSS JOIN 작은표 … WHERE 작은표.project_id = ?` | 0.03 ms (행이 많은 프로젝트), 0.25 ms (드문 프로젝트) |
| 여러 채팅방(프로젝트) | 채팅방마다 `LIMIT n` 으로 뽑아 합친 뒤 다시 정렬 | 0.04~0.07 ms |

- `INDEXED BY` 는 그 색인이 없어지면 질의가 오류를 낸다. 조용히 느려지는 것보다 낫다.
- 두 표를 UNION 해 정렬하는 목록은 어떤 색인도 정렬을 받지 못한다. 늘 함께 보이면 슈퍼타입 한 표로 합친다(`03_성능_데이터_모델링.md` §7).
- OFFSET 은 건너뛸 행을 다 읽는다. 끝까지 내려 더 불러오는 목록은 커서(`WHERE (ts, id) < (?, ?) ORDER BY ts DESC, id DESC LIMIT n`)로 한다. 행 값 비교는 3.15.0 부터 된다.

## 5. 통계와 플래너

- ANALYZE 통계가 있어야 플래너가 선택도를 안다. 편중된 데이터에서 특히 중요하다.
- 통계가 생기면 계획이 바뀐다. 좋아질 때가 많지만 위 사례처럼 나빠질 수도 있다. 색인이나 통계를 바꾼 뒤에는 핵심 질의의 계획을 다시 본다.
- 짧은 연결(명령행 도구)은 닫기 전에 `PRAGMA optimize;`.
  긴 연결(서버)은 열 때 `PRAGMA optimize=0x10002;`, 그 뒤 하루 한 번쯤 `PRAGMA optimize;`.
  색인을 만든 뒤에도 돌린다(https://www.sqlite.org/lang_analyze.html).

## 6. 트랜잭션과 잠금

- 쓰는 쪽은 언제나 하나다.
- `BEGIN`(DEFERRED)으로 읽다가 쓰기로 올리려는데 다른 연결이 먼저 썼으면 **바로 실패한다**.
  WAL 에서는 스냅숏이 낡아 `SQLITE_BUSY_SNAPSHOT` 이다(https://www.sqlite.org/isolation.html).
  실측: busy_timeout 이 5초인데도 0 ms 만에 `database is locked`.
- **쓰기 트랜잭션은 `BEGIN IMMEDIATE` 로 연다.** 앞선 쓰기가 끝날 때까지 기다렸다가 성공한다(실측 322 ms 기다림).
- busy_timeout 이 없으면 잠겨 있을 때 기다리지 않고 바로 실패한다.

### 파이썬 `sqlite3`

(https://docs.python.org/3.14/library/sqlite3.html)

- `connect()` 기본 `timeout=5.0`. busy_timeout 5000 ms 가 이미 켜져 있다(실측 `PRAGMA busy_timeout = 5000`).
- 기본(`autocommit=LEGACY_TRANSACTION_CONTROL`)은 INSERT·UPDATE·DELETE·REPLACE 앞에서만 몰래 `BEGIN`(DEFERRED)을 연다.
  그 앞의 SELECT 는 트랜잭션 밖이다. 읽고 나서 쓰는 코드가 한 트랜잭션이 아니다.
- 권장: `autocommit=True`(3.12+) 또는 `isolation_level=None` 으로 열고, 쓰기는 `BEGIN IMMEDIATE` … `COMMIT` 을 직접 쓴다.
- 여러 스레드(예: FastAPI 스레드 풀)가 쓰면 요청마다 연결을 열거나, 스레드마다 연결을 둔다. 연결 하나를 스레드끼리 나누지 않는다.

## 7. 저널과 동기화

| 설정 | 언제 |
|---|---|
| `journal_mode=WAL` | 쓰기가 잦고 읽기가 동시에 있을 때. 파일에 남는다(한 번만 설정) |
| `synchronous=NORMAL` | WAL 과 함께. 손상은 없고, 정전 때 마지막 커밋이 되돌아갈 수 있다(https://www.sqlite.org/pragma.html) |
| `synchronous=FULL` | 커밋 하나도 잃으면 안 될 때(돈, 주문). WAL 에서도 커밋마다 동기화 |

WAL 의 조건과 함정(https://www.sqlite.org/wal.html)

- 같은 호스트의 프로세스만. 네트워크 파일시스템에서는 쓰지 않는다.
- 자동 체크포인트는 WAL 이 1000 페이지(약 4 MB)가 되면. 읽기가 쉬지 않고 겹치면 체크포인트가 끝나지 못해 **WAL 이 끝없이 커진다**. 긴 읽기 트랜잭션을 열어 두지 않는다.
- 100 MB 넘는 큰 트랜잭션은 롤백 저널이 빠를 수 있다.
- `-wal` 과 `-shm` 파일이 함께 생긴다. 백업은 파일 복사가 아니라 백업 API 나 `VACUUM INTO` 로.

## 8. 큰 파일

100 KB 보다 작은 BLOB 은 DB 안에서 읽는 편이 빠르고, 크면 파일로 두는 편이 빠르다(https://www.sqlite.org/intern-v-extern-blob.html).
큰 파일은 디렉터리에 두고 DB 에는 경로와 해시만 둔다.

## 9. FTS5 운영

(https://www.sqlite.org/fts5.html)

- 커밋마다 새 세그먼트가 생긴다. 같은 층에 4개(automerge)가 모이면 조금씩 합치고, 16개(crisismerge)면 그 자리에서 합친다.
  한가할 때 `INSERT INTO f(f, rank) VALUES('merge', 500)` 이나 `INSERT INTO f(f) VALUES('optimize')`.
- **외부 콘텐츠 FTS 의 `count(*)` 는 내용 표를 센다.** 색인에서 행이 빠져도 같은 수가 나온다(실측).
  동기화 검사는 `INSERT INTO f(f, rank) VALUES('integrity-check', 1)`. 어긋나면 오류가 난다.
- 사용자 입력은 `"…"` 로 감싸고 안의 `"` 는 `""` 로 바꾼다. 그대로 넣으면 `v2.0` 은 문법 오류, URL 은 `no such column: https`,
  `견적서-최종` 은 `no such column: 최종` 이 된다(실측).
- `ORDER BY rank` 는 맞는 행 전부를 채점한다. 최신순이면 `ORDER BY rowid DESC LIMIT n` 이 일찍 멈출 수 있다.
- 트리거에서 앱 함수(`create_function`)를 부를 수 있다(`trusted_schema=1`, 실측). 함수를 등록하지 않은 연결의 쓰기는
  `no such function` 으로 크게 실패한다. 조용히 어긋나지 않는다.
- 한국어는 기본 토크나이저로 찾지 못한다. 형제 스킬 [[korean-fulltext-search]].

## 10. 공간과 수명 주기

- 지운 행의 페이지는 freelist 로 가서 다시 쓰인다. 파일은 줄지 않는다.
- `auto_vacuum=INCREMENTAL` 은 표를 만들기 전에 정한다. 나중에 바꾸려면 VACUUM 이 필요하다.
- 끝없이 커지는 표(로그, 논리 삭제 행, 세션, 작업 기록)는 설계 때 지우는 규칙과 그 규칙이 쓸 색인을 함께 적는다.

## 11. 운영 점검

| 점검 | 명령 | 주기 |
|---|---|---|
| 무결성 | `PRAGMA quick_check;` (빠름), `PRAGMA integrity_check;` | 백업할 때 |
| FTS 동기화 | `INSERT INTO f(f, rank) VALUES('integrity-check', 1)` | 백업할 때 |
| 통계 | `PRAGMA optimize;` | 위 5절 |
| 크기 | `scripts/sqlite_pages.py <db>` | 달마다. 어느 표가 크는지 본다 |
| 백업 | 백업 API 또는 `VACUUM INTO '<경로>'` | 유일본이면 매일 |
