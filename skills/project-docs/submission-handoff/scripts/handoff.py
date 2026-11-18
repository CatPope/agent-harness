# -*- coding: utf-8 -*-
"""제출 문서를 사람이 쓰도록 넘긴다. 에이전트는 최종본을 만들지 않는다.

  python handoff.py check <경로> [...]              쓰기 전 확인. 그 경로가 최종 제출본이면 멈춘다(종료 코드 2)
  python handoff.py give --form <양식> --dest <제출 폴더> --name <최종 파일명> [--draft <초안.md>]
                                                    양식을 바이트 그대로 복사해 `<제출 폴더>/작성용/` 에 둔다
  python handoff.py verify --dest <제출 폴더>       넘긴 양식 사본이 아직 양식 그대로인지, 초안이 바뀌었는지 본다

넘긴 것은 `<제출 폴더>/작성용/전달기록.jsonl` 에 한 줄씩 남는다. 이 기록과 해시로, 넘긴 뒤 에이전트가
손댄 파일이 없는지 사람이 확인할 수 있다. 이 도구는 아무 파일도 지우지 않는다.
"""
import argparse, datetime as dt, hashlib, json, os, re, shutil, sys

SUBMIT_EXTS = (".hwp", ".hwpx", ".docx", ".xlsx", ".pptx", ".pdf")
WORK = "작성용"
LEDGER = "전달기록.jsonl"


def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def is_submission(path, pattern):
    """최종 제출본으로 볼 파일인가. 작성용 폴더 안의 사본과 초안은 아니다."""
    parts = os.path.normpath(path).split(os.sep)
    if WORK in parts:
        return False
    name = os.path.basename(path)
    return name.lower().endswith(SUBMIT_EXTS) and bool(re.search(pattern, name))


def cmd_check(a):
    bad = [p for p in a.paths if is_submission(os.path.abspath(p), a.pattern)]
    for p in a.paths:
        state = "🔴 최종 제출본 — 쓰지 않는다. give 로 양식 사본과 초안을 넘긴다" if p in bad else "🟢 써도 된다(최종본 아님)"
        print("%s  %s" % (state, p))
    sys.exit(2 if bad else 0)


def cmd_give(a):
    form = os.path.abspath(a.form)
    assert os.path.isfile(form), "양식이 없다: " + form
    if os.path.splitext(a.name)[1].lower() != os.path.splitext(form)[1].lower():
        sys.exit("🔴 확장자가 양식과 다르다: %s ↔ %s. 최종본은 양식 확장자로 낸다" % (a.name, os.path.basename(form)))
    final = os.path.join(os.path.abspath(a.dest), a.name)
    if os.path.exists(final):
        print("ℹ 최종본이 이미 있다(사람이 쓴 판일 수 있다). 건드리지 않는다: " + final)
    work = os.path.join(os.path.abspath(a.dest), WORK)
    os.makedirs(work, exist_ok=True)
    copy = os.path.join(work, a.name)
    if os.path.exists(copy):
        sys.exit("🔴 작성용 사본이 이미 있다. 사람이 쓰는 중일 수 있어 덮지 않는다: " + copy)
    shutil.copyfile(form, copy)                       # 내용만 복사한다
    fs, cs = sha1(form), sha1(copy)
    assert fs == cs, "복사본 해시가 양식과 다르다"
    rec = {"time": dt.datetime.now().isoformat(timespec="seconds"), "form": form, "form_sha1": fs,
           "copy": copy, "copy_sha1": cs, "final_name": a.name}
    if a.draft:
        d = os.path.abspath(a.draft)
        assert os.path.isfile(d), "초안이 없다: " + d
        rec.update(draft=d, draft_sha1=sha1(d))
    with open(os.path.join(work, LEDGER), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("양식 사본  %s  (양식과 바이트 같음 %s…)" % (copy, fs[:10]))
    if a.draft:
        print("내용 초안  %s" % rec["draft"])
    print("기록       %s" % os.path.join(work, LEDGER))


def cmd_verify(a):
    work = os.path.join(os.path.abspath(a.dest), WORK)
    led = os.path.join(work, LEDGER)
    if not os.path.exists(led):
        sys.exit("전달 기록이 없다: " + led)
    for line in open(led, encoding="utf-8"):
        r = json.loads(line)
        c = r["copy"]
        if not os.path.exists(c):
            st = "옮겼거나 이름을 바꿨다(사람이 최종본으로 옮겼으면 정상)"
        elif sha1(c) == r["form_sha1"]:
            st = "아직 빈 양식 그대로"
        else:
            st = "양식에서 바뀌었다 — 사람이 쓴 것이어야 한다. 에이전트가 고쳤는지는 ai-trace-audit 로 본다"
        print("%s  %s  · %s" % (r["time"], os.path.basename(c), st))
        if r.get("draft"):
            d = r["draft"]
            ds = "없음" if not os.path.exists(d) else ("넘긴 그대로" if sha1(d) == r["draft_sha1"] else "넘긴 뒤 바뀌었다")
            print("    초안 %s · %s" % (os.path.basename(d), ds))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("check"); c.add_argument("paths", nargs="+")
    c.add_argument("--pattern", default=r".", help="최종본 파일 이름 정규식. 기본은 확장자만으로 판단")
    g = sp.add_parser("give")
    g.add_argument("--form", required=True); g.add_argument("--dest", required=True)
    g.add_argument("--name", required=True); g.add_argument("--draft")
    v = sp.add_parser("verify"); v.add_argument("--dest", required=True)
    a = ap.parse_args()
    {"check": cmd_check, "give": cmd_give, "verify": cmd_verify}[a.cmd](a)


if __name__ == "__main__":
    main()
