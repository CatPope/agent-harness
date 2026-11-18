"""Environment check for db-performance-design: Python 3.11+ (Connection.serialize) and SQLite FTS5."""
import sqlite3
import sys

if sys.version_info < (3, 11):
    raise SystemExit("python 3.11+ required (sqlite_pages.py uses Connection.serialize)")
con = sqlite3.connect(":memory:")
try:
    con.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
    fts = "fts5 ok"
except sqlite3.OperationalError:
    fts = "fts5 missing"
print(f"db-performance-design ready, python {sys.version.split()[0]}, sqlite {sqlite3.sqlite_version}, {fts}")
