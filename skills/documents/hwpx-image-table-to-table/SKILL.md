---
name: hwpx-image-table-to-table
description: >-
  Convert tables that are embedded as images inside a Hangul .hwpx document
  into real, editable native tables. Use when a .hwpx / HWPX / 한글 문서 has a
  table pasted as a picture (bmp/png screenshot) that must become a selectable,
  editable table — optionally pulling the cell data from an accompanying .xlsx.
  Works for a plain agent with no other skills or plugins.
---

# hwpx-image-table-to-table

Recipe for turning **picture-of-a-table** content in a `.hwpx` into **native
editable tables**. It relies on the sibling **`hwpx-table-kit`** skill for the
actual OWPML generation; this skill is the human-facing procedure and the data
sleuthing around it.

## When to use

A `.hwpx` opens fine but its "tables" are actually flat images (`BinData/*.bmp`
or `*.png`) — you can't click into cells. Goal: identical-looking real tables.

## Procedure

### 1. Bootstrap the kit

Run `hwpx-table-kit`'s `setup.sh` / `setup.ps1` once (installs Pillow, openpyxl,
and optionally kordoc). These two skills are meant to live side by side in the
same repo.

### 2. Find the image tables

Unpack the document and look at `Contents/section0.xml` — image tables appear as
`<hp:pic>` runs referencing `BinData/imageN.bmp`. Note their order and any
`<hp:t>` text paragraphs between them (headings, captions) so you can preserve
them.

```bash
python hwpx-table-kit/scripts/hwpx_pack.py unpack IN.hwpx ./unpacked
```

### 3. Recover the table data

Convert each embedded image to PNG and **read it visually** (you, the agent, can
see images):

```python
from PIL import Image
Image.open("unpacked/BinData/image1.bmp").save("t1.png")
```

Then transcribe each table's header + rows.

**If an `.xlsx` with the same data exists, cross-check it — but trust the image
for exact text.** Excel stores a cell like `100%` as the number `1.0`, so a
naive xlsx read shows `1` where the image shows `100%`. Use `openpyxl` to read
the xlsx, but reconcile every ambiguous cell against the image. Watch for
columns that were **cropped** in a screenshot but present in the xlsx (recover
them from the xlsx).

### 4. Build the spec

Assemble a `tables.json` in the shape `hwpx-table-kit` expects (see its
`examples/tables.example.json`): one object per table with `heading` (any text
that sat above the image), `header`, `rows`, optional `boldCols` and `widths`.
Column widths should sum to the page text width (~42520 HWPUNIT for A4 portrait).

### 5. Generate + verify

```bash
python hwpx-table-kit/scripts/inject_tables.py \
    --base IN.hwpx --tables tables.json --out OUT.hwpx
node   hwpx-table-kit/scripts/verify_hwpx.mjs OUT.hwpx
```

The verify step prints every recovered table as Markdown — diff it against your
transcription to catch typos.

### 6. Hand off

You cannot run Hangul. **Ask the user to open `OUT.hwpx` and confirm** the tables
look right (borders, header shading, spacing). Iterate on `style` / `widths` /
`boldCols` in `tables.json` and re-run — no need to re-transcribe.

## Tips

- Keep the original file untouched; write a new `*_변환.hwpx`.
- Preserve heading text that was baked into the image (it disappears with the
  image otherwise) by putting it in each table's `heading`.
- If the user later says "spacing too wide" → that's `JUSTIFY`; the kit already
  forces LEFT. "add vertical lines" / "basic grid" / "shade the header" are all
  `style` tweaks in `tables.json`.
