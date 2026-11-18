"""Figma 덱 페이지의 장들을 번호 붙은 모아 보기 그림으로 만든다. 장마다 get_screenshot 을 부르지 않는다.

쓰는 법: python deck_contact.py <metadata 파일> <페이지 스크린샷 png> <출력 폴더> [열 수] [행 수]

- metadata 파일: get_metadata(페이지 id) 결과. 크면 도구가 JSON 배열([{type, text}])로 저장한다. XML 파일도 받는다.
- 페이지 스크린샷: get_screenshot(페이지 id, maxDimension 6000) 으로 받은 PNG. 페이지의 최상위 노드 전체를 담는다.
- 최상위 frame 들의 x, y, width, height 와 스크린샷 배율로 장마다 잘라 sheet_1.png, sheet_2.png ... 를 만든다.
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_xml(path):
    raw = Path(path).read_text(encoding="utf-8")
    if raw.lstrip().startswith("["):
        raw = "".join(d.get("text", "") for d in json.loads(raw))
    end = raw.rindex("</canvas>") + len("</canvas>")  # 뒤에 붙는 안내 문구를 뗀다
    return ET.fromstring(raw[raw.index("<canvas"):end])


def main(meta, shot, out, cols=3, rows=4):
    root = load_xml(meta)
    kids = [c.attrib for c in root]
    x0 = min(float(a["x"]) for a in kids)
    y0 = min(float(a["y"]) for a in kids)
    x1 = max(float(a["x"]) + float(a["width"]) for a in kids)
    img = Image.open(shot).convert("RGB")
    s = img.width / (x1 - x0)
    frames = [a for a in kids if a.get("name") and float(a["width"]) > 0]
    frames.sort(key=lambda a: (float(a["y"]), float(a["x"])))
    tiles = []
    for a in frames:
        x, y, w, h = (float(a[k]) for k in ("x", "y", "width", "height"))
        box = (round((x - x0) * s), round((y - y0) * s), round((x - x0 + w) * s), round((y - y0 + h) * s))
        tiles.append((a["name"], a["id"], img.crop(box)))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    tw = max(t[2].width for t in tiles)
    th = max(t[2].height for t in tiles)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    per = cols * rows
    for k in range(0, len(tiles), per):
        sheet = Image.new("RGB", (cols * (tw + 10) + 10, rows * (th + 38) + 10), "white")
        d = ImageDraw.Draw(sheet)
        for i, (name, nid, t) in enumerate(tiles[k:k + per]):
            cx, cy = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 38)
            d.text((cx, cy), f"{name}  ({nid})", fill="black", font=font)
            sheet.paste(t, (cx, cy + 28))
        sheet.save(out / f"sheet_{k // per + 1}.png")
    print(f"{len(tiles)} frames -> {out}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], *(int(v) for v in a[3:5]))
