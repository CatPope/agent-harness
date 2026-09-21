#!/usr/bin/env python3
"""Portability linter - launcher.

The linter itself lives with the skill that owns it:

    skills/skillcraft/portable-skill-authoring/scripts/check_skill.py

A skill has to ship its own scripts to stay usable on its own, so that copy is
the canonical one. Keeping a second copy here would be the "same rule in two
places" problem: within weeks they drift, and the drift is invisible because
both files still run. So this file holds no checking logic at all - it only
forwards to the canonical linter.

Usage is unchanged:

    python tools/check_skill.py skills/_core
    python tools/check_skill.py skills/documents
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CANONICAL = os.path.normpath(os.path.join(
    HERE, os.pardir,
    "skills", "skillcraft", "portable-skill-authoring", "scripts",
    "check_skill.py",
))

if not os.path.isfile(CANONICAL):
    sys.stderr.write(
        "linter not found at {}\n"
        "Restore the 'skillcraft' pack - it owns the canonical copy.\n".format(CANONICAL)
    )
    raise SystemExit(2)

# run_name="__main__" so the target's own argument parsing and exit code apply.
runpy.run_path(CANONICAL, run_name="__main__")
