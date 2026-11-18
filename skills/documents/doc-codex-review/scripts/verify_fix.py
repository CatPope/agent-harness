# -*- coding: utf-8 -*-
"""고치기 전과 뒤의 문서를 대조한다. 수정 모드 뒤에 run_review.py 가 부른다.

사용: python verify_fix.py <백업> <고친 파일>
보는 것: zip 이 열리는지, 항목 목록이 같은지, 바뀐 XML 이 파싱되는지,
바뀐 문단 수, 영문·숫자 낱말이 달라진 문단(내용이 바뀌었을 수 있다).
문제가 있으면 종료 코드 1.
"""
import html
import os
import re
import sys
import zipfile
import xml.dom.minidom as md

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TAG = {".hwpx": ("Contents/section", "hp:t", "hp:p"),
       ".docx": ("word/document.xml", "w:t", "w:p"),
       ".pptx": ("ppt/slides/slide", "a:t", "a:p")}
TOK = re.compile(r"[A-Za-z_][A-Za-z_0-9.\-]*|\d+")
# 주장의 강도와 시제를 정하는 표지. 고친 뒤 개수가 바뀌면 "할 수 있다" 가 "했다" 로 올라간 것일 수 있다.
MODAL = re.compile(r"수 있|수 없|해야|하여야|어야|아야|ㄹ 것|을 것|할 것|것 같|보인다|보입니다|듯|겠|예정|않|못|없")


def paras(z, prefix, t, p):
    out = []
    for n in sorted(x for x in z.namelist() if x.startswith(prefix) and x.endswith(".xml")):
        xml = z.read(n).decode("utf-8", "replace")
        for chunk in re.split(r"</%s>" % p, xml):
            s = html.unescape("".join(re.findall(r"<%s(?:\s[^>]*)?>([^<]*)</%s>" % (t, t), chunk))).strip()
            if s:
                out.append(s)
    return out


def text_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return [l.rstrip("\n") for l in f]


def main(old, new):
    ext = os.path.splitext(new)[1].lower()
    bad = 0
    if ext in TAG:
        try:
            zo, zn = zipfile.ZipFile(old), zipfile.ZipFile(new)
        except zipfile.BadZipFile:
            print("🔴 고친 파일이 zip 으로 열리지 않는다")
            return 1
        if ext == ".hwpx":
            first = zn.infolist()[0]
            if first.filename != "mimetype" or first.compress_type != 0:
                print("🔴 mimetype 이 첫 항목 무압축이 아니다")
                bad += 1
        if sorted(zo.namelist()) != sorted(zn.namelist()):
            print("🔴 zip 항목 목록이 달라졌다")
            bad += 1
        for n in zn.namelist():
            if n in zo.namelist() and zo.read(n) != zn.read(n):
                print("바뀐 항목:", n)
                if n.endswith(".xml"):
                    try:
                        md.parseString(zn.read(n))
                    except Exception as e:
                        print("🔴 XML 파싱 실패:", n, e)
                        bad += 1
        a, b = paras(zo, *TAG[ext]), paras(zn, *TAG[ext])
    else:
        a, b = text_lines(old), text_lines(new)
    if len(a) != len(b):
        print("⚠️ 문단 수가 달라졌다: %d → %d" % (len(a), len(b)))
    changed = [(x, y) for x, y in zip(a, b) if x != y]
    print("바뀐 문단 %d개" % len(changed))
    for x, y in changed:
        flag = ""
        if TOK.findall(x) != TOK.findall(y):
            flag = "🔴 낱말 "
        elif sorted(MODAL.findall(x)) != sorted(MODAL.findall(y)):
            flag = "🔴 서법 "
        if flag:
            bad += 1
        print("  %s- %s\n  %s+ %s" % (flag, x[:160], flag, y[:160]))
    if bad:
        print("🔴 낱말: 영문·숫자 낱말이 달라졌다. 🔴 서법: '수 있다 · 해야 · 않다' 같은 표지가 달라졌다.")
        print("내용이나 주장의 강도가 바뀌었는지 사람이 원문과 견줘 본다.")
    else:
        print("이상 없음")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
