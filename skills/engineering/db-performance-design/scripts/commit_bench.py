#!/usr/bin/env python3
"""commit_bench.py — measure what one COMMIT costs on *this* machine's disk, per journal mode.

A commit waits for fsync (FlushFileBuffers on Windows). That wait is set by the storage hardware and
the filesystem, not by SQL, so it has to be measured where the database will run (the server VM, not
the developer PC).  Also shows how readers and a writer interfere under each mode.

Usage:
    python commit_bench.py [--dir <folder on the target disk>] [--n 300] [--concurrency 3]

Modes measured:  DELETE+FULL (SQLite default)  ·  WAL+FULL  ·  WAL+NORMAL
Output: per-commit latency p50/p95/max, commits per second, one-transaction bulk insert time,
and (with --concurrency) how many reader queries failed with "database is locked".
Standard library only. Creates and removes its own temp files.
"""
import argparse
import os
import sqlite3
import statistics
import sys
import tempfile
import threading
import time

MODES = [("delete", "FULL"), ("wal", "FULL"), ("wal", "NORMAL")]


def fresh(folder, journal, sync):
    fd, path = tempfile.mkstemp(suffix=".sqlite", dir=folder)
    os.close(fd)
    os.remove(path)
    con = sqlite3.connect(path, isolation_level=None, timeout=0.0)
    con.execute(f"PRAGMA journal_mode={journal}")
    con.execute(f"PRAGMA synchronous={sync}")
    con.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT, ts INTEGER)")
    return path, con


def cleanup(path):
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.remove(path + suffix)
        except OSError:
            pass


def single_commits(con, n):
    lat = []
    for i in range(n):
        t0 = time.perf_counter()
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT INTO t(v, ts) VALUES (?, ?)", ("x" * 40, i))
        con.execute("COMMIT")
        lat.append((time.perf_counter() - t0) * 1000)
    return lat


def bulk(con, n):
    t0 = time.perf_counter()
    con.execute("BEGIN IMMEDIATE")
    con.executemany("INSERT INTO t(v, ts) VALUES (?, ?)", (("y" * 40, i) for i in range(n)))
    con.execute("COMMIT")
    return (time.perf_counter() - t0) * 1000


def contention(path, sync, seconds, readers):
    """One writer commits in a loop while N readers query; count reader errors (no busy timeout)."""
    stop = time.perf_counter() + seconds
    errors, reads, writes = [0], [0], [0]
    lock = threading.Lock()

    def reader():
        c = sqlite3.connect(path, isolation_level=None, timeout=0.0, check_same_thread=False)
        while time.perf_counter() < stop:
            try:
                c.execute("SELECT count(*), max(ts) FROM t").fetchone()
                with lock:
                    reads[0] += 1
            except sqlite3.OperationalError:
                with lock:
                    errors[0] += 1
        c.close()

    def writer():
        c = sqlite3.connect(path, isolation_level=None, timeout=5.0, check_same_thread=False)
        c.execute(f"PRAGMA synchronous={sync}")
        i = 0
        while time.perf_counter() < stop:
            c.execute("BEGIN IMMEDIATE")
            c.execute("INSERT INTO t(v, ts) VALUES (?, ?)", ("z" * 40, i))
            c.execute("COMMIT")
            i += 1
            with lock:
                writes[0] += 1
        c.close()

    threads = [threading.Thread(target=reader) for _ in range(readers)] + [threading.Thread(target=writer)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return reads[0], errors[0], writes[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=None, help="folder on the disk to test (default: system temp)")
    ap.add_argument("--n", type=int, default=300, help="single-row commits per mode")
    ap.add_argument("--bulk", type=int, default=100000, help="rows in the one-transaction insert")
    ap.add_argument("--concurrency", type=int, default=0, help="reader threads for the contention test")
    ap.add_argument("--seconds", type=float, default=3.0)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(f"SQLite {sqlite3.sqlite_version} · folder {a.dir or tempfile.gettempdir()}")
    print(f"{'mode':12} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8} {'commits/s':>10} {'bulk ms':>9}"
          + (f" {'reads':>8} {'read errs':>9} {'writes':>7}" if a.concurrency else ""))
    for journal, sync in MODES:
        path, con = fresh(a.dir, journal, sync)
        try:
            lat = single_commits(con, a.n)
            b = bulk(con, a.bulk)
            con.close()
            p = sorted(lat)
            line = (f"{journal.upper() + '+' + sync:12} {statistics.median(p):8.3f} {p[int(len(p) * .95) - 1]:8.3f} "
                    f"{p[-1]:8.3f} {1000 * len(p) / sum(p):10.0f} {b:9.1f}")
            if a.concurrency:
                r, e, w = contention(path, sync, a.seconds, a.concurrency)
                line += f" {r:8d} {e:9d} {w:7d}"
            print(line)
        finally:
            cleanup(path)


if __name__ == "__main__":
    main()
