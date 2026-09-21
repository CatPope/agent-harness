---
name: portable-skill-authoring
description: >-
  Author portable, self-bootstrapping Agent Skills (스킬 만들기 / 스킬 작성) for
  document work that a "no-base" agent — one with no other skills or plugins
  installed — can use from a git clone alone. Use when creating or reviewing a
  SKILL.md, packaging scripts into a skill, deciding whether to split one skill
  into several, or checking that a skill will run on a fresh machine. Ships a
  stdlib-only portability linter and starter templates.
---

# portable-skill-authoring

The rules and tooling for writing skills in this repo so that **a plain agent
with nothing installed** can clone the repo and use them. It is the "skill for
making skills." It bundles a **standard-library-only** linter
(`scripts/check_skill.py`) and copy-paste **templates**.

## When to use

- You are creating a new skill (a new `skills/<name>/SKILL.md`).
- You are splitting a job into an engine skill + a recipe skill.
- You want to verify an existing skill is still portable before committing.

## The rules (why this skill exists)

1. **No-base compatible.** Assume the agent has *no other skills and no
   plugins* — nothing beyond a `git clone` of this repo. The **repo** is the
   self-contained unit, not each folder: a skill needs only its own folder plus
   the repo's `shared/` layer, all reachable from its `SKILL.md`. Never say
   "use the X skill" unless X is a sibling in the same repo and you say so.
2. **Abstract the common layer; don't duplicate.** Logic that is generic across
   documents or reused by two or more skills (OPC/ZIP container handling, XML
   assembly, unit/color conversion, a verification harness) belongs in the
   repo-root `shared/`, not copied into each skill. Keep only the skill-specific
   logic in `skills/<name>/`. Promote code to `shared/` when the *second* user
   appears — don't abstract speculatively. Skills reach `shared/` without any
   hardcoded path by copying `templates/repo_root.py` into their `scripts/`:

   ```python
   import sys, os
   sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
   from repo_root import shared_path
   sys.path.insert(0, shared_path(__file__))
   import opc          # <repo>/shared/opc.py
   ```

3. **Self-bootstrapping from a clone.** After `git clone`, running the skill's
   `setup.sh` (or `setup.ps1`) is the *only* manual step, and it installs every
   dependency (including the shared layer's, e.g. `-r ../../shared/requirements.txt`
   when present). No hidden global state, no hardcoded machine paths, no
   pre-existing virtualenv. Prefer the standard library; when a dep is truly
   needed, pin it in `requirements.txt` / `package.json` so setup installs it.
4. **Split when it clarifies reuse.** A reusable engine (does the mechanical
   work) and a recipe (the human-facing procedure that drives the engine) are
   two skills, side by side in the repo. See `hwpx-table-kit` (engine) +
   `hwpx-image-table-to-table` (recipe). Truly format-agnostic pieces go one
   level deeper — into `shared/`.

## How to author a skill (procedure)

1. **Copy the template.** Start from `templates/SKILL.template.md`,
   `templates/setup.sh`, `templates/setup.ps1`, `templates/requirements.txt`.
   Put them under `skills/<your-name>/`.
2. **Write the frontmatter — in English.** Author every skill (its `SKILL.md`
   and all bundled files) **in English**, so any agent can consume it. `name:`
   must equal the directory name. `description:` is what the agent
   keyword-matches on — write it in English but still include the
   target-language trigger terms a user would type (e.g. `한글 문서`, `.hwpx`),
   and end with the no-base note.
3. **Reuse before you write.** Check `shared/` first — if the mechanical piece
   you need is already there, import it (copy `templates/repo_root.py` into your
   `scripts/`). If your new logic is generic enough that another format would
   want it, put it in `shared/` and import it back, rather than in the skill.
4. **Bundle scripts, declare deps.** Any third-party import goes in
   `requirements.txt` (or `shared/requirements.txt` for shared code). Keep
   scripts path-relative (`os.path.dirname(__file__)`, `cd "$(dirname "$0")"`,
   `$PSScriptRoot`) and let `repo_root.py` locate `shared/`.
5. **Ensure LF endings** for `*.sh`. Add the `templates/gitattributes.snippet`
   lines to the repo-root `.gitattributes` (CRLF breaks `bash setup.sh`).
6. **Update the docs.** Adding or changing a skill is not finished until the
   repo docs reflect it: add a row to the README skill list (and update its
   quick-start / requirements if the new skill changes them), and refresh any
   index the repo keeps (e.g. `shared/README.md` if you added a shared module).
   Keep the skill's own `SKILL.md` in sync too.
7. **Validate — this is a required gate, not optional (see below).**
8. **Only after it passes:** commit and push.

## Validate before you finish (required)

A skill is **not done until the linter passes.** Run it against your skill (or
the whole `skills/` folder) from this skill's directory:

```bash
python scripts/check_skill.py ../            # lint every skill in the repo
python scripts/check_skill.py ../my-skill    # lint just one
```

It checks, using only the Python standard library (so a no-base agent can run
it too):

| Code | Rule |
|------|------|
| C1 | `SKILL.md` exists |
| C2 | has YAML frontmatter |
| C3 | `name:` equals the directory name |
| C4 | `description:` present and long enough to match on |
| C5 | shell scripts use **LF** (no CRLF) |
| C6 | ships `setup.sh` **and** `setup.ps1` (or clearly delegates to a sibling's) |
| C7 | setup scripts self-locate (`dirname "$0"` / `$PSScriptRoot`) |
| C8 | no hardcoded machine-local paths (user home, temp) |
| C9 | third-party imports are declared in `requirements.txt` |

Exit code is non-zero if any **FAIL** is present. **Fix every FAIL before
committing.** WARNs are advisory — resolve them or note why not.

Passing the linter proves the *structure* is portable; it cannot open the
document or run the domain logic. So the final human check still applies: for
any document-producing skill, **ask the user to open the output once and
confirm** it looks right.

## Files

| File | Purpose |
|------|---------|
| `scripts/check_skill.py` | stdlib-only portability linter (the validation gate) |
| `templates/SKILL.template.md` | starting point for a new `SKILL.md` |
| `templates/setup.sh` / `setup.ps1` | cross-platform self-bootstrap scripts |
| `templates/requirements.txt` | where to pin Python deps |
| `templates/repo_root.py` | stdlib resolver a skill copies in to import `shared/` without hardcoded paths |
| `templates/gitattributes.snippet` | LF/CRLF rules to paste into repo `.gitattributes` |

## Commit / publish discipline (via PR)

Author and verify in one pass; **publish only after the gate is green.** Do not
push a half-written skill or a skill that fails the linter. A change is
"complete" only when (a) the docs are updated (step 6) and (b) the linter
reports all skills passing.

**Only two kinds of thing may ever reach the remote** (`origin`,
`github.com/CatPope/doc-skills.git`): **(1) skills** — anything under `skills/`
plus the `shared/` common layer and the scripts/templates/config they need to
run — and **(2) repo-internal docs** — files that document the repo itself
(`README.md`, `LICENSE`, each `SKILL.md`, `shared/README.md`). Nothing else is
allowed. In particular, **never commit or push**: documents the skills operate
on or their outputs (`.hwpx`, `.xlsx`, images, `*_변환.hwpx`), any user/work
data, secrets or credentials, local paths, or temp/scratch/build artifacts —
these are user data, not repo assets. `.gitignore` enforces this; before adding
a file ask "is this a skill, or a repo doc?" — if neither, it does not go up.

**Publish through a pull request — never push straight to `main`.** Once the
change is complete:

```bash
git checkout -b skill/<name>              # a topic branch, not main
git add -A && git commit -m "..."         # skill + docs together, in one commit
git push -u origin skill/<name>
gh pr create --fill                        # open the PR for review
```

Keep the skill and its doc update in the **same commit/PR** — never leave the
README describing a different set of skills than the repo ships. Merge only
after the PR's checks/review pass.

## Notes / limits

- The linter is a *portability* check, not a correctness or security review; it
  does not run the skill's own logic.
- C8/C9 use conservative heuristics (known third-party module names, common
  home/temp path fragments). Extend the tables in `check_skill.py` as the repo
  grows.
