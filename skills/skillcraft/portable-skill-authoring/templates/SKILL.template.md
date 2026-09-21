---
name: my-skill
description: >-
  One or two sentences an agent will keyword-match on. Say WHAT it does and
  WHEN to use it, and include the terms a user would type — both English and
  the target language (e.g. 한글 문서, .hwpx). End with a portability note:
  "Works for a plain agent with no other skills or plugins installed."
---

# my-skill

One-paragraph statement of what this skill produces and why it edits/does it
this way (the constraint that shaped the approach).

## When to use

- Bullet the concrete situations that should trigger this skill.

## Setup (self-bootstrap)

From this skill directory, run once:

```bash
bash setup.sh          # macOS/Linux
# or
pwsh setup.ps1         # Windows PowerShell
```

State the minimum runtime (e.g. "Python 3.9+") and which deps are optional.

## Usage

1. Numbered, copy-pasteable steps. Show the exact command(s).
2. Reference example inputs shipped under `examples/`.

## Files

| File | Purpose |
|------|---------|
| `scripts/...` | ... |

## Gotchas this skill already handles

Number the mistakes that silently break the output, so a future author does
not reintroduce them.

## Notes / limits

What is explicitly out of scope.
