"""
The shared vocabulary for building the SRS and the project report.

Both documents follow the same department template — Times New Roman, 1.5 line
spacing, 1 inch margins, chapters on new pages, figures and tables numbered per
chapter — so the code that lays them out was identical in both builders, 300
lines copied word for word. It lives here instead.

The module owns the document and the running state: the Document itself, the
chapter and figure counters, and the figure/table/contents lists the front
matter is built from. A builder imports the names, calls `use()` to say which
page-number file it reads, and then writes its own content.

    import docx_kit as kit
    from docx_kit import *

    kit.use("toc-pages.json")
    chapter("Introduction")
    para("...")
"""

import json
import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DIAGRAMS = os.path.join(HERE, "diagrams")
SHOT = os.path.join(HERE, "screenshot-dashboard.png")

with open(os.path.join(HERE, "eval-results.json")) as f:
    EVAL = json.load(f)
FLAGGED, GRAPH, COUNTS = EVAL["metrics"]["flagged"], EVAL["graph"], EVAL["counts"]
REALISTIC = EVAL["metrics"]["realistic"]
# Ring transactions on which CIRCULAR_FLOW itself fired in the 31 Aug evaluation.
# eval-results.json records only the graph score, so this was counted from the
# stored explanations of that run's 36 ring transactions. Recount after a re-run.
CYCLE_HITS = 21

FONT = "Times New Roman"
BODY, SUB, CHAP = 12, 14, 16
LINE = 1.5                # every paragraph in the document, no exceptions
INK = RGBColor(0, 0, 0)
MARGIN = 1.0               # inches; 2.54 cm on all four sides
USABLE_W = 8.5 - 2 * MARGIN
MAX_FIG_H = 7.0

figures, tables = [], []   # (label, title) for the front-matter lists
# label -> (first cell of the first row, first cell of the last row). The PDF
# driver checks both land on one page, i.e. that no table straddles a break.
table_spans = {}
contents = []              # (level, title) for the table of contents

# Page numbers for the contents, produced by a first pass over the rendered PDF
# (docs/make_srs_pdf.py). Absent on the first pass, which is why the entries are
# laid out identically either way — the pagination must not shift between passes.
# use() loads them; until then the document builds with the column blank.
TOC_PAGES = {}
_chapter = 0
_fig_n = _tbl_n = 0

doc = Document()
_normal = doc.styles["Normal"]
_normal.font.name = FONT
_normal.font.size = Pt(BODY)
_normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
_normal.paragraph_format.line_spacing = LINE
_normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
_normal.paragraph_format.space_after = Pt(0)
_normal.paragraph_format.space_before = Pt(0)

for s in doc.sections:
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(MARGIN)



def use(toc_file):
    """
    Name the page-number file for this document and load it if it exists.

    Fills the existing dict rather than rebinding the name: the builders take
    these names with `from docx_kit import *`, so a rebind here would leave
    their copy pointing at the empty dict this module started with.
    """
    TOC_PAGES.clear()
    try:
        with open(os.path.join(HERE, toc_file)) as f:
            TOC_PAGES.update(json.load(f))
    except FileNotFoundError:
        pass
    return TOC_PAGES


# Set by a builder that prints something under each chapter heading; the report
# names the member responsible, the SRS names nobody.
CHAPTER_NOTE = None


def _field(paragraph, instr):
    r = paragraph.add_run()
    for tag, attr in (("begin", None), (None, instr), ("separate", None), ("end", None)):
        if attr is not None:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = attr
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        r._r.append(el)


def _page_number_format(section, fmt, start):
    sect_pr = section._sectPr
    el = sect_pr.find(qn("w:pgNumType"))
    if el is None:
        el = OxmlElement("w:pgNumType")
        sect_pr.append(el)
    el.set(qn("w:fmt"), fmt)
    el.set(qn("w:start"), str(start))


def start_body_numbering():
    """Front matter runs i, ii, iii...; the body restarts at 1 in Arabic."""
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Inches(MARGIN)
    _page_number_format(sec, "decimal", 1)
    return sec


def page_numbers():
    _page_number_format(doc.sections[0], "lowerRoman", 1)
    # The title page carries no number, which is what a separate first-page
    # footer gives us — it is left empty.
    doc.sections[0].different_first_page_header_footer = True
    for i, s in enumerate(doc.sections):
        if i:
            s.footer.is_linked_to_previous = False
        p = s.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = LINE
        p.paragraph_format.space_after = Pt(0)
        _field(p, "PAGE")
        for r in p.runs:
            r.font.name, r.font.size = FONT, Pt(11)


def refresh_fields_on_open():
    el = OxmlElement("w:updateFields")
    el.set(qn("w:val"), "true")
    doc.settings.element.append(el)


def para(text="", size=BODY, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         after=6, italic=False, indent=0.0, spacing=LINE):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = spacing
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    if text:
        r = p.add_run(text)
        r.font.size, r.bold, r.italic, r.font.name = Pt(size), bold, italic, FONT
    return p


def new_page():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def chapter(title, numbered=True, new_page_first=True):
    """Chapter heading: own page, centred, 16 pt bold."""
    global _chapter, _fig_n, _tbl_n
    if new_page_first:      # a section break has already turned the page
        new_page()
    if numbered:
        _chapter += 1
        _fig_n = _tbl_n = 0
        text = f"CHAPTER {_chapter}: {title.upper()}"
    else:
        text = title.upper()
    p = doc.add_paragraph(style="Heading 1")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(14)
    p.paragraph_format.line_spacing = LINE
    r = p.add_run(text)
    r.font.size, r.bold, r.font.color.rgb, r.font.name = Pt(CHAP), True, INK, FONT
    contents.append((1, text))
    # The report prints the member responsible under each chapter; the SRS
    # prints nothing, so the hook is unset there.
    note = CHAPTER_NOTE(title) if (numbered and CHAPTER_NOTE) else None
    if note:
        p.paragraph_format.space_after = Pt(4)
        para(note, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)
    return p


def section(title):
    p = doc.add_paragraph(style="Heading 2")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = LINE
    p.paragraph_format.keep_with_next = True
    r = p.add_run(title)
    r.font.size, r.bold, r.font.color.rgb, r.font.name = Pt(SUB), True, INK, FONT
    contents.append((2, title))
    return p


def bullet(text, indent=0.35):
    # "List Bullet" carries the bullet glyph; "List Paragraph" is just an indent.
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(indent)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = LINE
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    r.font.size, r.font.name = Pt(BODY), FONT
    return p


def figure(png, title, max_h=MAX_FIG_H):
    """Embed a rendered diagram with a chapter-scoped caption. max_h lowers the
    height cap when a full-width figure would leave its section heading stranded
    on an otherwise empty page."""
    global _fig_n
    _fig_n += 1
    label = f"Figure {_chapter}.{_fig_n}"
    path = png if os.path.isabs(png) else os.path.join(DIAGRAMS, png)
    with Image.open(path) as im:
        w_px, h_px = im.size
    width = USABLE_W
    if width * h_px / w_px > max_h:
        width = max_h * w_px / h_px
    doc.add_picture(path, width=Inches(width))
    pic = doc.paragraphs[-1]
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.paragraph_format.space_before = Pt(6)
    pic.paragraph_format.space_after = Pt(2)
    para(f"{label}: {title}", size=11, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=10, spacing=LINE)
    figures.append((label, title))


def table(title, headers, rows, widths=None, size=10.5):
    """Caption above the table, centred bold headers, no fill, and columns sized
    to their contents so a narrow column does not hold a gap open beside it."""
    global _tbl_n
    _tbl_n += 1
    label = f"Table {_chapter}.{_tbl_n}"
    caption = para(f"{label}: {title}", size=11, bold=True,
                   align=WD_ALIGN_PARAGRAPH.CENTER, after=4, spacing=LINE)
    caption.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = LINE
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        r = p.add_run(h)
        r.bold, r.font.size, r.font.name = True, Pt(size), FONT
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.line_spacing = LINE
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            r = p.add_run(str(v))
            r.font.size, r.font.name = Pt(size), FONT
    _apply_widths(t, _column_widths(headers, rows, size))
    keep_on_one_page(t)
    para("", after=10, spacing=LINE)
    tables.append((label, title))
    if rows:
        # The longest word of each end row: a whole word survives the wrapping
        # that the PDF text extractor applies, where a whole cell may not.
        table_spans[label] = [_row_text(rows[0]), _row_text(rows[-1])]
    return t


MAX_COL = 3.1                    # inches
CELL_PADDING = 0.17              # Word's default left+right cell margins
FONT_FILES = {
    False: "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    True: "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
}
_MEASURED = 200                  # measure at a large size, then scale down
_fonts = {}


def text_width(text, size, bold=False):
    """Width of `text` in inches, measured from the font rather than guessed.

    Estimating from a character count put "IPAddress" and "Transaction" in
    columns too narrow to hold them, and Word broke the words in half.
    """
    font = _fonts.get(bold)
    if font is None:
        font = _fonts[bold] = ImageFont.truetype(FONT_FILES[bold], _MEASURED)
    return font.getlength(text) / _MEASURED * size / 72


def _column_widths(headers, rows, size):
    """Width each column by what it holds, so a column of short values takes
    only the room it needs and the column beside it starts further left.

    Word's own autofit is advisory — LibreOffice renders the columns evenly
    regardless — so the widths are computed here and written as fixed values.
    Each column's floor is its longest single word, so nothing is ever broken
    mid-word; only the slack above that floor is given up when a table is wider
    than the text column.
    """
    bounds = []
    for i, header in enumerate(headers):
        cells = [str(r[i]) for r in rows]
        words = [w for cell in cells for w in cell.split()] or [""]
        low = max([text_width(w, size) for w in words]
                  + [text_width(header, size, bold=True)]) + CELL_PADDING
        high = max([text_width(cell, size) for cell in cells] + [low - CELL_PADDING])
        bounds.append((low, min(max(high + CELL_PADDING, low), max(MAX_COL, low))))

    total = sum(high for _, high in bounds)
    if total <= USABLE_W:
        return [high for _, high in bounds]       # narrower than the page: fine
    room = sum(high - low for low, high in bounds)
    if room <= 0:                                  # nothing left to give back
        return [USABLE_W * high / total for _, high in bounds]
    over = min(total - USABLE_W, room)
    return [high - (high - low) * over / room for low, high in bounds]


def _row_text(row):
    """The first cell's first token, as a unique page-location anchor. Three
    approaches broke before this one: the longest word across the whole row
    collided when rows shared a module name; concatenating every cell broke
    because pdftotext -layout emits wrapped columns in physical reading
    order, not logical cell order, so the concatenation never matched; and
    even a whole first cell can itself wrap onto two lines when it is long
    (e.g. "velocity:<account_id> member"). A single leading token is short
    enough to never wrap on its own, and distinct enough within one table to
    tell its first row from its last."""
    return str(row[0]).split()[0] if str(row[0]).split() else str(row[0])


def keep_on_one_page(t):
    """Stop a table being split across a page boundary.

    Word has no "keep this table together" property, so the effect is built from
    the two that do exist: no row may break internally, and every row but the
    last is kept with the row after it. If a table is taller than the text area
    it must still break somewhere — the header row is marked to repeat so that
    the continuation is at least readable.
    """
    for row in t.rows:
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    for row in t.rows[:-1]:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next = True
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))


def _apply_widths(t, widths):
    t.autofit = False
    tbl_pr = t._tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout"):
        el = tbl_pr.find(qn(tag))
        if el is not None:
            tbl_pr.remove(el)
    total = OxmlElement("w:tblW")
    total.set(qn("w:w"), str(int(sum(widths) * 1440)))
    total.set(qn("w:type"), "dxa")
    tbl_pr.append(total)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    for col, width in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        col.set(qn("w:w"), str(int(width * 1440)))
    for i, width in enumerate(widths):
        for row in t.rows:
            row.cells[i].width = Inches(width)


def code_block(lines, size=9):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    cell = t.cell(0, 0)
    cell.text = ""
    for i, line in enumerate(lines.split("\n")):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = LINE
        r = p.add_run(line if line else " ")
        r.font.name, r.font.size = "Consolas", Pt(size)
    para("", after=8)


def fill_contents(anchor, front_matter):
    """Write the table of contents with dot leaders and real page numbers."""
    anchor.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anchor.paragraph_format.space_after = Pt(14)
    anchor.paragraph_format.line_spacing = LINE
    r = anchor.add_run("TABLE OF CONTENTS")
    r.bold, r.font.size, r.font.name = True, Pt(CHAP), FONT
    cursor = anchor
    entries = [(1, t) for t in front_matter] + contents
    for level, title in entries:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = LINE
        p.paragraph_format.space_after = Pt(4 if level == 1 else 2)
        p.paragraph_format.left_indent = Inches(0 if level == 1 else 0.3)
        p.paragraph_format.tab_stops.add_tab_stop(
            Inches(USABLE_W), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        run = p.add_run(f"{title}\t{TOC_PAGES.get(title, '')}")
        run.bold = level == 1
        run.font.size, run.font.name = Pt(BODY), FONT
        cursor._p.addnext(p._p)
        cursor = p


def fill(anchor, heading_text, items):
    anchor.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anchor.paragraph_format.space_after = Pt(12)
    anchor.paragraph_format.line_spacing = LINE
    r = anchor.add_run(heading_text)
    r.bold, r.font.size, r.font.name = True, Pt(CHAP), FONT
    cursor = anchor
    for label, title in items:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = LINE
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"{label}:  {title}")
        run.font.size, run.font.name = Pt(BODY), FONT
        cursor._p.addnext(p._p)
        cursor = p

