---
name: skill-repair
description: >-
  Diagnose and fix problems that appear when following one of this repo's
  document skills — the steps fail, the environment won't bootstrap, or the
  output is wrong or corrupt (a .hwpx that won't open, a broken table, wrong
  data). Use when "I did what the skill said but it broke / 스킬대로 했는데 안
  돼 / 표가 깨졌어요 / 파일이 안 열려요": it unblocks the user's task with a
  minimal fix, then folds the durable fix back into the skill via a PR. Ships a
  stdlib-only OPC/ZIP container doctor.
---

# skill-repair

When another skill in this repo is followed and something still goes wrong,
this skill is the **recovery procedure**: reproduce and localize the failure,
get the user's immediate task unblocked with the *smallest* fix, then turn that
fix into a durable improvement to the offending skill (or `shared/`) and publish
it as a PR. It works on top of the other skills, so bootstrapping is delegated
to whichever skill you are repairing.

## When to use

- A skill's steps error out, or its `setup` won't bootstrap on this machine.
- The output is structurally broken (e.g. a `.hwpx` Hangul refuses to open).
- The output opens but is wrong (missing rows, wrong values, bad styling).
- You want to capture a one-off workaround as a permanent fix + a new "gotcha".

## Principles

- **Never damage the user's input.** Work on copies; keep the original file
  untouched. Write results to a new name (e.g. `*_fixed.hwpx`).
- **Reproduce before you fix.** A fix you can't trigger on demand is a guess.
- **Smallest fix that unblocks first, durable fix second.** Deliver the user's
  result, *then* harden the skill.
- **Feed every fix back.** A silent local workaround helps one user once;
  a skill/`shared/` patch + a numbered gotcha helps everyone. Publish per
  [`portable-skill-authoring`](../portable-skill-authoring/SKILL.md).

## Procedure

1. **Capture the failure.** Record the exact command, the full error (or the
   visible defect), the input, and expected-vs-actual. Note which skill and
   which step. Do not modify the user's original document.
2. **Reproduce minimally.** Bootstrap the *target* skill (run its `setup.sh` /
   `setup.ps1`) and re-run on a **copy** of the input. Trim to the smallest
   input that still fails.
3. **Localize the cause** to one of three buckets:
   - **Environment** — missing/older dependency, `python` vs `python3`, Node
     absent, or CRLF in `setup.sh`. Re-run the target skill's setup; run the
     portability linter (`portable-skill-authoring/scripts/check_skill.py`).
   - **Input** — the data was not what the skill assumed. (Classic: Excel
     stores `100%` as the number `1`; a screenshot cropped a column.) Compare
     the input against the skill's stated assumptions.
   - **Skill logic / schema** — the generated artifact is malformed. Diagnose
     it (next step).
4. **Diagnose a broken artifact.** For any OPC/ZIP document (`.hwpx`, `.docx`,
   `.xlsx`, `.pptx`):

   ```bash
   python scripts/opc_doctor.py OUT.hwpx
   ```

   It flags the corruption classics: not-a-zip / truncated, `mimetype` not
   first-and-stored, malformed XML part. Also run the target skill's own
   verifier if it has one (e.g. `hwpx-table-kit/scripts/verify_hwpx.mjs`).
5. **Unblock now.** Apply the minimal workaround and regenerate the user's
   result. Re-run the doctor/verifier. Because no skill here runs the office
   app, **ask the user to open the fixed file once and confirm** it looks right.
6. **Fix the skill durably.** Turn the workaround into a real change:
   - patch the skill, or **promote** the fix to `shared/` if it is generic;
   - add a **numbered entry to that skill's "Gotchas" section** so it can't
     recur;
   - update any affected docs.
7. **Publish as a PR.** Follow `portable-skill-authoring`: author in English,
   pass the linter, commit skill + docs together, and open a **PR** (never push
   to `main`). Only skills and repo-internal docs go to the remote — never the
   user's document, its output, or any data.

## Known failure catalog

Fast lookup for the failures already seen with these skills:

| Symptom | Cause | Fix |
|---------|-------|-----|
| `.hwpx` won't open in Hangul | `mimetype` not first / compressed on repack | repack with `mimetype` first + `ZIP_STORED` (`hwpx_pack.py` does this) |
| Word spacing far too wide in cells | cell paragraphs inherit `JUSTIFY` | force `LEFT`-aligned paraPr on cells |
| Bold not applied | `<hh:bold/>` misplaced in `charPr` | put it right after `<hh:offset/>` |
| Hangul rejects the styled file | new `borderFill`/`charPr`/`paraPr` didn't bump `itemCnt`, or reused an id | compute ids as `max(existing)+1` and bump `itemCnt` |
| Layout/margins changed | `<hp:secPr>` regenerated | reuse the original `secPr` |
| File opens but shows a broken image ref | image removed, `opf:item` left dangling | strip refs from `content.hpf` + manifests |
| `bash setup.sh` fails with `\r` errors | CRLF line endings | enforce LF (`.gitattributes` `* text=auto eol=lf`) |
| A value shows `1` instead of `100%` | Excel stores `100%` as float `1.0` | trust the image/source; reconcile via `openpyxl` |
| A column is missing vs. the image | screenshot cropped it | recover it from the accompanying `.xlsx` |

## Files

| File | Purpose |
|------|---------|
| `scripts/opc_doctor.py` | stdlib-only structural doctor for OPC/ZIP documents |

## Notes / limits

- The doctor validates the *container structure*, not the document's meaning; a
  file can pass and still look wrong — hence the human open-and-check step.
- This skill has no dependencies of its own; to reproduce a failure it uses the
  **target** skill's `setup`. If a fix turns out to be generic across skills,
  move it to `shared/` rather than copying it into each skill.
