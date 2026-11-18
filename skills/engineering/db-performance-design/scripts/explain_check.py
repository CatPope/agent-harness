#!/usr/bin/env python3
"""explain_check.py — run named queries against an SQLite database, show each query plan,
flag the plan shapes that get slow as tables grow, and time the query.

Usage:
    python explain_check.py <db> <queries.sql> [--params p.json] [--repeat 5] [--big 10000] [--json]

queries.sql holds one or more blocks like:

    -- name: timeline_by_channel
    -- params: {"src": 3, "lim": 20}
    SELECT ... WHERE source_id = :src ORDER BY event_ts DESC LIMIT :lim;

Flags (see https://www.sqlite.org/eqp.html):
    FULL-SCAN   "SCAN <table>" without an index on a table with at least --big rows
    TEMP-SORT   "USE TEMP B-TREE FOR ORDER BY/GROUP BY/DISTINCT" — every matching row is collected and sorted
    AUTO-INDEX  "AUTOMATIC ... INDEX" — the planner builds a throw-away index on every run
    CORRELATED  a correlated subquery that re-runs per outer row
Standard library only. Opens the database read-only.
"""
import argparse
import json
import os
import re
import sqlite3
import statistics
import sys
import time


def load_queries(path):
    blocks, cur = [], None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\s*--\s*name:\s*(\S+)", line)
        if m:
            cur = {"name": m.group(1), "params": {}, "sql": ""}
            blocks.append(cur)
            continue
        m = re.match(r"\s*--\s*params:\s*(\{.*\})\s*$", line)
        if m and cur is not None:
            cur["params"] = json.loads(m.group(1))
            continue
        if cur is not None and not line.lstrip().startswith("--"):
            cur["sql"] += line
    return [b for b in blocks if b["sql"].strip()]


def table_rows(con):
    rows = {}
    for (name,) in con.execute("SELECT name FROM sqlite_schema WHERE type='table'"):
        try:
            rows[name.lower()] = con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
        except sqlite3.DatabaseError:
            pass
    return rows


def flags_for(plan, rows, big):
    out = []
    for detail in plan:
        if detail.startswith("SCAN ") and " USING " not in detail and "VIRTUAL TABLE" not in detail:
            tbl = detail.split()[1].lower()
            if rows.get(tbl, 0) >= big:
                out.append(f"FULL-SCAN {tbl}({rows[tbl]})")
        if "USE TEMP B-TREE" in detail:
            out.append("TEMP-SORT " + detail.split("FOR ", 1)[-1])
        if "AUTOMATIC" in detail:
            out.append("AUTO-INDEX")
        if "CORRELATED" in detail:
            out.append("CORRELATED")
    return out


def run(db, qpath, repeat, big, shared_params=None, functions=None):
    con = sqlite3.connect(f"file:{os.path.abspath(db).replace(os.sep, '/')}?mode=ro", uri=True)
    for name, (nargs, fn) in (functions or {}).items():
        con.create_function(name, nargs, fn, deterministic=True)
    rows = table_rows(con)
    results = []
    for q in load_queries(qpath):
        sql = q["sql"].strip().rstrip(";")
        params = {**(shared_params or {}), **q["params"]}
        used = set(re.findall(r":(\w+)", sql))
        params = {k: v for k, v in params.items() if k in used}
        plan = [r[3] for r in con.execute("EXPLAIN QUERY PLAN " + sql, params)]
        times, n = [], 0
        for _ in range(max(1, repeat)):
            t0 = time.perf_counter()
            n = len(con.execute(sql, params).fetchall())
            times.append((time.perf_counter() - t0) * 1000)
        results.append({"name": q["name"], "rows": n, "ms_median": round(statistics.median(times), 3),
                        "ms_max": round(max(times), 3), "plan": plan, "flags": flags_for(plan, rows, big)})
    con.close()
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("db")
    ap.add_argument("queries")
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--big", type=int, default=10000, help="row count from which a full scan is flagged")
    ap.add_argument("--params", help="JSON file of parameters shared by every query (per-query params win)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    shared = json.load(open(a.params, encoding="utf-8")) if a.params else None
    res = run(a.db, a.queries, a.repeat, a.big, shared)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    for r in res:
        print(f"## {r['name']}  rows={r['rows']}  median={r['ms_median']} ms  max={r['ms_max']} ms")
        for d in r["plan"]:
            print(f"   {d}")
        if r["flags"]:
            print("   FLAGS: " + ", ".join(r["flags"]))
        print()


if __name__ == "__main__":
    main()
