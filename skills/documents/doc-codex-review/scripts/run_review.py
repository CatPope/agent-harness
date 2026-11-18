# -*- coding: utf-8 -*-
"""Codex 에게 문서 검토를 맡긴다. 결과는 md 로 받는다.

사용: python run_review.py <문서> [<문서> ...] [--form <양식>] [--note "<참고>"] [--fix] [--out <폴더>]
  기본      읽기 전용. 지적과 고친 문장을 보고만 한다.
  --fix     Codex 가 문서를 직접 고친다. 먼저 <문서 폴더>/이전 판/ 에 백업하고, 끝나면 verify_fix.py 로 대조한다.
결과: <문서 폴더>/검토/<짧은 이름>_검토_<N>.md  (N 은 차례로 늘어난다)
모델: gpt-5.6-sol, 추론 medium. 바꾸려면 환경 변수 REVIEW_MODEL, REVIEW_EFFORT.
"""
import argparse
import glob
import hashlib
import os
import shutil
import subprocess
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = os.path.join(HERE, "..", "prompts")
META = os.path.join(HERE, "meta_dump.py")
VERIFY = os.path.join(HERE, "verify_fix.py")
FIXABLE = (".hwpx", ".docx", ".pptx", ".md", ".txt")


def short_name(path):
    # 제출물 이름 <학번>_<회사>_<이름>_<주차>_<종류>.<확장자> 에서 종류만 쓴다
    return os.path.splitext(os.path.basename(path))[0].split("_")[-1]


def next_path(folder, name):
    n = 1
    while os.path.exists(os.path.join(folder, "%s_검토_%d.md" % (name, n))):
        n += 1
    return os.path.join(folder, "%s_검토_%d.md" % (name, n))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def backup(path):
    """고치기 전에 이전 판/<짧은 이름>_<YYYYMMDD_HHMM>.<확장자> 로 복사한다. 같은 내용이 이미 있으면 그것을 쓴다."""
    d = os.path.join(os.path.dirname(path), "이전 판")
    os.makedirs(d, exist_ok=True)
    ext = os.path.splitext(path)[1]
    h = sha(path)
    for old in glob.glob(os.path.join(d, "*" + ext)):
        if sha(old) == h:
            return old
    dst = os.path.join(d, "%s_%s%s" % (short_name(path), datetime.now().strftime("%Y%m%d_%H%M"), ext))
    if os.path.exists(dst):
        sys.exit("백업 이름이 겹친다. 1분 뒤 다시: " + dst)
    shutil.copyfile(path, dst)
    return dst


def locked(path):
    lock = os.path.join(os.path.dirname(path), "~$" + os.path.basename(path)[2:])
    return os.path.exists(lock)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--form", default="없음")
    ap.add_argument("--note", default="없음")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    files = [os.path.abspath(f) for f in a.files]
    for f in files:
        if not os.path.isfile(f):
            sys.exit("없는 파일: " + f)
    folder = os.path.dirname(files[0])
    out_dir = a.out or os.path.join(folder, "검토")
    os.makedirs(out_dir, exist_ok=True)
    out = next_path(out_dir, short_name(files[0]))

    backups = {}
    if a.fix:
        for f in files:
            if locked(f):
                sys.exit("열려 있는 파일이다. 닫고 다시: " + f)
            if f.lower().endswith(FIXABLE):
                backups[f] = backup(f)
                print("백업:", backups[f])

    with open(os.path.join(PROMPTS, "review.md"), encoding="utf-8") as fp:
        prompt = fp.read()
    if a.fix:
        with open(os.path.join(PROMPTS, "fix.md"), encoding="utf-8") as fp:
            prompt += fp.read()
    prompt = (prompt.replace("{FILES}", ", ".join(files))
              .replace("{FORM}", os.path.abspath(a.form) if a.form != "없음" else "없음")
              .replace("{NOTE}", a.note)
              .replace("{META}", os.path.abspath(META)))

    codex = shutil.which("codex")
    if not codex:
        sys.exit("codex 를 찾지 못했다")
    cmd = [codex, "exec",
           "-m", os.environ.get("REVIEW_MODEL", "gpt-5.6-sol"),
           "-c", 'model_reasoning_effort="%s"' % os.environ.get("REVIEW_EFFORT", "medium"),
           "-s", "workspace-write" if a.fix else "read-only",
           # 문서 폴더는 대개 git 저장소도 신뢰 폴더도 아니다. 쓰기 범위는 -C 폴더로 묶인다.
           "--skip-git-repo-check", "-C", folder, "-o", out, "-"]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    print("%s 중: %s" % ("검토·수정" if a.fix else "검토", ", ".join(os.path.basename(f) for f in files)))
    r = subprocess.run(cmd, input=prompt.encode("utf-8"), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode != 0 or not os.path.exists(out):
        sys.stderr.write(r.stderr.decode("utf-8", "replace")[-3000:])
        sys.exit("codex 실패 (종료 코드 %d)" % r.returncode)
    with open(out, encoding="utf-8") as fp:
        body = fp.read()
    verdict = [l for l in body.splitlines() if l.strip().startswith("판정:")]
    print("결과:", out)
    print(verdict[-1].strip() if verdict else "판정 줄이 없다. 결과 파일을 직접 본다")

    code = 0
    for f, b in backups.items():
        if sha(f) == sha(b):
            print("바뀌지 않음:", os.path.basename(f))
            continue
        print("\n대조:", os.path.basename(f))
        code |= subprocess.run([sys.executable, VERIFY, b, f], env=env).returncode
    sys.exit(code)


if __name__ == "__main__":
    main()
