# -*- coding: utf-8 -*-
"""문서 파일의 메타데이터와 만든 도구의 흔적을 보여 준다. 읽기만 한다.

사용: python meta_dump.py <파일> [...]
읽는 형식: .hwpx .hwp .docx .pptx .xlsx .pdf
.hwp 는 olefile 이 있으면 요약 정보까지 읽는다. 없으면 건너뛴다.
"""
import os
import re
import sys
import zipfile
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def zip_times(z):
    """zip 항목 시각. 한 파일 안에서 시각이 섞여 있으면 다른 도구가 끼어든 흔적이다."""
    groups = {}
    for i in z.infolist():
        groups.setdefault("%04d-%02d-%02d %02d:%02d" % i.date_time[:5], []).append(i.filename)
    print("  zip 항목 시각:")
    for t, names in sorted(groups.items()):
        print("    %s  %d개  %s" % (t, len(names), ", ".join(names[:4]) + (" …" if len(names) > 4 else "")))


def body_text(z, prefix, tag):
    xml = "".join(z.read(n).decode("utf-8", "replace") for n in sorted(z.namelist()) if n.startswith(prefix))
    return re.findall(r"<%s(?:\s[^>]*)?>([^<]*)</%s>" % (tag, tag), xml)


def hwpx(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    if "version.xml" in names:
        v = z.read("version.xml").decode("utf-8", "replace")
        app = re.search(r'application="([^"]*)"', v)
        ver = re.search(r'appVersion="([^"]*)"', v)
        print("  만든 프로그램: %s %s" % (app and app.group(1), ver and ver.group(1)))
    hpf = z.read("Contents/content.hpf").decode("utf-8", "replace") if "Contents/content.hpf" in names else ""
    for k in ("title",):
        m = re.search(r"<opf:%s>([^<]*)</opf:%s>" % (k, k), hpf)
        print("  %s: %s" % (k, m and m.group(1)))
    for k, v in re.findall(r'<opf:meta name="([^"]+)"[^>]*?(?:/>|>([^<]*)</opf:meta>)', hpf):
        print("  %s: %s" % (k, v))
    zip_times(z)
    texts = body_text(z, "Contents/section", "hp:t")
    body = "".join(texts)
    if "Preview/PrvText.txt" in names:
        prv = z.read("Preview/PrvText.txt").decode("utf-8", "replace")
        lines = [l.strip("<> \r") for l in prv.splitlines() if l.strip("<> \r")]
        miss = [l for l in lines if l.replace(" ", "") not in body.replace(" ", "")]
        print("  미리보기 글자: %d자, 본문에 없는 줄 %d개" % (len(prv), len(miss)))
        for l in miss[:5]:
            print("    본문에 없음: %s" % l[:80])
    print("  linesegarray 없는 문단 수: %d / 문단 %d" % (
        sum(1 for n in names if n.startswith("Contents/section")
            for p in re.findall(r"<hp:p\b(?:(?!<hp:p\b).)*?</hp:p>", z.read(n).decode("utf-8", "replace"), re.S)
            if "linesegarray" not in p),
        sum(z.read(n).decode("utf-8", "replace").count("<hp:p ") for n in names if n.startswith("Contents/section"))))


def ooxml(path):
    z = zipfile.ZipFile(path)
    for part in ("docProps/core.xml", "docProps/app.xml"):
        if part in z.namelist():
            xml = z.read(part).decode("utf-8", "replace")
            for k, v in re.findall(r"<(?:\w+:)?(\w+)(?:\s[^>]*)?>([^<]+)</", xml):
                print("  %s: %s" % (k, v))
    zip_times(z)


def hwp(path):
    try:
        import olefile
    except ImportError:
        print("  olefile 이 없어 요약 정보를 건너뛴다")
        return
    ole = olefile.OleFileIO(path)
    # 한글은 표준 SummaryInformation 대신 HwpSummaryInformation 에 적는다. 번호는 표준과 같다.
    names = {2: "title", 3: "subject", 4: "author", 5: "keywords", 6: "comments", 8: "last_saved_by",
             9: "revision", 12: "create_time", 13: "last_saved_time", 20: "date"}
    for stream in ("\x05HwpSummaryInformation", "\x05SummaryInformation"):
        if ole.exists(stream):
            props = ole.getproperties(stream, convert_time=True)
            for pid, k in names.items():
                if pid in props:
                    v = props[pid]
                    if isinstance(v, str):
                        # 한글이 적은 문자열 길이를 olefile 이 넘겨 읽어 다음 값까지 붙는다. 앞부분만 쓴다.
                        v = re.split(r"\x00| {3,}", v)[0].strip()
                    print("  %s: %s" % (k, v))
            break
    print("  스트림:", ", ".join("/".join(e) for e in ole.listdir() if e[0] in ("PrvText", "PrvImage", "DocInfo")))


def pdf(path):
    data = open(path, "rb").read()
    for k in (b"Producer", b"Creator", b"Author", b"Title", b"CreationDate", b"ModDate"):
        m = re.search(rb"/" + k + rb"\s*\(([^)]*)\)", data)
        print("  %s: %s" % (k.decode(), m and m.group(1).decode("latin-1", "replace")))


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    for p in argv:
        st = os.stat(p)
        print(p)
        print("  파일 수정 시각: %s" % datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"))
        ext = os.path.splitext(p)[1].lower()
        {".hwpx": hwpx, ".docx": ooxml, ".pptx": ooxml, ".xlsx": ooxml, ".hwp": hwp, ".pdf": pdf}.get(
            ext, lambda _: print("  읽지 않는 형식"))(p)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
