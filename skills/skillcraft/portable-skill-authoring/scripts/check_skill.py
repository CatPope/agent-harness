#!/usr/bin/env python3
"""Portability linter for Agent Skills.

Checks that a skill can be used by a "no-base" agent (no other skills or
plugins installed) after nothing more than a `git clone` + its own setup
script. Standard library only, so it runs anywhere Python 3.8+ runs.

Usage:
    python check_skill.py <path>

<path> may be a single skill directory (one that contains SKILL.md) or a
parent folder (e.g. the repo's `skills/`); in the latter case every child
skill is checked. Exit code is non-zero if any FAIL is reported.
"""
import os
import re
import sys

# Build the "forbidden hardcoded path" needles from fragments so this file
# does not match its own scan when the linter lints its own skill.
BAD_PATH_NEEDLES = [
    "C:" + chr(92) + "Users",           # Windows user home
    chr(92) + "AppData" + chr(92),      # Windows per-user temp/roaming
    "/" + "home" + "/",                 # Linux user home
    "/" + "Users" + "/",                # macOS user home
]

THIRD_PARTY_HINTS = {
    "PIL": "Pillow", "pillow": "Pillow", "openpyxl": "openpyxl",
    "requests": "requests", "numpy": "numpy", "pandas": "pandas",
    "yaml": "PyYAML", "bs4": "beautifulsoup4", "lxml": "lxml",
    "docx": "python-docx", "fitz": "PyMuPDF",
}

OK, WARN, FAIL = "OK", "WARN", "FAIL"


class Report:
    def __init__(self, skill):
        self.skill = skill
        self.rows = []

    def add(self, level, code, msg):
        self.rows.append((level, code, msg))

    @property
    def failed(self):
        return any(r[0] == FAIL for r in self.rows)

    def render(self):
        icon = {OK: "  ok ", WARN: "warn ", FAIL: "FAIL "}
        print("\n=== {} ===".format(self.skill))
        for level, code, msg in self.rows:
            print("  [{}] {}: {}".format(icon[level], code, msg))


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_frontmatter(text):
    """Return the raw YAML frontmatter block, or None."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    return m.group(1) if m else None


def yaml_scalar(block, key):
    """Grab a top-level scalar value for `key` from a simple YAML block.

    Handles `key: value` and block scalars (`key: >-` / `|`) well enough for
    frontmatter linting (we only need presence + the name string).
    """
    m = re.search(r"^{}\s*:\s*(.*)$".format(re.escape(key)), block, re.MULTILINE)
    if not m:
        return None
    val = m.group(1).strip()
    if val in (">", ">-", "|", "|-", ""):
        # Block scalar: collect following indented lines.
        lines = block.splitlines()
        idx = next(i for i, ln in enumerate(lines) if re.match(
            r"^{}\s*:".format(re.escape(key)), ln))
        collected = []
        for ln in lines[idx + 1:]:
            if ln.strip() == "" or ln.startswith((" ", "\t")):
                collected.append(ln.strip())
            else:
                break
        return " ".join(x for x in collected if x).strip()
    return val.strip("'\"")


def iter_files(skill_dir, exts):
    for root, _dirs, files in os.walk(skill_dir):
        for fn in files:
            if os.path.splitext(fn)[1] in exts:
                yield os.path.join(root, fn)


def check_skill(skill_dir):
    rep = Report(os.path.basename(os.path.abspath(skill_dir)))
    name = rep.skill

    # C1 — SKILL.md exists.
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        rep.add(FAIL, "C1", "SKILL.md missing")
        return rep
    text = read(skill_md)

    # C2 — frontmatter block.
    block = parse_frontmatter(text)
    if block is None:
        rep.add(FAIL, "C2", "no YAML frontmatter (--- ... ---) at top of SKILL.md")
        return rep
    rep.add(OK, "C2", "frontmatter present")

    # C3 — name matches directory.
    fm_name = yaml_scalar(block, "name")
    if not fm_name:
        rep.add(FAIL, "C3", "frontmatter has no `name:`")
    elif fm_name != name:
        rep.add(FAIL, "C3", "name '{}' != directory '{}'".format(fm_name, name))
    else:
        rep.add(OK, "C3", "name matches directory")

    # C4 — description present + descriptive enough for keyword matching.
    desc = yaml_scalar(block, "description")
    if not desc:
        rep.add(FAIL, "C4", "frontmatter has no `description:`")
    elif len(desc) < 40:
        rep.add(WARN, "C4", "description is short ({} chars); agents match on "
                            "it, so name the triggers/keywords".format(len(desc)))
    else:
        rep.add(OK, "C4", "description present ({} chars)".format(len(desc)))

    # C5 — no CRLF in shell scripts (breaks setup.sh on Unix).
    crlf_bad = []
    for p in iter_files(skill_dir, {".sh"}):
        with open(p, "rb") as f:
            if b"\r\n" in f.read():
                crlf_bad.append(os.path.relpath(p, skill_dir))
    if crlf_bad:
        rep.add(FAIL, "C5", "CRLF line endings in shell script(s): {} — enforce "
                            "LF (see .gitattributes)".format(", ".join(crlf_bad)))
    else:
        rep.add(OK, "C5", "shell scripts use LF")

    # C6 — self-bootstrap. If the skill ships runnable scripts it must ship a
    # setup for both OSes, OR clearly delegate to a sibling kit's setup.
    scripts = list(iter_files(skill_dir, {".py", ".mjs", ".js"}))
    has_sh = os.path.isfile(os.path.join(skill_dir, "setup.sh"))
    has_ps1 = os.path.isfile(os.path.join(skill_dir, "setup.ps1"))
    delegates = bool(re.search(r"setup\.(sh|ps1)", text)) or "bootstrap" in text.lower()
    if not scripts:
        rep.add(OK, "C6", "no bundled scripts (recipe/guide skill)")
    elif has_sh and has_ps1:
        rep.add(OK, "C6", "ships setup.sh + setup.ps1")
    elif (has_sh or has_ps1):
        rep.add(WARN, "C6", "ships only one of setup.sh/setup.ps1; add the other "
                            "for cross-platform bootstrap")
    elif delegates:
        rep.add(OK, "C6", "no setup of its own but SKILL.md points to a bootstrap")
    else:
        rep.add(FAIL, "C6", "bundles scripts but has no setup.sh/setup.ps1 and "
                            "SKILL.md never mentions bootstrapping")

    # C7 — setup scripts self-locate (so `bash setup.sh` works from anywhere).
    if has_sh:
        s = read(os.path.join(skill_dir, "setup.sh"))
        if 'dirname "$0"' not in s and "dirname $0" not in s:
            rep.add(WARN, "C7", "setup.sh does not cd to its own dir "
                                '(cd "$(dirname "$0")")')
    if has_ps1:
        s = read(os.path.join(skill_dir, "setup.ps1"))
        if "$PSScriptRoot" not in s:
            rep.add(WARN, "C7", "setup.ps1 does not Set-Location $PSScriptRoot")

    # C8 — no hardcoded machine-local paths.
    hits = []
    for p in [skill_md] + scripts + list(iter_files(skill_dir, {".mjs", ".js"})):
        body = read(p)
        for needle in BAD_PATH_NEEDLES:
            if needle in body:
                hits.append("{} contains '{}'".format(
                    os.path.relpath(p, skill_dir), needle))
    if hits:
        rep.add(FAIL, "C8", "hardcoded local path(s): " + "; ".join(sorted(set(hits))))
    else:
        rep.add(OK, "C8", "no hardcoded local paths")

    # C9 — declared Python deps. Third-party imports should appear in
    # requirements.txt so setup can install them.
    reqs = ""
    reqs_path = os.path.join(skill_dir, "requirements.txt")
    if os.path.isfile(reqs_path):
        reqs = read(reqs_path).lower()
    missing = set()
    for p in iter_files(skill_dir, {".py"}):
        body = read(p)
        for mod, pkg in THIRD_PARTY_HINTS.items():
            if re.search(r"^\s*(import|from)\s+{}\b".format(re.escape(mod)),
                         body, re.MULTILINE):
                if pkg.lower() not in reqs:
                    missing.add(pkg)
    if missing:
        rep.add(WARN, "C9", "third-party import(s) not in requirements.txt: {} "
                            "(a no-base agent won't have them)".format(
                                ", ".join(sorted(missing))))
    elif reqs.strip():
        rep.add(OK, "C9", "declared deps present")

    return rep


def find_skills(path):
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        return [path]
    found = []
    for entry in sorted(os.listdir(path)):
        d = os.path.join(path, entry)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "SKILL.md")):
            found.append(d)
    return found


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    target = argv[1]
    if not os.path.exists(target):
        print("no such path: {}".format(target))
        return 2
    skills = find_skills(target)
    if not skills:
        print("no SKILL.md found under: {}".format(target))
        return 2

    reports = [check_skill(s) for s in skills]
    for r in reports:
        r.render()

    failed = [r.skill for r in reports if r.failed]
    warned = sum(1 for r in reports for row in r.rows if row[0] == WARN)
    print("\n--- summary: {} skill(s), {} failing, {} warning(s) ---".format(
        len(reports), len(failed), warned))
    if failed:
        print("FAIL: " + ", ".join(failed))
        return 1
    print("all skills pass portability checks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
