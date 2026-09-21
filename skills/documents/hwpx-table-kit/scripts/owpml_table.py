# -*- coding: utf-8 -*-
"""Generate OWPML tables and splice them into an existing HWPX section.

Design decisions learned the hard way (see SKILL.md):
  * Do NOT regenerate the whole document. Keep the original <hp:secPr>
    (page size / margins) and only replace the body, so page design is kept.
  * Table-cell paragraphs must be LEFT aligned. The document default is
    often JUSTIFY, which stretches the spaces inside narrow cells.
  * Bold = an empty <hh:bold/> element inserted right after <hh:offset/>.
  * Every new borderFill / charPr / paraPr requires its itemCnt bumped.
  * New style ids must be max(existing)+1 -- never hardcoded.
"""
import re


# ---------------------------------------------------------------- helpers
def xesc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _max_id(xml, tag):
    ids = [int(m) for m in re.findall(r'<hh:%s id="(\d+)"' % tag, xml)]
    return max(ids) if ids else -1


def _bump_itemcnt(xml, plural, delta):
    m = re.search(r'<hh:%s itemCnt="(\d+)"' % plural, xml)
    n = int(m.group(1))
    return xml.replace('<hh:%s itemCnt="%d"' % (plural, n),
                       '<hh:%s itemCnt="%d"' % (plural, n + delta), 1)


# ---------------------------------------------------------------- styles
def add_styles(header_xml, opts):
    """Append the border/char/para styles a table needs.

    Returns (new_header_xml, ids) where ids has keys:
      bf_body, bf_head, cp_bold, cp_head, para_left
    """
    h = header_xml
    border = opts.get("border_color", "#000000")
    bw = opts.get("border_width", "0.12 mm")
    head_fill = opts.get("header_fill", "#F2F2F2")

    # --- borderFills ---
    bf_body = _max_id(h, "borderFill") + 1
    bf_head = bf_body + 1

    def _bf(bid, fill):
        parts = [
            '<hh:borderFill id="%d" threeD="0" shadow="0" centerLine="NONE" '
            'breakCellSeparateLine="0">' % bid,
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>',
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>',
            '<hh:leftBorder type="SOLID" width="%s" color="%s"/>' % (bw, border),
            '<hh:rightBorder type="SOLID" width="%s" color="%s"/>' % (bw, border),
            '<hh:topBorder type="SOLID" width="%s" color="%s"/>' % (bw, border),
            '<hh:bottomBorder type="SOLID" width="%s" color="%s"/>' % (bw, border),
            '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>',
        ]
        if fill:
            parts.append(
                '<hc:fillBrush><hc:winBrush faceColor="%s" hatchColor="%s" '
                'alpha="0"/></hc:fillBrush>' % (fill, fill))
        parts.append('</hh:borderFill>')
        return "".join(parts)

    h = _bump_itemcnt(h, "borderFills", 2)
    h = h.replace('</hh:borderFills>', _bf(bf_body, None) + _bf(bf_head, head_fill) + '</hh:borderFills>')

    # --- charProperties : derive bold variants from the first charPr ---
    base_cp = re.search(r'<hh:charPr id="\d+".*?</hh:charPr>', h, re.S).group(0)
    base_h = re.search(r'height="(\d+)"', base_cp).group(1)
    cp_bold = _max_id(h, "charPr") + 1
    cp_head = cp_bold + 1
    head_height = opts.get("heading_height", 1300)

    def _cp(new_id, height, bold):
        s = base_cp
        s = re.sub(r'id="\d+"', 'id="%d"' % new_id, s, count=1)
        s = re.sub(r'height="\d+"', 'height="%d"' % height, s, count=1)
        if bold and "<hh:bold/>" not in s:
            s = re.sub(r'(<hh:offset\b[^>]*/>)', r'\1<hh:bold/>', s, count=1)
        return s

    h = _bump_itemcnt(h, "charProperties", 2)
    h = h.replace('</hh:charProperties>',
                  _cp(cp_bold, int(base_h), True) + _cp(cp_head, head_height, True) + '</hh:charProperties>')

    # --- paraProperties : LEFT-aligned variant of the first paraPr ---
    base_pp = re.search(r'<hh:paraPr id="\d+".*?</hh:paraPr>', h, re.S).group(0)
    para_left = _max_id(h, "paraPr") + 1
    pleft = re.sub(r'id="\d+"', 'id="%d"' % para_left, base_pp, count=1)
    pleft = pleft.replace('horizontal="JUSTIFY"', 'horizontal="LEFT"', 1)
    h = _bump_itemcnt(h, "paraProperties", 1)
    h = h.replace('</hh:paraProperties>', pleft + '</hh:paraProperties>')

    return h, {"bf_body": bf_body, "bf_head": bf_head,
               "cp_bold": cp_bold, "cp_head": cp_head, "para_left": para_left}


# ---------------------------------------------------------------- table xml
CP_NORMAL = 0  # first charPr id is assumed 0 for plain body text


def _cell(text, col_w, is_header, bold, col, row, ids, row_h):
    charref = ids["cp_bold"] if (is_header or bold) else CP_NORMAL
    bfill = ids["bf_head"] if is_header else ids["bf_body"]
    para = ('<hp:p paraPrIDRef="%d" styleIDRef="0"><hp:run charPrIDRef="%d">'
            '<hp:t>%s</hp:t></hp:run></hp:p>' % (ids["para_left"], charref, xesc(text)))
    return (
        '<hp:tc name="" header="%d" hasMargin="0" protect="0" editable="1" dirty="0" borderFillIDRef="%d">'
        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
        'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        '%s</hp:subList>'
        '<hp:cellAddr colAddr="%d" rowAddr="%d"/>'
        '<hp:cellSpan colSpan="1" rowSpan="1"/>'
        '<hp:cellSz width="%d" height="%d"/>'
        '<hp:cellMargin left="510" right="510" top="141" bottom="141"/>'
        '</hp:tc>'
    ) % (1 if is_header else 0, bfill, para, col, row, col_w, row_h)


def build_table(table, tid, ids, total_w, row_h=2800):
    header = table["header"]
    rows = table.get("rows", [])
    ncol = len(header)
    widths = table.get("widths")
    if not widths:
        base = total_w // ncol
        widths = [base] * (ncol - 1) + [total_w - base * (ncol - 1)]
    bold_cols = set(table.get("boldCols", []))
    all_rows = [header] + rows
    nrow = len(all_rows)
    trs = []
    for r, row in enumerate(all_rows):
        is_header = (r == 0)
        cells = [
            _cell(str(v), widths[c], is_header, (not is_header and c in bold_cols), c, r, ids, row_h)
            for c, v in enumerate(row)
        ]
        trs.append('<hp:tr>' + ''.join(cells) + '</hp:tr>')
    tbl = (
        '<hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
        'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
        'rowCnt="%d" colCnt="%d" cellSpacing="0" borderFillIDRef="%d" noAdjust="0">'
        '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" '
        'vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="510" right="510" top="141" bottom="141"/>'
        '%s</hp:tbl>'
    ) % (tid, nrow, ncol, ids["bf_body"], total_w, row_h * nrow, ''.join(trs))
    return ('<hp:p paraPrIDRef="%d" styleIDRef="0"><hp:run charPrIDRef="0">%s<hp:t/></hp:run></hp:p>'
            % (ids["para_left"], tbl))


def _para(text, cpref, para_id):
    if text == "":
        return '<hp:p paraPrIDRef="%d" styleIDRef="0"><hp:run charPrIDRef="0"/></hp:p>' % para_id
    return ('<hp:p paraPrIDRef="%d" styleIDRef="0"><hp:run charPrIDRef="%d"><hp:t>%s</hp:t></hp:run></hp:p>'
            % (para_id, cpref, xesc(text)))


def _total_width(secpr):
    """Derive usable text width = page width - left/right margins (fallback 42520)."""
    try:
        w = int(re.search(r'<hp:pagePr[^>]*\bwidth="(\d+)"', secpr).group(1))
        mm = re.search(r'<hp:margin[^>]*\bleft="(\d+)"[^>]*\bright="(\d+)"', secpr)
        l, r = int(mm.group(1)), int(mm.group(2))
        return w - l - r
    except Exception:
        return 42520


def rebuild_section(section_xml, tables, ids):
    """Keep <hs:sec> + <hp:secPr>/<colPr>, then emit heading+table blocks."""
    x = section_xml
    decl_end = x.index("?>") + 2 if x.lstrip().startswith("<?xml") else 0
    xmldecl = x[:decl_end]
    si = x.index("<hs:sec")
    sec_open = xmldecl + x[si:x.index(">", si) + 1]
    secpr = re.search(r'<hp:secPr\b.*?</hp:secPr>', x, re.S).group(0)
    colm = re.search(r'<hp:ctrl><hp:colPr\b.*?</hp:ctrl>', x, re.S)
    colctrl = colm.group(0) if colm else ""
    total_w = _total_width(secpr)

    body = ['<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            '<hp:run charPrIDRef="0">' + secpr + colctrl + '</hp:run></hp:p>']
    tid = 2001
    for t in tables:
        if t.get("heading"):
            body.append(_para(t["heading"], ids["cp_head"], ids["para_left"]))
            body.append(_para("", 0, ids["para_left"]))
        body.append(build_table(t, tid, ids, total_w))
        tid += 1
        body.append(_para("", 0, ids["para_left"]))
        body.append(_para("", 0, ids["para_left"]))
    return sec_open + ''.join(body) + '</hs:sec>'


def strip_image_manifest(text):
    """Remove BinData image references from content.hpf / manifests."""
    t = re.sub(r'<[^>]*BinData/[^"]+\.(?:bmp|png|jpg|jpeg|gif|wmf)[^>]*/>', '', text, flags=re.I)
    return t
