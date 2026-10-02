#!/usr/bin/env python3
"""OOXML(.docx .xlsx .pptx) 메타데이터를 검사하고 양식에 맞춰 고친다. 표준 라이브러리만 쓴다.

    python office_meta.py check FILE [FILE ...] [--template TPL]
    python office_meta.py fix FILE --template TPL -o OUT [--author NAME] [--last-modified-by NAME]

check  docProps/core.xml · app.xml 에 남은 생성 흔적을 찾는다.
       🔴 = 생성 라이브러리·AI 이름이 그대로 남음, 🟡 = 사람이 저장한 파일로 보기 어려운 값.
       흔적이 하나라도 있으면 종료 코드 1.
fix    양식(TPL)의 메타데이터를 따라 새 파일(OUT)을 쓴다. 원본은 건드리지 않는다.
       양식 값 자체에 흔적이 있으면(예: 작성자 OpenAI) 그 칸은 --author 로 받아야 진행한다.

XML 은 파서로 다시 쓰지 않고 해당 요소의 글자만 바꾼다. ElementTree 로 왕복하면
네임스페이스 접두어가 바뀌어 Office 가 파일을 거부할 수 있기 때문이다.
"""
import argparse
import datetime
import os
import re
import sys
import zipfile

CORE = "docProps/core.xml"
APP = "docProps/app.xml"

NS_DC = "http://purl.org/dc/elements/1.1/"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"

# 생성 라이브러리가 남기는 문구 (2026-10-02 실측: python-pptx 1.0.2, python-docx, openpyxl 3.1.5, XlsxWriter)
LIB_PAT = re.compile(r"python-pptx|python-docx|openpyxl|xlsxwriter|pptxgenjs|docx4j|apache poi|aspose|"
                     r"generated (using|by)", re.I)
# 작성자 칸에 들어가면 안 되는 이름 — 라이브러리 저자, AI 서비스
NAME_PAT = re.compile(r"^(steve canny|openai|chatgpt|gpt|claude|anthropic|codex|gemini|google ai|"
                      r"copilot|microsoft copilot|grok|xai|python-docx|python-pptx|openpyxl|pptxgenjs)$", re.I)
# 라이브러리 기본 틀에 박힌 만든 날짜
KNOWN_DATES = {"2013-01-27T09:14:16Z": "python-pptx 기본 틀", "2013-12-23T23:15:00Z": "python-docx 기본 틀"}

CORE_TAGS = ["dc:title", "dc:subject", "dc:creator", "cp:keywords", "dc:description",
             "cp:lastModifiedBy", "cp:revision", "dcterms:created", "dcterms:modified", "cp:category"]
APP_TAGS = ["Application", "AppVersion", "Company", "Template", "PresentationFormat", "TotalTime"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def unesc(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _pat(tag):
    t = re.escape(tag)
    return re.compile(r"<{0}(\s[^>]*?)?(/>|>(.*?)</{0}>)".format(t), re.S)


def get(xml, tag):
    m = _pat(tag).search(xml)
    if not m:
        return None
    return unesc(m.group(3) or "")


def put(xml, tag, value, root_close):
    """요소가 있으면 글자만 바꾸고, 없으면 루트 닫는 태그 앞에 넣는다(코어·확장 속성은 xs:all 이라 순서 무관)."""
    v = esc(value)
    m = _pat(tag).search(xml)
    if m:
        attrs = m.group(1) or ""
        return xml[:m.start()] + "<{0}{1}>{2}</{0}>".format(tag, attrs, v) + xml[m.end():]
    decl = ""
    if tag.startswith("dc:"):
        decl = ' xmlns:dc="{}"'.format(NS_DC)
    elif tag.startswith("dcterms:"):
        decl = ' xmlns:dcterms="{}" xmlns:xsi="{}" xsi:type="dcterms:W3CDTF"'.format(NS_DCTERMS, NS_XSI)
    i = xml.rfind(root_close)
    if i < 0:
        raise ValueError("루트 닫는 태그를 찾지 못했습니다: " + root_close)
    return xml[:i] + "<{0}{1}>{2}</{0}>".format(tag, decl, v) + xml[i:]


def read_parts(path):
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        core = z.read(CORE).decode("utf-8") if CORE in names else None
        app = z.read(APP).decode("utf-8") if APP in names else None
        pres = z.read("ppt/presentation.xml").decode("utf-8") if "ppt/presentation.xml" in names else None
    return core, app, pres


def slide_ratio(pres):
    if not pres:
        return None
    m = re.search(r'<p:sldSz[^>]*\bcx="(\d+)"[^>]*\bcy="(\d+)"', pres)
    return int(m.group(1)) / int(m.group(2)) if m else None


def fmt_ratio(text):
    if not text:
        return None
    if "16:9" in text or "와이드" in text or "Widescreen" in text:
        return 16 / 9
    if "16:10" in text:
        return 16 / 10
    if "4:3" in text:
        return 4 / 3
    return None


def fields(path):
    core, app, pres = read_parts(path)
    f = {}
    if core:
        for t in CORE_TAGS:
            f[t] = get(core, t)
    if app:
        for t in APP_TAGS:
            f[t] = get(app, t)
    return f, core is not None, app is not None, slide_ratio(pres)


def audit(path, template=None):
    f, has_core, has_app, ratio = fields(path)
    out = []
    if not has_core:
        out.append(("🟡", "docProps/core.xml 이 없다 — Office 로 저장한 파일에는 보통 있다"))
    if not has_app:
        out.append(("🟡", "docProps/app.xml 이 없다"))
    for k, v in f.items():
        if v and LIB_PAT.search(v):
            out.append(("🔴", "{} = {!r} — 생성 라이브러리 문구".format(k, v)))
    for k in ("dc:creator", "cp:lastModifiedBy"):
        v = (f.get(k) or "").strip()
        if v and NAME_PAT.match(v):
            out.append(("🔴", "{} = {!r} — 라이브러리 저자·AI 이름".format(k, v)))
    created = f.get("dcterms:created") or ""
    if created in KNOWN_DATES:
        out.append(("🔴", "dcterms:created = {} — {}".format(created, KNOWN_DATES[created])))
    if has_core and not (f.get("dc:creator") or "").strip() and not (f.get("cp:lastModifiedBy") or "").strip():
        out.append(("🟡", "작성자·마지막 수정자가 둘 다 비었다"))
    modified = f.get("dcterms:modified") or ""
    if created and modified and modified < created:
        out.append(("🟡", "수정 날짜({})가 만든 날짜({})보다 앞선다".format(modified, created)))
    pf = f.get("PresentationFormat")
    fr = fmt_ratio(pf)
    if ratio and fr and abs(ratio - fr) > 0.02:
        out.append(("🟡", "PresentationFormat = {!r} 인데 실제 슬라이드 비율은 {:.2f}".format(pf, ratio)))
    app_name = f.get("Application") or ""
    if template:
        tf, _, _, tratio = fields(template)
        for k in ("Application", "AppVersion"):
            if (tf.get(k) or "") and (f.get(k) or "") != (tf.get(k) or ""):
                out.append(("🟡", "{} = {!r} — 양식은 {!r}".format(k, f.get(k), tf.get(k))))
        if ratio and tratio and abs(ratio - tratio) > 0.02:
            out.append(("🟡", "슬라이드 비율 {:.2f} — 양식은 {:.2f}".format(ratio, tratio)))
    elif "Macintosh" in app_name:
        out.append(("🟡", "Application = {!r} — 작업한 환경과 맞는지 확인 (python-pptx·docx 기본값)".format(app_name)))
    return f, out


def cmd_check(args):
    bad = False
    for p in args.files:
        if not p.lower().endswith((".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm")):
            print("== {}\n  건너뜀 — OOXML(.docx .xlsx .pptx) 만 본다".format(p))
            continue
        f, out = audit(p, args.template)
        print("== " + p)
        for k in ("dc:creator", "cp:lastModifiedBy", "dcterms:created", "dcterms:modified",
                  "dc:description", "Application", "PresentationFormat"):
            if k in f:
                print("  {:<18} {}".format(k, f[k] if f[k] is not None else "(없음)"))
        if out:
            bad = True
            for lv, msg in out:
                print("  {} {}".format(lv, msg))
        else:
            print("  🟢 흔적 없음")
    return 1 if bad else 0


def cmd_fix(args):
    src, tpl, dst = args.file, args.template, args.output
    if os.path.abspath(src) == os.path.abspath(dst):
        sys.exit("원본에 덮어쓰지 않습니다. -o 로 다른 경로를 주십시오.")
    tf, _, _, _ = fields(tpl)
    core, app, _ = read_parts(src)
    if core is None:
        sys.exit("docProps/core.xml 이 없는 파일은 아직 다루지 않습니다: " + src)

    def clean(v):
        return v if v and not NAME_PAT.match(v.strip()) and not LIB_PAT.search(v) else None

    author = args.author or clean(tf.get("dc:creator"))
    if not author:
        sys.exit("양식의 작성자({!r})를 쓸 수 없습니다. --author 로 작성자를 주십시오.".format(tf.get("dc:creator")))
    last = args.last_modified_by or args.author or clean(tf.get("cp:lastModifiedBy")) or author
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    created = tf.get("dcterms:created") or now
    if created in KNOWN_DATES or created > now:
        created = now
    try:
        rev = str(int(tf.get("cp:revision") or "1") + 1)
    except ValueError:
        rev = "2"

    root_c = "</cp:coreProperties>"
    new_core = core
    for tag in ("dc:title", "dc:subject", "cp:keywords", "dc:description", "cp:category"):
        v = tf.get(tag)
        v = "" if v is None or LIB_PAT.search(v) else v
        if get(new_core, tag) is not None or v:
            new_core = put(new_core, tag, v, root_c)
    new_core = put(new_core, "dc:creator", author, root_c)
    new_core = put(new_core, "cp:lastModifiedBy", last, root_c)
    new_core = put(new_core, "cp:revision", rev, root_c)
    new_core = put(new_core, "dcterms:created", created, root_c)
    new_core = put(new_core, "dcterms:modified", now, root_c)

    new_app = app
    if app is not None:
        for tag in ("Application", "AppVersion", "Company", "Template", "PresentationFormat"):
            v = tf.get(tag)
            if v is not None and not LIB_PAT.search(v):
                new_app = put(new_app, tag, v, "</Properties>")

    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == CORE:
                data = new_core.encode("utf-8")
            elif info.filename == APP and new_app is not None:
                data = new_app.encode("utf-8")
            zout.writestr(info, data, compress_type=info.compress_type)
    print("썼습니다: " + dst)
    print("다시 검사합니다.")
    args.files = [dst]
    return cmd_check(args)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="메타데이터 흔적 검사")
    c.add_argument("files", nargs="+")
    c.add_argument("--template", help="비교할 양식 파일")
    f = sub.add_parser("fix", help="양식 메타데이터를 따라 새 파일로 쓴다")
    f.add_argument("file")
    f.add_argument("--template", required=True)
    f.add_argument("-o", "--output", required=True)
    f.add_argument("--author", help="작성자. 양식 작성자가 AI 이름이면 필수")
    f.add_argument("--last-modified-by", help="마지막 수정자. 없으면 --author 또는 양식 값")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return cmd_check(a) if a.cmd == "check" else cmd_fix(a)


if __name__ == "__main__":
    sys.exit(main())
