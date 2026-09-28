"""과제제안서를 [양식] 과제제안서.hwpx 의 구조 그대로 만든다 (표지 · 목차 · 9개 장 · 상자 표 · 일정표).
양식에서 서식(쪽 여백 · 글꼴 · 표 테두리 · 머리말/꼬리말)을 읽어 오고 내용만 바꾼다.

    python proposal_build.py            # out/[1차] 과제제안서_v<VER>.docx (결과 폴더는 OUT_DIR)
내용 상수는 예시 프로젝트(모임 관리 앱)의 것이다. 자기 프로젝트에 맞게 바꿔 쓴다.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hwpx_docx import Hwpx, run, para, pic, cell, table, render, BORDER_THIN, BORDER_NONE, hu2pt

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
# 사용자 양식이 있으면 PROPOSAL_TEMPLATE 로 준다(.hwpx 또는 .docx). templates/ 의 양식은 사용자 양식이 없을 때만 쓴다.
_USER = os.environ.get('PROPOSAL_TEMPLATE') or ''
TPL = _USER if _USER.lower().endswith('.hwpx') else os.path.join(HERE, '..', 'templates', '[양식] 과제제안서.hwpx')   # HWPX 가 있으면 여기서 서식을 읽는다
TPL_DOCX = _USER if _USER.lower().endswith('.docx') else os.path.join(HERE, '..', 'templates', '[양식] 과제제안서.docx')   # HWPX 가 없으면 이 DOCX 에서 쪽 설정·머리말을 읽는다
if _USER.lower().endswith('.docx'):
    TPL = ''                     # 사용자가 DOCX 를 줬으면 기본 HWPX 를 찾지 않는다
OUT_DIR = os.environ.get('OUT_DIR') or os.path.join(os.getcwd(), 'out')
os.makedirs(OUT_DIR, exist_ok=True)
VER = '2.2.1'
OUT = os.path.join(OUT_DIR, f'[1차] 과제제안서_v{VER}.docx')
DATE = '2026-09-27'

TITLE = '주간발표회 모임 관리 웹사이트 개발'
GOTHIC, HEAD = '나눔고딕', '나눔고딕 ExtraBold'
BLUE = '#3057B9'

# ---------------------------------------------------------------- 내용
COVER = [('모 임 명', '주간발표회(임시)'), ('팀    장', '홍길동'), ('작 성 자', '홍길동'), ('작 성 일', DATE), ('버    전', f'v{VER}')]

TOC = ['과제명 : ' + TITLE, '과제제안팀명 및 팀원', '개발목표', '개발필요성', '개발내용', '예상실적', '기술 적용분야', '추진일정', '기술현황분석']

GOAL = [
    ('h', '시스템의 특징'),
    ('t', '① 일정 조율을 전화 대신 화면에서 한다. 팀장이 일정 작성을 요청하면 회원이 각자 가능한 시간을 달력에 넣는다. 시스템이 모임 진행 시간이 들어가는 후보를 뽑고, 투표로 정한 일정이 디스코드에 자동으로 공지된다.'),
    ('t', '② 공지를 템플릿으로 만든다. 매주 쓰는 공지 문구를 틀로 고정하고 빈칸만 채우게 한다. 공지를 쓰면 팀 공지방으로 바로 나간다. 매번 AI 에 문구를 다시 써 달라고 하던 일이 없어진다.'),
    ('t', '③ 자료를 한곳에 모은다. 녹화 저장 폴더의 파일 목록에서 골라 올리고, 공지 · 템플릿 · 노하우 · 기록으로 나눠 본다. 여러 곳에 흩어져 올리던 절차를 하나로 줄인다.'),
    ('t', '④ 모임이 직접 운영한다. 서버는 모임이 가진 미니PC 한 대에 두고, 코드는 GitHub 조직 저장소에 둔다. 외부 서비스 요금 없이 도메인 비용만 든다.'),
    ('h', '1단계 : 요구분석 및 설계 (W1 ~ W4)'),
    ('t', '- 요구사항 정의, 기술 스택 선정, 시스템 아키텍처 설계 (홍길동)'),
    ('t', '- 데이터 모델 설계 및 ERD, API 설계, 와이어프레임 초안 (홍길동)'),
    ('t', '- 와이어프레임 설계(이영희), 디자인 시안 구현(김철수, AI 활용), 시안 검수(이영희)'),
    ('t', '- 서버 구성 및 도메인 · HTTPS'),
    ('h', '2단계 : 구현 (W2 ~ W7)'),
    ('t', '- 김철수 : 프로젝트 골격, 공통 레이아웃(반응형), 회원가입 · 로그인, 모임 일정 관리'),
    ('t', '- 박민수 : 파일 업로드 · 자료 공유, 디스코드 공지'),
    ('t', '- 홍길동 : 서비스 관리자 페이지'),
    ('t', '- DB · 파일 저장소 · 백업 구성, 배포 자동화(Could), 운영 점검(Could)'),
    ('h', '3단계 : 사용자 테스트 및 오픈 (W4 ~ W9)'),
    ('t', '- 기능이 완성되는 대로 이영희이 사용자 입장에서 테스트'),
    ('t', '- 크로스 플랫폼(PC · 모바일 브라우저) 확인, 버그 수정'),
    ('t', '- 운영 배포 및 1차 오픈, 1차 회고와 2차 범위 정리'),
]

NEED = [
    ('h', '필요성'),
    ('t', 'o 일정 조율에 전화가 필요하다 (모임 날짜를 잡으려면 회원마다 전화를 돌려 가능한 시간을 물어야 한다. 사람이 늘수록 통화가 늘고, 한 사람이 바뀌면 처음부터 다시 돈다)'),
    ('t', 'o 공지를 매번 새로 쓴다 (공지 문구는 매주 비슷한데 매번 AI 에 내용을 넣고 가공을 부탁해야 한다. 시간이 들고 문구도 매번 조금씩 달라진다)'),
    ('t', 'o 자료 올리는 절차가 복잡하다 (발표를 녹화한 뒤 영상과 자료를 따로 올리고 링크를 다시 공유한다. 여러 단계를 거치다 빠뜨리는 일이 생긴다)'),
    ('t', 'o 기록이 흩어진다 (일정은 통화 기록에, 공지는 메신저에, 자료는 각자 저장소에 남는다. 지난 모임에 무엇을 발표했는지 되짚기 어렵다)'),
    ('t', 'o 모임 규모에 맞는 도구가 없다 (회원 4명 안팎의 모임에 유료 협업 도구는 과하고, 무료 도구는 일정 · 공지 · 자료가 서로 이어지지 않는다)'),
]
CASES = [
    ('h', '사례조사'),
    ('t', 'o 사례 1. 일정 조율 도구는 있으나 그 다음이 없다. When2meet, Doodle 같은 서비스는 여러 사람의 가능한 시간을 겹쳐 보여 준다. 그러나 정한 일정을 공지로 보내고 자료를 모으는 단계는 다른 도구로 넘어가야 한다.'),
    ('t', 'o 사례 2. 디스코드는 외부 프로그램이 글을 올릴 수 있다. 디스코드 채널마다 웹훅 주소를 만들 수 있고, 그 주소로 보낸 글이 채널에 올라간다. 봇을 따로 만들지 않아도 공지를 자동으로 보낼 수 있다.'),
    ('t', 'o 사례 3. 파일 공유 서비스는 모임 단위로 묶어 주지 않는다. 구글 드라이브 같은 서비스는 파일을 올리기는 쉽지만, 어느 모임의 어떤 발표 자료인지는 사람이 폴더 이름으로 관리해야 한다.'),
    ('t', 'o 모임 실태 확인 (2026년 9월). 위 세 가지 불편을 이 모임에서 그대로 겪고 있다. 매주 한 번 모이며, 일정은 전화로 잡고, 공지는 AI 로 가공해 메신저에 올리고, 녹화와 자료는 따로 올린다. 이 세 단계를 한 사이트에서 처리하는 것이 본 과제의 출발점이다.'),
]

DEV1 = [
    ('t', 'o 회원가입 · 로그인 (김철수)'),
    ('t', '- 회원가입, 로그인 · 로그아웃'),
    ('t', '- 로그인한 회원이 자기 활동을 저장하고 다시 불러온다'),
    ('t', 'o 모임 일정 관리 (김철수)'),
    ('t', '- 팀장이 진행 예상 시간을 정하고 일정 작성을 요청, 참여자에게 알림'),
    ('t', '- 참여자가 달력(월간 · 주간)에 가능한 시간을 등록'),
    ('t', '- 전원이 확정하면 진행 시간이 들어가는 후보를 산출, 투표로 확정, 디스코드 자동 공지'),
    ('t', 'o 디스코드 공지 (박민수)'),
    ('t', '- 공지 템플릿 만들기 · 수정, 공지 작성 즉시 팀 공지방으로 전송'),
    ('t', '- 팀별 공지방 연결. 채널 자동 생성 · 삭제는 방식(웹훅 · 봇)을 정한 뒤 결정'),
    ('t', 'o 파일 업로드 · 자료 공유 (박민수)'),
    ('t', '- 지정 폴더(녹화 저장 폴더)의 파일 목록에서 골라 확인 뒤 업로드, 새로 고침, 드래그앤드롭'),
    ('t', '- 공지 · 템플릿 · 노하우 · 기록으로 분류한 목록, 다운로드'),
    ('t', 'o 서비스 관리자 페이지 (홍길동)'),
    ('t', '- 역할 4종(서비스 관리자 · 팀장 · 부팀장 · 모임원), 팀장 · 부팀장 설정'),
    ('t', '- 대상(특정인 · 팀장 · 팀장/부팀장 · 전체)을 골라 공지, 대상에 맞는 공지방으로 전송'),
    ('t', '※ 기술 스택과 디스코드 연동 방식은 담당자 회의에서 정한다. 정해지기 전에는 구현을 시작하지 않는다.'),
]
DEV2 = [
    ('t', 'o 웹 클라이언트 (반응형)'),
    ('t', '- 공통 레이아웃, PC 와 모바일 브라우저에서 같은 기능'),
    ('t', '- 와이어프레임 초안(홍길동)을 이영희이 설계하고, 시안은 AI 를 활용해 구현(김철수)한 뒤 검수(이영희)'),
    ('t', 'o 인프라'),
    ('t', '- 미니PC 서버 구성 (OS · 계정 · 방화벽), 도메인 구매 · DNS · HTTPS'),
    ('t', '- DB · 파일 저장소 · 백업 구성 (주 1회 백업)'),
    ('t', '- 배포 자동화, 운영 점검 (일정이 밀리면 2차로 미룸)'),
    ('t', 'o 개발 결과물 시험 평가'),
    ('t', '- 사용자 테스트 시나리오 작성 (김철수 · 박민수 · 홍길동), 테스트 계획서'),
    ('t', '- 기능이 완성되는 대로 이영희이 사용자 입장에서 테스트하고 결과를 날짜 붙여 기록'),
    ('t', '- 크로스 플랫폼 확인 뒤 운영 배포, 1차 오픈'),
]

RESULT = [
    ('t', 'o 전화 조율이 없어진다 (회원이 각자 시간을 등록하면 후보 시간이 바로 나오고 투표로 정한다)'),
    ('t', 'o 공지 작성 시간이 줄어든다 (템플릿의 빈칸만 채우면 공지가 완성되고 디스코드로 바로 나간다)'),
    ('t', 'o 자료가 한곳에 모인다 (녹화 파일과 자료가 분류별로 남아 지난 발표를 되짚을 수 있다)'),
    ('t', 'o 운영 비용이 낮다 (미니PC 와 도메인 하나로 운영한다. 외부 서비스 요금이 없다)'),
    ('t', 'o 2차 확장의 바탕이 된다 (회원 · 모임 · 자료 데이터가 쌓이면 주제 요청, 프로필, 게시판 같은 선택 기능을 그 위에 얹을 수 있다)'),
]

FIELDS = [
    ('공통 빈 시간 추출', ['- 스터디 · 동호회 · 팀 회의처럼 여러 사람의 일정을 맞추는 모든 자리', '- 강의실 · 회의실 예약처럼 자원의 빈 시간을 찾는 문제']),
    ('양식 기반 공지 자동화', ['- 반복되는 안내문 · 주간 보고 · 회의 소집 문구의 틀 고정', '- 빈칸 채우기만으로 문서를 완성하는 사내 서식 시스템']),
    ('디스코드 웹훅 연동', ['- 서버 알림 · 빌드 결과 · 일정 알림을 메신저 채널로 보내는 자동화', '- 봇 없이 외부 시스템과 메신저를 잇는 경량 연동']),
    ('모임 단위 자료 보관', ['- 회차별로 묶이는 세미나 · 강의 자료실', '- 녹화 영상과 발표 자료를 한 묶음으로 관리하는 아카이브']),
    ('반응형 웹', ['- PC 와 모바일을 하나의 화면 코드로 지원하는 소규모 서비스', '- 앱 개발 없이 모바일 접근이 필요한 내부 도구']),
    ('미니PC 자가 호스팅', ['- 저비용으로 소규모 서비스를 직접 운영하는 동아리 · 소모임', '- 외부 클라우드에 올리기 어려운 내부 자료의 자체 보관']),
]

WEEKS = [('9월', 2), ('10월', 4), ('11월', 3)]          # 9주: 09/21 ~ 11/20
SCHEDULE = [
    ('1. 프로젝트 관리', [1, 2, 3, 4, 5, 6, 7, 8, 9]),
    ('2. 요구분석 및 설계', [1, 2, 3, 4]),
    ('3. 인프라 구축', [1, 2, 3, 4, 8]),
    ('4. 기능 개발 (서버 + 화면)', [2, 3, 4, 5, 6, 7]),
    ('5. 사용자 테스트 및 오픈', [4, 5, 6, 7, 8, 9]),
]
SCHEDULE_NOTE = '※ 세부 일정(영역 5개 · 작업 30개)과 담당자별 할 일은 「[1차] WBS_일정관리_v2.5.0.xlsm」에 있다. 기능별 요구사항은 「[1차] 요구사항서_v2.0.0.docx」에 있다.'

TECH = [
    ('h', '◦ 국외 기술 현황'),
    ('sh', '- 일정 조율 서비스'),
    ('t', 'When2meet, Doodle 처럼 여러 사람의 가능한 시간을 표에 겹쳐 보여 주는 서비스가 널리 쓰인다. 다만 조율이 끝난 뒤의 공지와 자료 보관은 다루지 않는다. 본 과제는 조율 결과가 공지와 자료실로 바로 이어지게 한다.'),
    ('sh', '- 메신저 연동 규격'),
    ('t', 'Discord, Slack 은 채널마다 웹훅 주소를 발급해 외부 프로그램이 글을 올릴 수 있게 한다. 봇을 만들지 않아도 되므로 소규모 서비스가 메신저와 이어지는 표준 경로가 되었다. 본 과제의 공지 전송도 이 경로를 쓴다.'),
    ('sh', '- 커뮤니티 플랫폼의 일정 기능'),
    ('t', 'Discord 의 이벤트 기능, Meetup 같은 모임 플랫폼은 일정 공지와 참석 확인을 제공한다. 그러나 참석 가능 시간을 모아 날짜를 정하는 단계와 발표 자료 보관은 별도다.'),
    ('h', '◦ 국내 기술 현황'),
    ('sh', '- 메신저 기반 모임 운영'),
    ('t', '카카오톡 투표 · 일정, 네이버 밴드 · 카페처럼 모임 운영을 메신저와 커뮤니티 서비스에 얹어 쓰는 경우가 많다. 손쉽지만 일정 · 공지 · 자료가 대화 흐름에 묻혀 지난 기록을 찾기 어렵다.'),
    ('sh', '- 소규모 자가 호스팅'),
    ('t', '미니PC 와 개인 도메인으로 서비스를 직접 운영하는 사례가 늘고 있다. 컨테이너와 HTTPS 자동 발급 도구가 보편화되어 소모임 규모에서도 운영 부담이 낮아졌다. 본 과제가 미니PC 운영을 택한 배경이다.'),
    ('h', '◦ 발전추세 및 본 과제의 위치'),
    ('t', '모임 운영 도구는 일정 조율, 공지, 자료 공유가 각각 따로 발전해 왔고 사용자는 이를 이어 붙여 쓴다. 본 과제는 이 세 가지를 소규모 모임에 맞게 한 사이트로 묶는다. 목표는 "대충 해도 굴러가게" 만드는 것이다. 필수 기능 다섯 가지를 9주 안에 오픈하고 나머지는 2차로 미룬다.'),
]


# ---------------------------------------------------------------- 조립
def box(lines, width_pt, valign='TOP'):
    """양식의 1x1 상자 표. lines: ('h', 굵은 소제목) / ('sh', 굵은 항목) / ('t', 본문)"""
    blocks = []
    for kind, text in lines:
        bold = kind in ('h', 'sh')
        left = 10 if kind == 't' and text.startswith('- ') else (14 if kind == 't' and not text[:1] in 'o◦①②③④※-' else 0)
        blocks.append(para([run(text, GOTHIC, 10, bold)], 'JUSTIFY', left=left, space_before=3 if kind == 'h' else 0, line=160))
    return table([[cell(blocks, borders=BORDER_THIN, valign=valign, width=width_pt)]], [width_pt])


def heading(text, page_break=True):
    return para([run(text, GOTHIC, 14, True)], 'JUSTIFY', space_before=10, line=190, page_break=page_break)


def template():
    """쪽 설정과 머리말. HWPX 양식이 있으면 거기서, 없으면(09-25 부터) DOCX 변환본의 sectPr 과 header1.xml 값으로 만든다."""
    if os.path.exists(TPL):
        src = Hwpx(TPL)
        header = src.parse()['header']
        for blk in header:
            blk['leader'] = False
        return src.page(), header
    from docx import Document
    s = Document(TPL_DOCX).sections[0]
    pt = lambda v: v / 12700.0          # EMU → pt
    page = dict(width=pt(s.page_width), height=pt(s.page_height), left=pt(s.left_margin), right=pt(s.right_margin),
                top=pt(s.top_margin), bottom=pt(s.bottom_margin), header=pt(s.header_distance), footer=pt(s.footer_distance))
    # 변환본 header1.xml: 나눔고딕 9pt "과제제안서 " + 오른쪽 탭 + 굵은 PAGE/NUMPAGES, 앞 간격 20pt, 줄 높이 13.5pt 고정, 아래 회색 선
    h = para([run('과제제안서 ', GOTHIC, 9), run('', GOTHIC, 9, True, tab=True), run('', GOTHIC, 9, True, field='PAGE'),
              run('/', GOTHIC, 9, True), run('', GOTHIC, 9, True, field='NUMPAGES')],
             'JUSTIFY', left=2.85, space_before=20, border_bottom='#ADADAD', leader=False)
    h['line_pt'] = 13.5
    return page, [h]


def main():
    page, header = template()
    body_w = page['width'] - page['left'] - page['right']
    # 머리말은 양식 것을 그대로 쓰되 학교 로고(꼬리말 그림)는 뺀다 — 이 모임의 문서가 아니다
    footer = []                      # 양식 꼬리말은 학교 로고와 과정명(PBL Off-JT)이라 이 모임 문서에는 넣지 않는다

    blocks = []
    # 표지 (양식과 같은 세로 배치: 제목 · 밑줄 · 과제명 · 정보 표)
    blocks.append(para([run('과 제 제 안 서', HEAD, 40)], 'CENTER', space_before=110, line=160))
    blocks.append(para([], 'CENTER', line=100, border_bottom='#000000', line_width=396))
    blocks.append(para([run(TITLE, GOTHIC, 20, True, BLUE)], 'CENTER', space_before=8, line=160))
    info = [[cell([para([run(k, GOTHIC, 10)], 'CENTER')], borders={**BORDER_THIN, 'left': BORDER_NONE['left']}, width=71),
             cell([para([run(v, '맑은 고딕', 11)], 'DISTRIBUTE')], borders={**BORDER_THIN, 'right': BORDER_NONE['right']}, width=129)] for k, v in COVER]
    t = table(info, [71, 129]); t['row_heights'] = [21] * len(COVER)
    blocks.append(para([], 'CENTER', space_before=170, line=100))
    blocks.append(t)
    # 목차
    blocks.append(para([run('<목  차>', '휴먼둥근헤드라인', 18)], 'CENTER', space_before=20, line=160, page_break=True))
    blocks.append(para([], 'CENTER', line=100))
    for i, item in enumerate(TOC, 1):
        blocks.append(para([run(f'{i}. {item}', GOTHIC, 14, color='#0000FF'), run('', tab=True), run('#', GOTHIC, 14, color='#0000FF')], 'JUSTIFY', line=160))
    # 1 · 2
    blocks.append(heading('1. ' + TOC[0]))
    blocks.append(heading('2. ' + TOC[1], page_break=False))
    for line in ['제안자 :', '　　팀명 : 주간발표회(임시)', '　　팀장 : 홍길동 (프로젝트 관리 · 인프라 · 설계 · 서비스 관리자 페이지)',
                 '　　팀원 : 김철수 (설계 · 개발 · AI 활용 시안 구현)', '　　팀원 : 이영희 (와이어프레임 · 시안 검수 · 사용자 테스트)',
                 '　　팀원 : 박민수 (개발 · 파일 업로드 · 디스코드 공지)']:
        blocks.append(para([run(line, GOTHIC, 14)], 'JUSTIFY', left=20, space_before=10, line=160))
    # 3
    blocks.append(heading('3. ' + TOC[2]))
    blocks.append(box(GOAL, body_w - 12))
    # 4
    blocks.append(heading('4. ' + TOC[3]))
    blocks.append(box(NEED, body_w - 4))
    blocks.append(para([], line=100))
    blocks.append(box(CASES, body_w - 4))
    # 5
    blocks.append(heading('5. ' + TOC[4]))
    blocks.append(box(DEV1, body_w - 4))
    blocks.append(para([], line=100))
    blocks.append(box(DEV2, body_w - 4))
    # 6
    blocks.append(heading('6. ' + TOC[5]))
    blocks.append(box(RESULT, body_w - 4))
    # 7
    blocks.append(heading('7. ' + TOC[6]))
    w1, w2 = 91, body_w - 4 - 91
    rows = [[cell([para([run(k, GOTHIC, 11)], 'CENTER')], borders=BORDER_THIN, width=w1),
             cell([para([run(v, GOTHIC, 10)], 'JUSTIFY') for v in vs], borders=BORDER_THIN, width=w2)] for k, vs in FIELDS]
    blocks.append(table(rows, [w1, w2]))
    # 8
    blocks.append(heading('8. ' + TOC[7]))
    nweeks = sum(n for _, n in WEEKS)
    lw, ww = 150, (body_w - 4 - 150) / nweeks
    thick = lambda **kw: {**{s: ('SOLID', 0.15, '#000000') for s in ('left', 'right', 'top', 'bottom')}, **kw}
    kfont = 'KoPub돋움체 Light'
    hdr = [cell([para([run('활동 내용', kfont, 10)], 'CENTER')], span=(1, 2), borders=thick(top=('SOLID', 0.3, '#000000'), left=('SOLID', 0.3, '#000000')), width=lw)]
    for name, n in WEEKS:
        hdr.append(cell([para([run(name, kfont, 10)], 'CENTER')], span=(n, 1), borders=thick(top=('SOLID', 0.3, '#000000')), width=ww * n))
        hdr += [None] * (n - 1)
    sub = [None] + [cell([para([run(str(w), kfont, 10)], 'CENTER')], borders=thick(), width=ww) for w in range(1, nweeks + 1)]
    grid = [hdr, sub]
    for name, marks in SCHEDULE:
        row = [cell([para([run(name, kfont, 10, True)], 'JUSTIFY')], borders=thick(left=('SOLID', 0.3, '#000000')), fill='#FFFF00', width=lw)]
        row += [cell([para([run('■' if w in marks else '', kfont, 10)], 'CENTER')], borders=thick(), width=ww) for w in range(1, nweeks + 1)]
        grid.append(row)
    for r in grid:
        for c in r:
            if c and r is grid[-1]:
                c['borders']['bottom'] = ('SOLID', 0.3, '#000000')
        if r[-1]:
            r[-1]['borders']['right'] = ('SOLID', 0.3, '#000000')
    blocks.append(table(grid, [lw] + [ww] * nweeks))
    blocks.append(para([run(SCHEDULE_NOTE, GOTHIC, 14)], 'LEFT', space_before=10, line=160))   # 양쪽 맞춤이면 파일명 사이가 벌어진다
    # 9
    blocks.append(heading('9. ' + TOC[8]))
    blocks.append(box(TECH, body_w - 4))

    model = dict(page=page, header=header, footer=footer, blocks=blocks)
    render(model, OUT)
    print('saved', OUT)


if __name__ == '__main__':
    main()
