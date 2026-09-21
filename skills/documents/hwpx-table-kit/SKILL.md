---
name: hwpx-table-kit
description: >-
  Insert real, editable OWPML tables into an existing Hangul .hwpx document
  without corrupting it. Use when you need to add or replace tables in an
  .hwpx / HWPX / 한글 문서 programmatically, convert an image-of-a-table into
  a native table, or style table borders and header shading. Bundles
  self-contained Python scripts and a self-bootstrap setup — works for a plain
  agent with no other skills or plugins installed.
---

# hwpx-table-kit

A small, dependency-light toolkit for putting **native (editable) tables** into
a Hangul Office **`.hwpx`** file. It edits the document's XML directly instead
of regenerating the whole file, so the original page setup and design survive.

`.hwpx` is an OPC (ZIP) container of OWPML XML. Writing tables into it by hand is
error-prone; get one detail wrong and Hangul refuses to open the file. This kit
encodes the details that actually matter.

## When to use

- Add or replace tables inside an existing `.hwpx`.
- Convert a table that is embedded as an **image** into a real table
  (pair this with the `hwpx-image-table-to-table` recipe skill).
- Restyle table borders / header background.

## Setup (self-bootstrap)

From this skill directory, run once:

```bash
bash setup.sh          # macOS/Linux
# or
pwsh setup.ps1         # Windows PowerShell
```

This installs `Pillow` + `openpyxl` (Python) and `kordoc` (Node, for
verification). Generation needs only Python 3.9+. Node is optional and used
only for roundtrip verification.

## Usage

1. Write a `tables.json` describing the tables (see `examples/tables.example.json`):

   ```json
   {
     "style": { "header_fill": "#F2F2F2", "border_color": "#000000",
                "border_width": "0.12 mm", "heading_height": 1300 },
     "keepImages": false,
     "tables": [
       { "heading": "A. 제목",
         "header":  ["관리항목", "품질지표", "목표값"],
         "boldCols": [2],
         "widths":  [12000, 18000, 12520],
         "rows":    [["고객만족", "고객만족도", "90점 이상"]] }
     ]
   }
   ```

   - `heading` (optional) — a bold paragraph rendered above the table.
   - `header` — first row, rendered with header style (shaded + bold).
   - `boldCols` (optional) — 0-based body columns to bold (e.g. a target column).
   - `widths` (optional) — per-column width in HWPUNIT; omit for an even split.
     Column widths should sum to the page's text width (page width − L/R margins;
     for the common A4 portrait 1-column layout that is ~42520 HWPUNIT).
   - `keepImages` — by default embedded BinData images are removed (the usual
     goal is replacing image-tables). Set `true` to keep them.

2. Generate:

   ```bash
   python scripts/inject_tables.py --base IN.hwpx --tables tables.json --out OUT.hwpx
   ```

   The source document's body is replaced by the tables (page setup preserved).

3. Verify (optional, needs Node):

   ```bash
   node scripts/verify_hwpx.mjs OUT.hwpx
   ```

   Parses the result back with kordoc and prints the recovered tables as
   Markdown. If it reports the right table count and data, the file is a valid
   HWPX. **You cannot open Hangul from here, so always ask the user to open the
   file once and confirm the visual result.**

## Files

| File | Purpose |
|------|---------|
| `scripts/hwpx_pack.py` | unpack / repack `.hwpx` (mimetype first, stored) |
| `scripts/owpml_table.py` | build `tbl/tr/tc`, inject border/char/para styles |
| `scripts/inject_tables.py` | CLI wiring the above |
| `scripts/verify_hwpx.mjs` | kordoc roundtrip verification |
| `examples/tables.example.json` | minimal spec |

## Gotchas this kit already handles

These are the mistakes that silently corrupt an `.hwpx` or look wrong in Hangul:

1. **Repack order** — `mimetype` must be the **first** ZIP entry and **stored
   uncompressed**; everything else is deflate. Otherwise Hangul won't open it.
2. **Cell text spacing** — table-cell paragraphs must be **LEFT** aligned. The
   document default is often `JUSTIFY`, which stretches the spaces inside narrow
   cells so word spacing looks far too wide.
3. **Bold** — bold is an empty `<hh:bold/>` element placed **right after
   `<hh:offset/>`** inside a `charPr` (not an attribute).
4. **Style bookkeeping** — every new `borderFill` / `charPr` / `paraPr` must
   bump its parent `itemCnt`, and new ids must be `max(existing)+1`
   (never hardcoded). The kit computes these dynamically.
5. **Keep `<hp:secPr>`** — reuse the original section properties (page size /
   margins) rather than regenerating the document, or the layout changes.
6. **Dangling image refs** — when images are removed, strip their `opf:item`
   entries from `Contents/content.hpf` (and the manifests).

## Notes / limits

- Tables are emitted as `treatAsChar` inline blocks in a single-column body.
  Merged cells (`colspan`/`rowspan`) are not generated (parsing them is
  supported by kordoc, generating them is out of scope here).
- Default styling mirrors Hangul's plain **"일반 - 기본"** look: thin black grid
  with a light-gray shaded header row.
