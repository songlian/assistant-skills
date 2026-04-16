# python-docx Reference

Concise reference for building Word documents with python-docx (v1.2+).

---

## Installation

```bash
pip install python-docx
# Already installed in: work-meetings/.venv
```

---

## Document Basics

```python
from docx import Document
from docx.shared import Pt, Inches

doc = Document()          # new blank document
doc.save("/tmp/out.docx") # save to disk
```

---

## Page Margins

Set all four margins (narrow = 0.5"):

```python
for section in doc.sections:
    section.top_margin    = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin   = Inches(0.5)
    section.right_margin  = Inches(0.5)
```

---

## Setting the Default Paragraph Font

Sets the Normal style baseline (affects new paragraphs that don't override it):

```python
doc.styles["Normal"].font.name = "Everyday Sans"
doc.styles["Normal"].font.size = Pt(10)
```

**Gotcha:** python-docx's built-in default style uses Calibri. The Normal style change above sets the document default, but individual runs may still render in Calibri if the XML theme fonts take precedence. Always also set the font explicitly on each run (see below).

---

## Setting Font on a Run (Explicit Override)

The reliable way — sets font in both the run properties and the low-level rFonts XML element:

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def apply_font(run, name="Everyday Sans", size_pt=10.0, bold=False, italic=False):
    run.font.name = name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    # Patch theme font fallback so Word respects the font name
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rFonts.set(qn(attr), name)
    existing = rPr.find(qn("w:rFonts"))
    if existing is not None:
        rPr.remove(existing)
    rPr.insert(0, rFonts)
```

---

## Headings

Use plain paragraphs with explicit font styling (preferred over Word's Heading styles, which carry their own fonts):

```python
# H1: bold, larger
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(10)
p.paragraph_format.space_after  = Pt(3)
run = p.add_run("Section Title")
apply_font(run, size_pt=14, bold=True)

# H2: bold, slightly smaller
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(7)
run = p.add_run("Subsection")
apply_font(run, size_pt=12, bold=True)

# H3: bold, body size
p = doc.add_paragraph()
run = p.add_run("Sub-subsection")
apply_font(run, size_pt=10, bold=True)
```

Alternatively, use Word's built-in heading styles (easier but font override is still needed):

```python
p = doc.add_heading("My Heading", level=1)
# Then override fonts on all runs if needed
for run in p.runs:
    apply_font(run, size_pt=14, bold=True)
```

---

## Body Paragraphs

```python
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(1)
p.paragraph_format.space_after  = Pt(2)
run = p.add_run("Some body text.")
apply_font(run)
```

---

## Bullet Lists

Two relevant built-in styles: `"List Bullet"` (top-level) and `"List Bullet 2"` (indented).

```python
# Top-level bullet
p = doc.add_paragraph(style="List Bullet")
p.paragraph_format.left_indent  = Inches(0.2)
p.paragraph_format.space_before = Pt(1)
p.paragraph_format.space_after  = Pt(1)
run = p.add_run("Bullet item text")
apply_font(run)

# Indented sub-bullet
p = doc.add_paragraph(style="List Bullet 2")
p.paragraph_format.left_indent  = Inches(0.4)
run = p.add_run("Sub-bullet text")
apply_font(run)
```

---

## Tables

```python
table = doc.add_table(rows=1 + len(data_rows), cols=len(headers))
table.style = "Table Grid"   # adds visible borders

# Header row (row index 0)
for col_i, header in enumerate(headers):
    cell = table.cell(0, col_i)
    cell.text = ""            # clear default empty paragraph
    run = cell.paragraphs[0].add_run(header)
    apply_font(run, bold=True)

# Data rows
for row_i, row in enumerate(data_rows):
    for col_i, value in enumerate(row):
        cell = table.cell(row_i + 1, col_i)
        cell.text = ""
        run = cell.paragraphs[0].add_run(value)
        apply_font(run)
```

**Note:** `cell.text = "some text"` bypasses font control — always clear the cell with `cell.text = ""` first, then use `cell.paragraphs[0].add_run(...)`.

---

## Page Breaks

```python
doc.add_page_break()
```

---

## Paragraph Alignment

```python
from docx.enum.text import WD_ALIGN_PARAGRAPH

p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.alignment = WD_ALIGN_PARAGRAPH.LEFT    # default
p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
```

---

## Colors

```python
from docx.shared import RGBColor

run.font.color.rgb = RGBColor(0, 53, 148)   # Walmart blue
run.font.color.rgb = RGBColor(50, 50, 50)   # dark gray
```

---

## Pt to EMU Conversion

python-docx uses English Metric Units (EMU) internally. `Pt()` and `Inches()` handle conversion:

```python
Pt(10)        # 10 points → 127000 EMU
Inches(0.5)   # 0.5 inches → 457200 EMU
```

---

## Common Gotchas

| Gotcha | Fix |
|--------|-----|
| Font stays Calibri despite setting Normal style | Patch rFonts XML on every run (see apply_font above) |
| Table cell text has wrong font | Never use `cell.text = "..."` for styled content; clear then add_run |
| Margins don't apply | Iterate over `doc.sections`, not just `doc.sections[0]` |
| Bullet indentation looks wrong | Set `left_indent` explicitly on the paragraph format |
| Style name not found | Check exact name: `"List Bullet"`, `"List Bullet 2"`, `"Table Grid"` |

---

## Quick Reference: make_doc.py Module API

```python
from skills.public.word_document.scripts.make_doc import (
    new_doc, add_heading, add_paragraph,
    add_bullet, add_table, add_page_break, save_doc,
)

doc = new_doc("/tmp/out.docx", title="My Doc")
add_heading(doc, "Section 1", level=1)
add_paragraph(doc, "Body text here.")
add_bullet(doc, "First bullet")
add_bullet(doc, "Sub-bullet", level=1)
add_table(doc, headers=["Col A", "Col B"], rows=[["r1c1", "r1c2"]])
add_page_break(doc)
path = save_doc(doc, "/tmp/out.docx")
```
