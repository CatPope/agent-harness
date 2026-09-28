"""1차 WBS 생성기 v2.3 — 막대를 값(우선순위·시작주·끝주)+조건부 서식으로 그리고, 인원별 시트는 일정 관리를 참조한다.
작업 제목은 모든 행에서 C:G 를 병합해 C 에 넣는다(하위 항목은 앞에 빈칸). VBA(양방향 동기화)는 별도 inject_vba.ps1 이 붙인다."""
import copy, datetime as dt, json, os, sys
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter as L
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.formatting.rule import FormulaRule

sys.stdout.reconfigure(encoding='utf-8')
# 양식은 이 스킬의 templates/ 에서 읽고, 결과는 실행 폴더의 out/ 에 쓴다.
HERE = os.path.dirname(os.path.abspath(__file__))
# 사용자 양식이 있으면 TEMPLATE 로 준다. templates/ 의 양식은 사용자 양식이 없을 때만 쓴다.
SRC = os.environ.get('TEMPLATE') or os.path.join(HERE, '..', 'templates', '[양식] WBS_일정관리.xlsx')
OUT_DIR = os.environ.get('OUT_DIR') or os.path.join(os.getcwd(), 'out')
os.makedirs(OUT_DIR, exist_ok=True)
VER = '2.5.0'
SUB_INDENT = '    '                       # 하위 항목 제목 앞 빈칸 (C:G 병합이라 열로 들여쓸 수 없다)
OUT = os.path.join(os.environ.get('TEMP', '.'), f'wbs_v{VER}_nomacro.xlsx')   # 중간 산출물. inject_vba.ps1 이 out 에 .xlsm 으로 저장한다
OUT_HTML = os.path.join(OUT_DIR, f'[1차] WBS_일정관리_v{VER}.html')
HTML_TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wbs_template.html')

START = dt.date(2026, 9, 21)
WEEKS = 9
END = START + dt.timedelta(weeks=WEEKS) - dt.timedelta(days=3)
TODAY = dt.date(2026, 9, 24)
C_PRIO, C_W0, C_W1 = 10, 11, 12          # J 우선순위, K 시작주, L 끝주
FIRST, PER = 13, 5                        # M 열부터 타임라인, 주당 5칸
LASTCOL = FIRST + WEEKS * PER - 1
CF_LAST_ROW = 400
MONTHS = [('9월', 1, 2), ('10월', 3, 6), ('11월', 7, 9)]
SRC_NAME, DST_NAME = '일정 관리', '인원별'

D, K, J, S = '홍길동', '김철수', '이영희', '박민수'
PEOPLE = [
    (D, '프로젝트 관리 · 인프라 · 설계', ''),
    (K, '설계 · 개발 (AI 활용 시안 구현 포함)', ''),
    (J, '와이어프레임 · 사용자 입장의 테스터', ''),
    (S, '개발 (파일 업로드 · 디스코드 공지)', ''),          # 2026-09-24 사용자 배정
]

GREEN, YELLOW = 'FFC6EFCE', 'FFFFEB9C'
FILL = {'S': PatternFill('solid', start_color=GREEN, end_color=GREEN),
        'C': PatternFill('solid', start_color=YELLOW, end_color=YELLOW)}

SECTIONS = [
    ('프로젝트 관리', [
        ('제안서·분업 확정', [D], 'S', 1, 1, 1),
        ('WBS 작성·주간 진척 점검', [D], 'S', 0, 1, 9),
        ('GitHub 레포 운영 규칙 (브랜치·PR·이슈)', [D], 'C', 0, 1, 1),
        ('1차 회고·2차 범위 정리', [D, K, J, S], 'C', 0, 9, 9),     # 세 명 이상 = "전원". VBA 는 비고 없는 사람 모두에게 붙인다
    ]),
    # 2026-09-24 사용자가 v2.3.1 에서 직접 고친 배분 (2.1·2.4·2.6·4.1·4.4·4.7·5.1). 여기가 정본이다
    ('요구분석 및 설계', [
        ('요구사항 정의 (필수 기능 5종)', [D], 'S', 0, 1, 1),
        ('기술 스택 선정', [D, K], 'S', 0, 1, 1),
        ('시스템 아키텍처 설계', [D], 'S', 0, 1, 2),
        ('데이터 모델 설계·ERD', [D], 'S', 0, 2, 2),
        ('API 설계', [D], 'S', 0, 2, 2),                          # 2026-09-25 사용자: 김철수 → 홍길동 (설계 단계 확정)
        ('와이어프레임 초안', [D], 'S', 0, 1, 2),
        ('와이어프레임 설계', [J], 'S', 0, 1, 2),
        ('디자인 시안 구현 (AI 활용)', [K], 'S', 0, 3, 3),
        ('디자인 시안 검수', [J], 'S', 0, 3, 4),
    ]),
    ('인프라 구축', [
        ('미니PC 서버 구성 (OS·계정·방화벽)', [D], 'S', 0, 1, 2),
        ('도메인 구매·DNS·HTTPS 인증서', [D], 'S', 0, 2, 2),
        ('DB·파일 저장소·백업 구성', [D], 'S', 0, 3, 3),
        ('배포 자동화 (CI/CD)', [D], 'C', 0, 4, 4),
        ('운영 점검 (로그·장애 알림)', [D], 'C', 0, 8, 8),
    ]),
    ('기능 개발 (서버 + 화면)', [
        ('프로젝트 골격·개발환경', [K], 'S', 0, 2, 3),
        ('공통 레이아웃·반응형 (크로스 플랫폼)', [K], 'S', 0, 3, 4),
        ('회원가입·로그인', [K], 'S', 0, 4, 4),
        ('모임 일정 관리', [K], 'S', 0, 5, 6),                     # 하위 항목(개인 일정·빈 시간)은 사용자가 뺌
        ('파일 업로드·자료 공유', [S], 'S', 0, 5, 6),              # 로그인(4주차) 뒤 김철수과 나란히
        ('디스코드 공지 (공지 양식 적용)', [S], 'S', 0, 7, 7),
        ('관리자 페이지', [D], 'S', 0, 7, 7),
    ]),
    ('사용자 테스트 및 오픈', [
        ('사용자 테스트 시나리오 작성', [K, S, D], 'S', 0, 4, 5),
        ('기능별 사용자 테스트 (완성되는 대로)', [J], 'S', 0, 5, 9),
        ('크로스 플랫폼 확인 (PC·모바일 브라우저)', [J], 'S', 0, 9, 9),
        ('버그 수정', [K, S], 'S', 0, 8, 9),
        ('운영 배포·1차 오픈', [D], 'S', 0, 9, 9),
    ]),
]

GLOSSARY = [
    ('1차 개발', f'필수 기능(디스코드 공지·모임 일정 관리·파일 업로드·관리자 페이지·회원가입/로그인)을 오픈하는 단계. 기간은 {START:%Y-%m-%d} ~ {END:%Y-%m-%d} (9주).'),
    ('2차 개발', '선택 기능 일부를 붙이는 단계. 범위와 기한은 1차 회고에서 정한다.'),
    ('Should / Could', 'Should(초록)는 1차 오픈에 꼭 필요한 작업, Could(노랑)는 있으면 좋지만 일정이 밀리면 2차로 미룰 수 있는 작업. 우선순위 칸에 S/C 로 적으면 막대 색이 따라 바뀐다.'),
    ('시작주 · 끝주', '막대는 색칠하는 것이 아니라 시작주·끝주 숫자로 그려진다(조건부 서식). 숫자를 바꾸면 막대가 옮겨진다. 1W = 09/21 주.'),
    ('인원별 시트', '일정 관리 시트를 사람별로 다시 묶어 보여 준다. 시트를 열 때마다 원본에서 다시 만들어지고, 여기서 고친 값은 매크로가 일정 관리 시트에 써 넣는다. 매크로(콘텐츠 사용)를 켜야 동작한다.'),
    ('공통 빈 시간', '회원 각자가 등록한 일정을 겹쳐 보고, 모두가 비어 있는 시간대를 뽑은 것. 모임 날짜를 정하는 근거가 된다.'),
    ('공지 양식', '매번 쓰는 공지 문구의 틀. 빈칸만 채우면 공지가 완성되게 해서, 문구를 AI 에 가공 요청하던 수고를 없앤다.'),
    ('디스코드 웹훅', '외부 프로그램이 디스코드 채널에 메시지를 올리는 주소. 봇 없이도 공지를 보낼 수 있다.'),
    ('미니PC 서버', '모임이 직접 운영하는 소형 PC 서버. 웹사이트·DB·업로드 파일이 여기에 올라간다.'),
    ('크로스 플랫폼', 'PC·모바일 등 기기와 브라우저가 달라도 같은 기능을 쓸 수 있는 것. 1차에서는 반응형 웹으로 대응한다.'),
    ('디자인 시안', '와이어프레임(이영희)을 바탕으로 AI 를 써서 만든 화면 초안(김철수). 이영희이 사용자 입장에서 검수한다.'),
    ('사용자 테스트', '개발자가 아닌 사용자 입장에서 기능을 써 보고 불편·오류를 적는 것. 이영희이 맡는다.'),
    ('버퍼', '일정이 밀릴 때를 대비해 비워 둔 기간. 1차는 9주차를 테스트·수정·오픈 전용으로 둔다.'),
    ('임계경로', '가장 긴 의존 사슬. 이 경로가 밀리면 전체 일정이 밀린다. 본 프로젝트는 기술 스택 선정 → 프로젝트 골격 → 회원가입·로그인 → 기능 개발(개발자 1명) → 사용자 테스트 → 운영 배포.'),
    ('문서 버전', 'X.Y.Z. X 는 기간·범위·구조가 바뀔 때, Y 는 항목·배분·시트 기능이 바뀔 때, Z 는 색·서식·오탈자 수정.'),
]


def week_date(w):
    return START + dt.timedelta(weeks=w - 1)


# ---------- 양식 스타일 채집 ----------
wb = load_workbook(SRC)
ws = wb[SRC_NAME]
ST = dict(
    title=copy.copy(ws['A2']._style), proj=copy.copy(ws['A4']._style), sub=copy.copy(ws['A5']._style),
    head={c: copy.copy(ws.cell(6, c)._style) for c in range(1, 10)},
    month=copy.copy(ws['J6']._style), week=copy.copy(ws['J7']._style),
    sec={c: copy.copy(ws.cell(8, c)._style) for c in range(1, 10)},
    item={c: copy.copy(ws.cell(9, c)._style) for c in range(1, 10)},
    sub_d=copy.copy(ws['D35']._style), total={c: copy.copy(ws.cell(62, c)._style) for c in range(1, 10)},
    tl_blank=copy.copy(ws.cell(9, 40)._style), tl_sec=copy.copy(ws.cell(8, 40)._style),
    blank=copy.copy(ws.cell(200, 1)._style),
)
ST['sec'][8] = copy.copy(ST['sec'][9])
for d in (ST['head'], ST['sec'], ST['item'], ST['total']):
    for c in (C_PRIO, C_W0, C_W1):
        d[c] = copy.copy(d[9])
ITEM_H, SEC_H, WEEK_H = ws.row_dimensions[9].height, ws.row_dimensions[8].height, ws.row_dimensions[7].height
COLW = {c: ws.column_dimensions[L(c)].width for c in range(1, 10)}

for rng in list(ws.merged_cells.ranges):
    if rng.min_row >= 6:
        ws.unmerge_cells(str(rng))
for r in range(6, ws.max_row + 1):
    for c in range(1, 85):
        ws.cell(r, c).value = None
        ws.cell(r, c)._style = copy.copy(ST['blank'])
for c in range(1, 85):
    ws.column_dimensions[L(c)].width = 2.88
ws.delete_cols(LASTCOL + 1, 85 - LASTCOL)

HIDDEN_FONT = Font(color='FFFFFFFF', size=6)


def put_header(sh, title, col8_label, narrow_title=False):
    sh['A2'] = title; sh['A2']._style = copy.copy(ST['title'])
    sh['A4'] = '주간발표회 모임 관리 웹사이트 개발'; sh['A4']._style = copy.copy(ST['proj'])
    sh['A5'] = f'1차 개발(필수 기능) · {WEEKS}주 ({START:%Y-%m-%d} ~ {END:%Y-%m-%d}) · 작성 {TODAY:%Y-%m-%d} · v{VER}'
    sh['A5']._style = copy.copy(ST['sub'])
    for r, key, txt in [(4, 'S', 'Should — 1차 오픈에 꼭 필요  (우선순위 칸에 S)'), (5, 'C', 'Could — 일정이 밀리면 2차로 미룸  (우선순위 칸에 C)')]:
        sh.cell(r, FIRST + PER).fill = copy.copy(FILL[key])
        sh.cell(r, FIRST + PER + 1).value = txt
        sh.cell(r, FIRST + PER + 1)._style = copy.copy(ST['sub'])
    for c, v in [(1, '번호'), (3, '작업 제목'), (8, col8_label), (9, '완료 비율'), (C_PRIO, '우선\n순위'), (C_W0, '시작주'), (C_W1, '끝주')]:
        sh.cell(6, c).value = v
    for c in range(1, FIRST):
        sh.cell(6, c)._style = copy.copy(ST['head'][c]); sh.cell(7, c)._style = copy.copy(ST['head'][c])
    sh.merge_cells('A6:B7'); sh.merge_cells('C6:G7')
    for c in range(8, FIRST):
        sh.merge_cells(start_row=6, start_column=c, end_row=7, end_column=c)
    for name, w0, w1 in MONTHS:
        c0, c1 = FIRST + (w0 - 1) * PER, FIRST + w1 * PER - 1
        sh.cell(6, c0).value = name
        for c in range(c0, c1 + 1):
            sh.cell(6, c)._style = copy.copy(ST['month'])
        sh.merge_cells(start_row=6, start_column=c0, end_row=6, end_column=c1)
    for w in range(1, WEEKS + 1):
        c0 = FIRST + (w - 1) * PER
        sh.cell(7, c0).value = f'{w}W\n{week_date(w):%m/%d}'
        for c in range(c0, c0 + PER):
            sh.cell(7, c)._style = copy.copy(ST['week'])
            sh.cell(1, c).value = w                      # 조건부 서식이 보는 주 번호 (흰 글씨)
            sh.cell(1, c).font = HIDDEN_FONT
        sh.merge_cells(start_row=7, start_column=c0, end_row=7, end_column=c0 + PER - 1)
    for c in range(1, 10):
        if COLW[c]:
            sh.column_dimensions[L(c)].width = COLW[c]
    sh.column_dimensions['H'].width = 15
    # 완료 비율(I): 양식 너비 4.63 이면 구분 행(11pt 굵게)의 100% 가 #### 이 된다 (2026-09-24 사용자 지적). Excel 5.5 부터 보임 → 6.0
    sh.column_dimensions['I'].width = 6.7
    # 2026-09-24 사용자가 v2.1.0 에서 고친 서식: 두 시트 배율 70%. 제목 칸(F·G)은 `일정 관리` 만 줄였다
    # (타임라인이 한 화면에 들어오게). `인원별` 은 양식 너비 그대로 — v2.2.0 에서 둘 다 줄인 것은 잘못이라 v2.3.0 에서 되돌림.
    if narrow_title:
        sh.column_dimensions['F'].width = 2.4
        sh.column_dimensions['G'].width = 3.1
        sh.column_dimensions['H'].width = 19.0     # 담당자 세 명 이름이 들어가게 (사용자 v2.3.1 에서 18.38 로 넓힘)
    sh.sheet_view.zoomScale = 70
    for c in (C_PRIO, C_W0, C_W1):
        sh.column_dimensions[L(c)].width = 6.5
    for c in range(FIRST, LASTCOL + 1):
        sh.column_dimensions[L(c)].width = 2.88
    sh.freeze_panes = sh.cell(8, FIRST).coordinate
    sh.row_dimensions[7].height = WEEK_H
    # 막대 = 조건부 서식. 우선순위 S/C · 시작주 ≤ 주 ≤ 끝주
    a = f'{L(FIRST)}8'
    rng = f'{L(FIRST)}8:{L(LASTCOL)}{CF_LAST_ROW}'
    for key in ('S', 'C'):
        sh.conditional_formatting.add(rng, FormulaRule(
            formula=[f'AND(${L(C_PRIO)}8="{key}",{L(FIRST)}$1>=${L(C_W0)}8,{L(FIRST)}$1<=${L(C_W1)}8)'],
            fill=FILL[key], stopIfTrue=True))


def put_section(sh, row, num, title):
    for c in range(1, LASTCOL + 1):
        sh.cell(row, c)._style = copy.copy(ST['sec'][c] if c < FIRST else ST['tl_sec'])
    sh.cell(row, 1).value = num; sh.cell(row, 3).value = title
    merge_title(sh, row)
    for c in (C_PRIO, C_W0, C_W1):
        sh.cell(row, c).number_format = 'General'
    sh.row_dimensions[row].height = SEC_H


def merge_title(sh, row):
    """작업 제목 칸 C:G 병합 (2026-09-24 사용자 지시: 구분·항목·하위·합계 행 모두)."""
    sh.merge_cells(start_row=row, start_column=3, end_row=row, end_column=7)


def put_item(sh, row, num, title, col8, done, prio, w0, w1, is_sub=False):
    for c in range(1, LASTCOL + 1):
        sh.cell(row, c)._style = copy.copy(ST['item'][c] if c < FIRST else ST['tl_blank'])
    sh.cell(row, 1).value = num
    if is_sub:
        sh.cell(row, 3).value = SUB_INDENT + title; sh.cell(row, 3)._style = copy.copy(ST['sub_d'])
    else:
        sh.cell(row, 3).value = title
    merge_title(sh, row)
    sh.cell(row, 8).value = col8
    sh.cell(row, 9).value = done; sh.cell(row, 9).number_format = '0%'
    sh.cell(row, C_PRIO).value = prio; sh.cell(row, C_W0).value = w0; sh.cell(row, C_W1).value = w1
    for c in (C_PRIO, C_W0, C_W1):
        sh.cell(row, c).alignment = Alignment(horizontal='center', vertical='center')
        sh.cell(row, c).number_format = 'General'
    sh.row_dimensions[row].height = ITEM_H


def put_total(sh, row, label, refs):
    for c in range(1, 10):
        sh.cell(row, c)._style = copy.copy(ST['total'][c])
    sh.cell(row, 3).value = label
    merge_title(sh, row)
    sh.cell(row, 9).value = '=AVERAGE(' + ','.join(refs) + ')'; sh.cell(row, 9).number_format = '0%'


# ---------- 시트 1: 일정 관리 (원본) ----------
put_header(ws, '주간발표회 일정 관리', '담당자', narrow_title=True)
tasks = []
row = 8
for si, (title, items) in enumerate(SECTIONS, 1):
    sec_row = row
    put_section(ws, row, str(si), title); row += 1
    ii = sub = 0
    sec_leaf_rows = []
    for t, who, prio, done, w0, w1 in items:
        is_sub = t.startswith('  ')
        if is_sub:
            sub += 1; num = f'{si}.{ii}.{sub}'
            parent = tasks[-sub]
            parent['children'] = parent.get('children', 0) + 1
            ws.cell(parent['row'], 9).value = f'=AVERAGE(I{parent["row"] + 1}:I{parent["row"] + sub})'
            if parent['row'] in sec_leaf_rows:
                sec_leaf_rows.remove(parent['row'])
        else:
            ii += 1; sub = 0; num = f'{si}.{ii}'
        # "전원" 은 인원 전부일 때만. 세 명이라도 일부면 이름을 다 적는다 (VBA 는 이름 포함 여부로 찾는다)
        put_item(ws, row, num, t.strip(), '전원' if len(who) >= len(PEOPLE) else ', '.join(who), done, prio, w0, w1, is_sub)
        sec_leaf_rows.append(row)
        tasks.append(dict(num=num, title=t.strip(), who=who, prio=prio, done=done, w0=w0, w1=w1,
                          sub=is_sub, section=title, row=row))
        row += 1
    ws.cell(sec_row, 9).value = '=AVERAGE(' + ','.join(f'I{r}' for r in sec_leaf_rows) + ')'
    ws.cell(sec_row, 9).number_format = '0%'
leaves = [t for t in tasks if 'children' not in t]
put_total(ws, row, '전체 진척률', [f'I{t["row"]}' for t in leaves])
total_row = row

# ---------- 시트 2: 인원별 (참조 + 매크로가 다시 조립) ----------
S = f"'{SRC_NAME}'"


def ref_formulas(r):
    """인원별 한 행이 일정 관리 r 행을 참조하는 수식. VBA 의 FormulaFor 와 같아야 한다."""
    return {1: f'={S}!A{r}',
            3: f'={S}!C{r}',                      # 제목은 하위 항목도 C 에 있다 (앞 빈칸으로 들여쓰기)
            8: f'={S}!H{r}', 9: f'={S}!I{r}',
            C_PRIO: f'={S}!{L(C_PRIO)}{r}', C_W0: f'={S}!{L(C_W0)}{r}', C_W1: f'={S}!{L(C_W1)}{r}'}


ps = wb.create_sheet(DST_NAME, 1)
put_header(ps, '주간발표회 인원별 할 일', '담당자')
ps['A3'] = '이 시트는 열 때마다 일정 관리 시트에서 다시 만들어진다. 여기서 값을 고치면 일정 관리 시트에 써 넣어진다 (매크로 필요).'
ps['A3']._style = copy.copy(ST['sub'])
row = 8
for pi, (name, role, note) in enumerate(PEOPLE, 1):
    mine = sorted([t for t in leaves if name in t['who']], key=lambda x: (x['w0'], x['w1'], x['num']))
    label = f'{name} — {role}' + (f' ({len(mine)}건)' if mine else '') + (f' — {note}' if note else '')
    put_section(ps, row, str(pi), label)
    sec_row = row; row += 1
    refs = []
    for t in mine:
        put_item(ps, row, '', '', '', 0, '', 0, 0)
        for c, f in ref_formulas(t['row']).items():
            ps.cell(row, c).value = f
        refs.append(f'I{row}'); row += 1
    if refs:
        ps.cell(sec_row, 9).value = '=AVERAGE(' + ','.join(refs) + ')'; ps.cell(sec_row, 9).number_format = '0%'
put_total(ps, row, '전체 진척률', [f"{S}!I{t['row']}" for t in leaves])

# ---------- 숨김 시트: 설정(인원) · _서식(매크로가 복사할 행 서식) ----------
cfg = wb.create_sheet('설정')
cfg.append(['이름', '역할', '비고'])
for p in PEOPLE:
    cfg.append(list(p))
cfg.column_dimensions['A'].width = 10; cfg.column_dimensions['B'].width = 40; cfg.column_dimensions['C'].width = 45
cfg.sheet_state = 'hidden'

tpl = wb.create_sheet('_서식')
for c in range(FIRST, LASTCOL + 1):
    tpl.cell(1, c).value = ws.cell(1, c).value; tpl.cell(1, c).font = HIDDEN_FONT
put_section(tpl, 2, '', '구분 행 서식')
put_item(tpl, 3, '', '항목 행 서식', '', 0, '', 0, 0)
put_total(tpl, 4, '합계 행 서식', ['I3'])
for c in range(1, LASTCOL + 1):
    tpl.column_dimensions[L(c)].width = ps.column_dimensions[L(c)].width
tpl.row_dimensions[2].height = SEC_H; tpl.row_dimensions[3].height = ITEM_H
rng = f'{L(FIRST)}2:{L(LASTCOL)}4'
for key in ('S', 'C'):
    tpl.conditional_formatting.add(rng, FormulaRule(
        formula=[f'AND(${L(C_PRIO)}2="{key}",{L(FIRST)}$1>=${L(C_W0)}2,{L(FIRST)}$1<=${L(C_W1)}2)'],
        fill=FILL[key], stopIfTrue=True))
tpl.sheet_state = 'hidden'

# ---------- 용어 사전 ----------
g = wb['용어 사전']
for r in range(5, g.max_row + 1):
    g.cell(r, 1).value = None; g.cell(r, 2).value = None
sa, sb = copy.copy(g['A5']._style), copy.copy(g['B5']._style)
for i, (a, b) in enumerate(GLOSSARY):
    g.cell(5 + i, 1).value = a; g.cell(5 + i, 1)._style = copy.copy(sa)
    g.cell(5 + i, 2).value = b; g.cell(5 + i, 2)._style = copy.copy(sb)

wb.save(OUT)
print('xlsx saved', OUT, 'rows', total_row)

# ---------- HTML (내용은 v2.0.0 과 같다) ----------
data = dict(
    version=VER, start=START.isoformat(), end=END.isoformat(), weeks=WEEKS, today=TODAY.isoformat(),
    months=MONTHS, weekDates=[week_date(w).isoformat() for w in range(1, WEEKS + 1)],
    people=[dict(name=n, role=r) for n, r, note in PEOPLE if not note],
    absent=next((dict(name=n, note=f'{r} — {note}') for n, r, note in PEOPLE if note), None),
    sections=[s for s, _ in SECTIONS],
    tasks=[{k: v for k, v in t.items() if k != 'row'} | {'parent': 'children' in t} for t in tasks],
    glossary=GLOSSARY,
)
html = open(HTML_TPL, encoding='utf-8').read().replace('__DATA__', json.dumps(data, ensure_ascii=False))
open(os.path.join(os.environ.get('TEMP', '.'), 'wbs_artifact.html'), 'w', encoding='utf-8', newline='\n').write(html)   # 아티팩트용(뼈대 없음)
full = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + html.split('\n', 1)[0] + '\n' + html.split('\n', 1)[1].split('</style>', 1)[0] + '</style>\n</head>\n'
        '<body>\n' + html.split('</style>', 1)[1] + '\n</body>\n</html>\n')
open(OUT_HTML, 'w', encoding='utf-8', newline='\n').write(full)
print('html saved', OUT_HTML)
