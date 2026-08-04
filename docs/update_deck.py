"""
Bring the review deck up to date with the current state of the project and
write a standalone speaking script alongside it.

Patches docs/Indus11-Review2.pptx in place: refreshes the slides whose content
has changed since the July review, inserts a measured-accuracy slide after the
implementation slides. The speaking script is written as a separate Word
document in ~/Downloads — deliberately not embedded in the deck.

    python docs/update_deck.py
"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.join(HERE, "Indus11-Review2.pptx")
SCRIPT_OUT = os.path.expanduser("~/Downloads/Indus11_Presentation_Script.docx")

FONT = "Cambria"
NAVY = RGBColor(0x00, 0x20, 0x60)
INK = RGBColor(0x22, 0x28, 0x33)
MUTE = RGBColor(0x55, 0x5B, 0x66)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
AMBER = RGBColor(0xB2, 0x6A, 0x00)
RED = RGBColor(0xC6, 0x28, 0x28)
TEAL = RGBColor(0x02, 0x80, 0x90)
CARD = RGBColor(0xF4, 0xF6, 0xFA)
LINE = RGBColor(0xC7, 0xD0, 0xDE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation(DECK)
slides = prs.slides


def ph(slide, idx):
    for p in slide.placeholders:
        if p.placeholder_format.idx == idx:
            return p
    return None


def set_bullets(placeholder, items, base=15):
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
        p.space_after = Pt(4 if lvl else 7)
        r = p.add_run()
        r.text = text
        r.font.name = FONT
        r.font.size = Pt(base if lvl == 0 else base - 2)
        r.font.bold = bold
        r.font.color.rgb = colour


def set_title(slide, text, size=28):
    p = ph(slide, 0)
    if p is None:
        return
    tf = p.text_frame
    tf.clear()
    r = tf.paragraphs[0].add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(size), True, FONT, NAVY


# ─────────────────── slide 3 — feedback and improvements ───────────────────
s3 = slides[2]
set_title(s3, "Guide Feedback & Improvements", 28)
left, right = sorted(
    [p for p in s3.placeholders if p.placeholder_format.idx in (1, 2)],
    key=lambda p: p.left,
)
set_bullets(left, [
    ("Feedback received", 0, True, NAVY),
    ("Show measured evidence, not just a working demo", 1),
    ("SRS: correct DFD notation and UML diagrams", 1),
    ("Single spacing; each chapter on a new page", 1),
    ("Conclusion, References, Definitions last, unnumbered", 1),
    ("Abstract must be written by the team", 1),
    ("Keep the repository updated for review", 1),
])
set_bullets(right, [
    ("Action taken", 0, True, GREEN),
    ("Built an evaluation harness; results in this deck", 1),
    ("DFDs redrawn in Gane-Sarson notation; 7 UML diagrams", 1),
    ("Document reformatted to the prescribed style", 1),
    ("Sections reordered as instructed", 1),
    ("Abstract being written by the team", 1),
    ("Repository public with continuous integration", 1),
])

# ─────────────────── new slide — measured accuracy ───────────────────
acc = slides.add_slide(prs.slide_layouts[5])       # "Title Only"
set_title(acc, "Detection Accuracy — Measured Results", 28)

tb = acc.shapes.add_textbox(Inches(0.55), Inches(1.42), Inches(12.2), Inches(0.4))
r = tb.text_frame.paragraphs[0].add_run()
r.text = ("208 labelled synthetic transactions — 52 fraudulent, 156 legitimate — "
          "replayed through the complete pipeline")
r.font.size, r.font.name, r.font.color.rgb = Pt(14), FONT, MUTE

x = 0.55
for value, label, sub, colour in [
        ("93.8%", "Precision", "of flagged were fraud", GREEN),
        ("86.5%", "Recall", "of fraud was caught", TEAL),
        ("0.90", "F1 score", "combined measure", NAVY),
        ("36/36", "Ring recall", "mule-ring hops detected", GREEN)]:
    box = acc.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                               Inches(x), Inches(1.95), Inches(2.95), Inches(1.55))
    box.fill.solid(); box.fill.fore_color.rgb = CARD
    box.line.color.rgb = LINE; box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_top = Inches(0.12)
    for i, (txt, size, bold, col) in enumerate([
            (value, 30, True, colour), (label, 13, True, NAVY), (sub, 10.5, False, MUTE)]):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = PP_ALIGN.CENTER
        para.space_after = Pt(1)
        run = para.add_run(); run.text = txt
        run.font.size, run.font.bold, run.font.name, run.font.color.rgb = \
            Pt(size), bold, FONT, col
    x += 3.1

rows = [["Decision", "Actually fraud", "Actually legitimate"],
        ["APPROVE", "7", "153"], ["REVIEW", "45", "3"], ["BLOCK", "0", "0"]]
tbl = acc.shapes.add_table(4, 3, Inches(0.55), Inches(3.65), Inches(6.1), Inches(1.9)).table
for ri, row in enumerate(rows):
    for ci, val in enumerate(row):
        cell = tbl.cell(ri, ci)
        cell.text = ""
        run = cell.text_frame.paragraphs[0].add_run()
        run.text = val
        run.font.size, run.font.name = Pt(12), FONT
        run.font.bold = (ri == 0)
        run.font.color.rgb = WHITE if ri == 0 else INK
        if ri == 0:
            cell.fill.solid(); cell.fill.fore_color.rgb = NAVY

fb = acc.shapes.add_textbox(Inches(7.0), Inches(3.65), Inches(5.8), Inches(2.4))
tf = fb.text_frame; tf.word_wrap = True
for i, (txt, size, bold, col) in enumerate([
        ("Key finding", 15, True, RED),
        ("No transaction reached the block threshold of 70.", 13.5, True, INK),
        ("Every detection is routed to a human analyst; nothing is blocked "
         "automatically. Lowering the band would automate blocking — but would also "
         "auto-block the three false positives. That is a policy decision, not a "
         "configuration change.", 12.5, False, MUTE)]):
    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    para.space_after = Pt(6)
    run = para.add_run(); run.text = txt
    run.font.size, run.font.bold, run.font.name, run.font.color.rgb = \
        Pt(size), bold, FONT, col

cav = acc.shapes.add_textbox(Inches(0.55), Inches(5.8), Inches(12.2), Inches(0.6))
tf = cav.text_frame; tf.word_wrap = True
run = tf.paragraphs[0].add_run()
run.text = ("Measured on synthetic data in which fraud is far denser than a real payment "
            "feed, so precision here is optimistic — it measures the separation between "
            "the engines, not production performance.")
run.font.size, run.font.italic, run.font.name, run.font.color.rgb = \
    Pt(11.5), True, FONT, MUTE

# move the new slide to sit directly after slide 9 (implementation)
xml_slides = slides._sldIdLst
ids = list(xml_slides)
xml_slides.remove(ids[-1])
xml_slides.insert(9, ids[-1])

# ─────────────────── refresh challenges / future work ───────────────────
s_chal = slides[10]
set_title(s_chal, "Challenges Faced & Future Work", 28)
left, right = sorted(
    [p for p in s_chal.placeholders if p.placeholder_format.idx in (1, 2)],
    key=lambda p: p.left,
)
set_bullets(left, [
    ("Challenges faced", 0, True, AMBER),
    ("Coordinating four data stores on one machine", 1),
    ("Keeping model output consistent — solved with a 30-point cap", 1),
    ("Writing Cypher queries for circular money-mule flows", 1),
    ("Two defects the benchmark exposed: a repeated request returned", 1),
    ("a server error, and a parsing fault silently zeroed the AI", 1),
    ("score — both fixed and covered by tests", 1),
])
set_bullets(right, [
    ("Future work", 0, True, GREEN),
    ("Resolve the block-threshold trade-off from recorded scores", 1),
    ("Add API authentication and request logging", 1),
    ("Fraud-ring visualisation on the graph endpoint", 1),
    ("Investigate the 7 undetected frauds; fan-in / fan-out patterns", 1),
    ("Train a supervised classifier as a fourth signal", 1),
    ("Reduce latency, presently dominated by the local model", 1),
])

# ─────────────────── refresh conclusion ───────────────────
s_con = slides[11]
# Compare the underlying XML elements: python-pptx hands back a new wrapper
# object on every access, so an identity check would delete the title too.
title_el = ph(s_con, 0)._element
for shape in list(s_con.shapes):
    if shape._element is not title_el and shape.has_text_frame:
        shape._element.getparent().remove(shape._element)
set_title(s_con, "Conclusion — Where the Project Stands", 28)
x = 0.5
for head, body, colour in [
        ("Measured, not asserted",
         "93.8% precision, 86.5% recall, F1 0.90 on 208 labelled transactions.", NAVY),
        ("The graph layer earns its place",
         "All 36 planted mule-ring transactions were detected.", TEAL),
        ("A finding worth reporting",
         "Nothing reaches the block threshold; every catch reaches an analyst.", RED),
        ("Engineering discipline",
         "27 automated tests, continuous integration, one-command deployment.", GREEN)]:
    box = s_con.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 Inches(x), Inches(2.0), Inches(3.0), Inches(3.1))
    box.fill.solid(); box.fill.fore_color.rgb = CARD
    box.line.color.rgb = LINE; box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = Inches(0.16); tf.margin_right = Inches(0.14)
    tf.margin_top = Inches(0.2)
    for i, (txt, size, bold, col) in enumerate([(head, 14, True, colour),
                                                (body, 12, False, INK)]):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.space_after = Pt(8)
        run = para.add_run(); run.text = txt
        run.font.size, run.font.bold, run.font.name, run.font.color.rgb = \
            Pt(size), bold, FONT, col
    x += 3.27

# ─────────────────── speaking script ───────────────────
SCRIPT = [
 (1, "Title", """Good morning. We are presenting Indus11, an AI-based financial risk and
fraud decision engine. I am Joshi Om, with Krish Gajera and Drashti Dedaniya, guided by
Dr. Deven Gol. Since the last review we have moved from a working prototype to a system we
can put numbers against, and those numbers are what most of this presentation is about."""),
 (2, "Outline", """Briefly, the flow: the feedback we received and what we did about it, the
problem and objectives, the architecture and process flow, a comparison with existing
products, our implementation, then the measured accuracy results, the challenges, and the
conclusion."""),
 (3, "Guide Feedback & Improvements", """Sir's main point last time was that we should show
measured evidence rather than a demo that appears to work. That directly drove the
evaluation harness you will see shortly. On the SRS, the data flow diagrams did not follow
standard notation, so they have been redrawn in Gane-Sarson form, and the UML set is now
seven proper diagrams. The document has been reformatted to single spacing with each
chapter on a new page, and the closing sections reordered as instructed. The abstract is
being written by us, in our own words, as required."""),
 (4, "Problem Statement & Objectives", """The problem is not that fraud systems are
inaccurate. It is that they cannot explain themselves. Most return an internal reason code
that a developer can interpret and a customer cannot. When a payment is held, both the
customer and the analyst need to know why, in plain language. Our objective was a system
that scores every transaction from 0 to 100, returns approve, review or block, and attaches
a readable reason to every decision."""),
 (5, "System Architecture", """The system is a five-layer pipeline. Layer one validates the
request and loads the account profile from cache, falling back to the document store.
Layers two, three and four score concurrently — rules, graph analysis, and a
retrieval-augmented language model. Layer five adds the scores and maps the total to a
decision. Because the three engines run concurrently, total latency is bounded by the
slowest layer rather than by their sum."""),
 (6, "Process Flow / DFD", """Walking through one transaction: it is validated, profiles are
loaded, the three engines score in parallel, the decision engine sums them and clamps the
total at 100, the bands map to approve, review or block, and the record is persisted so
every decision can be audited afterwards."""),
 (7, "Literature Review", """Commercial systems — FICO Falcon, Feedzai, Featurespace — are
accurate but proprietary and limited in explanation. Traditional rule engines explain well
but are rigid. Our position is the combination: rules and graph analysis for reliable
evidence, and a language model for the explanation, capped so it cannot dominate. The APATE
study supports combining graph features with traditional ones, reporting AUC above 0.98."""),
 (8, "Implementation — Dashboard & API", """This is the running system. The dashboard shows
live risk metrics, the decision mix, the score distribution and flagged transactions. An
analyst can open any flagged transaction, read the reason, and approve or block it. Behind
it are twelve documented REST endpoints."""),
 (9, "Implementation — Structure, Code & Stack", """The codebase separates the five layers
into independent modules, each returning the same score-and-flags type, so a layer can be
replaced without touching the others. The decision engine is the short piece of code shown
here. The stack is Python and FastAPI, MongoDB, Neo4j, Redis, ChromaDB, a local language
model through Ollama, and React. The whole stack starts with one command."""),
 (10, "Detection Accuracy", """This is the slide we most wanted to reach. We built a harness
that replays 208 labelled transactions — 52 fraudulent, 156 legitimate — through the
complete pipeline. Precision is 93.8 per cent, recall 86.5 per cent, F1 0.90. The graph
layer detected all 36 planted mule-ring transactions, which single-transaction rules cannot
find by construction.

The confusion matrix carries a finding we did not expect. The block row is empty. No
transaction scored 70 or above, so nothing is blocked automatically — all 45 detections go
to a human analyst. We could lower the threshold, but the same change would auto-block our
three false positives, so we are treating it as a policy decision that needs evidence
rather than a setting to change.

One caveat we should state ourselves: fraud is far denser in this synthetic data than in a
real payment feed, so the precision figure is optimistic. It measures how well the engines
separate the classes, not production performance."""),
 (11, "Challenges & Future Work", """The hardest parts were coordinating four data stores on
one machine and keeping the language model's output consistent, which we solved with a
temperature of zero and the 30-point cap. Worth noting: the benchmark itself exposed two
real defects — a repeated transaction returned a server error instead of a conflict, and a
parsing fault silently zeroed the AI score. Both are fixed and covered by tests. Next is
resolving the block threshold, API authentication, and a fraud-ring visualisation."""),
 (12, "Conclusion", """To summarise: the system works end to end, and we can now put
measured numbers to it rather than assert that it works. The graph layer earns its place.
We are reporting the block-threshold finding openly because it changes how the system would
be deployed. And the engineering is disciplined — 27 automated tests, continuous
integration, and a one-command deployment."""),
 (13, "References", """These are the sources we used, in IEEE format."""),
 (14, "Thank you", """Thank you. We are happy to take questions."""),
]

# The script is delivered as a separate file, not as slide notes.

QUESTIONS = [
    ("Why three engines instead of one?",
     "Each sees something the others cannot. Rules catch known patterns on a single "
     "transaction. The graph catches coordinated fraud across accounts — that is where all "
     "36 ring transactions came from. The language model supplies the explanation."),
    ("Why cap the language model at 30 points?",
     "It is the only non-deterministic component. Capping it means reliable rule and graph "
     "evidence always controls the outcome, and a model failure degrades the explanation "
     "rather than the decision."),
    ("Why does nothing get blocked?",
     "No transaction scored 70 or above on our dataset. The seeded fraud accounts have no "
     "stored profile, so the amount-anomaly rule contributes nothing and the scores land in "
     "the review band. We are deciding whether to lower the threshold."),
    ("Is 93.8 per cent precision realistic?",
     "No, and we say so on the slide. Fraud is far denser in our synthetic set than in a "
     "real feed. The figure shows the engines separate the classes well; it is not a "
     "production estimate."),
    ("What happens if a component fails?",
     "The pipeline degrades rather than failing. An unknown account is treated as elevated "
     "risk, and if the language model is unreachable the AI score is zero with a stated "
     "reason. Nothing fails towards approval."),
    ("How is this different from FICO or Feedzai?",
     "Those are accurate but proprietary and explain little. Ours is open, runs locally with "
     "no external service, and attaches a plain-language reason to every decision."),
    ("How do you know the results are reproducible?",
     "The datasets are generated from a fixed random seed and the harness is one command. "
     "Anyone can rerun it and get the same confusion matrix."),
]

def write_script_document(path):
    """Standalone speaking script — one section per slide, then likely questions."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor as DocxRGB

    d = Document()
    style = d.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.paragraph_format.line_spacing = 1.15
    style.paragraph_format.space_after = Pt(6)
    for sec in d.sections:
        sec.left_margin = sec.right_margin = Inches(1.0)
        sec.top_margin = sec.bottom_margin = Inches(1.0)

    def line(text, size=12, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT,
             after=6, colour=None, italic=False):
        p = d.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(text)
        r.font.size, r.bold, r.italic = Pt(size), bold, italic
        r.font.name = "Times New Roman"
        if colour:
            r.font.color.rgb = colour
        return p

    line("INDUS11 — PRESENTATION SCRIPT", 16, True, WD_ALIGN_PARAGRAPH.CENTER, 4)
    line("AI Financial Risk and Fraud Decision Engine", 13, False,
         WD_ALIGN_PARAGRAPH.CENTER, 4)
    line("Joshi Om (24DCE052)  ·  Krish Gajera (24DCE040)  ·  "
         "Drashti Dedaniya (24DCE029)", 11, False, WD_ALIGN_PARAGRAPH.CENTER, 16)
    line("Approximate speaking time: 9 to 11 minutes. Timings assume a normal pace; "
         "slide 10 carries the main result and deserves the most time.", 11, False,
         WD_ALIGN_PARAGRAPH.LEFT, 16, italic=True)

    for number, title, text in SCRIPT:
        line(f"SLIDE {number} — {title}", 13, True, after=4,
             colour=DocxRGB(0x00, 0x20, 0x60))
        for para_text in text.strip().split("\n\n"):
            line(" ".join(para_text.split()), 12, after=8)

    d.add_page_break()
    line("LIKELY QUESTIONS", 14, True, WD_ALIGN_PARAGRAPH.CENTER, 14,
         colour=DocxRGB(0x00, 0x20, 0x60))
    for q, a in QUESTIONS:
        line(f"Q.  {q}", 12, True, after=2)
        line(f"A.  {' '.join(a.split())}", 12, after=10)

    d.save(path)


write_script_document(SCRIPT_OUT)

prs.save(DECK)
print(f"Updated {DECK} — {len(slides._sldIdLst)} slides")
print(f"Script written to {SCRIPT_OUT}")
