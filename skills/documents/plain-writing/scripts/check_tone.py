# -*- coding: utf-8 -*-
"""AI 티가 나는 문장 형식을 찾는다. 표준 라이브러리만 쓴다.

사용: python check_tone.py <파일 또는 폴더> [...]
읽는 형식: .md .txt .docx .pptx .hwpx
"""
import os
import re
import sys
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MAX_LEN = 60

RULES = [
    ("줄표 설명", re.compile(r"\S\s+[—–]\s+\S|\S\s+-\s+[가-힣A-Za-z(]")),
    ("화살표 연결", re.compile(r"→|->")),
    ("콜론 설명", re.compile(r"^[^:：]{1,20}\s?[:：]\s+\S")),
    ("대구 'A가 아니라 B'", re.compile(r"(이|가) 아니라 ")),
    ("상투어", re.compile(r"핵심은|결론적으로|즉,|중요합니다|할 수 있습니다")),
]
BOLD = re.compile(r"\*\*[^*]+\*\*")
TEXT_TAGS = re.compile(r"<(?:a:t|w:t|hp:t)(?:\s[^>]*)?>([^<]*)</(?:a:t|w:t|hp:t)>")
PARA_END = re.compile(r"</(?:a:p|w:p|hp:p)>")


def lines_from_zip(path, members):
    z = zipfile.ZipFile(path)
    out = []
    for name in sorted(n for n in z.namelist() if members(n)):
        xml = z.read(name).decode("utf-8", errors="replace")
        for chunk in PARA_END.split(xml):
            text = "".join(TEXT_TAGS.findall(chunk)).strip()
            if text:
                out.append((name.split("/")[-1], text))
    return out


def read_lines(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".md", ".txt"):
        with open(path, encoding="utf-8", errors="replace") as f:
            body = f.read()
        body = re.sub(r"```.*?```", "", body, flags=re.S)
        return [(str(i), l.strip()) for i, l in enumerate(body.splitlines(), 1) if l.strip()]
    if ext == ".docx":
        return lines_from_zip(path, lambda n: n == "word/document.xml")
    if ext == ".pptx":
        return lines_from_zip(path, lambda n: re.match(r"ppt/slides/slide\d+\.xml$", n))
    if ext == ".hwpx":
        return lines_from_zip(path, lambda n: n.startswith("Contents/section"))
    return []


def check(path):
    hits = 0
    for where, line in read_lines(path):
        plain = line.strip("|#>-* ").strip()
        found = [name for name, rx in RULES if rx.search(plain)]
        if len(BOLD.findall(line)) >= 2:
            found.append("굵은 글씨 과다")
        for sent in re.split(r"(?<=[.다요])\s+", plain):
            if len(sent) > MAX_LEN and "|" not in line:
                found.append("긴 문장(%d자)" % len(sent))
                break
        if found:
            hits += 1
            print("  [%s] %s\n      %s" % (where, " · ".join(found), plain[:110]))
    return hits


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    total = 0
    for arg in argv:
        paths = [arg]
        if os.path.isdir(arg):
            paths = [os.path.join(r, f) for r, _, fs in os.walk(arg) for f in fs
                     if os.path.splitext(f)[1].lower() in (".md", ".txt", ".docx", ".pptx", ".hwpx")]
        for p in paths:
            print(p)
            n = check(p)
            print("  → %d줄\n" % n)
            total += n
    print("합계 %d줄. 걸린 것을 사람이 읽고 판단한다." % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
