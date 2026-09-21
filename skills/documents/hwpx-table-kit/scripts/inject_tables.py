# -*- coding: utf-8 -*-
"""CLI: splice real OWPML tables into an existing .hwpx.

    python inject_tables.py --base IN.hwpx --tables tables.json --out OUT.hwpx

The section body of the source document is replaced by the tables described
in tables.json (page setup is preserved). Embedded images are removed by
default because the usual use-case is "image-of-a-table -> real table".

tables.json shape:
{
  "style":   { "header_fill": "#F2F2F2", "border_color": "#000000",
               "border_width": "0.12 mm", "heading_height": 1300 },
  "keepImages": false,
  "tables": [
    { "heading": "A. ...",          // optional paragraph above the table
      "header":  ["col1", "col2"],  // first row (rendered as header)
      "boldCols": [3],              // 0-based body columns to bold (optional)
      "widths":  [7600, 8000],      // HWPUNIT per column (optional -> even split)
      "rows":    [["a","b"], ...] }
  ]
}
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hwpx_pack
import owpml_table as ot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="source .hwpx")
    ap.add_argument("--tables", required=True, help="tables.json spec")
    ap.add_argument("--out", required=True, help="output .hwpx")
    ap.add_argument("--keep-images", action="store_true",
                    help="do not strip embedded BinData images")
    args = ap.parse_args()

    spec = json.load(open(args.tables, encoding="utf-8"))
    tables = spec["tables"]
    style = spec.get("style", {})
    keep_images = args.keep_images or spec.get("keepImages", False)

    workdir = tempfile.mkdtemp(prefix="hwpxkit_")
    try:
        d = os.path.join(workdir, "doc")
        hwpx_pack.unpack(args.base, d)

        hpath = os.path.join(d, "Contents", "header.xml")
        spath = os.path.join(d, "Contents", "section0.xml")

        header = open(hpath, encoding="utf-8").read()
        header, ids = ot.add_styles(header, style)
        open(hpath, "w", encoding="utf-8").write(header)

        section = open(spath, encoding="utf-8").read()
        section = ot.rebuild_section(section, tables, ids)
        open(spath, "w", encoding="utf-8").write(section)

        if not keep_images:
            bindir = os.path.join(d, "BinData")
            if os.path.isdir(bindir):
                shutil.rmtree(bindir, onexc=hwpx_pack._onerr)
            for rel in ["Contents/content.hpf", "META-INF/manifest.xml",
                        "META-INF/container.rdf"]:
                p = os.path.join(d, rel)
                if os.path.exists(p):
                    t = open(p, encoding="utf-8").read()
                    t2 = ot.strip_image_manifest(t)
                    if t2 != t:
                        open(p, "w", encoding="utf-8").write(t2)

        hwpx_pack.pack(d, args.out)
        print("WROTE", args.out, os.path.getsize(args.out), "bytes",
              "| tables:", len(tables))
    finally:
        shutil.rmtree(workdir, onexc=hwpx_pack._onerr)


if __name__ == "__main__":
    main()
