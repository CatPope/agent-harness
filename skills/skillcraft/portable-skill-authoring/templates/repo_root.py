"""Locate the repo root from inside a skill script so shared modules under
`<repo>/shared` can be imported without any hardcoded path.

Copy this file into your skill's `scripts/` folder. It is stdlib-only, so a
no-base agent can use it as-is. The repo root is the nearest ancestor
directory that contains both `skills/` and `shared/`.

Usage:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))   # so this module is importable
    from repo_root import shared_path
    sys.path.insert(0, shared_path(__file__))
    import opc            # a module living in <repo>/shared/opc.py
"""
from pathlib import Path


def find_repo_root(start=None):
    p = Path(start or __file__).resolve()
    if p.is_file():
        p = p.parent
    while True:
        if (p / "skills").is_dir() and (p / "shared").is_dir():
            return str(p)
        parent = p.parent
        if parent == p:
            raise RuntimeError(
                f"repo root not found: no ancestor of {start or __file__} has both skills/ and shared/"
            )
        p = parent


def shared_path(start=None):
    return str(Path(find_repo_root(start)) / "shared")
