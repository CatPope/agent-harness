"""장면 파일(JSON 배열, 한 줄 한 단계)을 읽어 시연 대본 엑셀을 만든다.

    python scenes_to_xlsx.py <설정.json>

시트 셋: 흐름(동작 한 줄씩) · 대본(클릭 한 줄씩, 장면·동작·화면 병합) · 리허설 결과.
한 대본 줄 = 커서가 한 곳을 가리키는 순간(point) 또는 말풍선만 띄우는 순간(say).
그 뒤의 누르기·입력·기다리기는 같은 줄 「설명」에 붙인다.

설정 파일 키 (예시: example-config.json)
  scenes_dir     장면 파일 폴더(설정 파일 기준 상대 경로 가능). 파일 이름 첫 글자가 장면 키(A, B, ...)
  out            만들 .xlsx 경로
  scene_titles   {"A": "A. 연결", ...}
  windows        {"창 제목 일부": "화면 이름", ...}   point·waitfor 의 win 을 사람이 읽는 이름으로
  spots          [["공간", x, y, "화면 이름", "가리키는 것"], ...]   이름 없는 좌표 지점. 공간은 "" 또는 space 이름
  groups         {"A01": ["동작 이름", "보여 주는 것"], ...}   동작이 시작하는 대본 번호
  pages          ["PC", "자료", ...]   이 이름의 링크를 누르면 그 화면으로 바뀐 것으로 적는다
  results        [["회차", "시각", "걸린 시간", "무엇이 있었나", "고친 것·남은 것"], ...]
  read_base, read_cps   말풍선 시간 = read_base + 공백 뺀 글자 수 / read_cps (기본 0.5, 10)
  sample_vars    {"code": "○○○ ○○○"}   멘트 안 {변수} 를 대본에 보일 값

openpyxl 이 필요하다.
"""
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

THIN = Side(style="thin", color="BFBFBF")
THICK = Side(style="medium", color="404040")
PALETTE = ["EAF1FB", "EEF7EE", "FDF3E7", "F3EEF9", "FBEAEA", "EAF7F7"]
KEYS = {"enter": "Enter", "esc": "Esc", "tab": "Tab"}


class Script:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.windows = cfg.get("windows", {})
        self.spots = {(s[0], s[1], s[2]): (s[3], s[4]) for s in cfg.get("spots", [])}
        self.pages = set(cfg.get("pages", []))
        self.page: dict[str, str] = {}
        self.base = cfg.get("read_base", 0.5)
        self.cps = cfg.get("read_cps", 10)
        self.vars = cfg.get("sample_vars", {})

    def label(self, win: str) -> str:
        for k, v in self.windows.items():
            if k in win:
                return v
        return win

    def fill(self, text: str) -> str:
        for k, v in self.vars.items():
            text = text.replace("{" + k + "}", v)
        return text

    def hold(self, text: str) -> float:
        return round(self.base + len(text.replace(" ", "")) / self.cps, 1)

    def where(self, s: dict) -> tuple[str, str]:
        if "win" in s and "name" in s:
            return self.label(s["win"]), f"「{s['name']}」"
        if "win" in s:
            return self.label(s["win"]), f"「{s.get('text', '')}」 자리"
        return self.spots.get((s.get("in", ""), s.get("x"), s.get("y")), ("?", f"좌표 {s.get('x')},{s.get('y')}"))

    def rows(self, title: str, steps: list[dict]) -> list[dict]:
        rows, cur, pending = [], None, []
        for s in steps:
            op = s["op"]
            if op == "space":
                continue
            if op in ("front", "place", "minimize"):
                pending.append(f"{self.label(s['win'])} 창을 " + {"front": "앞으로", "place": "제자리에", "minimize": "내림"}[op])
                continue
            if op in ("point", "say"):
                if cur:
                    rows.append(cur)
                screen, target = ("화면 위", "") if op == "say" else self.where(s)
                text = s.get("text", "")
                shown = screen + (f" ({self.page[screen]})" if self.page.get(screen) else "")
                cur = {"장면": title, "화면": shown, "_screen": screen, "_target": s.get("name", ""),
                       "설명": pending + ([f"{target} 가리킴"] if target else ["말풍선만 띄움"]),
                       "멘트": self.fill(text), "초": s.get("hold") or self.hold(self.fill(text))}
                pending = []
                continue
            if cur is None:
                cur = {"장면": title, "화면": "", "_screen": "", "_target": "", "설명": pending, "멘트": "", "초": 0}
                pending = []
            d = cur["설명"]
            if op in ("click", "dclick", "rclick"):
                d.append({"click": "누름", "dclick": "두 번 누름", "rclick": "오른쪽 단추로 누름"}[op])
                if cur["_target"] in self.pages:
                    self.page[cur["_screen"]] = f"「{cur['_target']}」 화면"
            elif op == "type":
                d.append(f"「{self.fill(s['text'])}」 입력")
            elif op == "key":
                d.append(f"{KEYS.get(s['keys'], s['keys'].title())} 키")
            elif op == "waitfor":
                d.append(f"{self.label(s['win'])}에 「{s['name']}」 뜰 때까지 기다림(최대 {s['timeout']}초)")
            elif op == "wait":
                d.append(f"{s['s']}초 기다림")
            elif op == "read":
                d.append(f"화면 글자를 읽어 {{{s.get('var', '값')}}} 로 둠")
            elif op == "move":
                d.append("커서를 옮김" + (f" (「{s['name']}」 옆)" if "name" in s else ""))
            elif op == "scroll":
                d.append(f"목록을 {abs(s['n'])}칸 {'내림' if s['n'] < 0 else '올림'}")
            elif op == "hide":
                d.append("말풍선 숨김")
            else:
                d.append(op)
        if cur:
            rows.append(cur)
        return rows


def style(ws, widths, center_cols=()):
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top",
                                    horizontal="center" if c.column in center_cols else None)
            c.border = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
            c.font = Font(name="맑은 고딕", size=10)
    for c in ws[1]:
        c.font = Font(name="맑은 고딕", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="404040")
        c.alignment = Alignment(horizontal="center", vertical="center")
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    ws.freeze_panes = "A2"


def merge_col(ws, col, lo, hi, bounds, center=False, bold=False):
    """lo..hi 행에서 col 값이 같은 줄을 합친다. bounds 행에서는 새로 시작한다. 묶음 첫 행 목록을 돌려준다."""
    starts, start = [], lo
    for r in range(lo + 1, hi + 2):
        if r <= hi and r not in bounds and ws.cell(r, col).value == ws.cell(start, col).value:
            continue
        if r - 1 > start:
            ws.merge_cells(start_row=start, start_column=col, end_row=r - 1, end_column=col)
        cell = ws.cell(start, col)
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center" if center else None)
        if bold:
            cell.font = Font(name="맑은 고딕", size=11 if col == 1 else 10, bold=True)
        starts.append(start)
        start = r
    return starts


def top_line(ws, rows, ncol, side):
    for r in rows:
        for c in range(1, ncol + 1):
            b = ws.cell(r, c).border
            ws.cell(r, c).border = Border(top=side, bottom=b.bottom, left=b.left, right=b.right)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not argv:
        print(__doc__)
        return 2
    cfg_path = Path(argv[0]).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    scenes = (cfg_path.parent / cfg["scenes_dir"]).resolve()
    out = (cfg_path.parent / cfg["out"]).resolve()
    titles = cfg.get("scene_titles", {})
    groups_cfg = cfg.get("groups", {})
    sc = Script(cfg)

    wb = Workbook()
    flow = wb.active
    flow.title = "흐름"
    ws = wb.create_sheet("대본")
    ws.append(["장면", "동작", "번호", "화면", "설명 (커서가 하는 일)", "멘트 (말풍선)", "말풍선 초"])
    flow.append(["장면", "동작", "번호", "보여 주는 것", "화면", "말풍선 초"])
    groups, missing, total, secs = [], [], 0, 0.0
    color = {}
    for p in sorted(scenes.glob("*.json")):
        key = p.name[0]
        color[key] = PALETTE[len(color) % len(PALETTE)]
        title = titles.get(key, p.stem)
        for i, r in enumerate(sc.rows(title, json.loads(p.read_text(encoding="utf-8"))), 1):
            rid = f"{key}{i:02d}"
            if rid in groups_cfg:
                groups.append([title, groups_cfg[rid][0], rid, rid, groups_cfg[rid][1], [], 0.0])
            elif not groups or groups[-1][0] != title:
                missing.append(rid)
                groups.append([title, "(동작 이름 없음)", rid, rid, "", [], 0.0])
            g = groups[-1]
            g[3] = rid
            if r["_screen"] and r["_screen"] != "화면 위" and r["_screen"] not in g[5]:
                g[5].append(r["_screen"])
            g[6] += r["초"] or 0
            ws.append([title, g[1], rid, r["화면"], ", ".join(r["설명"]), r["멘트"], r["초"] or None])
            total += 1
            secs += r["초"] or 0
    for g in groups:
        flow.append([g[0], g[1], g[2] if g[2] == g[3] else f"{g[2]}~{g[3]}", g[4], "\n".join(g[5]), round(g[6], 1)])

    style(ws, (14, 22, 7, 24, 52, 52, 8), center_cols=(3, 7))
    for row in ws.iter_rows(min_row=2):
        for c in row[:2]:
            c.fill = PatternFill("solid", fgColor=color[row[2].value[0]])
    scene_rows = merge_col(ws, 1, 2, ws.max_row, [], center=True, bold=True)
    group_rows = merge_col(ws, 2, 2, ws.max_row, scene_rows, bold=True)
    merge_col(ws, 4, 2, ws.max_row, group_rows)
    top_line(ws, group_rows, 7, Side(style="thin", color="7F7F7F"))
    top_line(ws, scene_rows, 7, THICK)

    style(flow, (14, 26, 10, 60, 26, 8), center_cols=(3, 6))
    for row in flow.iter_rows(min_row=2):
        row[0].fill = PatternFill("solid", fgColor=color[row[2].value[0]])
        row[1].font = Font(name="맑은 고딕", size=10, bold=True)
    top_line(flow, merge_col(flow, 1, 2, flow.max_row, [], center=True, bold=True), 6, THICK)

    rs = wb.create_sheet("리허설 결과")
    rs.append(["회차", "시각", "걸린 시간", "무엇이 있었나", "고친 것·남은 것"])
    for r in cfg.get("results", []):
        rs.append(list(r))
    style(rs, (16, 18, 22, 60, 60))

    wb.save(out)
    print(f"{out} 동작 {len(groups)}, 줄 {total}, 말풍선 합 {secs:.0f}초")
    if missing:
        print("동작 이름이 없는 장면 첫 줄(groups 에 넣는다):", missing)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
