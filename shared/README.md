# shared — common layer

Cross-skill, cross-format logic lives here, abstracted once. As more document
types are added, the same mechanical work (OPC/ZIP container pack·unpack, XML
helpers, unit/color conversion, verification harnesses) is maintained in **one
place (DRY)** instead of being re-implemented in every skill.

## What belongs here

- Low-level / format-agnostic utilities **shared by two or more skills** (or
  document formats).
- Examples: handling an OPC (ZIP) container, safe XML assembly, unit/color
  conversion, a roundtrip verification skeleton.

## What does **not** belong here

- Logic meaningful only to one document or one skill → keep it in that skill's
  folder (`skills/<name>/`).
- Promote code here only when a **second** consumer actually appears; avoid
  premature abstraction.

## How a skill uses it (no hardcoded paths)

Each skill copies `skills/portable-skill-authoring/templates/repo_root.py` into
its own `scripts/`, then walks up to the repo root and adds `shared/` to
`sys.path`:

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from repo_root import shared_path
sys.path.insert(0, shared_path(__file__))
import opc            # imports <repo>/shared/opc.py
```

This works wherever the repo is cloned, which makes the **repo as a whole** —
not any single folder — the self-contained, self-bootstrapping unit.

## Bootstrap

Put shared Python dependencies in this folder's `requirements.txt` (once one
exists) and have each skill's `setup` script install it too (e.g.
`pip install -r ../../shared/requirements.txt`). For now, prefer utilities that
use only the standard library.
