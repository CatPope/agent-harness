"""요구사항서 v2 생성기. 09-25 판 양식(docs/양식/[양식] 요구사항서.docx)의 본보기 문단·표를 복제해 채운다.

- 양식은 문단 스타일이 전부 Normal + 직접 서식이라, 글자로 본보기 문단을 찾아 deepcopy 한 뒤 글자만 바꾼다.
- 표는 양식의 표(머리행 + 데이터행 1개)를 본보기로 두고 행을 복제한다. 열 폭은 본보기 표를 따른다.
- 그림 4장은 matplotlib(맑은 고딕)로 그려 %TEMP% 에 PNG 로 두고 폭 160 mm 로 넣는다.
- 목차는 `제목\t#` 로 쓰고 fill_toc.ps1(Word COM)이 쪽 번호를 채운다. 목차 줄과 본문 제목 글자가 같아야 한다.
- 3.5 · 3.13 · 3.14 는 양식 본문에 없어 목차에서도 뺀다(양식의 주석: 필요 없는 목차는 제외).
실행: python req_build.py   →  out/[1차] 요구사항서_v<VER>.docx (결과 폴더는 OUT_DIR 로 바꾼다)
BODY 는 예시 프로젝트(모임 관리 앱)의 내용이다. 자기 프로젝트에 맞게 바꿔 쓴다.
3.11 그림은 arch_build.py 로 만든 PNG 를 ARCH_PNG(기본: out/구성 아키텍처.png)에서 읽는다.
"""
import copy, os, sys, tempfile
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, '..', 'templates', '[양식] 요구사항서.docx')
OUT_DIR = os.environ.get('OUT_DIR') or os.path.join(os.getcwd(), 'out')
os.makedirs(OUT_DIR, exist_ok=True)
VER = '2.3.0'      # 2.3.0: 기술 스택 확정, 이메일 로그인(사용자 09-27, 결정 #74 #75). 2.2.1: 구성 아키텍처 그림을 v1.2.0 으로(사용자 09-27). 2.2.0: 3.11 에 구성 아키텍처 그림(docs/설계 v1.1.0) 추가(사용자 09-27 지시). 2.1.1: 용어 정리(서비스/시스템 관리자·운영자, 사용자 09-27 지시). 2.1.0: 역할 5종·운영자(2차)·임시 저장/발송·확정 뒤 재투표·미니PC 사양·2.1 "기능: 내용" 형식·표 글자 10.5pt (사용자 09-25 지시)
DATE = '2026-09-27'
TABLE_SZ = 21      # 표 글자 크기(half-point). 양식은 18(9pt)인데 작아서 읽기 힘들다는 지적으로 10.5pt
OUT = os.path.join(OUT_DIR, f'[1차] 요구사항서_v{VER}.docx')
IMG_DIR = os.path.join(tempfile.gettempdir(), 'req_build_img')

# ---------------------------------------------------------------- 내용
TITLE = '요 구 사 항 서'
SUBTITLE = '주간발표회 모임 관리 웹사이트 개발'
COVER = [('프로젝트', '주간발표회 모임 관리 웹사이트'), ('주    관', '주간발표회(임시)'), ('작 성 자', '홍길동'),
         ('검 토 자', '김철수, 이영희, 박민수'), ('문서 버전', f'v{VER}'), ('작 성 일', DATE)]

# 본문 요소: ('h1', 글)  ('h2', 글)  ('h3', 글)  ('item', 글)  ('text', 글)  ('note', 글)  ('dict', 글)  ('small', 글)
#            ('table', 본보기표번호, 머리행, 데이터행들)  ('img', 파일이름)  ('blank',)  ('pagebreak',)
# 번호 문단은 'item' 으로 쓰고 번호는 생성기가 "1) " 로 붙인다(절마다 다시 1부터).
BODY = [
    ('pagebreak',),
    ('h1', '1. 개요'),
    ('h2', '1.1 시스템의 개발 배경 및 목적'),
    ('item', '모임 일정을 잡을 때마다 회원에게 전화를 돌렸다. 각자 되는 시간을 모아 겹치는 시간을 찾는 일을 사람이 했다.'),
    ('item', '공지 문구를 매번 AI 에 다시 써 달라고 했다. 같은 형식의 공지를 매주 새로 만들었다.'),
    ('item', '발표 녹화와 자료를 올리는 절차가 번거로웠다. 녹화 파일이 어느 폴더에 있는지 찾아 올려야 했다.'),
    ('text', '목적: 이 세 가지를 웹사이트 하나에서 처리한다. 회원이 되는 시간을 달력에 넣으면 시스템이 후보 시간을 내고 투표로 정한다. '
             '공지는 템플릿을 채우면 디스코드로 바로 나간다. 녹화 파일은 지정 폴더에서 골라 올린다.'),
    ('h2', '1.2 범위 및 목표'),
    ('h3', '시스템 구성'),
    ('img', 'system.png'),
    ('blank',),
    ('h3', '범위에 포함되는 것'),
    ('table', 1, ['구분', '내용'], [
        ['회원', '회원가입, 로그인, 활동 기록 저장과 불러오기'],
        ['일정', '진행 예상 시간 설정, 일정 작성 요청과 알림, 달력에 가능 시간 등록, 후보 시간 산출, 투표, 확정, 자동 공지'],
        ['공지', '공지 템플릿 만들기와 수정, 공지 작성 즉시 디스코드 전송, 팀별 공지방'],
        ['파일', '지정 폴더의 파일 목록 보기, 확인 뒤 업로드, 새로 고침, 드래그앤드롭, 분류별 목록과 다운로드'],
        ['서비스 관리', '역할 5종, 팀장과 부팀장 설정, 대상별 공지 발송, 팀과 공지방 짝짓기'],
        ['서버', '미니PC 한 대(Intel N100, RAM 16GB, HDD 2TB 두 개 RAID 1)에 웹, DB, 업로드 파일 보관. 도메인과 HTTPS'],
    ]),
    ('blank',),
    ('h3', '범위에서 제외되는 것'),
    ('table', 2, ['제외 항목', '사유'], [
        ['서비스 운영자 기능 (역할 만들기, 권한 주기)', '2차. 1차에서는 역할 이름만 둔다'],
        ['주제 요청', '2차'],
        ['개인 프로필', '2차'],
        ['구글 OAuth 로그인', '2차'],
        ['발표자에게 보내는 메모장', '2차'],
        ['커뮤니티 게시판', '2차'],
        ['라이브 스트리밍과 녹화', '서버 사양을 확인한 뒤 2차에서 검토한다'],
        ['영상 자막 추출', '서버 사양을 확인한 뒤 2차에서 검토한다'],
        ['외부 공개 서비스', '회원만 쓰는 비공개 사이트다'],
    ]),
    ('blank',),
    ('h3', '목표'),
    ('table', 3, ['목표', '달성 기준'], [
        ['전화 없이 일정 확정', '일정 요청부터 확정 공지까지 웹과 디스코드 안에서 끝난다'],
        ['공지 자동화', '템플릿을 채워 저장하면 10초 안에 디스코드 공지방에 올라간다'],
        ['자료 한곳에', '녹화 파일과 자료가 분류별로 한 곳에 있고 회원이 내려받는다'],
        ['어디서나 접속', '스마트폰 앱, PC 앱, 웹에서 같은 기능을 쓴다'],
        ['1차 오픈', '2026-11-20 까지 필수 기능을 미니PC 에 배포한다'],
    ]),
    ('blank',),
    ('h2', '1.3 정의'),
    ('text', '본 시스템은 모임 관리 웹사이트다. 회원이 달력에 되는 시간을 넣으면 시스템이 후보 시간을 낸다. 투표로 정한 일정은 디스코드에 알린다. '
             '공지는 템플릿을 채워 디스코드로 보낸다. 녹화 파일과 자료를 올리고 분류별로 내려받는다. 서비스 관리자가 역할과 팀을 관리한다.'),
    ('text', '팀은 모임 자체다. 1차에서는 팀이 하나뿐이지만, 팀과 역할은 여러 팀을 전제로 설계한다. 팀마다 디스코드 공지방이 따로 있다.'),
    ('text', '역할은 서비스 관리자, 서비스 운영자, 팀장, 부팀장, 회원 다섯 가지다. 서비스 운영자는 모임에 필요한 역할을 만들고 권한을 주는 자리다. 서비스 운영자 기능은 2차에서 만든다.'),
    ('text', '서비스 관리자와 서비스 운영자는 앱 안의 역할이다. 화면에는 관리자, 운영자로만 보인다. 서버, DB, 배포를 맡는 사람은 시스템 관리자, 시스템 운영자라 부른다.'),
    ('h2', '1.4 약어'),
    ('item', '팀 : 모임 단위. 1차에서는 주간발표회 하나다.'),
    ('item', '역할 : 서비스 관리자, 서비스 운영자, 팀장, 부팀장, 회원 다섯 가지.'),
    ('item', '서비스 관리자 : 앱 안에서 역할과 팀을 정하고 대상별 공지를 보내는 역할. 화면에는 관리자로 보인다.'),
    ('item', '서비스 운영자 : 모임에 필요한 역할을 만들고 권한을 주는 역할. 화면에는 운영자로 보인다. 1차에서는 이름만 있고 기능은 2차다.'),
    ('item', '시스템 관리자, 시스템 운영자 : 미니PC 서버, DB, 배포, 백업을 맡는 사람. 앱의 역할이 아니다.'),
    ('item', '공지 템플릿 : 빈칸만 채우면 공지가 완성되는 문구 틀.'),
    ('item', '공지방 : 팀별 디스코드 공지 채널.'),
    ('item', '웹훅(Webhook) : 외부 프로그램이 디스코드 채널에 글을 올리는 주소. 보내기만 할 수 있다.'),
    ('item', '봇(Bot) : 디스코드 서버에 회원으로 들어가 채널과 권한을 다루는 프로그램.'),
    ('item', '일정 작성 요청 : 팀장이 참여자에게 가능 시간을 등록하라고 보내는 요청.'),
    ('item', '가능 시간 : 참여자가 달력에 표시한 모임 가능 시간대.'),
    ('item', '후보 시간 : 모든 참여자의 가능 시간이 겹치고 진행 예상 시간이 들어가는 날짜와 시간.'),
    ('item', '확정 일정 : 투표로 뽑힌 후보 시간. 그날의 발표 시간이 된다.'),
    ('item', '지정 폴더 : 녹화 저장 폴더처럼 파일 목록을 항상 보여 줄 로컬 폴더.'),
    ('item', '분류 : 자료의 갈래. 공지, 템플릿, 노하우, 기록.'),
    ('item', '1차 / 2차 : 필수 기능 개발 / 선택 기능 개발.'),
    ('h2', '1.5 참고문헌'),
    ('item', '개발 내용.txt, 모임 개요.txt (docs/기획)'),
    ('item', '공지사항 양식.txt (상위 작업 폴더)'),
    ('item', '[1차] 과제제안서_v2.1.0.docx'),
    ('item', '[1차] WBS_일정관리_v2.5.0.xlsm'),
    ('item', '설계 문서 검토 보고서 (Claude Docs, 2026-09-25)'),
    ('item', '디스코드 연동·기술 스택 검토 보고서 (Claude Docs, 2026-09-25)'),
    ('item', '컴포넌트별 기술 스택 평가 보고서 v1.2.1 (docs/보고서)'),
    ('item', 'Discord Developer Portal, Webhook Resource (공식 문서)'),
    ('pagebreak',),
    ('h1', '2. 일반적인 사항'),
    ('h2', '2.1 시스템 기능'),
    ('item', '디스코드 공지: 공지 템플릿을 만들고 고친다. 임시 저장하기로 쓰던 내용을 저장하고, 발송하기로 팀 공지방에 보낸다.'),
    ('item', '모임 일정 관리: 팀장이 진행 예상 시간을 정하고 일정 작성을 요청한다. 참여자가 달력에 가능 시간을 넣는다. '
             '전원이 확정하면 후보 시간이 뜨고 투표로 정한다. 확정 뒤 일정을 바꾸면 전원에게 알림이 가고 다시 투표한다. 확정 일정은 디스코드에 자동 공지된다.'),
    ('item', '파일 업로드: 지정 폴더의 파일 목록에서 골라 올린다. 올리기 전에 확인한다. 드래그앤드롭으로도 올린다.'),
    ('item', '파일 다운로드: 공지, 템플릿, 노하우, 기록으로 분류된 목록을 보고 내려받는다.'),
    ('item', '서비스 관리자 페이지: 역할 5종을 두고 팀장과 부팀장을 정한다. 대상을 골라 공지를 보낸다.'),
    ('item', '회원가입과 로그인: 가입한 회원이 로그인해 자기 활동을 저장하고 불러온다.'),
    ('h2', '2.2 사용자 특성'),
    ('text', '본 시스템은 매주 한 번 모여 발표하는 소규모 모임이 쓴다. 회원은 4명 안팎이다. 서비스 관리자와 팀장은 회원 중 한 명이 겸한다. '
             '회원은 스마트폰 앱, PC 앱, 웹을 섞어 쓰고, 디스코드를 이미 쓰고 있다. 녹화는 발표자의 PC 에서 하므로 그 PC 의 폴더에서 파일을 올린다.'),
    ('h2', '2.3 일반적 제약사항'),
    ('item', '요구사항서에 명시된 필수 기능은 모두 포함되어야 한다.'),
    ('item', '기술 스택은 Flutter + Supabase 셀프호스팅 + Go 보조 서버로 정했다. Flutter 코드 하나로 스마트폰 앱, PC 앱, 웹을 만든다. Supabase 가 인증, DB, 파일 저장소를 맡는다.'),
    ('item', '로그인은 이메일과 비밀번호로 한다. 인증은 Supabase Auth 를 쓰고, 인증 메일과 비밀번호 재설정 메일도 Supabase 가 보낸다.'),
    ('item', '디스코드 채널을 자동으로 만들고 지우는 기능은 봇 방식이 필요하다. 웹훅으로는 되지 않는다. 방식은 담당자 회의에서 정한다.'),
    ('item', '개발자는 세 명이고 기능은 서버와 화면을 한 사람이 맡는다. 김철수이 골격과 회원과 일정, 박민수이 파일과 공지, 홍길동가 서비스 관리자 페이지를 맡는다.'),
    ('item', '서버는 미니PC 한 대다. Intel N100, RAM 16GB, HDD 2TB 두 개를 RAID 1 로 묶어 실사용 2TB 다. 성능이 제한된다.'),
    ('item', '지정 폴더의 파일 목록은 PC 앱에서 늘 보인다. 웹에서는 Chrome 과 Edge 에서만 폴더를 지정할 수 있고, 스마트폰은 파일을 골라 올린다.'),
    ('item', '1차는 2026-11-20 까지 끝낸다.'),
    ('h2', '2.4 자료 흐름도'),
    ('h3', '공지 발송 흐름'),
    ('img', 'notice.png'),
    ('blank',),
    ('h3', '일정 조율 흐름'),
    ('img', 'schedule.png'),
    ('blank',),
    ('h3', '파일 업로드·공유 흐름'),
    ('img', 'file.png'),
    ('blank',),
    ('h2', '2.5 자료 사전'),
    ('dict', '회원         = 이메일 + 비밀번호(해시) + 이름 + 아이디(표시용) + 디스코드ID + 가입일 + 인증여부'),
    ('dict', '팀           = 팀명 + 공지방 + 생성일'),
    ('dict', '팀소속       = 회원 + 팀 + 역할'),
    ('dict', '역할         = [서비스 관리자 | 서비스 운영자 | 팀장 | 부팀장 | 회원]'),
    ('dict', '공지방       = 팀 + 디스코드채널 + 웹훅URL'),
    ('dict', '공지템플릿   = 팀 + 템플릿명 + 본문틀 + 빈칸목록 + 수정시각'),
    ('dict', '공지         = 팀 + 작성자 + 대상 + 템플릿 + 본문 + 작성시각 + 발송상태'),
    ('dict', '대상         = [특정인 | 팀장 | 팀장/부팀장 | 팀원 | 전체]'),
    ('dict', '발송상태     = [임시저장 | 대기 | 발송 | 실패]'),
    ('dict', '일정요청     = 팀 + 요청자 + 대상주 + 진행예상시간 + 요청시각 + 회차'),
    ('dict', '가능시간     = 일정요청 + 회원 + 시작시각 + 종료시각 + 확정여부'),
    ('dict', '후보시간     = 일정요청 + 회차 + 시작시각 + 종료시각 + 득표수'),
    ('dict', '확정일정     = 일정요청 + 후보시간 + 확정시각 + 상태[확정 | 변경으로 취소]'),
    ('dict', '자료         = 팀 + 올린회원 + 파일명 + 크기 + 분류 + 올린시각 + 저장경로'),
    ('dict', '분류         = [공지 | 템플릿 | 노하우 | 기록]'),
    ('blank',),
    ('pagebreak',),
    ('h1', '3. 세부 요구사항'),
    ('h2', '3.1 기능 요구사항'),
    ('table', 4, ['ID', '요구사항', '우선순위'], [
        ['FR-01', '공지 템플릿을 만들고 수정할 수 있어야 한다', '필수'],
        ['FR-02', '임시 저장하기를 누르면 쓰던 공지 내용이 저장되어야 한다. 공지방에는 보내지 않는다', '필수'],
        ['FR-03', '발송하기를 누르면 최종 내용이 즉시 팀 공지방으로 전송되어야 한다', '필수'],
        ['FR-04', '팀마다 디스코드 공지방이 따로 있어야 한다. 팀과 공지방을 짝지어 저장한다', '필수'],
        ['FR-05', '팀을 만들거나 없앨 때 디스코드 공지방을 자동으로 만들고 지울 수 있어야 한다', '미정'],
        ['FR-06', '팀장이 모임 진행 예상 시간을 미리 설정할 수 있어야 한다. 예를 들어 1시간 30분', '필수'],
        ['FR-07', '팀장이 일정 작성 요청을 보내면 참여자에게 알림이 가야 한다', '필수'],
        ['FR-08', '참여자가 달력에 자기 가능 시간을 설정할 수 있어야 한다. 월간과 주간 보기를 고를 수 있다', '필수'],
        ['FR-09', '참여자 전원이 그 주의 일정 확정을 누르면 후보 시간이 모두에게 떠야 한다. 후보는 진행 예상 시간이 들어가는 날짜와 시간이다', '필수'],
        ['FR-10', '참여자가 후보 시간에 투표할 수 있어야 한다', '필수'],
        ['FR-11', '투표에서 뽑힌 날짜와 시간이 그날의 발표 시간으로 고정되어야 한다', '필수'],
        ['FR-12', '확정 뒤에 팀장이 일정 변경을 시작하면 참여자 전원에게 알림이 가고 후보 투표를 다시 해야 한다', '필수'],
        ['FR-13', '확정된 일정이 디스코드에 자동으로 공지되어야 한다. 변경으로 다시 확정된 일정도 같다', '필수'],
        ['FR-14', '지정 폴더를 정해 두면 그 폴더의 파일 목록이 항상 보여야 한다. 녹화 저장 폴더가 대상이다', '필수'],
        ['FR-15', '목록에서 고른 파일을 올리기 전에 정말 올릴지 확인하는 버튼이 있어야 한다', '필수'],
        ['FR-16', '새로 고침 버튼으로 폴더 목록을 다시 읽을 수 있어야 한다', '필수'],
        ['FR-17', '파일을 드래그앤드롭으로도 올릴 수 있어야 한다', '필수'],
        ['FR-18', '올린 파일을 공지, 템플릿, 노하우, 기록 분류로 나눠 목록으로 볼 수 있어야 한다', '필수'],
        ['FR-19', '원하는 파일을 직접 내려받을 수 있어야 한다', '필수'],
        ['FR-20', '역할은 서비스 관리자, 서비스 운영자, 팀장, 부팀장, 회원 다섯 가지여야 한다', '필수'],
        ['FR-21', '서비스 운영자가 모임에 필요한 역할을 만들고 권한을 줄 수 있어야 한다', '2차'],
        ['FR-22', '팀마다 팀장 1인과 부팀장 1인 이상이 있어야 한다', '필수'],
        ['FR-23', '서비스 관리자가 팀원과 팀장을 설정할 수 있어야 한다', '필수'],
        ['FR-24', '서비스 관리자가 특정인, 팀장, 팀장과 부팀장, 전체에게 공지를 보낼 수 있어야 한다', '필수'],
        ['FR-25', '팀장이 부팀장과 팀원에게 공지를 보낼 수 있어야 한다', '필수'],
        ['FR-26', '공지가 대상에 맞는 디스코드 공지방으로 전송되어야 한다', '필수'],
        ['FR-27', '서비스 관리자 페이지에서 설정한 권한에 따라 디스코드 공지방이 구성, 수정, 삭제되어야 한다', '미정'],
        ['FR-28', '사용자가 이메일로 회원가입을 할 수 있어야 한다. 가입하면 인증 메일을 받고, 메일의 링크를 눌러야 가입이 끝난다', '필수'],
        ['FR-29', '사용자가 이메일과 비밀번호로 로그인과 로그아웃을 할 수 있어야 한다. 비밀번호를 잊으면 이메일로 다시 정할 수 있어야 한다', '필수'],
        ['FR-30', '로그인한 회원이 자기 활동을 저장하고 다시 불러올 수 있어야 한다', '필수'],
    ]),
    ('blank',),
    ('note', 'FR-05 와 FR-27 이 미정인 이유. 웹훅은 정해진 채널에 글을 보내는 일만 한다. 채널을 만들고 지우고 권한을 고치려면 봇이 서버에 들어가 있어야 한다. '
             '어느 방식으로 갈지는 담당자 회의에서 정한다. 두 방식의 비교는 디스코드 연동·기술 스택 검토 보고서에 있다.'),
    ('note', 'FR-21 이 2차인 이유. 서비스 운영자는 역할을 새로 만들고 권한을 주는 자리다. 1차에서는 역할 다섯 가지를 고정으로 두고, 서비스 운영자 기능은 2차에서 만든다.'),
    ('h2', '3.2 성능 요구사항'),
    ('table', 5, ['ID', '요구사항', '기준값'], [
        ['PR-01', '발송하기를 누르면 디스코드 공지방에 도착한다', '10초 안'],
        ['PR-02', '일반 화면이 뜬다', '3초 안'],
        ['PR-03', '동시 접속', '10명'],
        ['PR-04', '후보 시간 산출', '전원 확정 뒤 5초 안'],
        ['PR-05', '업로드 파일 크기 상한', '녹화 영상 1건 기준. RAID 1 실사용 2TB 안에서 정한다'],
        ['PR-06', '업로드 진행 상태 표시', '진행률을 화면에 보여 준다'],
    ]),
    ('blank',),
    ('h2', '3.3 인터페이스 요구사항'),
    ('h3', '사용자 인터페이스'),
    ('item', '모든 화면이 스마트폰 앱, PC 앱, 웹에서 같은 기능으로 동작해야 한다.'),
    ('item', '달력은 월간과 주간 보기를 전환할 수 있어야 한다.'),
    ('item', '후보 시간과 투표 현황을 한 화면에서 볼 수 있어야 한다.'),
    ('item', '지정 폴더의 파일 목록 화면에는 새로 고침 버튼과 업로드 확인 버튼이 있어야 한다.'),
    ('item', '공지 작성 화면에는 임시 저장하기와 발송하기 버튼이 따로 있어야 한다.'),
    ('item', '공지 발송 결과(임시 저장, 대기, 발송, 실패)를 공지 목록에서 볼 수 있어야 한다.'),
    ('item', '확정 뒤 일정이 바뀌면 이전 확정은 취소로 표시하고 새 투표 화면을 연다.'),
    ('item', '지정 폴더 보기는 PC 앱에서 늘 동작한다. 웹은 Chrome 과 Edge 에서만 되고, 다른 브라우저에서는 드래그앤드롭만 쓴다.'),
    ('h3', '시스템 인터페이스'),
    ('item', '디스코드 공지는 웹훅 또는 봇으로 보낸다. 방식은 담당자 회의에서 정한다.'),
    ('item', '디스코드 메시지는 공지 템플릿의 항목을 임베드 형식으로 보낸다.'),
    ('item', '화면 흐름은 상세설계서의 화면 설계를 따른다.'),
    ('h2', '3.4 운영 요구사항'),
    ('item', '미니PC 서버는 24시간 켜 둔다.'),
    ('item', '도메인과 HTTPS 로 접속한다.'),
    ('item', '시스템 관리자가 주 1회 백업을 확인한다.'),
    ('item', '디스코드 웹훅 주소와 봇 토큰은 서비스 관리자 페이지 또는 설정 파일에서 바꿀 수 있어야 한다.'),
    ('item', '장애가 나면 시스템 관리자에게 알린다. 이 항목은 Could 다.'),
    ('h2', '3.6 검증 요구사항'),
    ('table', 6, ['ID', '검증 항목', '판정 기준'], [
        ['VR-01', '공지 발송', '템플릿을 채워 발송하기를 누르면 팀 공지방에 같은 내용이 10초 안에 올라온다'],
        ['VR-02', '임시 저장', '임시 저장하기를 누르면 공지방에 올라가지 않고, 다시 열면 쓰던 내용이 남아 있다'],
        ['VR-03', '팀별 공지방', '두 팀을 만들고 각각 공지하면 서로 다른 채널에만 올라온다'],
        ['VR-04', '일정 요청 알림', '팀장이 요청을 보내면 참여자 전원에게 알림이 간다'],
        ['VR-05', '가능 시간 등록', '월간과 주간 보기에서 등록한 시간이 같게 보인다'],
        ['VR-06', '후보 시간 산출', '전원 확정 뒤 진행 예상 시간이 들어가는 구간만 후보로 뜬다. 안 들어가는 구간은 뜨지 않는다'],
        ['VR-07', '투표와 확정', '최다 득표 후보가 확정 일정으로 저장되고 디스코드에 자동 공지된다'],
        ['VR-08', '확정 뒤 일정 변경', '팀장이 일정 변경을 시작하면 전원에게 알림이 가고 새 투표가 열린다. 이전 확정은 취소로 표시된다'],
        ['VR-09', '지정 폴더 업로드', '지정 폴더에 파일을 넣고 새로 고침하면 목록에 나타난다. 확인 버튼을 눌러야 올라간다'],
        ['VR-10', '드래그앤드롭 업로드', '끌어다 놓은 파일이 올라가고 분류 목록에 나타난다'],
        ['VR-11', '다운로드', '다른 회원이 내려받은 파일이 원본과 같다'],
        ['VR-12', '역할과 공지 대상', '팀장은 부팀장과 팀원에게만 보낼 수 있고, 서비스 관리자는 네 가지 대상 모두에게 보낼 수 있다'],
        ['VR-13', '회원 활동 복원', '로그아웃 뒤 다시 로그인하면 등록한 가능 시간과 올린 파일이 그대로 보인다'],
    ]),
    ('blank',),
    ('h2', '3.7 인수 테스트 요구사항'),
    ('text', '검증(3.6)은 개발자가 스스로 확인하는 절차다. 인수는 모임이 결과물을 받아들이는 기준이다. 본 과제는 1차 오픈 시연으로 인수한다.'),
    ('table', 7, ['ID', '인수 항목', '인수 기준'], [
        ['AT-01', '시연 시나리오 완주', '회원가입, 로그인, 일정 요청, 가능 시간 등록, 투표, 자동 공지까지 중단 없이 수행'],
        ['AT-02', '실제 디스코드 동작', '테스트 서버가 아닌 모임 디스코드 공지방에 공지가 올라온다'],
        ['AT-03', '사용자 테스트 통과', '이영희이 사용자 시나리오 전부를 통과로 판정'],
        ['AT-04', '세 가지 기기', '같은 시나리오를 스마트폰 앱, PC 앱, 웹에서 각각 완주'],
        ['AT-05', '산출물 제출', '3.8 문서화 요구사항에 정한 문서 일체 제출'],
    ]),
    ('blank',),
    ('small', '인수 시 유의 사항'),
    ('item', '시연 전날 디스코드 웹훅 주소와 봇 토큰이 살아 있는지 확인한다.'),
    ('item', '시연용 팀과 회원 계정을 미리 만들어 둔다.'),
    ('h2', '3.8 문서화 요구사항'),
    ('text', '작성 대상 문서는 docs 폴더에 두고 이름 뒤에 버전을 붙인다.'),
    ('h3', '수행 산출물'),
    ('table', 8, ['ID', '문서', '본 과제에서의 내용', '시점'], [
        ['DR-01', '과제제안서', '배경, 목표, 추진 체계, 일정', '착수'],
        ['DR-02', '요구사항서', '본 문서', '요구분석'],
        ['DR-03', '상세설계서', '시스템 구조, ERD, API 계약, 프로세스, 화면 설계, 모듈 경계', '설계'],
        ['DR-04', '테스트 계획서', '범위, 테스트 종류, 시나리오, 환경, 일정', '4주차'],
        ['DR-05', '테스트 결과서', '수행 결과와 판정, 캡처', '검증'],
        ['DR-06', 'WBS 일정표', '작업 분해와 주차별 진척', '상시'],
        ['DR-07', '1차 회고', '잘된 것, 문제, 2차 범위', '종료'],
    ]),
    ('blank',),
    ('h3', '작성·갱신 규칙'),
    ('item', '문서 이름 뒤에 버전을 붙인다. 이전 판은 같은 폴더의 레거시 폴더에 옮긴다.'),
    ('item', '설계 변경이 생기면 같은 주 안에 상세설계서를 고친다.'),
    ('item', 'DB 스키마를 바꾸면 ERD 를 함께 고친다.'),
    ('item', '결정 사항은 근거와 함께 기록한다.'),
    ('item', '테스트 계획서와 결과서를 분리한다. 판정 기준은 결과가 나오기 전에 정한다.'),
    ('h2', '3.9 보안 요구사항'),
    ('table', 10, ['ID', '요구사항'], [
        ['SR-01', '비밀번호는 해시로 저장한다'],
        ['SR-02', 'HTTPS 만 쓴다'],
        ['SR-03', '역할 검사는 서버에서 한다. 화면에서 숨기는 것만으로 권한을 나누지 않는다'],
        ['SR-04', '디스코드 웹훅 주소와 봇 토큰은 코드 저장소에 넣지 않는다. 설정 파일이나 환경 변수에 둔다'],
        ['SR-05', '올릴 수 있는 파일 종류와 크기를 제한한다'],
        ['SR-06', '회원이 아니면 어떤 자료도 볼 수 없다'],
        ['SR-07', '탈퇴한 회원의 개인정보는 지운다'],
    ]),
    ('blank',),
    ('h2', '3.10 이식성 요구사항'),
    ('table', 11, ['ID', '요구사항'], [
        ['PO-01', '모든 화면이 스마트폰 앱, PC 앱, 웹에서 같은 기능으로 동작해야 한다. 스마트폰은 Android 와 iOS, PC 는 Windows 와 macOS 다'],
        ['PO-02', '서버는 특정 호스팅 환경에 종속되지 않아야 한다. 미니PC 를 바꿔도 다시 배포할 수 있게 설치 절차를 남긴다'],
        ['PO-03', '업로드 파일은 파일 저장소에 두고 DB 에는 경로만 둔다. 저장소 위치를 설정으로 바꿀 수 있다'],
        ['PO-04', '서버는 Docker Compose 로 띄운다. Supabase 는 셀프호스팅판을 쓰고, 파일 저장소는 설정만 바꿔 S3 호환 저장소로 옮길 수 있다'],
    ]),
    ('blank',),
    ('text', '기술 스택은 Flutter + Supabase 셀프호스팅 + Go 보조 서버다. 후보 비교와 평점은 컴포넌트별 기술 스택 평가 보고서 v1.2.1 에 있다.'),
    ('pagebreak',),
    ('h2', '3.11 시스템 요구사항'),
    ('h3', '구성 아키텍처'),
    ('img', os.environ.get('ARCH_PNG') or os.path.join(OUT_DIR, '구성 아키텍처.png')),
    ('text', '그림의 추천 칸이 정한 기술 스택이다. 대안 칸은 비교할 때 본 후보로 남겨 둔다.'),
    ('blank',),
    ('h3', '운영 환경'),
    ('table', 12, ['구분', '요구사항'], [
        ['서버', '미니PC 1대. Intel N100, RAM 16GB, HDD 2TB 두 개를 RAID 1 로 묶어 실사용 2TB. 리눅스 위에 Docker Compose 로 Caddy, Supabase, Go 보조 서버를 띄운다. Supabase Studio 는 시스템 운영자만 Tailscale 로 연다'],
        ['클라이언트', '스마트폰 앱(Android, iOS), PC 앱(Windows, macOS), 웹 브라우저. 웹의 폴더 지정은 Chrome 과 Edge'],
        ['외부 서비스', '디스코드 서버와 팀별 공지 채널, GitHub 조직 저장소, 도메인 1개'],
    ]),
    ('blank',),
    ('h3', '데이터 관리'),
    ('item', '개발 중 스키마를 바꿀 때 이미 들어간 데이터를 보존하는 이행 절차를 둔다.'),
    ('item', 'DB 와 업로드 파일을 주 1회 백업한다. 백업은 세대별로 보관한다.'),
    ('item', '백업 파일은 시스템 관리자만 접근하는 곳에 둔다.'),
    ('h2', '3.12 신뢰성 요구사항'),
    ('table', 13, ['ID', '요구사항', '기준'], [
        ['RR-01', '공지 전송 실패를 조용히 넘기지 않는다', '실패 상태를 목록에 표시하고 다시 보낼 수 있다'],
        ['RR-02', '확정 일정이 유실되지 않는다', '확정 뒤 서버가 재시작해도 그대로 남는다'],
        ['RR-03', '업로드가 중단되면 부분 파일이 남지 않는다', '실패한 업로드는 목록에 나타나지 않는다'],
        ['RR-04', '백업에서 복원할 수 있다', '백업으로 복원한 뒤 회원, 일정, 자료가 그대로다'],
    ]),
    ('blank',),
    ('h2', '부록 A. 요구사항 추적표'),
    ('table', 14, ['요구사항', '관련 개발 항목', '검증 항목'], [
        ['FR-01 ~ FR-04', '디스코드 공지 (WBS 4.6)', 'VR-01 ~ VR-03'],
        ['FR-05', '미정. 방식을 정한 뒤 배정한다', '없음'],
        ['FR-06 ~ FR-13', '모임 일정 관리 (WBS 4.4)', 'VR-04 ~ VR-08'],
        ['FR-14 ~ FR-19', '파일 업로드·자료 공유 (WBS 4.5)', 'VR-09 ~ VR-11'],
        ['FR-20, FR-22 ~ FR-26', '서비스 관리자 페이지 (WBS 4.7)', 'VR-12'],
        ['FR-21', '2차. 서비스 운영자 기능', '없음'],
        ['FR-27', '미정. 방식을 정한 뒤 배정한다', '없음'],
        ['FR-28 ~ FR-30', '회원가입·로그인 (WBS 4.3)', 'VR-13'],
        ['PR-01 ~ PR-06', '각 기능 개발, 버그 수정 (WBS 4.3 ~ 4.7, 5.4)', 'AT-01'],
        ['SR-01 ~ SR-07', '프로젝트 골격, 회원가입·로그인 (WBS 4.1, 4.3)', 'VR-12, VR-13'],
        ['PO-01 ~ PO-04', '공통 레이아웃·반응형 (WBS 4.2), 운영 배포 (WBS 5.5)', 'AT-04'],
        ['RR-01 ~ RR-04', '디스코드 공지, 파일 업로드, 운영 점검 (WBS 4.6, 4.5, 3.5)', 'VR-01, VR-09'],
        ['DR-01 ~ DR-07', '문서화 (WBS 1.2, 2.1 ~ 2.5, 5.1)', 'AT-05'],
        ['AT-01 ~ AT-05', '사용자 테스트, 운영 배포·1차 오픈 (WBS 5.2 ~ 5.5)', '없음'],
    ]),
    ('blank',),
]

# 표 열 폭 비율. 키 = "첫 머리글/끝 머리글". 없으면 양식대로 같은 폭.
WIDTHS = {
    '구분/내용': (1, 3.5), '제외 항목/사유': (1.6, 2), '목표/달성 기준': (1.2, 3),
    'ID/우선순위': (1, 5.2, 1.1), 'ID/기준값': (1, 3.2, 2.4), 'ID/판정 기준': (1, 2, 3.4), 'ID/인수 기준': (1, 2, 3.4),
    'ID/시점': (1, 1.6, 3.4, 1), 'ID/요구사항': (1, 4.5), '구분/요구사항': (1, 3.5), 'ID/기준': (1, 3, 3),
    '요구사항/검증 항목': (1.4, 3.2, 1.6),
}

# 목차: h1 → toc1, h2 → toc2 (부록 A 는 h2 이지만 목차에서는 toc1)
def toc_entries():
    for el in BODY:
        if el[0] == 'h1' or (el[0] == 'h2' and el[1].startswith('부록')):
            yield 1, el[1]
        elif el[0] == 'h2':
            yield 2, el[1]


# ---------------------------------------------------------------- 그림 (matplotlib)
def draw_all():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
    os.makedirs(IMG_DIR, exist_ok=True)

    def figure(cols, rows):
        # 격자 8칸 = 6.3 인치(160 mm) 가 되게 잡아 글자 크기가 문서에서 그대로 나오게 한다.
        fig = plt.figure(figsize=(cols * 0.79, rows * 0.5 + 0.05), dpi=200)
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, cols); ax.set_ylim(0, rows); ax.axis('off')
        return fig, ax

    def box(ax, x, y, w, h, text, fill='#F2F2F2', bold=False, size=7.5):
        ax.add_patch(FancyBboxPatch((x + 0.05, y + 0.06), w - 0.1, h - 0.12, boxstyle='round,pad=0.02,rounding_size=0.05',
                                    linewidth=0.8, edgecolor='#404040', facecolor=fill))
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=size, fontweight='bold' if bold else 'normal', linespacing=1.3)

    def arrow(ax, p, q, text=None, size=6.5):
        ax.annotate('', xy=q, xytext=p, arrowprops=dict(arrowstyle='-|>', lw=0.8, color='#404040', shrinkA=0, shrinkB=0))
        if text:
            ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.07, text, ha='center', va='bottom', fontsize=size, color='#303030')

    # 1. 시스템 구성
    fig, ax = figure(8, 4)
    box(ax, 0, 2.2, 2, 1.2, '회원 브라우저\nPC · 모바일')
    box(ax, 0, 0.4, 2, 1.2, '발표자 PC\n지정 폴더(녹화)')
    box(ax, 3, 0.4, 2.6, 3.2, '', fill='#E8EEF7')
    ax.text(4.3, 3.35, '미니PC 서버', ha='center', va='center', fontsize=7, fontweight='bold')
    box(ax, 3.2, 2.3, 2.2, 0.75, '웹 앱 (화면 + API)', fill='white')
    box(ax, 3.2, 1.45, 2.2, 0.75, 'DB', fill='white')
    box(ax, 3.2, 0.6, 2.2, 0.75, '파일 저장소', fill='white')
    box(ax, 6.2, 2.2, 1.8, 1.2, '디스코드\n팀 공지방')
    box(ax, 6.2, 0.4, 1.8, 1.2, 'GitHub\n조직 저장소')
    arrow(ax, (2, 2.8), (3.2, 2.8), 'HTTPS')
    arrow(ax, (2, 1.0), (2.6, 1.0)); arrow(ax, (2.6, 1.0), (2.6, 2.6)); ax.text(2.55, 1.8, '파일 목록\n·선택', ha='right', va='center', fontsize=5.5)
    arrow(ax, (5.4, 2.7), (6.2, 2.7), '웹훅 / 봇')
    arrow(ax, (6.2, 1.0), (5.5, 1.0), '배포')
    fig.savefig(os.path.join(IMG_DIR, 'system.png')); plt.close(fig)

    # 2. 공지 발송 흐름
    fig, ax = figure(8, 3.1)
    steps = ['작성자\n템플릿 고르기', '빈칸 채우기\n대상 고르기', '발송하기', '서버가 대상의\n공지방 찾기', '디스코드로\n전송', '발송 결과\n기록']
    for i, s in enumerate(steps):
        box(ax, i * 1.33, 1.6, 1.3, 1.1, s)
        if i:
            arrow(ax, (i * 1.33 - 0.03, 2.15), (i * 1.33 + 0.05, 2.15))
    box(ax, 0.0, 0.1, 1.25, 1.0, '공지 템플릿\n만들기 · 수정', fill='#E8EEF7', size=7)
    arrow(ax, (0.62, 1.1), (0.62, 1.6))
    box(ax, 1.4, 0.1, 1.9, 1.0, '임시 저장하기\n쓰던 내용 보관, 발송 안 함', fill='#E8EEF7', size=7)
    arrow(ax, (2.2, 1.1), (2.2, 1.6)); arrow(ax, (2.45, 1.6), (2.45, 1.1))
    ax.text(2.33, 1.35, '저장 / 다시 열기', ha='left', va='center', fontsize=6, color='#303030')
    box(ax, 4.2, 0.1, 3.4, 1.0, '팀 공지방 (팀마다 하나)\n웹훅 URL 또는 봇 채널', fill='#E8EEF7', size=7)
    arrow(ax, (5.9, 1.1), (5.9, 1.6))
    fig.savefig(os.path.join(IMG_DIR, 'notice.png')); plt.close(fig)

    # 3. 일정 조율 흐름 (확정 뒤 변경 → 전원 알림 → 재투표 고리 포함)
    fig, ax = figure(8, 5.3)
    top = ['팀장\n진행 예상 시간 설정', '일정 작성 요청', '참여자에게 알림', '참여자\n달력에 가능 시간']
    bottom = ['전원 "확정" 누름', '후보 시간 산출', '투표', '확정 일정 고정\n디스코드 자동 공지']
    for i, s in enumerate(top):
        box(ax, i * 2, 3.9, 1.9, 1.2, s)
        if i:
            arrow(ax, (i * 2 - 0.1, 4.5), (i * 2 + 0.05, 4.5))
    arrow(ax, (7, 3.9), (7, 3.5)); arrow(ax, (7, 3.5), (0.95, 3.5)); arrow(ax, (0.95, 3.5), (0.95, 3.1))
    ax.text(4, 3.6, '월간 / 주간 보기로 등록', ha='center', va='bottom', fontsize=6, color='#303030')
    for i, s in enumerate(bottom):
        box(ax, i * 2, 1.8, 1.9, 1.2, s, fill='#E8EEF7' if i == 3 else '#F2F2F2')
        if i:
            arrow(ax, (i * 2 - 0.1, 2.4), (i * 2 + 0.05, 2.4))
    box(ax, 2.6, 0.2, 3.2, 1.0, '확정 뒤 팀장이 일정 변경\n전원에게 알림, 이전 확정은 취소', fill='#FBEFEF', size=7)
    arrow(ax, (7, 1.8), (7, 0.7)); arrow(ax, (7, 0.7), (5.8, 0.7))
    arrow(ax, (2.6, 0.7), (2.95, 0.7)); arrow(ax, (2.95, 0.7), (2.95, 1.8))
    ax.text(2.85, 1.3, '재투표', ha='right', va='center', fontsize=6, color='#303030')
    fig.savefig(os.path.join(IMG_DIR, 'schedule.png')); plt.close(fig)

    # 4. 파일 업로드·공유 흐름
    fig, ax = figure(8, 3.2)
    box(ax, 0, 1.9, 1.9, 1.2, '지정 폴더\n파일 목록 (새로 고침)')
    box(ax, 0, 0.2, 1.9, 1.2, '드래그앤드롭')
    box(ax, 2.4, 1.05, 1.6, 1.2, '올릴지 확인')
    box(ax, 4.4, 1.05, 1.6, 1.2, '서버 저장\n분류 붙이기')
    box(ax, 6.4, 1.9, 1.6, 1.2, '분류별 목록\n공지·템플릿·노하우·기록', size=5.8)
    box(ax, 6.4, 0.2, 1.6, 1.2, '다운로드')
    arrow(ax, (1.9, 2.5), (2.4, 1.85), '선택')
    arrow(ax, (1.9, 0.8), (2.4, 1.45))
    arrow(ax, (4.0, 1.65), (4.4, 1.65), '업로드')
    arrow(ax, (6.0, 1.85), (6.4, 2.4))
    arrow(ax, (7.2, 1.9), (7.2, 1.4))
    fig.savefig(os.path.join(IMG_DIR, 'file.png')); plt.close(fig)


# ---------------------------------------------------------------- docx 조립
def p_text(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t')))


def set_text(p, text, keep=None):
    """문단의 run 을 하나만 남기고 글자를 바꾼다. keep 은 남길 run 을 고르는 함수(기본: 첫 run). '\t' 는 탭."""
    runs = p.findall(qn('w:r'))
    r = keep(runs) if keep else runs[0]
    for x in runs:
        if x is not r:
            p.remove(x)
    for t in list(r):
        if t.tag in (qn('w:t'), qn('w:tab'), qn('w:br'), qn('w:drawing')):
            r.remove(t)
    for i, part in enumerate(text.split('\t')):
        if i:
            r.append(OxmlElement('w:tab'))
        if part:
            t = OxmlElement('w:t'); t.text = part; t.set(qn('xml:space'), 'preserve'); r.append(t)


def set_cell(tc, text):
    ps = tc.findall(qn('w:p'))
    for p in ps[1:]:
        tc.remove(p)
    p = ps[0]
    if not p.findall(qn('w:r')):
        p.append(OxmlElement('w:r'))
    set_text(p, text)


def strip_bold(el):
    """본보기 run 이 굵게였던 경우(양식 T5·T10 데이터행, '목적:' 문단) 굵기를 뺀다. 머리행에는 쓰지 않는다."""
    for rpr in el.iter(qn('w:rPr')):
        for tag in ('w:b', 'w:bCs'):
            for b in rpr.findall(qn(tag)):
                rpr.remove(b)


def make_table(tpl_tbl, header, rows, widths=None):
    """양식 표를 복제해 머리행 + 데이터행을 채운다. widths 는 열 폭 비율(합계는 양식 표의 전체 폭을 유지)."""
    t = copy.deepcopy(tpl_tbl)
    trs = t.findall(qn('w:tr'))
    for tr in trs[2:]:
        t.remove(tr)
    hdr, data = trs[0], trs[1]
    t.remove(data)
    strip_bold(data)
    for tc, txt in zip(hdr.findall(qn('w:tc')), header):
        set_cell(tc, txt)
    for row in rows:
        tr = copy.deepcopy(data)
        for tc, txt in zip(tr.findall(qn('w:tc')), row):
            set_cell(tc, txt)
        t.append(tr)
    for sz in t.iter(qn('w:sz')):          # 양식 9pt → TABLE_SZ (사용자: 표 글자가 작아 읽기 힘들다)
        sz.set(qn('w:val'), str(TABLE_SZ))
    for sz in t.iter(qn('w:szCs')):
        sz.set(qn('w:val'), str(TABLE_SZ))
    if widths:
        # 양식 표는 열 폭이 모두 같다(2열 4759/4759, 3열 3173×3). ID 열이 넓고 본문 열이 좁아 세 줄로 접히므로 비율을 준다.
        cols = t.find(qn('w:tblGrid')).findall(qn('w:gridCol'))
        total = sum(int(c.get(qn('w:w'))) for c in cols)
        ws = [int(total * w / sum(widths)) for w in widths]
        for c, w in zip(cols, ws):
            c.set(qn('w:w'), str(w))
        for tr in t.findall(qn('w:tr')):
            for tc, w in zip(tr.findall(qn('w:tc')), ws):
                tcw = tc.find(qn('w:tcPr')).find(qn('w:tcW'))
                tcw.set(qn('w:w'), str(w)); tcw.set(qn('w:type'), 'dxa')
    return t


def add_right_tab(p, pos=9500):
    """목차 문단에 오른쪽 탭(점선)을 넣어 쪽 번호를 오른쪽 끝에 맞춘다. 본문 폭 167.9 mm ≈ 9519 twip."""
    ppr = p.find(qn('w:pPr'))
    if ppr is None:
        ppr = OxmlElement('w:pPr'); p.insert(0, ppr)
    for old in ppr.findall(qn('w:tabs')):
        ppr.remove(old)
    tabs = OxmlElement('w:tabs'); tab = OxmlElement('w:tab')
    tab.set(qn('w:val'), 'right'); tab.set(qn('w:leader'), 'dot'); tab.set(qn('w:pos'), str(pos)); tabs.append(tab)
    before = {qn(t) for t in ('w:pStyle', 'w:keepNext', 'w:keepLines', 'w:pageBreakBefore', 'w:framePr', 'w:widowControl',
                              'w:numPr', 'w:suppressLineNumbers', 'w:pBdr', 'w:shd')}
    idx = 0
    for i, ch in enumerate(list(ppr)):
        if ch.tag in before:
            idx = i + 1
    ppr.insert(idx, tabs)


def build():
    draw_all()
    d = Document(TPL)
    body = d.element.body
    els = list(body.iterchildren())
    paras = [e for e in els if e.tag == qn('w:p')]
    tbls = [e for e in els if e.tag == qn('w:tbl')]
    sect = els[-1]
    assert sect.tag == qn('w:sectPr'), '마지막 요소가 sectPr 이 아니다'

    def find(prefix):
        for p in paras:
            if p_text(p).startswith(prefix):
                return copy.deepcopy(p)
        raise KeyError(prefix)

    def toc_of(style):
        # 스타일 ID(XML 의 w:val)와 스타일 이름('toc 1')이 다르므로 python-docx 로 이름을 비교한다
        for p in paras:
            if Paragraph(p, d._body).style.name == style:
                return copy.deepcopy(p)
        raise KeyError(style)

    X = {
        'title': find('요 구 사 항 서'), 'subtitle': find('Agent를 위한'), 'toc_title': find('목 차'),
        'toc1': toc_of('toc 1'), 'toc2': toc_of('toc 2'),
        'h1': find('1. 개요'), 'h2': find('1.1 시스템의'), 'h3': find('시스템 구성'),
        'item': find('1) LLM'), 'text': find('목적:'), 'note': find('FR-04 · FR-05'), 'dict': find('소스(채널)'),
        'small': find('인수 시 유의 사항'), 'img': next(copy.deepcopy(p) for p in paras if p.find('.//' + qn('w:drawing')) is not None),
        # 빈 문단 본보기. 표지 뒤 문단(P15)은 쪽 나눔을 품고 있어 빼야 한다 — 이걸 썼더니 빈 줄마다 쪽이 넘어가 42쪽이 됐다
        'blank': next(copy.deepcopy(p) for p in paras[16:] if not p_text(p).strip()
                      and all(p.find('.//' + qn(t)) is None for t in ('w:drawing', 'w:br', 'w:pageBreakBefore'))),
    }
    cover_tbl = copy.deepcopy(tbls[0])
    tbl_x = [copy.deepcopy(t) for t in tbls]

    # 본문 비우기
    for e in els[:-1]:
        body.remove(e)

    def add(el):
        sect.addprevious(el)
        return el

    def para(kind, text, **kw):
        p = copy.deepcopy(X[kind]); set_text(p, text, **kw); return add(p)

    def pagebreak():
        p = copy.deepcopy(X['blank']); r = OxmlElement('w:r'); br = OxmlElement('w:br'); br.set(qn('w:type'), 'page'); r.append(br); p.append(r); add(p)

    # 표지: 양식과 같은 위치(빈 줄 5개 → 제목 → 빈 줄 → 부제 → 빈 줄 6개 → 표)
    for _ in range(5): add(copy.deepcopy(X['blank']))
    para('title', TITLE); add(copy.deepcopy(X['blank']))
    para('subtitle', SUBTITLE)
    for _ in range(6): add(copy.deepcopy(X['blank']))
    for tr, (k, v) in zip(cover_tbl.findall(qn('w:tr')), COVER):
        tcs = tr.findall(qn('w:tc')); set_cell(tcs[0], k); set_cell(tcs[1], v)
    add(cover_tbl)
    pagebreak()
    # 목차 (쪽 번호는 '#', fill_toc.ps1 이 채운다)
    para('toc_title', '목 차', keep=lambda runs: next((r for r in runs if '목' in ''.join(t.text or '' for t in r.iter(qn('w:t')))), runs[0]))
    for lv, title in toc_entries():
        add_right_tab(para('toc1' if lv == 1 else 'toc2', f'{title}\t#'))
    # 본문
    n = 0
    for el in BODY:
        k = el[0]
        if k in ('h1', 'h2', 'h3', 'small'):
            n = 0; para(k, el[1])
        elif k == 'item':
            n += 1; para('item', f'{n}) {el[1]}')
        elif k in ('text', 'note', 'dict'):
            strip_bold(para(k, el[1]))
        elif k == 'blank':
            add(copy.deepcopy(X['blank']))
        elif k == 'pagebreak':
            pagebreak()
        elif k == 'table':
            add(make_table(tbl_x[el[1]], el[2], el[3], WIDTHS.get(el[2][0] + '/' + el[2][-1])))
        elif k == 'img':
            img = os.path.join(IMG_DIR, el[1])
            if not os.path.exists(img):
                sys.exit(f'그림이 없다: {img}. 먼저 arch_build.py 로 만들거나 ARCH_PNG 로 다른 그림을 가리킨다.')
            p = copy.deepcopy(X['img'])
            for r in p.findall(qn('w:r')):
                p.remove(r)
            add(p)
            Paragraph(p, d._body).add_run().add_picture(img, width=Mm(160))
        else:
            raise ValueError(k)
    d.save(OUT)
    print('saved', OUT)


if __name__ == '__main__':
    build()
