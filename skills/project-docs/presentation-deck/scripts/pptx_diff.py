"""생성본과 사용자 수정본 PPTX 를 슬라이드·도형 단위로 비교한다.

python pptx_diff.py <생성본.pptx> <수정본.pptx>
사용자가 PPT 를 직접 고쳤을 때 바뀐 곳을 찾아 생성기에 되먹이는 데 쓴다(스킬 presentation-deck).
텍스트 상자 높이만 바뀐 것은 PowerPoint 가 저장할 때 자동 맞춤을 다시 계산한 것이라 무시한다.
"""
import sys, hashlib
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu

sys.stdout.reconfigure(encoding='utf-8')
A, B = Presentation(sys.argv[1]), Presentation(sys.argv[2])
mm = lambda v: round(Emu(v).mm, 1) if v is not None else None


def walk(shapes, pre=''):
    for sh in shapes:
        yield pre, sh
        if sh.shape_type == 6:
            yield from walk(sh.shapes, pre + '  ')


def desc(sl):
    out = []
    for pre, sh in walk(sl.shapes):
        t = sh.text_frame.text.replace('\n', ' / ') if sh.has_text_frame else ''
        sizes = sorted({r.font.size.pt for p in sh.text_frame.paragraphs for r in p.runs if r.font.size} ) if sh.has_text_frame else []
        img = hashlib.md5(sh.image.blob).hexdigest()[:8] if sh.shape_type == 13 else ''
        out.append((sh.name, str(sh.shape_type).split('.')[-1][:6], (mm(sh.left), mm(sh.top), mm(sh.width), mm(sh.height)), t, tuple(sizes), img))
    return out


print('장 수', len(A.slides), len(B.slides))
for i, (sa, sb) in enumerate(zip(A.slides, B.slides), 1):
    da, db = desc(sa), desc(sb)
    if da == db:
        continue
    print(f'=== 슬라이드 {i}')
    ka = {(x[0], x[1]): x for x in da}; kb = {(x[0], x[1]): x for x in db}
    for k in ka.keys() - kb.keys():
        print('  빠짐 ', ka[k][0], ka[k][3][:60])
    for k in kb.keys() - ka.keys():
        print('  추가 ', kb[k][0], kb[k][1], kb[k][2], kb[k][3][:80], kb[k][4])
    for k in ka.keys() & kb.keys():
        x, y = ka[k], kb[k]
        if x != y:
            ch = []
            if x[2] != y[2]: ch.append(f'위치/크기 {x[2]} -> {y[2]}')
            if x[3] != y[3]: ch.append(f'글 [{x[3][:60]}] -> [{y[3][:80]}]')
            if x[4] != y[4]: ch.append(f'글자 {x[4]} -> {y[4]}')
            if x[5] != y[5]: ch.append('그림 바뀜')
            print('  바뀜 ', x[0], ' | '.join(ch))
