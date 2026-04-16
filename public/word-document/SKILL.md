---
name: word-document
description: Create Word (.docx) documents programmatically using python-docx. Use this skill when asked to "create a Word document", "make a .docx", "write a Word doc", "generate a document", "format as a Word document", or "save as docx". Triggers on any request to produce a .docx file with formatted content (headings, bullets, tables, body text).
---

<!-- Tested 2026-04-16: `python3 skills/public/word-document/scripts/make_doc.py demo --output /tmp/word-skill-test-v2.docx` succeeded. All features including branded title/subtitle/section-header/subheader/divider confirmed working with python-docx 1.2.0 in work-meetings/.venv. -->

# Word Document Skill

Create `.docx` files programmatically. The module at `scripts/make_doc.py` handles all python-docx boilerplate: font patching, margins, paragraph spacing, bullets, tables, and branded color formatting.

## Quick Start

Import and use the module directly from Python (preferred):

```python
import sys
sys.path.insert(0, "/home/songlian/.openclaw/workspace/skills/public/word-document/scripts")
from make_doc import (
    new_doc, save_doc,
    add_title, add_subtitle, add_divider,
    add_section_header, add_subheader,
    add_heading, add_paragraph, add_bullet, add_table, add_page_break,
    COLOR_WALMART_BLUE, COLOR_GREEN,
)

doc = new_doc("/tmp/output.docx")
add_title(doc, "My Document")
add_subtitle(doc, "April 2026")
add_divider(doc)
add_section_header(doc, "Overview")
add_heading(doc, "Background", level=1)
add_paragraph(doc, "Some body text here.")
add_bullet(doc, "First bullet point")
add_bullet(doc, "Indented sub-bullet", level=1)
add_table(doc, headers=["Name", "Value"], rows=[["Foo", "Bar"], ["Baz", "Qux"]])
add_page_break(doc)
add_heading(doc, "Page 2", level=1)
path = save_doc(doc, "/tmp/output.docx")
print("Saved:", path)
```

Or call via CLI for quick testing:

```bash
/home/songlian/.openclaw/workspace/work-meetings/.venv/bin/python3 \
    skills/public/word-document/scripts/make_doc.py demo \
    --output /tmp/word-skill-test-v2.docx
```

---

## Default Formatting

| Setting | Default | Override via |
|---------|---------|-------------|
| Font | Everyday Sans | `font_name=` in `new_doc()` |
| Font size | 10 pt | `font_size_pt=` in `new_doc()` |
| Margins (all sides) | 0.5" (narrow) | `margin_inches=` in `new_doc()` |

---

## Color Constants

Defined at module top for consistent branded use:

```python
COLOR_WALMART_BLUE = "003594"   # primary headers (default for section_header, subheader, title)
COLOR_HEADING_1    = "365F91"   # Heading 1 style
COLOR_HEADING_2    = "4F81BD"   # Heading 2 and 3 styles
COLOR_GRAY         = "646464"   # subtitles
COLOR_GREEN        = "146E37"   # accent / callout
COLOR_DIVIDER      = "C8C8C8"   # divider line
```

Pass any constant (or a raw 6-char hex string) to the `color=` parameter of `add_section_header()` and `add_subheader()`.

---

## Full Module API

### `new_doc(output_path, title=None, font_name="Everyday Sans", font_size_pt=10.0, margin_inches=0.5) -> Document`

Create a new Document with margins and styles configured. Sets up Normal style and Heading 1–3 styles with branded colors/sizes/spacing so `add_heading()` picks them up automatically. Optionally adds a title at the top via `add_title()`.

```python
doc = new_doc("/tmp/report.docx")
# or with a quick title:
doc = new_doc("/tmp/report.docx", title="Q2 Report")
```

### `add_title(doc, text) -> None`

Add a document title: 15pt bold `#003594`. `space_after=2pt`.

```python
add_title(doc, "Quarterly Business Review")
```

### `add_subtitle(doc, text) -> None`

Add a subtitle line: 10pt `#646464`. `space_after=8pt`.

```python
add_subtitle(doc, "April 2026 · Finance Team")
```

### `add_section_header(doc, text, color=COLOR_WALMART_BLUE) -> None`

Add an ALL-CAPS bold section header. 12pt, `#003594` by default. `space_before=10pt`, `space_after=3pt`. Text is uppercased automatically.

```python
add_section_header(doc, "Key Findings")           # → "KEY FINDINGS" in Walmart blue
add_section_header(doc, "Risks", color=COLOR_GREEN)
```

### `add_subheader(doc, text, color=COLOR_WALMART_BLUE) -> None`

Add a bold sub-section header. Inherits default font size (10pt), `#003594` by default. `space_before=5pt`, `space_after=2pt`.

```python
add_subheader(doc, "Revenue Breakdown")
add_subheader(doc, "Note:", color=COLOR_GREEN)
```

### `add_divider(doc) -> None`

Add a decorative horizontal divider: a row of em dashes (──────────) in 7pt `#C8C8C8`. `space_before=3pt`, `space_after=3pt`.

```python
add_divider(doc)
```

### `add_heading(doc, text, level=1) -> None`

Add a heading paragraph using the Word Heading style (configured by `new_doc()`).
- Level 1: 14pt `#365F91`, `space_before=24pt`
- Level 2: 13pt `#4F81BD`, `space_before=10pt`
- Level 3: 10pt `#4F81BD`, `space_before=10pt`

```python
add_heading(doc, "Main Section", level=1)
add_heading(doc, "Subsection", level=2)
add_heading(doc, "Minor Point", level=3)
```

### `add_paragraph(doc, text, bold=False, italic=False) -> None`

Add a body paragraph with default font applied.

```python
add_paragraph(doc, "Normal text.")
add_paragraph(doc, "Key insight.", bold=True)
add_paragraph(doc, "Attribution note.", italic=True)
```

### `add_bullet(doc, text, level=0) -> None`

Add a bullet list item. `space_before=1pt`, `space_after=1pt` (tight).
- `level=0`: top-level bullet (List Bullet style)
- `level=1`: indented sub-bullet (List Bullet 2 style)

```python
add_bullet(doc, "Top-level item")
add_bullet(doc, "Sub-item under it", level=1)
```

### `add_table(doc, headers, rows) -> None`

Add a table with a bold header row and data rows.

```python
add_table(
    doc,
    headers=["Owner", "Task", "Due"],
    rows=[
        ["Alice", "Write spec", "Friday"],
        ["Bob",   "Review PR",  "Monday"],
    ],
)
```

### `add_page_break(doc) -> None`

Insert a page break.

```python
add_page_break(doc)
```

### `save_doc(doc, output_path) -> str`

Save the document and return the absolute path.

```python
path = save_doc(doc, "/tmp/report.docx")
# Returns: "/tmp/report.docx" (absolute)
```

---

## Dependency

python-docx must be installed. It is available in the workspace venv:

```
/home/songlian/.openclaw/workspace/work-meetings/.venv
```

Use that interpreter when running scripts directly:

```bash
/home/songlian/.openclaw/workspace/work-meetings/.venv/bin/python3 \
    scripts/make_doc.py demo --output /tmp/test.docx
```

Or install in the current environment:

```bash
pip install python-docx
```

---

## References

- [`references/python-docx-reference.md`](references/python-docx-reference.md) — How default fonts work, margins, heading styles, bullet styles, table styling, and the rFonts XML gotcha
