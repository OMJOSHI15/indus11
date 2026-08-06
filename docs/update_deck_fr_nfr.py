"""
Add a Functional Requirements slide, a Non-Functional Requirements slide, and
the six SRS diagrams (docs/diagrams/final-*.png) to the review deck.

Run once against the 16-slide deck left by update_deck_progress.py and
patch_outline.py. Re-running would insert everything a second time.

    python docs/update_deck_fr_nfr.py
"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.join(HERE, "Indus11-Review2.pptx")
DIAGRAMS = os.path.join(HERE, "diagrams")

FONT = "Cambria"
NAVY = RGBColor(0x00, 0x20, 0x60)
INK = RGBColor(0x22, 0x28, 0x33)
MUTE = RGBColor(0x55, 0x5B, 0x66)
TEAL = RGBColor(0x02, 0x80, 0x90)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation(DECK)
slides = prs.slides
assert len(slides) == 16, f"expected the 16-slide deck, found {len(slides)} — already updated?"


def ph(slide, idx):
    for p in slide.placeholders:
        if p.placeholder_format.idx == idx:
            return p
    return None


def set_title(slide, text, size=28):
    p = ph(slide, 0)
    tf = p.text_frame
    tf.clear()
    r = tf.paragraphs[0].add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(size), True, FONT, NAVY


def move_last_slide_to(position):
    xml_slides = slides._sldIdLst
    ids = list(xml_slides)
    last = ids[-1]
    xml_slides.remove(last)
    xml_slides.insert(position, last)


def add_table(slide, left, top, width, height, headers, rows, size=10.5, id_col=None):
    t = slide.shapes.add_table(1 + len(rows), len(headers), left, top, width, height).table
    for ci, h in enumerate(headers):
        cell = t.cell(0, ci)
        cell.text = ""
        cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
        run = cell.text_frame.paragraphs[0].add_run()
        run.text = h
        run.font.size, run.font.bold, run.font.name, run.font.color.rgb = \
            Pt(size), True, FONT, WHITE
    for ri, row in enumerate(rows, start=1):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.text = ""
            run = cell.text_frame.paragraphs[0].add_run()
            run.text = str(val)
            run.font.size, run.font.name, run.font.color.rgb = Pt(size), FONT, INK
            run.font.bold = (id_col is not None and ci == id_col)
    return t


def add_textbox(slide, left, top, width, height, lines):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame; tf.word_wrap = True
    first = True
    for text, size, bold, colour, after in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(after)
        run = p.add_run(); run.text = text
        run.font.size, run.font.bold, run.font.name, run.font.color.rgb = \
            Pt(size), bold, FONT, colour
    return tb


# ─────────────────── slide — functional requirements ───────────────────
fr = slides.add_slide(prs.slide_layouts[5])        # "Title Only"
set_title(fr, "Functional Requirements", 28)
add_textbox(fr, Inches(0.55), Inches(1.35), Inches(12.2), Inches(0.4), [
    ("28 requirements across two tables, each traceable to the module that "
     "implements it (SRS Chapter 3, Tables 3.1-3.2) — a representative selection:",
     13, False, MUTE, 0),
])
FR_ROWS = [
    ("FR-1", "Accept a transaction over HTTP POST with sender, receiver, amount and context fields", "routes/transactions"),
    ("FR-5", "Score 0-40 on blacklist, velocity, amount-anomaly, merchant and risk-tier rules", "services/rule_engine"),
    ("FR-7", "Score 0-30 by detecting shared devices, circular flows and fee-skimming chains", "services/graph_analyzer"),
    ("FR-9", "Score 0-30 via RAG retrieval and an LLM explanation, degrading to 0 if unreachable", "services/rag_pipeline"),
    ("FR-10", "Execute the three scoring layers concurrently", "routes/transactions"),
    ("FR-12", "Map the composite score to APPROVE, REVIEW or BLOCK", "services/decision_engine"),
    ("FR-17", "Allow an analyst to override a decision", "routes/transactions"),
    ("FR-20", "Propagate fraud labels to accounts within two hops", "services/graph_analyzer"),
    ("FR-23", "Replay a labelled dataset and report precision, recall, F1 and ring detection", "scripts/evaluate"),
    ("FR-28", "Display metrics, decision mix, accuracy and flagged transactions on the dashboard", "dashboard"),
]
add_table(fr, Inches(0.55), Inches(1.8), Inches(12.2), Inches(4.5),
          ["ID", "Requirement", "Module"], FR_ROWS, size=11, id_col=0)
add_textbox(fr, Inches(0.55), Inches(6.55), Inches(12.2), Inches(0.4), [
    ("Full list: SRS §3.1, Tables 3.1 (FR-1 to FR-17) and 3.2 (FR-18 to FR-28).",
     11, True, MUTE, 0),
])
move_last_slide_to(4)      # right after "Problem Statement & Objectives" (index 3)


# ─────────────────── slide — non-functional requirements ───────────────────
nfr = slides.add_slide(prs.slide_layouts[3])       # "Two Content"
set_title(nfr, "Non-Functional Requirements", 28)
left, right = sorted(
    [p for p in nfr.placeholders if p.placeholder_format.idx in (1, 2)],
    key=lambda p: p.left,
)


def set_bullets(placeholder, items, base=14):
    tf = placeholder.text_frame
    tf.clear()
    tf.word_wrap = True
    first = True
    for it in items:
        text = it[0]
        lvl = it[1] if len(it) > 1 else 0
        bold = it[2] if len(it) > 2 else False
        colour = it[3] if len(it) > 3 else (NAVY if bold and lvl == 0 else INK)
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = lvl
        p.space_after = Pt(4 if lvl else 6)
        r = p.add_run()
        r.text = text
        r.font.name = FONT
        r.font.size = Pt(base if lvl == 0 else base - 1.5)
        r.font.bold = bold
        r.font.color.rgb = colour


set_bullets(left, [
    ("Measured performance", 0, True, NAVY),
    ("Rule engine: 8 ms  ·  Graph analyzer: 48 ms warm", 1),
    ("Complete pipeline: 14,046 ms (13.9 s in the language model)", 1),
    ("Deterministic layers complete within 500 ms; latency is bounded by "
     "the slowest layer, not the sum", 1),
    ("Reliability & maintainability", 0, True, TEAL),
    ("No state held between requests; an instance restarts without loss", 1),
    ("An unavailable component never approves a transaction silently", 1),
    ("Every decision persisted with its explanation for audit", 1),
    ("Testability & portability", 0, True, GREEN),
    ("Automated tests run with no database or network access", 1),
    ("The entire stack starts with one command via Docker Compose", 1),
])
set_bullets(right, [
    ("Software quality attributes (SRS Table 3.4)", 0, True, NAVY),
    ("Reliability — pipeline degrades one component at a time; a duplicate "
     "submission returns a defined conflict response", 1),
    ("Maintainability — each layer is one function, one input, one output "
     "type; replaceable independently", 1),
    ("Testability — 27 automated tests, no database or network", 1),
    ("Portability — the whole stack is one container composition file", 1),
    ("Usability — every decision is accompanied by a written explanation", 1),
    ("Accuracy — 93.8% precision, 86.5% recall, F1 0.90 over 208 "
     "transactions (see the Detection Accuracy slide)", 1),
])
move_last_slide_to(5)      # right after the new FR slide (index 4)


# ─────────────────── six slides — SRS diagrams ───────────────────
DIAGRAM_SLIDES = [
    ("final-architecture.png", "System Architecture — Five-Layer Pipeline"),
    ("final-dfd0.png", "Data Flow Diagram — Level 0 (Context Diagram)"),
    ("final-dfd1.png", "Data Flow Diagram — Level 1"),
    ("final-usecase.png", "Use Case Diagram"),
    ("final-activity.png", "Activity Diagram — Transaction Analysis Workflow"),
    ("final-class.png", "Class Diagram — Core Domain and Service Classes"),
]

SLIDE_W, SLIDE_H = prs.slide_width, prs.slide_height
MAX_W = SLIDE_W - Inches(1.0)
MAX_H = SLIDE_H - Inches(1.6)

insert_at = 8   # right after DFD/Process-Flow (index 7), before Literature Review
for filename, title in DIAGRAM_SLIDES:
    path = os.path.join(DIAGRAMS, filename)
    with Image.open(path) as im:
        w_px, h_px = im.size
    ratio = h_px / w_px
    width = MAX_W
    height = int(width * ratio)
    if height > MAX_H:
        height = MAX_H
        width = int(height / ratio)
    left = (SLIDE_W - width) // 2
    top = Inches(1.35) + (MAX_H - height) // 2

    ds = slides.add_slide(prs.slide_layouts[5])    # "Title Only"
    set_title(ds, title, 24)
    ds.shapes.add_picture(path, left, top, width=width, height=height)
    move_last_slide_to(insert_at)
    insert_at += 1


prs.save(DECK)
print(f"Updated {DECK} — {len(slides._sldIdLst)} slides")
