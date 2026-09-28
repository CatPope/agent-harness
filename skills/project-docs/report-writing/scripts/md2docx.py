"""보고서 md 를 docx 로 바꾼다. pandoc 이 없는 PC 용 (2026-09-26).

지원: # ~ #### 제목, 문단, 파이프 표, 글머리(- ), 체크 목록(- [ ]), 번호 목록(1. ), 코드 블록(```),
      인라인 **굵게**, `코드`, [글자](URL) 링크.
쓰는 법: python md2docx.py <입력.md> [출력.docx]   출력을 빼면 같은 이름의 .docx
글꼴은 맑은 고딕, A4, 표는 Table Grid + 머리행 음영. 보고서 규칙은 스킬 report-writing.
"""
import re, sys, os
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Mm, RGBColor

FONT = '맑은 고딕'
MONO = 'Consolas'   # D2Coding 은 이 PC 에 없어 명조로 대체됐다 (2026-09-26 실측)
TEXT_W = 170        # 본문 폭 mm (A4 210 - 좌우 여백 20 x 2)
INLINE = re.compile(r'(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))')


def set_font(run, name=FONT, size=None, bold=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts'); rpr.insert(0, rfonts)
    for k in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rfonts.set(qn(k), name)
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if color: run.font.color.rgb = RGBColor.from_string(color)


def add_link(par, text, url, size):
    part = par.part
    rid = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    h = OxmlElement('w:hyperlink'); h.set(qn('r:id'), rid)
    r = OxmlElement('w:r'); rpr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts')
    for k in ('w:ascii', 'w:hAnsi', 'w:eastAsia'):
        rf.set(qn(k), FONT)
    c = OxmlElement('w:color'); c.set(qn('w:val'), '0B5394')
    u = OxmlElement('w:u'); u.set(qn('w:val'), 'single')
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), str(int(size * 2)))
    for e in (rf, c, u, sz): rpr.append(e)
    r.append(rpr)
    t = OxmlElement('w:t'); t.text = text; t.set(qn('xml:space'), 'preserve'); r.append(t)
    h.append(r); par._p.append(h)


def add_inline(par, text, size=10.5, bold=False):
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith('**') and piece.endswith('**'):
            set_font(par.add_run(piece[2:-2]), size=size, bold=True)
        elif piece.startswith('`') and piece.endswith('`'):
            set_font(par.add_run(piece[1:-1]), name=MONO, size=size - 0.5, color='444444')
        elif piece.startswith('[') and '](' in piece:
            t, u = piece[1:].split('](', 1)
            add_link(par, t, u[:-1], size)
        else:
            set_font(par.add_run(piece), size=size, bold=bold)


def shade(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    s = OxmlElement('w:shd'); s.set(qn('w:val'), 'clear'); s.set(qn('w:color'), 'auto'); s.set(qn('w:fill'), fill)
    tcpr.append(s)


def spacing(par, before=0, after=4, line=1.25):
    pf = par.paragraph_format
    pf.space_before = Pt(before); pf.space_after = Pt(after); pf.line_spacing = line


def add_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r':?-{2,}:?', c) for c in r)]
    ncol = max(len(r) for r in cells)
    t = doc.add_table(rows=len(cells), cols=ncol)
    t.style = 'Table Grid'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    # 열 폭은 글자 수에 비례. 링크는 보이는 글자만 센다. 너무 좁은 열이 생기지 않게 최소값을 둔다.
    def vis(s):  # 한글·별 같은 넓은 글자는 2 로 센다
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s).replace('**', '').replace('`', '')
        return sum(1 if ord(ch) < 0x1100 else 3 if ch in '★☆½' else 2 for ch in s)   # 별은 한글보다 넓다
    def colw(j):
        vals = [vis(r[j]) if j < len(r) else 0 for r in cells]
        avg = sum(min(v, 90) for v in vals) / len(vals)
        return max(vals) + 2 if max(vals) <= 30 else max(avg, 24)   # 짧은 열(평점, ID, 후보명)은 가장 긴 값이 한 줄에 들도록
    w = [colw(j) for j in range(ncol)]
    widths = [Mm(TEXT_W * x / sum(w)) for x in w]
    # Word 가 자동 맞춤으로 폭을 되돌리지 않게 고정 배치 + 격자 폭을 같이 적는다
    tblpr = t._tbl.tblPr
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblpr.append(lay)
    for gc, wd in zip(t._tbl.tblGrid.findall(qn('w:gridCol')), widths):
        gc.set(qn('w:w'), str(int(wd.twips)))
    for i, r in enumerate(cells):
        for j in range(ncol):
            cell = t.cell(i, j)
            cell.width = widths[j]
            p = cell.paragraphs[0]; spacing(p, 1, 1, 1.15)
            add_inline(p, r[j] if j < len(r) else '', size=9.5, bold=(i == 0))
            if i == 0:
                shade(cell, 'EFEFEF'); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()


def convert(src, dst):
    lines = open(src, encoding='utf-8').read().split('\n')
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = Mm(20); sec.top_margin = sec.bottom_margin = Mm(20)
    st = doc.styles['Normal']; st.font.name = FONT; st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    sizes = {1: 20, 2: 15, 3: 12.5, 4: 11}
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('```'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            for code in lines[i + 1:j]:
                p = doc.add_paragraph(); spacing(p, 0, 0, 1.1)
                p.paragraph_format.left_indent = Mm(4)
                set_font(p.add_run(code), name=MONO, size=9, color='333333')
            doc.add_paragraph(); i = j + 1; continue
        if ln.startswith('|'):
            j = i
            while j < len(lines) and lines[j].startswith('|'):
                j += 1
            add_table(doc, lines[i:j]); i = j; continue
        m = re.match(r'^(#{1,4}) (.+)$', ln)
        if m:
            lv = len(m.group(1)); p = doc.add_paragraph()
            spacing(p, 14 if lv <= 2 else 8, 6 if lv <= 2 else 3, 1.1)
            add_inline(p, m.group(2), size=sizes[lv], bold=True)
            if lv == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1; continue
        m = re.match(r'^(\s*)- \[( |x)\] (.+)$', ln)
        if m:
            p = doc.add_paragraph(); spacing(p, 0, 2)
            p.paragraph_format.left_indent = Mm(5)
            add_inline(p, ('☑ ' if m.group(2) == 'x' else '☐ ') + m.group(3)); i += 1; continue
        m = re.match(r'^(\s*)- (.+)$', ln)
        if m:
            p = doc.add_paragraph(); spacing(p, 0, 2)
            p.paragraph_format.left_indent = Mm(5 + len(m.group(1)) * 2); p.paragraph_format.first_line_indent = Mm(-3.5)
            add_inline(p, '• ' + m.group(2)); i += 1; continue
        m = re.match(r'^(\s*)(\d+)\. (.+)$', ln)
        if m:
            p = doc.add_paragraph(); spacing(p, 0, 2)
            p.paragraph_format.left_indent = Mm(6); p.paragraph_format.first_line_indent = Mm(-4.5)
            add_inline(p, f'{m.group(2)}. ' + m.group(3)); i += 1; continue
        if ln.strip():
            p = doc.add_paragraph(); spacing(p)
            add_inline(p, ln.strip())
        i += 1
    doc.save(dst)
    print('saved', dst)


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '.docx'
    convert(src, dst)
