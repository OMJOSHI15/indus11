"""
Add a progress-since-last-review slide and a per-member contributions slide to
the review deck, and extend the speaking script to match.

Run once against docs/Indus11-Review2.pptx (14 slides, accuracy slide already
inserted by update_deck.py). Re-running would insert the two slides a second
time — check the slide count first if in doubt.

    python docs/update_deck_progress.py
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
TEAL = RGBColor(0x02, 0x80, 0x90)
PURPLE = RGBColor(0x5B, 0x3A, 0x8E)
CARD = RGBColor(0xF4, 0xF6, 0xFA)
LINE = RGBColor(0xC7, 0xD0, 0xDE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation(DECK)
slides = prs.slides
assert len(slides) == 14, f"expected the 14-slide deck, found {len(slides)} — already updated?"


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
    """add_slide() always appends; relocate the sldId entry it just created.

    The slide's own XML element lives in the .pptx package's slide part, not
    in the sldIdLst — that list holds separate <p:sldId> reference elements,
    so the element to move has to come from xml_slides itself, not from
    slide._element.
    """
    xml_slides = slides._sldIdLst
    ids = list(xml_slides)
    last = ids[-1]
    xml_slides.remove(last)
    xml_slides.insert(position, last)


# ─────────────────── new slide — progress since last review ───────────────────
prog = slides.add_slide(prs.slide_layouts[3])      # "Two Content"
set_title(prog, "Progress Since the Last Review", 28)
left, right = sorted(
    [p for p in prog.placeholders if p.placeholder_format.idx in (1, 2)],
    key=lambda p: p.left,
)


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
        p.space_after = Pt(5 if lvl else 7)
        r = p.add_run()
        r.text = text
        r.font.name = FONT
        r.font.size = Pt(base if lvl == 0 else base - 2)
        r.font.bold = bold
        r.font.color.rgb = colour


set_bullets(left, [
    ("Specification", 0, True, NAVY),
    ("Front matter numbered in roman (i-ix); body restarts at 1", 1),
    ("Every reference cited in the text at its point of use, IEEE style", 1),
    ("Tables restyled — caption above, columns sized to content, "
     "none split across a page break", 1),
    ("32 functional requirements consolidated to 28 real, distinct ones", 1),
    ("Diagram set re-checked against the guide's notation comments "
     "and against the running code", 1),
])
set_bullets(right, [
    ("Product", 0, True, TEAL),
    ("Flagged-transactions table made interactive — filters, search, "
     "sortable columns", 1),
    ("Entrance and count-up motion, with an automatic reduced-motion "
     "fallback", 1),
    ("Static demo mode: the dashboard runs from a snapshot with no live "
     "backend", 1),
    ("Weekly-report generator with an automatic duplicate-reference check "
     "across weeks", 1),
])
move_last_slide_to(10)     # sits right after the accuracy slide (index 9)


# ─────────────────── new slide — team contributions ───────────────────
team = slides.add_slide(prs.slide_layouts[5])      # "Title Only"
set_title(team, "Team Contributions", 28)

MEMBERS = [
    ("Joshi Om", "24DCE052", "Platform & Documentation", NAVY, [
        "FastAPI gateway, MongoDB/Beanie schema, Redis caching and rate limiting",
        "Rule Engine — velocity, amount, blacklist, merchant, risk-tier checks",
        "Docker Compose stack for all five services",
        "SRS requirements and database design; verified every schema table "
        "against the running code",
    ]),
    ("Krish Gajera", "24DCE040", "Graph & Fraud Detection", TEAL, [
        "Neo4j schema and Cypher queries for rings, circular flow, fee-skimming",
        "Graph Analyzer — shared device/IP clustering, fraud-label propagation",
        "Synthetic fraud dataset generator — 500 accounts, 3 planted mule rings",
        "UML and DFD diagram set for the specification",
    ]),
    ("Drashti Dedaniya", "24DCE029", "AI & Dashboard", PURPLE, [
        "LangChain RAG pipeline, ChromaDB knowledge base, prompt engineering",
        "Decision Engine — score aggregation and threshold mapping",
        "React dashboard — charts, interactive table, motion, demo mode",
        "Review-2 deck and the standalone speaking script",
    ]),
]

x = 0.5
for name, sid, role, colour, items in MEMBERS:
    box = team.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Inches(x), Inches(1.5), Inches(4.05), Inches(5.3))
    box.fill.solid(); box.fill.fore_color.rgb = CARD
    box.line.color.rgb = LINE; box.shadow.inherit = False

    avatar = team.shapes.add_shape(MSO_SHAPE.OVAL,
                                   Inches(x + 1.575), Inches(1.75), Inches(0.9), Inches(0.9))
    avatar.fill.solid(); avatar.fill.fore_color.rgb = colour
    avatar.line.fill.background()
    at = avatar.text_frame
    at.margin_left = at.margin_right = at.margin_top = at.margin_bottom = 0
    ap = at.paragraphs[0]; ap.alignment = PP_ALIGN.CENTER
    ar = ap.add_run(); ar.text = "".join(w[0] for w in name.split()[:2])
    ar.font.size, ar.font.bold, ar.font.name, ar.font.color.rgb = Pt(20), True, FONT, WHITE

    tb = team.shapes.add_textbox(Inches(x + 0.25), Inches(2.75), Inches(3.55), Inches(0.9))
    tf = tb.text_frame; tf.word_wrap = True
    for i, (txt, size, bold, col) in enumerate([
            (name, 16, True, NAVY), (f"{sid}  ·  {role}", 12, True, colour)]):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = PP_ALIGN.CENTER
        para.space_after = Pt(2)
        run = para.add_run(); run.text = txt
        run.font.size, run.font.bold, run.font.name, run.font.color.rgb = \
            Pt(size), bold, FONT, col

    lb = team.shapes.add_textbox(Inches(x + 0.28), Inches(3.75), Inches(3.5), Inches(2.9))
    tf = lb.text_frame; tf.word_wrap = True
    first = True
    for item in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(8)
        run = p.add_run(); run.text = f"•  {item}"
        run.font.size, run.font.name, run.font.color.rgb = Pt(11.5), FONT, INK
    x += 4.25

move_last_slide_to(14)     # after Conclusion (index 12), before References


# ─────────────────── extend the speaking script ───────────────────
SCRIPT = [
 (1, "Title", """Good morning. We are presenting Indus11, an AI-based financial risk and
fraud decision engine. I am Joshi Om, with Krish Gajera and Drashti Dedaniya, guided by
Dr. Deven Gol. Since the last review we have moved from a working prototype to a system we
can put numbers against, and those numbers are what most of this presentation is about."""),
 (2, "Outline", """Briefly, the flow: the feedback we received and what we did about it, the
problem and objectives, the architecture and process flow, a comparison with existing
products, our implementation, then the measured accuracy results, our progress since the
last review, the challenges, the conclusion, and finally who did what."""),
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
 (11, "Progress Since the Last Review", """Since the last review, the specification has been
substantially reworked: the front matter is numbered in roman numerals and the body restarts
at one, every reference is cited in the text at the point it is used, and every table now
fits on a single page. We also went back through the requirements and cut thirty-two down to
twenty-eight, removing the ones that were really clauses of another. On the product side, the
dashboard's flagged-transactions view is now interactive — filters, search, sortable columns —
and we added a static demo mode so the interface can be shown without the backend running."""),
 (12, "Challenges & Future Work", """The hardest parts were coordinating four data stores on
one machine and keeping the language model's output consistent, which we solved with a
temperature of zero and the 30-point cap. Worth noting: the benchmark itself exposed two
real defects — a repeated transaction returned a server error instead of a conflict, and a
parsing fault silently zeroed the AI score. Both are fixed and covered by tests. Next is
resolving the block threshold, API authentication, and a fraud-ring visualisation."""),
 (13, "Conclusion", """To summarise: the system works end to end, and we can now put
measured numbers to it rather than assert that it works. The graph layer earns its place.
We are reporting the block-threshold finding openly because it changes how the system would
be deployed. And the engineering is disciplined — 27 automated tests, continuous
integration, and a one-command deployment."""),
 (14, "Team Contributions", """Quickly, on who built what. Joshi Om owns the platform — the
FastAPI gateway, the MongoDB schema, the rule engine, and the containerised deployment, and
led the specification's requirements and database design. Krish Gajera owns the graph side —
the Neo4j schema, the fraud-ring Cypher queries, and the synthetic dataset all thirty-six
ring transactions came from. Drashti Dedaniya owns the AI and the dashboard — the retrieval
pipeline, the decision engine, and everything you have seen running on screen today."""),
 (15, "References", """These are the sources we used, in IEEE format."""),
 (16, "Thank you", """Thank you. We are happy to take questions."""),
]

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
    ("How did you divide the work?",
     "Along the system's own layers: platform and rules, graph and fraud detection, AI and "
     "dashboard. Each of us owns the requirements, code and diagrams for our layer, which is "
     "also how the codebase itself is split into independent modules."),
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
    line("Approximate speaking time: 10 to 12 minutes. Timings assume a normal pace; "
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
