"""Codex 계정 한도 조회 — `codex app-server` 에 initialize → initialized → account/rateLimits/read.

모델 요청이 아니라 한도를 쓰지 않는다. 결제 상태는 rateLimits.planType 으로 본다
(~/.codex/auth.json 토큰 안의 구독 만료일은 갱신되지 않은 값일 수 있다).

python codex_ratelimits.py              # 전체 JSON (초기화권 목록 포함)
python codex_ratelimits.py --summary    # 한 줄 요약 + 종료코드
  종료코드 0 = 결제 플랜(Plus 이상)·사용 가능 · 2 = 5시간 창이 기준 이상이거나 한도 도달
          3 = 응답 없음 · 4 = 결제 플랜 아님

2026-10-21 신설(한 개인 프로젝트 세션). 형제 스크립트와 같이 stdout 을 UTF-8 로 올린다.
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import threading
import time

PAID = {"plus", "pro", "team", "business", "enterprise", "edu"}
KST = dt.timezone(dt.timedelta(hours=9))


def read_limits(timeout=30):
    exe = shutil.which("codex") or "codex"
    proc = subprocess.Popen(
        [exe, "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    responses = {}
    cond = threading.Condition()

    def reader():
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if "id" in msg and ("result" in msg or "error" in msg):
                with cond:
                    responses[msg["id"]] = msg
                    cond.notify_all()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def wait_for(msg_id):
        deadline = time.time() + timeout
        with cond:
            while msg_id not in responses:
                left = deadline - time.time()
                if left <= 0:
                    return None
                cond.wait(left)
            return responses[msg_id]

    threading.Thread(target=reader, daemon=True).start()
    try:
        send({"id": 1, "method": "initialize",
              "params": {"clientInfo": {"name": "codex-ratelimits", "version": "0.2"}}})
        if wait_for(1) is None:
            raise RuntimeError("NO_INITIALIZE_RESPONSE")
        send({"method": "initialized"})
        send({"id": 2, "method": "account/rateLimits/read"})
        resp = wait_for(2)
        if resp is not None and "error" in resp:
            # 빈 params 로 한 번 더 — 서버 버전에 따라 요구가 다를 수 있다
            send({"id": 3, "method": "account/rateLimits/read", "params": {}})
            resp = wait_for(3) or resp
        if resp is None:
            raise RuntimeError("NO_RATELIMIT_RESPONSE")
        if "error" in resp:
            raise RuntimeError("ERROR " + json.dumps(resp["error"], ensure_ascii=False)[:800])
        return resp.get("result") or {}
    finally:
        proc.kill()


def kst(ts):
    return dt.datetime.fromtimestamp(ts, KST).strftime("%m-%d %H:%M") if ts else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true", help="한 줄 요약과 종료코드")
    ap.add_argument("--threshold", type=float, default=90.0, help="5시간 창 사용률 기준(%%)")
    args = ap.parse_args()

    try:
        res = read_limits()
    except RuntimeError as e:
        print(str(e))
        return 3

    if not args.summary:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0

    rl = res.get("rateLimits") or {}
    plan = (rl.get("planType") or "").lower()
    p = rl.get("primary") or {}
    s = rl.get("secondary") or {}
    credits = (res.get("rateLimitResetCredits") or {}).get("availableCount")
    print("PLAN=%s 5H=%s%% (reset %s KST) WEEK=%s%% (reset %s KST) REACHED=%s RESET_CREDITS=%s" % (
        plan or "?", p.get("usedPercent"), kst(p.get("resetsAt")),
        s.get("usedPercent"), kst(s.get("resetsAt")), rl.get("rateLimitReachedType"), credits))
    if plan not in PAID:
        return 4
    if rl.get("rateLimitReachedType") or (p.get("usedPercent") or 0) >= args.threshold \
            or (s.get("usedPercent") or 0) >= 100:
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
