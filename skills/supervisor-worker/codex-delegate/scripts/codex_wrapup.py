# -*- coding: utf-8 -*-
"""컨텍스트가 기준 이상이면 (1) 작업 기록 턴을 보내고 (2) 기록 파일을 확인한 뒤 (3) 수동 압축을 건다.

왜 필요한가
  Codex 는 컨텍스트가 자동 압축 한도에 닿으면 알아서 압축하는데 그 시점은 작업 한복판이다.
  한도는 ~/.codex/config.toml 의 model_auto_compact_token_limit 이다(이 환경 140,000 토큰,
  창 258,400 의 약 54%). 창 대비 %로 재면 70% 가 영영 오지 않는다 — **한도 대비 %** 로 잰다.
  우리가 고른 매듭(턴 사이)에서 먼저 압축하되, 압축 전에 **파일로 남기게** 해서
  손실을 통제한다. Codex 는 자기 점유율을 모르므로 **밖에서 재서** 판단한다.

  관리자가 기억해야 작동하는 절차는 신뢰할 수 없다 — 그래서 한 명령으로 묶었다.

사용법
  python codex_wrapup.py <task> --dir <작업디렉토리>               # 70% 이상이면 기록 -> 압축
  python codex_wrapup.py <task> --dir <작업디렉토리> --dry-run      # 점유율과 계획만
  python codex_wrapup.py <task> --dir <작업디렉토리> --force        # 기준 무시하고 실행(시험용)
  python codex_wrapup.py <task> --dir <작업디렉토리> --threshold 60

언제 부르나: 한 턴의 완료보고를 검수한 직후, 다음 지시서를 보내기 **전**.
턴이 진행 중일 때는 부르지 않는다(압축은 매듭에서만).

종료 코드  0 = 정상(기준 미만이라 건너뛴 경우 포함) · 2 = 한도 임박으로 보류
          3 = 점유율을 못 읽음 · 4 = 기록 턴 실패 · 5 = 기록 파일 검증 실패(압축 안 함)
          6 = 압축 실패
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import codex_task                           # 같은 scripts/ 폴더
import codex_usage

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "checkpoint_prompt.md"
REQUIRED_SECTIONS = 7
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
DEFAULT_LIMIT_RATIO = 0.88              # config 에 한도가 없을 때만 쓰는 대체값
CKPT_REL_DIR = Path("reports") / "checkpoints"


def effective_limit(window: int) -> tuple[int, str]:
    """자동 압축이 걸리는 토큰 수. config 값이 있으면 그것, 없으면 창의 88%."""
    try:
        m = re.search(r"^\s*model_auto_compact_token_limit\s*=\s*(\d+)",
                      CODEX_CONFIG.read_text(encoding="utf-8", errors="replace"), flags=re.M)
        if m:
            return min(int(m.group(1)), window or int(m.group(1))), "config"
    except OSError:
        pass
    return int(window * DEFAULT_LIMIT_RATIO), "기본 88%"


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def build_prompt(task: str, pct: float, ckpt_rel: str) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    return text.replace("{pct}", f"{pct:.0f}%").replace("{ckpt_path}", ckpt_rel).replace("{task}", task)


def check_ckpt(path: Path, sent_at: float) -> tuple[bool, str]:
    """기록 파일이 실제로 생겼고 절이 다 있는지 본다. 파일이 없으면 압축하지 않는다."""
    if not path.exists():
        return False, f"기록 파일이 없다: {path}"
    if path.stat().st_mtime < sent_at - 2:
        return False, f"기록 파일이 이번 턴 이전 것이다(수정 시각이 옛날): {path}"
    text = path.read_text(encoding="utf-8", errors="replace")
    heads = re.findall(r"^## (\d+)\. ", text, flags=re.M)
    nums = {int(h) for h in heads}
    missing = [n for n in range(1, REQUIRED_SECTIONS + 1) if n not in nums]
    if missing:
        return False, f"절이 빠졌다: {missing} (찾은 절 {sorted(nums)})"
    if len(text) < 800:
        return False, f"기록이 너무 짧다({len(text)}자)"
    return True, f"절 {REQUIRED_SECTIONS}개 확인 · {len(text):,}자"


def main() -> int:
    _utf8()
    ap = argparse.ArgumentParser(description="기준 이상이면 작업 기록 -> 수동 압축")
    ap.add_argument("task")
    ap.add_argument("--dir", default=".")
    ap.add_argument("--threshold", type=float, default=70.0,
                    help="자동 압축 한도(config) 대비 점유율 기준(%%). 창 대비가 아니다")
    ap.add_argument("--force", action="store_true", help="기준을 무시한다(시험용)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-compact", action="store_true", help="기록 턴까지만 하고 압축은 하지 않는다")
    ap.add_argument("--sandbox", default=None)
    args = ap.parse_args()

    work_dir = Path(args.dir).resolve()
    state = codex_task.load_state(work_dir)
    task = state["tasks"].get(args.task)
    if not task:
        print(f"'{args.task}' 세션이 없습니다.", file=sys.stderr)
        return 3
    tid = task["thread_id"]

    usage = codex_usage.read_usage(tid)
    if not usage:
        print("[점유율] 롤아웃에서 읽지 못했다 — 판단할 수 없다", file=sys.stderr)
        return 3
    print("[점유율] " + codex_usage.format_usage(usage))
    limit, src = effective_limit(usage["window"])
    pct = usage["ctx"] / limit * 100 if limit else 0.0      # 자동 압축 한도 대비 %
    print(f"[한도 대비] {usage['ctx']:,} / {limit:,} 토큰({src}) = {pct:.1f}%  · 창 대비 {usage['pct']:.1f}%")

    if pct < args.threshold and not args.force:
        print(f"자동 압축 한도 대비 {pct:.1f}% < 기준 {args.threshold:.0f}% — 기록·압축하지 않습니다.")
        return 0

    ok, why = codex_usage.startup_decision(codex_usage.read_usage())
    print(f"[한도] {why}")
    if not ok:
        print("한도가 임박했다. 기록 턴을 시작하면 도중에 끊길 수 있어 보류한다.", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    ckpt_rel = (CKPT_REL_DIR / f"{stamp}_{args.task}.md").as_posix()
    ckpt = work_dir / ckpt_rel
    print(f"[계획] 기록 파일 {ckpt_rel}")
    print(f"[계획] 1) 기록 턴 전송  2) 파일·절 검증  3) 수동 압축{' (생략)' if args.no_compact else ''}")
    if args.dry_run:
        print("--dry-run: 여기서 멈춥니다.")
        return 0

    prompt = build_prompt(args.task, pct, ckpt_rel)
    run_dir = work_dir / ".claude-codex" / args.task
    sandbox = args.sandbox or task.get("sandbox", "workspace-write")
    sent_at = time.time()
    report, events, _ = codex_task.run_codex(
        codex_task.find_codex(), work_dir, prompt, schema=codex_task.DEFAULT_SCHEMA,
        sandbox=sandbox, resume_id=tid, run_dir=run_dir)
    task["turns"].append({"at": codex_task.now(), "kind": "checkpoint", "events": events, "report": report})
    codex_task.save_state(work_dir, state)
    if report is None:
        print("기록 턴이 실패했다(보고 없음). 압축하지 않는다.", file=sys.stderr)
        return 4
    if isinstance(report, dict) and report.get("blocked"):
        print("기록 턴이 blocked 로 끝났다. 압축하지 않는다.", file=sys.stderr)
        return 4

    good, detail = check_ckpt(ckpt, sent_at)
    print(f"[검증] {'통과' if good else '실패'} — {detail}")
    if not good:
        print("기록이 확인되지 않았으므로 **압축하지 않는다.**", file=sys.stderr)
        return 5

    if args.no_compact:
        print("--no-compact: 압축을 건너뜁니다.")
        return 0

    before = usage
    cmd = [sys.executable, str(Path(__file__).with_name("codex_compact.py")),
           "--dir", str(work_dir), "--task", args.task]
    proc = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(f"압축 실패(exit={proc.returncode}). 기록 파일은 남아 있다: {ckpt_rel}", file=sys.stderr)
        return 6

    after = codex_usage.read_usage(tid)
    if after and after.get("ctx", 0) == 0:
        after = None        # 압축 요청 자체의 기록(입력 0)을 읽은 것 — 진짜 값은 압축 뒤 첫 요청에 생긴다
    entry = {"at": codex_task.now(), "checkpoint": ckpt_rel,
             "before_pct": round(before["pct"], 1), "after_pct": round(after["pct"], 1) if after else None}
    state = codex_task.load_state(work_dir)
    state["tasks"][args.task].setdefault("compactions", []).append(entry)
    codex_task.save_state(work_dir, state)

    print("\n=== 완료 ===")
    print(f"기록 파일  {ckpt_rel}")
    if after:
        print(f"점유율     {before['pct']:.1f}% -> {after['pct']:.1f}%")
    else:
        print("점유율     압축 직후 값은 아직 없다(첫 요청 이후 codex_usage.py 로 확인). 실측 예: 125k -> 56k")
    print("다음 지시서 맨 앞에 넣을 문장:")
    print(f"  「먼저 `{ckpt_rel}` 를 읽어라. 압축 전의 시도 목록·제약·다음 첫 행동이 적혀 있다.」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
