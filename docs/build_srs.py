"""
Build the Indus11 SRS document.

Structure and formatting follow the department template and the internal
guide's review comments:

  - running text at 1.5 line spacing and justified (latest review); tables stay
    at single spacing, since a 32-row requirements table at 1.5 is unreadable
  - no stray space before/after paragraphs
  - only chapters start on a new page; chapter titles centred at 16 pt
  - figures numbered per chapter (Figure 4.1, 5.3, ...), no repeated titles
  - every store is given its own data-dictionary table
  - Conclusion, References and Definitions appear last, unnumbered
  - References begin on their own page
  - diagrams rendered by PlantUML/Graphviz in the document's own typeface, and
    kept small enough in content that none of their text falls below roughly
    8 pt once scaled to the page

Regenerate the diagrams first if they changed:

    plantuml -tpng docs/diagrams/*.puml
    for f in 10-dfd0 11-dfd1 12-dfd2; do
        dot -Tpng -Gdpi=200 docs/diagrams/$f.dot -o docs/diagrams/$f.png
    done
    python docs/build_srs.py
"""
import json
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.shared import Inches, Pt, RGBColor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DIAGRAMS = os.path.join(HERE, "diagrams")
SHOT = os.path.join(HERE, "screenshot-dashboard.png")
OUT = os.path.expanduser("~/Downloads/Indus11_SRS.docx")

with open(os.path.join(HERE, "eval-results.json")) as f:
    EVAL = json.load(f)
FLAGGED, GRAPH, COUNTS = EVAL["metrics"]["flagged"], EVAL["graph"], EVAL["counts"]

FONT = "Times New Roman"
BODY, SUB, CHAP = 12, 14, 16
LINE = 1.5                # running text; tables and captions stay single-spaced
INK = RGBColor(0, 0, 0)
USABLE_W = 6.0            # 8.5in page, 1.5in left + 1.0in right margin
MAX_FIG_H = 7.0

figures, tables = [], []   # (label, title) for the front-matter lists
contents = []              # (level, title) for the table of contents

# Page numbers for the contents, produced by a first pass over the rendered PDF
# (docs/make_srs_pdf.py). Absent on the first pass, which is why the entries are
# laid out identically either way — the pagination must not shift between passes.
try:
    with open(os.path.join(HERE, "toc-pages.json")) as f:
        TOC_PAGES = json.load(f)
except FileNotFoundError:
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
    s.left_margin, s.right_margin = Inches(1.5), Inches(1.0)
    s.top_margin, s.bottom_margin = Inches(1.5), Inches(1.5)


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


def page_numbers():
    for s in doc.sections:
        p = s.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.0
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


def chapter(title, numbered=True):
    """Chapter heading: own page, centred, 16 pt bold."""
    global _chapter, _fig_n, _tbl_n
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
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(text)
    r.font.size, r.bold, r.font.color.rgb, r.font.name = Pt(CHAP), True, INK, FONT
    contents.append((1, text))
    return p


def section(title):
    p = doc.add_paragraph(style="Heading 2")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.0
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


def figure(png, title):
    """Embed a rendered diagram with a chapter-scoped caption."""
    global _fig_n
    _fig_n += 1
    label = f"Figure {_chapter}.{_fig_n}"
    path = png if os.path.isabs(png) else os.path.join(DIAGRAMS, png)
    with Image.open(path) as im:
        w_px, h_px = im.size
    width = USABLE_W
    if width * h_px / w_px > MAX_FIG_H:
        width = MAX_FIG_H * w_px / h_px
    doc.add_picture(path, width=Inches(width))
    pic = doc.paragraphs[-1]
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.paragraph_format.space_before = Pt(6)
    pic.paragraph_format.space_after = Pt(2)
    para(f"{label}: {title}", size=11, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=10, spacing=1.0)
    figures.append((label, title))


def table(title, headers, rows, widths=None, size=10.5):
    global _tbl_n
    _tbl_n += 1
    label = f"Table {_chapter}.{_tbl_n}"
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        shade = OxmlElement("w:shd")
        shade.set(qn("w:fill"), "E8EEF7")
        c._tc.get_or_add_tcPr().append(shade)
        p = c.paragraphs[0]
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        r = p.add_run(h)
        r.bold, r.font.size, r.font.name = True, Pt(size), FONT
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            r = p.add_run(str(v))
            r.font.size, r.font.name = Pt(size), FONT
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    para(f"{label}: {title}", size=11, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=10, spacing=1.0)
    tables.append((label, title))
    return t


def code_block(lines, size=9):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    cell = t.cell(0, 0)
    cell.text = ""
    for i, line in enumerate(lines.split("\n")):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(line if line else " ")
        r.font.name, r.font.size = "Consolas", Pt(size)
    para("", after=8)


# ───────────────────────── FRONT MATTER ─────────────────────────
para("SOFTWARE REQUIREMENTS SPECIFICATION", CHAP, True, WD_ALIGN_PARAGRAPH.CENTER, 10)
para("INDUS11 — AI FINANCIAL RISK AND FRAUD DECISION ENGINE", CHAP, True,
     WD_ALIGN_PARAGRAPH.CENTER, 20)
para("A Software Group Project Report", BODY, False, WD_ALIGN_PARAGRAPH.CENTER, 4)
para("Semester 5   |   Academic Year 2026-27   |   Project ID: PRJ_CE_5_2026_7",
     BODY, False, WD_ALIGN_PARAGRAPH.CENTER, 20)
para("Submitted by", BODY, True, WD_ALIGN_PARAGRAPH.CENTER, 6)
for n, sid in [("Joshi Om", "24DCE052"), ("Krish Gajera", "24DCE040"),
               ("Drashti Dedaniya", "24DCE029")]:
    para(f"{n}   ({sid})", BODY, False, WD_ALIGN_PARAGRAPH.CENTER, 2)
para("", after=16)
para("Under the guidance of", BODY, False, WD_ALIGN_PARAGRAPH.CENTER, 4)
para("Dr. Deven Gol", BODY, True, WD_ALIGN_PARAGRAPH.CENTER, 2)
para("Assistant Professor, Department of Computer Engineering", BODY, False,
     WD_ALIGN_PARAGRAPH.CENTER, 20)
para("DEVANG PATEL INSTITUTE OF ADVANCE TECHNOLOGY AND RESEARCH (DEPSTAR)",
     BODY, True, WD_ALIGN_PARAGRAPH.CENTER, 3)
para("CHAROTAR UNIVERSITY OF SCIENCE AND TECHNOLOGY (CHARUSAT)", BODY, True,
     WD_ALIGN_PARAGRAPH.CENTER, 3)
para("Changa, Gujarat — 388421", BODY, False, WD_ALIGN_PARAGRAPH.CENTER)

new_page()
para("CERTIFICATE", CHAP, True, WD_ALIGN_PARAGRAPH.CENTER, 18)
para("This is to certify that the Software Requirements Specification entitled "
     "“Indus11 — AI Financial Risk and Fraud Decision Engine” is the bona fide work "
     "carried out by Joshi Om (24DCE052), Krish Gajera (24DCE040) and Drashti "
     "Dedaniya (24DCE029) of Semester 5, Department of Computer Engineering, DEPSTAR, "
     "CHARUSAT, in partial fulfilment of the requirements of the Software Group "
     "Project during the academic year 2026-27.", after=48)
_c = doc.add_table(rows=1, cols=2)
for i, txt in enumerate(["Dr. Deven Gol\nInternal Guide\nAssistant Professor\n"
                         "Computer Engineering",
                         "Head of Department\nComputer Engineering\n"
                         "DEPSTAR, CHARUSAT"]):
    cell = _c.cell(0, i)
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(txt)
    r.font.size, r.font.name = Pt(BODY), FONT
    cell.width = Inches(3.0)
para("", after=10)
para("Date: ______________                    Place: Changa")

new_page()
para("ACKNOWLEDGEMENT", CHAP, True, WD_ALIGN_PARAGRAPH.CENTER, 18)
para("The satisfaction that accompanies the successful completion of any task would be "
     "incomplete without mentioning the people who made it possible, and whose constant "
     "guidance and encouragement crowned our effort with success.", after=10)
para("We are deeply indebted to our internal guide, Dr. Deven Gol, Assistant Professor, "
     "Department of Computer Engineering, DEPSTAR, for his valuable guidance, his "
     "patience with our drafts and the detailed review comments that shaped both this "
     "project and this document. His insistence on measured results rather than claims "
     "has improved our work considerably.", after=10)
para("We extend our sincere thanks to the Head of the Department of Computer "
     "Engineering and to the Principal of Devang Patel Institute of Advance Technology "
     "and Research (DEPSTAR) for providing us with the laboratory facilities, the "
     "academic environment and the freedom to pursue this problem.", after=10)
para("We are thankful to the faculty members of the Department of Computer Engineering "
     "for the foundation in databases, software engineering and machine learning on "
     "which this project rests, and to our classmates for their review and testing of "
     "our early prototypes.", after=10)
para("We also acknowledge the open-source communities behind FastAPI, MongoDB, Neo4j, "
     "Redis, ChromaDB, LangChain, Ollama and React, and the authors of the research "
     "cited in this report, whose work made a project of this scope possible within a "
     "single semester.", after=10)
para("Finally, we thank our parents and families for their constant support and "
     "encouragement throughout the course of this work.", after=24)
for n, sid in [("Joshi Om", "24DCE052"), ("Krish Gajera", "24DCE040"),
               ("Drashti Dedaniya", "24DCE029")]:
    para(f"{n} ({sid})", align=WD_ALIGN_PARAGRAPH.RIGHT, after=2)

new_page()
para("ABSTRACT", CHAP, True, WD_ALIGN_PARAGRAPH.CENTER, 18)
para("[ TO BE WRITTEN BY THE TEAM IN YOUR OWN WORDS — approximately 250 to 300 words. ]",
     BODY, True, WD_ALIGN_PARAGRAPH.LEFT, 10)
para("The internal guide has asked specifically that the abstract be original and "
     "reflect your own understanding of the project. Write it yourselves, covering the "
     "points below in continuous prose rather than as a list. The measured figures are "
     "supplied so that you do not have to look them up.", after=10)
for prompt in [
    "The problem — why fraud detection needs both accuracy and a reason for every "
    "decision, and what goes wrong when a system provides only one of the two.",
    "The objective — what you set out to build and what the system returns for each "
    "transaction.",
    "The methodology — the three detection engines you combined (rules, graph analysis "
    "and a retrieval-augmented language model), how their scores are weighted "
    "(40, 30 and 30 out of 100) and why the language model is capped.",
    f"The outcome — measured on {COUNTS['total']} labelled transactions "
    f"({COUNTS['fraud']} fraudulent and {COUNTS['legit']} legitimate): precision "
    f"{FLAGGED['precision']*100:.1f} per cent, recall {FLAGGED['recall']*100:.1f} per "
    f"cent, F1 {FLAGGED['f1']:.2f}, and all {GRAPH['ring_transactions']} planted "
    "mule-ring transactions detected by the graph layer.",
    "Your own conclusion — what the results told you, including the finding that no "
    "transaction reached the block threshold, so every detection currently reaches a "
    "human analyst.",
]:
    bullet(prompt)
para("", after=8)
para("Keywords: ______________________________________________", italic=True)

new_page()
TOC_ANCHOR = doc.add_paragraph()

new_page()
LOF_ANCHOR = doc.add_paragraph()
LOT_ANCHOR = doc.add_paragraph()

# Front matter is not produced by chapter()/section(), so it is listed by hand.
FRONT_MATTER = ["CERTIFICATE", "ACKNOWLEDGEMENT", "ABSTRACT",
                "LIST OF FIGURES", "LIST OF TABLES"]

# ───────────────────────── CHAPTER 1 ─────────────────────────
chapter("Introduction")
section("1.1 Purpose")
para("This document specifies the software requirements for Indus11, a real-time "
     "financial fraud detection and decision engine. It states what the system must "
     "do, the interfaces it exposes, the constraints it operates under and the quality "
     "attributes against which it is measured.")
para("The intended readers are the project team, the internal guide and the evaluation "
     "panel, and any developer who later integrates with or extends the system. Every "
     "measured figure quoted in this document comes from an executed benchmark run "
     "rather than an estimate.")
section("1.2 Scope")
para("Indus11 accepts one financial transaction over a REST interface, analyses it "
     "with three independent detection engines and returns a composite risk score from "
     "0 to 100, a decision of APPROVE, REVIEW or BLOCK, and a plain-language "
     "explanation. A web dashboard allows an analyst to view live statistics, inspect "
     "any flagged transaction and override a review outcome.")
para("The following are outside the scope of the system: it does not move money or "
     "settle payments; it is not a core banking system; it processes synthetic data "
     "only; it performs no regulatory reporting; and the training of a supervised "
     "model is identified as future work.")
section("1.3 Document Overview")
para("Chapter 2 describes the system as a whole. Chapter 3 states the functional, "
     "non-functional and security requirements. Chapter 4 presents the system design "
     "and data flow. Chapter 5 contains the UML models. Chapter 6 specifies the "
     "database design. The conclusion, the references and the list of definitions and "
     "acronyms follow at the end of the document.")

# ───────────────────────── CHAPTER 2 ─────────────────────────
chapter("Overall Description")
section("2.1 Product Perspective")
para("Indus11 is a new, self-contained decision service rather than a replacement for "
     "an existing product. In a production setting it would sit beside a payment "
     "processor: the processor submits a transaction and acts on the returned "
     "decision.")
para("The system comprises a FastAPI application, a React dashboard and four data "
     "stores, each with a distinct role — MongoDB for account profiles and the audit "
     "trail, Neo4j for the transaction graph, Redis for caching and the velocity "
     "window, and ChromaDB for the fraud-pattern knowledge base.")
section("2.2 Product Functions")
for fn in ["Accept and validate a transaction over a documented REST interface.",
           "Load account profiles from cache, falling back to the document store.",
           "Score the transaction against configurable rules, including a "
           "rolling-window velocity check.",
           "Detect fraud rings and shared-identity clusters in the transaction graph.",
           "Retrieve similar fraud patterns and generate a natural-language explanation.",
           "Combine the layer scores into one score and map it to a decision.",
           "Persist every analysis so that decisions can be audited.",
           "Present live statistics and flagged transactions on a dashboard.",
           "Allow an analyst to inspect a transaction and override a review decision.",
           "Measure detection accuracy against a labelled dataset.",
           "Protect the service with per-client rate limiting."]:
    bullet(fn)
section("2.3 User Characteristics")
table("User classes and their characteristics", ["User class", "Characteristics"],
      [["Fraud analyst", "Primary user. Reviews and acts on flagged transactions. "
                         "Understands fraud typologies but does not read code or write "
                         "queries, so each decision must be explained in plain language."],
       ["System administrator", "Deploys and operates the stack, tunes thresholds and "
                                "runs the seed and evaluation scripts."],
       ["Integrating developer", "Consumes the REST interface from a payment system. "
                                 "Requires accurate schemas and documented status codes."],
       ["Project evaluator", "Assesses the system against this specification and "
                             "reproduces the measured results."]],
      widths=[1.5, 4.5])
section("2.4 Operating Environment")
table("Operating environment", ["Element", "Requirement"],
      [["Hardware", "64-bit x86 or ARM machine, 8 GB RAM minimum, approximately 5 GB "
                    "free disk space. No graphics processor is required."],
       ["Operating system", "Linux, macOS or Windows with Docker support."],
       ["Runtime", "Python 3.12 for the backend, Node.js 20 for the dashboard build."],
       ["Databases", "MongoDB 7, Neo4j 5.20 Community Edition, Redis 7.2, ChromaDB."],
       ["Language model", "Ollama running llama3 locally, or the OpenAI service."],
       ["Client", "Any modern browser at 1280 pixels width or greater."]],
      widths=[1.4, 4.6])
section("2.5 Design Constraints")
for c in ["The system shall run in full on a single machine without a graphics processor.",
          "No real customer or payment data may be used; all datasets are synthetic.",
          "The language model shall contribute no more than 30 of the 100 points.",
          "The language model shall be able to run locally, at no external cost.",
          "The backend shall be written in Python 3.12 and the dashboard in React.",
          "Neo4j Community Edition is used, so enterprise-only features are unavailable.",
          "The sum of all layer score budgets shall equal 100.",
          "Credentials shall never be committed to version control."]:
    bullet(c)
section("2.6 Assumptions and Dependencies")
for a in ["The four data stores are reachable. If a store is unavailable the affected "
          "layer degrades rather than failing the request.",
          "A local language model or an external service key is available. Without "
          "either, the rule and graph layers still produce a decision and only the "
          "written explanation is lost.",
          "The synthetic dataset is representative enough to compare configurations "
          "against one another, but not to predict production accuracy: fraud is far "
          "denser in it than in a real payment feed, so the measured precision is "
          "optimistic.",
          "An account with no stored profile is treated as elevated risk rather than "
          "as safe.",
          "Decision thresholds are tunable for each deployment; the values quoted in "
          "this document are the defaults.",
          "Any change to a layer's score budget would require the thresholds and the "
          "accuracy baseline to be derived again."]:
    bullet(a)

# ───────────────────────── CHAPTER 3 ─────────────────────────
chapter("System Requirements")
section("3.1 Functional Requirements")
para("Each requirement is traceable to the module that implements it.")
table("Functional requirements", ["ID", "Requirement", "Module"],
      [["FR-1", "Accept a transaction over HTTP POST carrying identifier, sender, receiver, amount, currency and optional merchant, device, address and note fields.", "routes/transactions"],
       ["FR-2", "Validate every request against a schema and reject a malformed or non-positive amount before any analysis is performed.", "schemas/transaction"],
       ["FR-3", "Reject a duplicate transaction identifier with a conflict response so that a retried request does not produce a server error.", "routes/transactions"],
       ["FR-4", "Load sender and receiver profiles from cache, falling back to the document store, treating an unknown account as elevated risk.", "routes/transactions"],
       ["FR-5", "Score from 0 to 40 using blacklist, velocity, amount-anomaly, merchant and risk-tier rules, returning the reason for each rule that fired.", "services/rule_engine"],
       ["FR-6", "Return the maximum rule score immediately when either party is blacklisted.", "services/rule_engine"],
       ["FR-7", "Count transactions for an account within an exact ten-minute rolling window and flag more than five.", "core/redis_client"],
       ["FR-8", "Score from 0 to 30 by detecting shared devices, circular flows within four hops, fee-skimming chains and proximity to a known fraud cluster.", "services/graph_analyzer"],
       ["FR-9", "Record the transaction, its accounts, device and address in the graph so later transactions can be evaluated against it.", "services/graph_analyzer"],
       ["FR-10", "Retrieve similar fraud patterns and obtain a score from 0 to 30 with an explanation from the language model.", "services/rag_pipeline"],
       ["FR-11", "Degrade to a zero score with a stated reason when no language model is reachable.", "services/rag_pipeline"],
       ["FR-12", "Execute the three scoring layers concurrently.", "routes/transactions"],
       ["FR-13", "Compute the composite score as the sum of the layer scores, clamped to 100.", "services/decision_engine"],
       ["FR-14", "Map the composite score to APPROVE, REVIEW or BLOCK using configured thresholds.", "services/decision_engine"],
       ["FR-15", "Include the triggered signals and the model's reasoning in every response.", "services/decision_engine"],
       ["FR-16", "Persist every analysed transaction with its score, decision, explanation and note.", "models/transaction"],
       ["FR-17", "Return a previously analysed transaction by identifier, or a not-found response.", "routes/transactions"],
       ["FR-18", "List recent transactions, optionally filtered by decision.", "routes/transactions"],
       ["FR-19", "Allow an analyst to override a decision and reject any invalid value.", "routes/transactions"],
       ["FR-20", "Support creating and listing accounts and toggling blacklist status.", "routes/accounts"],
       ["FR-21", "Return the graph neighbourhood of an account to a depth of one to three hops.", "routes/graph"],
       ["FR-22", "Propagate fraud labels to accounts within two hops and assign a cluster identifier.", "services/graph_analyzer"],
       ["FR-23", "Report graph statistics for accounts, devices, addresses, transactions and labels.", "routes/graph"],
       ["FR-24", "Report decision counts and a composite-score histogram.", "routes/stats"],
       ["FR-25", "Report the most recent transactions marked for review or blocked.", "routes/stats"],
       ["FR-26", "Serve the latest accuracy results and indicate clearly when none exist.", "routes/stats"],
       ["FR-27", "Replay a labelled dataset and report precision, recall, F1, a confusion matrix and ring detection.", "scripts/evaluate"],
       ["FR-28", "Derive decisions again across candidate thresholds and report no block threshold when none is reachable.", "scripts/evaluate"],
       ["FR-29", "Limit each client to 120 requests per minute overall and 30 on the analysis endpoint.", "core/rate_limit"],
       ["FR-30", "Expose a health endpoint reporting service status.", "routes/health"],
       ["FR-31", "Provide repeatable seed scripts for account profiles and a synthetic fraud graph.", "scripts/seed"],
       ["FR-32", "Display metrics, decision mix, score distribution, accuracy and flagged transactions with detail and override.", "dashboard"]],
      widths=[0.5, 4.2, 1.3], size=9)
section("3.2 Non-Functional Requirements")
para("The values below were measured on the development machine, an Apple Silicon "
     "computer running without a graphics processor.")
table("Measured performance", ["Measurement", "Value", "Note"],
      [["Rule engine", "8 ms", "Velocity check and in-memory rules."],
       ["Graph analyzer", "158 ms first call, 48 ms warm", "Graph write and four pattern queries."],
       ["Rule and graph concurrently", "48 ms", "Deterministic layers only."],
       ["Complete pipeline", "14,046 ms", "The language model accounts for about 13.9 s."],
       ["Benchmark run", "208 transactions", "Sequential, bound by the language model."]],
      widths=[1.9, 1.6, 2.5])
for n in ["The deterministic layers shall complete within 500 milliseconds per transaction.",
          "The layers shall run concurrently so that total latency is bounded by the "
          "slowest layer rather than by their sum.",
          "The service shall hold no state between requests, so that an instance can be "
          "restarted without loss of data.",
          "An unavailable component shall never cause a transaction to be approved silently.",
          "The composite score shall be clamped so that no combination exceeds the range.",
          "Every decision shall be persisted with its explanation for audit.",
          "The stack shall start with a single command on Linux, macOS or Windows.",
          "The automated test suite shall run without any database or network access."]:
    bullet(n)
table("Software quality attributes", ["Attribute", "How it is achieved"],
      [["Reliability", "The pipeline degrades one component at a time; a duplicate "
                       "submission returns a defined conflict response."],
       ["Maintainability", "Each layer is a single function with one input and one "
                           "output type, so a layer can be replaced independently."],
       ["Testability", "Twenty-seven automated tests run with no database or network."],
       ["Portability", "The entire stack is defined in one container composition file."],
       ["Usability", "Every decision is accompanied by a written explanation."],
       ["Accuracy", f"Precision {FLAGGED['precision']:.3f}, recall {FLAGGED['recall']:.3f}, "
                    f"F1 {FLAGGED['f1']:.3f} over {COUNTS['total']} transactions; "
                    f"{GRAPH['graph_flagged']} of {GRAPH['ring_transactions']} ring "
                    "transactions detected."]],
      widths=[1.3, 4.7])
section("3.3 Security Requirements")
for s in ["Credentials shall be supplied through environment variables and never committed.",
          "All input shall be validated against a strict schema before use.",
          "Database access shall use parameterised queries throughout.",
          "Rate limiting shall be applied for each client address.",
          "Stored explanations shall be truncated to a bounded length.",
          "Account identifiers are the only data shared between stores; no payment "
          "instrument data is persisted.",
          "Authentication and authorisation are not implemented in the current version. "
          "The interface is intended for deployment on a trusted network only, and the "
          "addition of key-based authentication is recorded as required future work."]:
    bullet(s)

# ───────────────────────── CHAPTER 4 ─────────────────────────
chapter("System Design")
section("4.1 Overall Architecture")
para("The system is organised as a five-layer pipeline. The first layer validates the "
     "request and loads context, the second, third and fourth layers score the "
     "transaction concurrently, and the fifth layer aggregates the scores and "
     "determines the decision.")
figure("01-architecture.png", "System architecture — five-layer pipeline")
section("4.2 Context Diagram")
para("The context diagram shows the system as a single process together with the "
     "external entities that exchange data with it.")
figure("10-dfd0.png", "Data flow diagram — Level 0 (context diagram)")
section("4.3 Data Flow Diagram — Level 1")
para("The level 1 diagram decomposes the system into its seven principal processes and "
     "shows the data stores each process reads from and writes to.")
figure("11-dfd1.png", "Data flow diagram — Level 1")
section("4.4 Data Flow Diagram — Level 2")
para("The level 2 diagram expands process 3.0, rule evaluation, into its component "
     "checks and the order in which they contribute to the rule score.")
figure("12-dfd2.png", "Data flow diagram — Level 2 (rule evaluation)")

# ───────────────────────── CHAPTER 5 ─────────────────────────
chapter("UML Diagrams")
section("5.1 Use Case Diagram")
para("The use case diagram identifies the three actors and the services each may invoke.")
figure("02-usecase.png", "Use case diagram")
section("5.2 Activity Diagram")
para("The workflow is presented as two diagrams. The first covers intake, schema "
     "validation and the concurrent evaluation of the three scoring layers; the second "
     "covers score aggregation, the three decision bands, the response returned to the "
     "client and the analyst review path. Splitting the workflow keeps each diagram "
     "large enough on the page for its text to be read without magnification.")
figure("03-activity.png",
       "Activity diagram (1 of 2) — intake and concurrent scoring")
figure("03b-activity-decision.png",
       "Activity diagram (2 of 2) — decision, response and analyst review")
section("5.3 Sequence Diagram")
para("The sequence diagram shows the order of interaction between the components while "
     "a single transaction is analysed.")
figure("04-sequence.png", "Sequence diagram — transaction analysis")
section("5.4 Class Diagram")
para("The class model is presented in two parts, for the same reason of legibility. The "
     "first part shows the domain classes — the request accepted at the interface, the "
     "account and transaction records that are persisted, the response returned and the "
     "decision enumeration. The second part shows the abstract analysis layer, its three "
     "concrete implementations and the decision engine that aggregates the layer scores.")
figure("05-class.png", "Class diagram (1 of 2) — domain classes")
figure("05b-class-services.png", "Class diagram (2 of 2) — analysis service classes")
section("5.5 State Diagram")
para("The state diagram shows the states a transaction passes through from submission "
     "to a final outcome, including the analyst override path.")
figure("06-state.png", "State diagram — transaction lifecycle")
section("5.6 Component Diagram")
para("The component diagram shows the deployable components and the interfaces through "
     "which they communicate.")
figure("07-component.png", "Component diagram")
section("5.7 Deployment Diagram")
para("The deployment diagram shows the physical arrangement of the containers and the "
     "ports on which they communicate.")
figure("08-deployment.png", "Deployment diagram — container topology")
table("Deployment configuration", ["Node", "Component", "Port", "Persistent storage"],
      [["Client device", "Web browser", "—", "None"],
       ["Container: dashboard", "nginx serving the React build", "5173 to 80", "None"],
       ["Container: api", "uvicorn running the FastAPI application", "8000", "None"],
       ["Container: mongo", "MongoDB 7", "27017", "Volume mongo_data"],
       ["Container: neo4j", "Neo4j 5.20", "7474, 7687", "Volume neo4j_data"],
       ["Container: redis", "Redis 7.2", "6379", "Volume redis_data"],
       ["Docker host", "ChromaDB persistent store", "—", "Bind mount ./data/chroma"],
       ["Host machine", "Ollama running llama3", "11434", "Local model files"]],
      widths=[1.5, 2.2, 1.0, 1.3])

# ───────────────────────── CHAPTER 6 ─────────────────────────
chapter("Database Design")
section("6.1 Entity Relationship Diagram")
para("The entity relationship diagram shows the stored entities and the relationships "
     "between them across the document store and the graph store.")
figure("09-er.png", "Entity relationship diagram")
section("6.2 Logical Data Schema")
para("The document store is schemaless, so the schema below is the logical one enforced "
     "by the application: the Beanie document models declare the fields, their types and "
     "their indexes, and those indexes are created when the application starts, so no "
     "migration step is required. The two collections and their keys are given first, "
     "followed by the field-level definition of each.")
table("Collections, keys and indexes",
      ["Collection", "Primary key", "Unique index", "Secondary indexes", "Referenced by"],
      [["accounts", "_id (ObjectId)", "account_id", "—",
        "transactions (sender and receiver); Neo4j Account"],
       ["transactions", "_id (ObjectId)", "tx_id",
        "sender_account_id, receiver_account_id, decision",
        "Neo4j Transaction"]],
      widths=[0.9, 1.0, 0.9, 1.5, 1.7], size=9.5)
table("Accounts collection", ["Field", "Type", "Constraint", "Description"],
      [["account_id", "String", "Unique index", "Primary business key."],
       ["owner_name", "String", "Required", "Account holder name (synthetic)."],
       ["country_code", "String", "Default", "Two-letter country code."],
       ["avg_monthly_transaction", "Float", "Default 0.0", "Baseline for the anomaly rule."],
       ["is_blacklisted", "Boolean", "Default false", "Forces the maximum rule score."],
       ["risk_tier", "String", "Default standard", "One of standard, elevated or high."]],
      widths=[1.6, 0.9, 1.2, 2.3], size=10)
table("Transactions collection", ["Field", "Type", "Constraint", "Description"],
      [["tx_id", "String", "Unique index", "A duplicate insert is rejected."],
       ["sender_account_id", "String", "Indexed", "Supports per-account history."],
       ["receiver_account_id", "String", "Indexed", "Counterparty account."],
       ["amount", "Float", "Greater than 0", "Transaction value."],
       ["currency", "String", "Default INR", "Currency code."],
       ["merchant_category", "String", "Optional", "Drives the merchant rule."],
       ["device_id", "String", "Optional", "Identity signal for the graph layer."],
       ["ip_address", "String", "Optional", "Identity signal for the graph layer."],
       ["composite_score", "Integer", "0 to 100", "Final risk score."],
       ["decision", "String", "Indexed", "APPROVE, REVIEW or BLOCK."],
       ["explanation", "String", "Bounded length", "Signals and model reasoning."],
       ["note", "String", "Optional", "Free text supplied at submission."],
       ["created_at", "DateTime", "Default now", "Supports recent-first listing."]],
      widths=[1.6, 0.9, 1.2, 2.3], size=10)
section("6.3 Data Dictionary")
para("Every entity held outside the document store is defined below, one table per "
     "store. Together with the two collection tables above these cover all persisted "
     "data in the system.")
table("Graph node types (Neo4j)",
      ["Node label", "Properties", "Key", "Purpose"],
      [["Account", "account_id, risk_label, fraud_cluster", "account_id",
        "One vertex per party. risk_label carries fraud or fraud_adjacent and "
        "fraud_cluster names the seed account of the cluster."],
       ["Transaction", "tx_id, amount, timestamp", "tx_id",
        "One vertex per analysed transfer, retained as the graph-side record."],
       ["Device", "device_id", "device_id",
        "Shared-device identity signal, used to link otherwise unrelated accounts."],
       ["IPAddress", "address", "address",
        "Shared-address identity signal, used in the same way as Device."]],
      widths=[0.9, 1.7, 1.2, 2.2], size=9.5)
table("Graph relationship types (Neo4j)",
      ["Relationship", "From", "To", "Properties", "Purpose"],
      [["SENT", "Account", "Account", "tx_id, amount",
        "One money movement. Circular-flow and fee-skimming patterns are found "
        "by traversing two to four of these."],
       ["USED_DEVICE", "Account", "Device", "—",
        "Supports shared-device cluster detection."],
       ["USED_IP", "Account", "IPAddress", "—",
        "Supports shared-address cluster detection."],
       ["CONNECTED_TO", "Account", "Account", "—",
        "Materialised from a shared device or address; traversed by fraud label "
        "propagation to a depth of two."]],
      widths=[1.1, 0.9, 0.9, 1.1, 2.0], size=9.5)
table("Cache keys (Redis)",
      ["Key pattern", "Type", "Value", "Lifetime"],
      [["account:<account_id>", "String (JSON)", "Serialised account profile", "300 seconds"],
       ["velocity:<account_id>", "Sorted set",
        "Transaction timestamps scored by epoch second", "600 second rolling window"],
       ["velocity:<account_id> member", "String",
        "Event timestamp with a random suffix, so simultaneous events are distinct",
        "Aged out with its window"]],
      widths=[1.6, 1.1, 2.3, 1.0], size=9.5)
table("Vector store (ChromaDB)",
      ["Collection", "Field", "Type", "Description"],
      [["fraud_patterns", "id", "String", "Stable identifier of the pattern document."],
       ["fraud_patterns", "document", "Text",
        "Description of one fraud typology; 58 documents are seeded on startup."],
       ["fraud_patterns", "embedding", "Vector",
        "Embedding used for similarity retrieval by the RAG layer."],
       ["fraud_patterns", "metadata.category", "String",
        "Typology group, for example mule ring, card testing or account takeover."],
       ["fraud_patterns", "metadata.severity", "String",
        "Indicative severity, used to weight the retrieved context."]],
      widths=[1.2, 1.4, 0.9, 2.5], size=9.5)
para("Transaction records are retained indefinitely to preserve the audit trail, and no "
     "deletion path is exposed through the interface. Referential integrity between "
     "accounts and transactions is enforced by the application, since the document "
     "store does not impose foreign keys. Both seed scripts are idempotent.")

# ────────────────── UNNUMBERED CLOSING SECTIONS ──────────────────
chapter("Conclusion and Future Enhancements", numbered=False)
para("Indus11 shows that detection capability and explainability need not be traded "
     "against one another. Combining deterministic rules, graph traversal and a "
     "retrieval-augmented language model produced "
     f"{FLAGGED['precision']*100:.1f} per cent precision at "
     f"{FLAGGED['recall']*100:.1f} per cent recall on a labelled synthetic dataset of "
     f"{COUNTS['total']} transactions, while every decision carries the list of signals "
     "that caused it.")
para("The graph layer justified its inclusion. It detected all "
     f"{GRAPH['ring_transactions']} planted mule-ring transactions, which rules that "
     "examine a single transaction cannot detect by construction.")
para("The evaluation also produced a negative result worth recording. No transaction "
     "reached the configured block threshold, so nothing is blocked automatically and "
     "every detection reaches an analyst. Lowering the threshold would automate "
     "blocking at the cost of also blocking the false positives, which is a policy "
     "decision requiring evidence rather than a change of configuration.")
para("Planned enhancements, in order of priority:")
for e in ["Resolve the block-threshold trade-off using the recorded transaction scores.",
          "Add key-based authentication and structured request logging.",
          "Build an interactive fraud-ring visualisation on the existing graph endpoint.",
          "Investigate the seven undetected frauds and add fan-in and fan-out graph patterns.",
          "Train a supervised classifier as a fourth scoring signal.",
          "Reduce latency, which is presently dominated by the local language model.",
          "Validate against a public labelled dataset to obtain a realistic precision figure."]:
    bullet(e)

chapter("References", numbered=False)
for i, r in enumerate([
    "IEEE, “IEEE Recommended Practice for Software Requirements Specifications,” "
    "IEEE Std 830-1998, Institute of Electrical and Electronics Engineers, 1998.",
    "V. Van Vlasselaer, C. Bravo, O. Caelen, T. Eliassi-Rad, L. Akoglu, M. Snoeck and "
    "B. Baesens, “APATE: A novel approach for automated credit card transaction fraud "
    "detection using network-based extensions,” Decision Support Systems, vol. 75, "
    "pp. 38–48, 2015.",
    "B. Lebichot, F. Braun, O. Caelen and M. Saerens, “A graph-based, semi-supervised, "
    "credit card fraud detection system,” in Complex Networks and Their Applications V, "
    "Springer, 2017, pp. 721–733.",
    "D. Vijayanand and G. S. Smrithy, “Explainable AI-enhanced ensemble learning for "
    "financial fraud detection,” 2025, doi:10.1177/18724981241289751.",
    "P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin and others, "
    "“Retrieval-augmented generation for knowledge-intensive NLP tasks,” Advances in "
    "Neural Information Processing Systems, vol. 33, pp. 9459–9474, 2020.",
    "FICO, “Falcon Fraud Manager,” product documentation, 2026. [Online]. "
    "Available: https://www.fico.com",
    "Feedzai, “RiskOps platform,” product overview, 2026. [Online]. "
    "Available: https://feedzai.com",
    "Featurespace, “ARIC Risk Hub,” product overview, 2026. [Online]. "
    "Available: https://www.featurespace.com",
    "Neo4j, “Graph algorithms for fraud detection,” developer documentation, 2026. "
    "[Online]. Available: https://neo4j.com/developer",
    "S. Ramirez, “FastAPI documentation,” 2026. [Online]. "
    "Available: https://fastapi.tiangolo.com",
    "MongoDB Inc., “MongoDB manual and Beanie ODM documentation,” 2026. [Online]. "
    "Available: https://www.mongodb.com/docs",
    "LangChain and Chroma documentation, 2026. [Online]. "
    "Available: https://python.langchain.com",
], 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.first_line_indent = Inches(-0.4)
    p.paragraph_format.line_spacing = LINE
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(f"[{i}]  {r}")
    run.font.size, run.font.name = Pt(BODY), FONT

chapter("Definitions, Acronyms and Abbreviations", numbered=False)
_t = doc.add_table(rows=1, cols=2)
_t.style = "Table Grid"
for i, h in enumerate(["Term", "Definition"]):
    c = _t.rows[0].cells[i]
    c.text = ""
    sh = OxmlElement("w:shd"); sh.set(qn("w:fill"), "E8EEF7")
    c._tc.get_or_add_tcPr().append(sh)
    r = c.paragraphs[0].add_run(h)
    r.bold, r.font.size, r.font.name = True, Pt(10.5), FONT
for term, definition in [
    ("API", "Application Programming Interface."),
    ("APPROVE", "Decision for a composite score of 0 to 39; the transaction proceeds."),
    ("BLOCK", "Decision for a composite score of 70 or above; the transaction is refused."),
    ("Composite score", "The sum of the three layer scores, clamped to 100."),
    ("Confusion matrix", "A table cross-tabulating the decision taken against the true label."),
    ("DFD", "Data Flow Diagram."),
    ("ER", "Entity Relationship."),
    ("F1", "The harmonic mean of precision and recall."),
    ("Fee skimming", "Each hop of a mule chain passing on slightly less money than it received."),
    ("Flag", "A signal code together with the values that triggered it."),
    ("HTTP", "Hypertext Transfer Protocol."),
    ("JSON", "JavaScript Object Notation."),
    ("Layer", "One stage of the analysis pipeline that produces a score and flags."),
    ("LLM", "Large Language Model."),
    ("Money-mule ring", "Accounts cycling funds among themselves to disguise the origin."),
    ("ODM", "Object-Document Mapper."),
    ("Precision", "Of the transactions flagged, the proportion genuinely fraudulent."),
    ("RAG", "Retrieval-Augmented Generation."),
    ("Recall", "Of the genuinely fraudulent transactions, the proportion flagged."),
    ("REST", "Representational State Transfer."),
    ("REVIEW", "Decision for a composite score of 40 to 69; held for a human analyst."),
    ("SRS", "Software Requirements Specification."),
    ("TTL", "Time To Live; the expiry period of a cached entry."),
    ("UML", "Unified Modeling Language."),
    ("Velocity", "The number of transactions an account makes inside a rolling window."),
]:
    cells = _t.add_row().cells
    for i, v in enumerate((term, definition)):
        cells[i].text = ""
        p = cells[i].paragraphs[0]
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(v)
        r.font.size, r.font.name = Pt(10.5), FONT
    cells[0].width, cells[1].width = Inches(1.6), Inches(4.4)

chapter("Appendix", numbered=False)
section("Appendix A — Application Screen")
if os.path.exists(SHOT):
    doc.add_picture(SHOT, width=Inches(USABLE_W))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para("Figure A.1: Analyst dashboard showing risk metrics, decision mix, score "
         "distribution, accuracy results and flagged transactions", size=11, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=10, spacing=1.0)
section("Appendix B — Reproducing the Measured Results")
code_block("""# 1. Start the complete stack
docker compose up --build

# 2. Seed the synthetic datasets (run automatically by the API container)
python -m scripts.seed_mongo
python -m scripts.seed_neo4j

# 3. Replay the labelled dataset through the pipeline
python -m scripts.evaluate

# 4. Run the automated test suite (no databases required)
pytest -q""")


# ────────────────── back-fill lists of figures and tables ──────────────────
def fill_contents(anchor):
    """Write the table of contents with dot leaders and real page numbers."""
    anchor.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anchor.paragraph_format.space_after = Pt(14)
    anchor.paragraph_format.line_spacing = 1.0
    r = anchor.add_run("TABLE OF CONTENTS")
    r.bold, r.font.size, r.font.name = True, Pt(CHAP), FONT
    cursor = anchor
    entries = [(1, t) for t in FRONT_MATTER] + contents
    for level, title in entries:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.0
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
    anchor.paragraph_format.line_spacing = 1.0
    r = anchor.add_run(heading_text)
    r.bold, r.font.size, r.font.name = True, Pt(CHAP), FONT
    cursor = anchor
    for label, title in items:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"{label}:  {title}")
        run.font.size, run.font.name = Pt(BODY), FONT
        cursor._p.addnext(p._p)
        cursor = p


fill(LOT_ANCHOR, "LIST OF TABLES", tables)
fill(LOF_ANCHOR, "LIST OF FIGURES", figures)
fill_contents(TOC_ANCHOR)

# The PDF driver needs the heading list to look each page number up.
with open(os.path.join(HERE, "toc-entries.json"), "w") as f:
    json.dump(FRONT_MATTER + [t for _, t in contents], f, indent=2)

page_numbers()
refresh_fields_on_open()
doc.save(OUT)
print(f"Saved {OUT}")
print(f"  figures: {len(figures)}   tables: {len(tables)}   "
      f"contents entries: {len(FRONT_MATTER) + len(contents)}"
      f"{'' if TOC_PAGES else '   (page numbers not filled in yet)'}")
