import os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('OUT_DIR') or 'out', '구성 아키텍처.png')
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)

W, H = 20, 13.2
fig = plt.figure(figsize=(W, H), dpi=150)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
fig.patch.set_facecolor('white')

C_CLIENT = '#E3EEF9'; C_SERVER = '#E6F4EA'; C_EXT = '#FDF0E1'; C_TOOL = '#F1ECF8'
EDGE = '#3A3A3A'


def box(x, y, w, h, fill, title, need, pick, alt, tsize=13):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.12',
                                lw=1.3, ec=EDGE, fc=fill, zorder=2))
    ax.text(x + 0.18, y + h - 0.3, title, fontsize=tsize, fontweight='bold', va='top', zorder=3)
    ax.text(x + 0.18, y + h - 0.82, '필요한 것: ' + need, fontsize=10.5, va='top', color='#333', zorder=3)
    ax.text(x + 0.18, y + h - 1.25, '추천: ' + pick, fontsize=10.5, va='top', color='#0B5394', fontweight='bold', zorder=3)
    if alt:
        ax.text(x + 0.18, y + h - 1.68, '대안: ' + alt, fontsize=9.5, va='top', color='#666', zorder=3)


def arrow(p, q, label=None, lx=0, ly=0.12, both=False, color=EDGE):
    ax.annotate('', xy=q, xytext=p, zorder=1,
                arrowprops=dict(arrowstyle='<|-|>' if both else '-|>', lw=1.4, color=color, shrinkA=0, shrinkB=0))
    if label:
        ax.text((p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly, label, fontsize=9.5, ha='center', va='bottom',
                color='#222', zorder=4, bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none'))


# 제목
ax.text(0.4, H - 0.35, '주간발표회 1차 구성 아키텍처와 컴포넌트별 기술 스택', fontsize=19, fontweight='bold', va='top')
ax.text(0.4, H - 0.98, '추천 = 컴포넌트별 기술 스택 평가 보고서 v1.2.1 의 제안 (조합 H2: Flutter + Supabase 셀프호스팅 + Go 보조 서버). 기술 스택은 회의에서 확정한다.',
        fontsize=11, va='top', color='#444')

# ── 사용자 쪽
ax.text(0.4, 11.35, '사용자 기기', fontsize=13, fontweight='bold', color='#0B5394')
box(0.4, 8.75, 5.0, 2.35, C_CLIENT, '① 스마트폰 앱  (Android · iOS)',
    '크로스플랫폼 앱 프레임워크', 'Flutter (Dart)', 'React Native + Expo (TypeScript)')
ax.text(0.58, 8.98, '모든 화면 · 파일 고르기와 공유하기로 올리기', fontsize=9.5, color='#555', zorder=3)
box(0.4, 5.85, 5.0, 2.55, C_CLIENT, '② PC 앱  (Windows · macOS)',
    '데스크톱 앱 프레임워크', 'Flutter desktop (①과 같은 코드)', 'Tauri, Electron')
ax.text(0.58, 6.08, '모든 화면 · 녹화 폴더 감시 · 이어 올리기(tus)', fontsize=9.5, color='#555', zorder=3)
box(0.4, 3.2, 5.0, 2.3, C_CLIENT, '③ 웹  (브라우저)',
    '웹 프론트엔드', 'Flutter web (①과 같은 코드)', 'Next.js (TypeScript)')
ax.text(0.58, 3.42, '모든 화면 · 폴더 지정은 Chrome · Edge', fontsize=9.5, color='#555', zorder=3)

# ── 미니PC 서버
SX, SY, SW, SH = 6.7, 3.2, 7.4, 7.9
ax.add_patch(FancyBboxPatch((SX, SY), SW, SH, boxstyle='round,pad=0.02,rounding_size=0.15',
                            lw=1.8, ec='#2E7D32', fc='#F7FBF7', ls='--', zorder=0))
ax.text(SX + 0.2, SY + SH + 0.2, '미니PC 서버  (Intel N100 · RAM 16GB · HDD 2TB×2 RAID 1 · Linux)',
        fontsize=13, fontweight='bold', color='#2E7D32')
ax.text(SX + SW - 0.2, SY + 0.22, '전체를 Docker Compose 로 실행', fontsize=10, ha='right', color='#2E7D32', style='italic')
ax.text(SX + 0.3, SY + 0.22, 'Supabase Studio = 시스템 운영자 전용. Tailscale 로만 접속', fontsize=9.5, color='#8B1A1A', zorder=3)

box(SX + 0.3, 9.25, SW - 0.6, 1.55, C_SERVER, '④ 리버스 프록시 · HTTPS',
    '웹 서버 / 인증서 자동 발급', 'Caddy', None, tsize=12)
ax.text(SX + 4.2, 10.02, '대안: Nginx + Let\'s Encrypt', fontsize=9.5, color='#666', zorder=3)

box(SX + 0.3, 6.6, 3.45, 2.3, C_SERVER, '⑤ 인증 · 데이터 API',
    'BaaS 또는 백엔드', 'Supabase', '직접 구현 (Go)', tsize=12)
box(SX + 3.95, 6.6, 3.15, 2.3, C_SERVER, '⑥ 업무 로직 서버',
    '백엔드 언어', 'Go', 'Node(Hono), Python', tsize=12)
ax.text(SX + 4.13, 6.78, '후보 시간 계산 · 공지 발송', fontsize=9, color='#555', zorder=3)

box(SX + 0.3, 3.75, 3.45, 2.45, C_SERVER, '⑦ 데이터베이스',
    '관계형 DB', 'PostgreSQL (Supabase 내장)', 'SQLite (⑤ 가 PocketBase 면)', tsize=12)
ax.text(SX + 0.48, 3.93, '회원 · 팀 · 일정 · 투표 · 공지', fontsize=9, color='#555', zorder=3)
box(SX + 3.95, 3.75, 3.15, 2.45, C_SERVER, '⑧ 파일 저장소',
    '파일 스토리지', 'Supabase Storage', 'tusd + 디스크', tsize=12)
ax.text(SX + 4.13, 3.93, '녹화 영상 · 발표 자료', fontsize=9, color='#555', zorder=3)

# ── 외부 서비스
EX = 15.2
ax.text(EX, 11.35, '외부 서비스', fontsize=13, fontweight='bold', color='#B45F06')
box(EX, 8.75, 4.4, 2.35, C_EXT, '⑨ 디스코드',
    '공지 연동 방식', '웹훅 (1차)', '봇 (채널 자동 생성 시)')
box(EX, 5.95, 4.4, 2.4, C_EXT, '⑩ 알림',
    '회원에게 알림 보내기', '디스코드 알림 (⑨) + 앱 안 알림', 'FCM · APNs 앱 푸시')
box(EX, 3.2, 4.4, 2.35, C_EXT, '⑪ 앱 배포',
    '설치 파일 배포 경로', 'GitHub Actions 빌드 · APK·PC 설치 파일', 'Play 내부 테스트 · TestFlight')

# ── 화살표
arrow((5.4, 9.9), (SX + 0.3, 9.9), 'HTTPS · REST/JSON', both=True)
arrow((5.4, 7.1), (SX + 0.3, 9.6), 'HTTPS · tus 업로드', lx=-0.2, ly=0.1)
arrow((5.4, 4.35), (SX + 0.3, 9.4), 'HTTPS', lx=0.25, ly=-0.2, both=True)
# 프록시 → 내부
arrow((SX + 2.0, 9.25), (SX + 2.0, 8.9))
arrow((SX + 5.5, 9.25), (SX + 5.5, 8.9))
# 내부 연결
arrow((SX + 2.0, 6.6), (SX + 2.0, 6.2))
arrow((SX + 3.75, 7.75), (SX + 3.95, 7.75), both=True)
arrow((SX + 5.5, 6.6), (SX + 2.9, 6.2))
arrow((SX + 5.5, 6.6), (SX + 5.5, 6.2), color='#999')
# 외부로
arrow((SX + 7.1, 8.3), (EX, 9.6), '웹훅 POST', lx=0.1, ly=0.08)
arrow((SX + 7.1, 7.3), (EX, 7.1), '앱 푸시 (대안)', ly=0.08, color='#999')
ax.text(EX + 0.18, 3.42, 'iPhone 회원이 있으면 iOS 만 TestFlight', fontsize=9.5, color='#B45F06', zorder=3)

# ── 개발 도구 띠
ax.add_patch(FancyBboxPatch((0.4, 1.55), 19.2, 1.0, boxstyle='round,pad=0.02,rounding_size=0.1',
                            lw=1.2, ec=EDGE, fc=C_TOOL, zorder=2))
ax.text(0.6, 2.05, '⑫ 개발 · 운영 도구', fontsize=12, fontweight='bold', va='center', zorder=3)
ax.text(3.5, 2.05, '코드 저장소 GitHub (조직 레포)   ·   CI/CD 와 APK 빌드 GitHub Actions   ·   컨테이너 Docker Compose   ·   '
                   'iOS 빌드 Mac + Xcode   ·   AI 코딩 도구', fontsize=10.5, va='center', zorder=3)

# ── 범례
lx = 0.4
for c, t in [(C_CLIENT, '사용자 기기에서 도는 것'), (C_SERVER, '미니PC 서버에서 도는 것'),
             (C_EXT, '외부 서비스'), (C_TOOL, '개발 도구')]:
    ax.add_patch(FancyBboxPatch((lx, 0.75), 0.45, 0.35, boxstyle='round,pad=0.01', fc=c, ec=EDGE, lw=0.8))
    ax.text(lx + 0.6, 0.92, t, fontsize=10.5, va='center')
    lx += 4.1
ax.text(0.4, 0.3, '파란 글자 = 추천안(H2).  회색 글자 = 대안.  ①②③ 은 같은 Flutter 코드 하나로 모든 화면(서비스 관리자 화면 포함)을 낸다.  '
                  '개발 편의 스택(E1)이면 ① Expo, ② Tauri, ③ Next.js 로 나뉘고 ⑥ 이 Hono 가 된다.',
        fontsize=10, color='#444')

fig.savefig(OUT, dpi=150, facecolor='white')
print('saved', OUT)
