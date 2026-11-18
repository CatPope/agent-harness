#!/usr/bin/env python3
"""sqlite_pages.py — read the SQLite file format directly and report, per table and index,
how many pages it uses, how deep its B-tree is, how full its leaves are, and its overflow pages.

Why: the `dbstat` virtual table is missing from many builds (Python's bundled SQLite included),
so there is no SQL way to see which object takes the space. This walks the B-trees itself.
Standard library only.

Usage:
    python sqlite_pages.py <db> [--json] [--min-pages N]

The original file is never read directly: the script copies it with the online backup API into an
in-memory database (a consistent snapshot, WAL content included), takes its byte image with
Connection.serialize() (Python 3.11+) and walks that. No temp file is written, nothing is deleted.
Memory use is about the size of the database.
Layout facts used here come from https://www.sqlite.org/fileformat2.html
"""
import argparse
import json
import math
import os
import sqlite3
import struct
import sys


def varint(buf, i):
    """SQLite varint: 1-9 bytes, big-endian, high bit = more bytes follow (9th byte uses all 8 bits)."""
    v = 0
    for k in range(8):
        b = buf[i + k]
        v = (v << 7) | (b & 0x7F)
        if b < 0x80:
            return v, i + k + 1
    return (v << 8) | buf[i + 8], i + 9


class BTreeWalker:
    def __init__(self, image):
        self.img = image
        hdr = image[:100]
        if hdr[:16] != b"SQLite format 3\x00":
            raise ValueError("not an SQLite 3 database")
        ps = struct.unpack(">H", hdr[16:18])[0]
        self.page_size = 65536 if ps == 1 else ps
        self.reserved = hdr[20]
        self.usable = self.page_size - self.reserved
        self.freelist_pages = struct.unpack(">I", hdr[36:40])[0]
        self.autovacuum_root = struct.unpack(">I", hdr[52:56])[0]
        self.npages = len(image) // self.page_size

    def page(self, n):
        return self.img[(n - 1) * self.page_size:n * self.page_size]

    def _local(self, payload, is_index):
        """Bytes of a cell payload kept on the b-tree page; the rest goes to overflow pages."""
        u = self.usable
        x = ((u - 12) * 64 // 255) - 23 if is_index else u - 35
        if payload <= x:
            return payload
        m = ((u - 12) * 32 // 255) - 23
        k = m + ((payload - m) % (u - 4))
        return k if k <= x else m

    def _overflow_pages(self, payload, is_index):
        local = self._local(payload, is_index)
        return 0 if local >= payload else math.ceil((payload - local) / (self.usable - 4))

    def walk(self, root):
        st = {"interior": 0, "leaf": 0, "overflow": 0, "cells": 0, "depth": 0,
              "payload": 0, "leaf_used": 0, "leaf_capacity": 0}
        stack = [(root, 1)]
        while stack:
            pno, depth = stack.pop()
            buf = self.page(pno)
            off = 100 if pno == 1 else 0
            kind = buf[off]
            ncell = struct.unpack(">H", buf[off + 3:off + 5])[0]
            content = struct.unpack(">H", buf[off + 5:off + 7])[0] or 65536
            frag = buf[off + 7]
            hlen = 12 if kind in (2, 5) else 8
            p0 = off + hlen
            ptrs = [struct.unpack(">H", buf[p0 + 2 * i:p0 + 2 * i + 2])[0] for i in range(ncell)]
            if kind in (2, 5):                      # interior index / interior table
                st["interior"] += 1
                if kind == 2:
                    # An index b-tree is a true B-tree: interior cells are index entries too.
                    # A table b-tree is a B+tree: interior cells only hold rowid dividers.
                    st["cells"] += ncell
                for p in ptrs:
                    stack.append((struct.unpack(">I", buf[p:p + 4])[0], depth + 1))
                    if kind == 2:                   # index interior cells carry a key payload
                        payload, _ = varint(buf, p + 4)
                        st["overflow"] += self._overflow_pages(payload, True)
                stack.append((struct.unpack(">I", buf[off + 8:off + 12])[0], depth + 1))
            elif kind in (10, 13):                  # leaf index / leaf table
                st["leaf"] += 1
                st["cells"] += ncell
                st["depth"] = max(st["depth"], depth)
                for p in ptrs:
                    payload, j = varint(buf, p)
                    st["payload"] += payload
                    st["overflow"] += self._overflow_pages(payload, kind == 10)
                free = content - (p0 + 2 * ncell) + frag
                fb = struct.unpack(">H", buf[off + 1:off + 3])[0]
                while fb:
                    nxt, size = struct.unpack(">HH", buf[fb:fb + 4])
                    free += size
                    fb = nxt
                st["leaf_capacity"] += self.usable - off
                st["leaf_used"] += self.usable - off - free
            else:
                raise ValueError(f"page {pno}: unexpected b-tree page type {kind}")
        return st


def snapshot(db):
    """Backup the database into memory and return (connection, byte image of the file format)."""
    src = sqlite3.connect(f"file:{os.path.abspath(db).replace(os.sep, '/')}?mode=ro", uri=True)
    mem = sqlite3.connect(":memory:")
    try:
        src.backup(mem)
    finally:
        src.close()
    return mem, mem.serialize()


def analyze(db):
    con, image = snapshot(db)
    try:
        objs = [("table", "sqlite_schema", "sqlite_schema", 1)]
        objs += con.execute("SELECT type, name, tbl_name, rootpage FROM sqlite_schema "
                            "WHERE rootpage > 0 ORDER BY tbl_name, type DESC, name").fetchall()
        w = BTreeWalker(image)
        rows = []
        for typ, name, tbl, root in objs:
            s = w.walk(root)
            pages = s["interior"] + s["leaf"] + s["overflow"]
            rows.append({
                "type": typ, "name": name, "table": tbl, "root": root,
                "pages": pages, "bytes": pages * w.page_size, "depth": s["depth"],
                "interior": s["interior"], "leaf": s["leaf"], "overflow": s["overflow"],
                "cells": s["cells"], "payload": s["payload"],
                "leaf_fill_pct": round(100 * s["leaf_used"] / s["leaf_capacity"], 1) if s["leaf_capacity"] else 0.0,
                "bytes_per_cell": round(pages * w.page_size / s["cells"], 1) if s["cells"] else None,
            })
        counted = sum(r["pages"] for r in rows)
        ptrmap = 0
        if w.autovacuum_root:
            j = w.usable // 5
            ptrmap = math.ceil(max(0, w.npages - 1) / (j + 1))
        lock_byte = 1 if w.npages * w.page_size > 1073741824 else 0
        summary = {
            "page_size": w.page_size, "file_pages": w.npages, "btree_pages": counted,
            "freelist_pages": w.freelist_pages, "ptrmap_pages": ptrmap, "lock_byte_page": lock_byte,
            "unaccounted": w.npages - counted - w.freelist_pages - ptrmap - lock_byte,
        }
        return summary, rows
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("db")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-pages", type=int, default=0, help="hide objects smaller than this")
    a = ap.parse_args()
    summary, rows = analyze(a.db)
    if a.json:
        print(json.dumps({"summary": summary, "objects": rows}, ensure_ascii=False, indent=1))
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(f"page_size {summary['page_size']} · file {summary['file_pages']} pages · "
          f"b-tree {summary['btree_pages']} · freelist {summary['freelist_pages']} · "
          f"ptrmap {summary['ptrmap_pages']} · unaccounted {summary['unaccounted']}")
    print(f"{'type':6} {'name':38} {'pages':>7} {'KiB':>8} {'depth':>5} {'ovfl':>5} "
          f"{'cells':>9} {'B/cell':>7} {'fill%':>6}")
    for r in sorted(rows, key=lambda r: -r["pages"]):
        if r["pages"] < a.min_pages:
            continue
        print(f"{r['type']:6} {r['name'][:38]:38} {r['pages']:7d} {r['bytes'] / 1024:8.1f} {r['depth']:5d} "
              f"{r['overflow']:5d} {r['cells']:9d} {str(r['bytes_per_cell']):>7} {r['leaf_fill_pct']:6.1f}")
    if summary["unaccounted"]:
        print(f"WARNING: {summary['unaccounted']} pages not accounted for — walker or file layout issue")


if __name__ == "__main__":
    main()
