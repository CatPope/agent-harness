"""보고서 md 를 docx 로 바꾼다. pandoc 이 없는 PC 용 (2026-09-26).

지원: # ~ #### 제목, 문단, 파이프 표, 글머리(- ), 체크 목록(- [ ]), 번호 목록(1. ), 코드 블록(```),
      인라인 **굵게**, `코드`, [글자](URL) 링크, 그림 ![설명](md 기준 상대경로)(2026-10-30),
      글머리 다음 줄을 들여 쓴 이어지는 줄(앞 글머리에 붙인다).
쓰는 법: python md2docx.py <입력.md> [출력.docx] [--gdocs]   출력을 빼면 같은 이름의 .docx
      --gdocs: 구글독스에 올릴 판. 머리 메타줄(날짜 · 작성자 · 버전 · 종류)을 뺀다(report-format §7).
      --compact: 한 장 요약. 제목 크기와 간격, 그림 폭을 줄인다.
      "## 목차" 아래 글머리 목록은 Word 목차 필드가 된다. ## 이하 제목은 Heading 스타일이다.
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


def add_toc(doc, items):
    """## 목차 아래 글머리 목록을 Word 목차 필드로 만든다. 목록 글이 필드의 표시값이 된다.
    구글독스로 변환하면 목차 요소가 되고, 문서에서 목차 새로고침을 한 번 누르면 제목 링크가 걸린다."""
    def fld(run, kind):
        el = OxmlElement('w:fldChar'); el.set(qn('w:fldCharType'), kind); run._r.append(el)
    for k, (indent, text) in enumerate(items):
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)   # md 목차의 내부 링크는 글만 남긴다
        p = doc.add_paragraph(); spacing(p, 0, 1)
        p.paragraph_format.left_indent = Mm(4 + (5 if indent else 0))
        if k == 0:
            r = p.add_run(); fld(r, 'begin')
            ins = OxmlElement('w:instrText'); ins.set(qn('xml:space'), 'preserve'); ins.text = ' TOC \\o "1-2" \\h \\z \\u '
            r._r.append(ins); fld(r, 'separate')
        set_font(p.add_run(text), size=10.5)
        if k == len(items) - 1:
            fld(p.add_run(), 'end')


META = re.compile(r'^\d{4}-\d{2}-\d{2} · .+ · v\d+\.\d+\.\d+')
IMG = re.compile(r'^!\[[^\]]*\]\(([^)]+)\)$')
CONT = re.compile(r'^\s+(?!- |\d+\. )\S')


def convert(src, dst, gdocs=False, compact=False):
    lines = open(src, encoding='utf-8').read().split('\n')
    base = os.path.dirname(os.path.abspath(src))
    last = None   # 바로 앞 글머리 문단. 들여 쓴 이어지는 줄을 여기에 붙인다
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = Mm(20); sec.top_margin = sec.bottom_margin = Mm(20)
    st = doc.styles['Normal']; st.font.name = FONT; st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    sizes = {1: 24, 2: 18, 3: 12.5, 4: 11} if gdocs else {1: 20, 2: 15, 3: 12.5, 4: 11}   # 구글독스 판은 사용자가 고친 크기(2026-10-30)
    if compact:   # 한 장 요약. 제목을 줄여 한 쪽에 들게 한다
        sizes = {1: 18, 2: 13, 3: 11.5, 4: 11}
    img_w = Mm(118) if compact else Mm(TEXT_W - 10)
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
        if gdocs and META.match(ln):
            i += 1; continue
        m = IMG.match(ln.strip())
        if m:
            p = doc.add_paragraph(); spacing(p, 4, 2); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(os.path.join(base, m.group(1)), width=img_w)
            last = None; i += 1; continue
        if last is not None and CONT.match(ln):   # 글머리 아래 들여 쓴 줄은 한 줄씩 들여 쓴 문단으로 둔다(사용자가 구글독스에서 이렇게 나눴다, 2026-10-30)
            p = doc.add_paragraph(); spacing(p, 0, 2); p.paragraph_format.left_indent = Mm(18)
            add_inline(p, ln.strip()); i += 1; continue
        last = None
        if ln.startswith('|'):
            j = i
            while j < len(lines) and lines[j].startswith('|'):
                j += 1
            add_table(doc, lines[i:j]); i = j; continue
        m = re.match(r'^(#{1,4}) (.+)$', ln)
        if m:
            lv = len(m.group(1)); title = m.group(2).strip()
            if title == '목차':   # 목차 제목은 목차에 다시 나오지 않게 보통 문단으로 둔다
                p = doc.add_paragraph(); spacing(p, 14, 6, 1.1)
                add_inline(p, title, size=sizes[lv], bold=True)
                j = i + 1; items = []
                while j < len(lines) and (not lines[j].strip() or re.match(r'^\s*- ', lines[j])):
                    if lines[j].strip():
                        items.append((len(lines[j]) - len(lines[j].lstrip()), lines[j].strip()[2:]))
                    j += 1
                add_toc(doc, items); i = j; continue
            # 구글독스가 제목으로 알아보고 목차·개요에 넣도록 ## 이하는 제목 스타일을 쓴다. 맨 위 # 은 보통 문단
            p = doc.add_paragraph(style=f'Heading {lv - 1}') if lv >= 2 else doc.add_paragraph()
            spacing(p, (6 if compact else 14) if lv <= 2 else (3 if compact else 8), (2 if compact else 6) if lv <= 2 else 3, 1.1)
            add_inline(p, title, size=sizes[lv], bold=True)
            for r in p.runs:
                r.font.color.rgb = RGBColor(0, 0, 0); r.italic = False
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
            add_inline(p, '• ' + m.group(2).rstrip()); last = p; i += 1; continue
        m = re.match(r'^(\s*)(\d+)\. (.+)$', ln)
        if m:
            p = doc.add_paragraph(); spacing(p, 0, 2)
            p.paragraph_format.left_indent = Mm(6); p.paragraph_format.first_line_indent = Mm(-4.5)
            add_inline(p, f'{m.group(2)}. ' + m.group(3)); i += 1; continue
        if ln.strip():
            p = doc.add_paragraph(); spacing(p)
            add_inline(p, ln.strip())
        i += 1
    if compact:   # 한 쪽에 들도록 여백과 줄 간격을 줄인다. 구글독스 변환 뒤 쪽 수는 PDF 로 내려받아 센다
        sec.top_margin = sec.bottom_margin = Mm(15); sec.left_margin = sec.right_margin = Mm(18)
        for p in list(doc.paragraphs):   # 표 뒤에 넣은 빈 문단을 지운다. 그림 문단은 글이 없어도 남긴다
            if not p.text.strip() and not p._p.xpath('.//w:drawing'):
                p._p.getparent().remove(p._p)
        for p in doc.paragraphs:
            p.paragraph_format.line_spacing = 1.0
            if p.paragraph_format.space_after and p.paragraph_format.space_after > Pt(2):
                p.paragraph_format.space_after = Pt(2)
        for t in doc.tables:
            for row in t.rows:
                for c in row.cells:
                    for p in c.paragraphs:
                        p.paragraph_format.line_spacing = 1.0
    doc.save(dst)
    print('saved', dst)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src = args[0]
    dst = args[1] if len(args) > 1 else os.path.splitext(src)[0] + '.docx'
    convert(src, dst, gdocs='--gdocs' in sys.argv, compact='--compact' in sys.argv)
