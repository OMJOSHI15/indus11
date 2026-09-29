"""
Build the Indus11 project report.

Chapter structure follows the report outline supplied by the team; formatting
reuses the SRS builder's conventions (Times New Roman, 16/14/12 pt, 1.5 line
spacing, justified text, 1 in margins, figures and tables numbered by chapter).
Layout comes from docs/docx_kit.py, shared with the SRS builder.

Data-derived figures come from docs/report_assets.py; build the PDF with

    python docs/make_srs_pdf.py report
"""
import docx_kit as kit
from docx_kit import *          # noqa: F401,F403 — the document-building vocabulary

OUT = os.path.expanduser("~/Downloads/Indus11_Project_Report.docx")
kit.use("report-toc-pages.json")

# ═════════════════════════════ PROJECT REPORT BODY ═════════════════════════════
from docx.enum.text import WD_COLOR_INDEX

ASSETS = os.path.join(HERE, "report-assets")
with open(os.path.join(HERE, "eval-layer-scores.json")) as f:
    LAYERS = json.load(f)["rows"]
with open(os.path.join(ASSETS, "ablation.json")) as f:
    ABLATION = json.load(f)
RULE_ONLY_TP = next(a["tp"] for a in ABLATION if a["layers"] == "Rule")
SUGGESTED = EVAL["suggested_thresholds"]


def mean(values):
    values = list(values)
    return sum(values) / len(values)


def sub(text):
    """Run-in label inside a section; not a heading, so not in the contents."""
    p = para(text, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, after=2)
    p.paragraph_format.keep_with_next = True
    return p


def eq(expression, number, size=BODY):
    """The expression centred on the line, its number flush with the right
    margin, so every number in the chapter lands in the same column. An
    expression that would wrap takes a smaller size instead: a wrapped line
    pushes its number out of that column."""
    p = para("", align=WD_ALIGN_PARAGRAPH.LEFT, after=6)
    stops = p.paragraph_format.tab_stops
    stops.add_tab_stop(Inches(USABLE_W / 2), WD_TAB_ALIGNMENT.CENTER)
    stops.add_tab_stop(Inches(USABLE_W), WD_TAB_ALIGNMENT.RIGHT)
    r = p.add_run("\t" + expression)
    r.italic, r.font.size, r.font.name = True, Pt(size), FONT
    r = p.add_run(f"\t({number})")
    r.font.size, r.font.name = Pt(BODY), FONT
    return p


def bullets(items):
    for item in items:
        bullet(item)


def term_table(items, widths=(1.6, 4.4)):
    """Two-column term/definition table without a numbered caption."""
    half = (len(items) + 1) // 2
    for part in (items[:half], items[half:]):
        t = doc.add_table(rows=1, cols=2)
        t.style = "Table Grid"
        for i, h in enumerate(["Abbreviation", "Expansion"]):
            c = t.rows[0].cells[i]
            c.text = ""
            r = c.paragraphs[0].add_run(h)
            r.bold, r.font.size, r.font.name = True, Pt(10.5), FONT
        for a, b in part:
            cells = t.add_row().cells
            for i, v in enumerate((a, b)):
                cells[i].text = ""
                p = cells[i].paragraphs[0]
                p.paragraph_format.line_spacing = CELL_LINE
                p.paragraph_format.space_after = Pt(1)
                r = p.add_run(v)
                r.font.size, r.font.name = Pt(10.5), FONT
            cells[0].width, cells[1].width = Inches(widths[0]), Inches(widths[1])
        keep_on_one_page(t)
        para("", after=10)


# ───────────────────────── FRONT MATTER ─────────────────────────
# The icon alone, not the wordmark: the registered title below is still Indus11.
doc.add_picture(os.path.join(HERE, "brand", "nirix-icon.png"), width=Inches(1.15))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.paragraphs[-1].paragraph_format.space_after = Pt(14)
para("PROJECT REPORT", CHAP, True, WD_ALIGN_PARAGRAPH.CENTER, 10)
para("INDUS11 — AI FINANCIAL RISK AND FRAUD DECISION ENGINE", CHAP, True,
     WD_ALIGN_PARAGRAPH.CENTER, 20)
para("A Software Group Project Report", BODY, False, WD_ALIGN_PARAGRAPH.CENTER, 4)
para("B.Tech Computer Engineering   |   Semester 5   |   Academic Year 2026-27", BODY,
     False, WD_ALIGN_PARAGRAPH.CENTER, 4)
para("Project ID: PRJ_CE_5_2026_7", BODY, False, WD_ALIGN_PARAGRAPH.CENTER, 20)
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
para("This is to certify that the project report entitled “Indus11 — AI Financial Risk "
     "and Fraud Decision Engine” is the bona fide work carried out by Joshi Om (24DCE052), "
     "Krish Gajera (24DCE040) and Drashti Dedaniya (24DCE029) of Semester 5, Department of "
     "Computer Engineering, DEPSTAR, CHARUSAT, in partial fulfilment of the requirements of "
     "the Software Group Project during the academic year 2026-27.", after=48)
_c = doc.add_table(rows=1, cols=2)
for i, txt in enumerate(["Dr. Deven Gol\nInternal Guide\nAssistant Professor\n"
                         "Computer Engineering",
                         "Head of Department\nComputer Engineering\nDEPSTAR, CHARUSAT"]):
    cell = _c.cell(0, i)
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = LINE
    r = p.add_run(txt)
    r.font.size, r.font.name = Pt(BODY), FONT
    cell.width = Inches(3.0)
para("", after=10)
para("Date: ______________                    Place: Changa")

new_page()
para("ACKNOWLEDGEMENT", CHAP, True, WD_ALIGN_PARAGRAPH.CENTER, 18)
para("We are grateful to our internal guide, Dr. Deven Gol, Assistant Professor, "
     "Department of Computer Engineering, DEPSTAR, for his guidance throughout the "
     "semester and for review comments that asked for measured results rather than "
     "claims.", after=10)
para("We thank Mr. Het Shah for the questions he raised at the first project review. "
     "Several of them (the latency of the language model inside the decision path, the "
     "behaviour of the dashboard when a data store is unavailable, and which graph pattern "
     "produces the most false positives) led directly to changes described in this "
     "report.", after=10)
para("We thank the Head of the Department of Computer Engineering and the Principal of "
     "DEPSTAR for the laboratory facilities and academic environment, and the faculty of "
     "the department for the foundation in databases and software engineering on which "
     "this work rests.", after=10)
para("We acknowledge the open-source projects this system is built on, among them "
     "FastAPI, MongoDB, Neo4j, Redis, ChromaDB, LangChain, Ollama and React.", after=10)
para("Finally, we thank our families for their support throughout this work.", after=24)
for n, sid in [("Joshi Om", "24DCE052"), ("Krish Gajera", "24DCE040"),
               ("Drashti Dedaniya", "24DCE029")]:
    para(f"{n} ({sid})", align=WD_ALIGN_PARAGRAPH.RIGHT, after=2)

new_page()
para("ABSTRACT", CHAP, True, WD_ALIGN_PARAGRAPH.CENTER, 18)
# The abstract is the team's own text, carried over from the SRS unchanged. The
# highlighted phrases are out of date against docs/eval-results.json and are left
# for the team to correct; nothing here rewrites their wording.
para("Indus11 is an AI-powered financial fraud detection and decision support system "
     "developed to identify suspicious banking transactions using a multi-layer risk "
     "assessment approach. The system addresses the limitations of conventional "
     "rule-based fraud detection by combining deterministic rules, graph-based "
     "relationship analysis, and Retrieval-Augmented Generation (RAG) to produce "
     "explainable risk decisions.")
para("The application is implemented using Python 3.12 and FastAPI for the backend "
     "APIs, React for the analyst dashboard, MongoDB (Beanie ODM) for transactional "
     "data storage, Neo4j for relationship analysis, Redis for caching, and ChromaDB "
     "as the vector database for document retrieval. LangChain and Ollama integrate "
     "the Large Language Model with the RAG pipeline, enabling the system to retrieve "
     "relevant banking policies, fraud guidelines, and historical cases before "
     "generating contextual explanations for analysts.")
para("Incoming transactions are evaluated through a three-layer scoring pipeline. The "
     "rule engine contributes 0–40 risk points based on predefined fraud indicators, "
     "graph analysis contributes 0–30 points by detecting shared devices, IP "
     "addresses, and circular transaction flows among accounts, while the RAG-based "
     "reasoning module contributes 0–30 points by validating contextual evidence. The "
     "combined score determines whether a transaction is classified as APPROVE, "
     "REVIEW, or BLOCK, while providing an explanation for every decision.")
_abs = para("", after=10)
# The wording is the team's. Only the figures are filled from the evaluation
# record, so a later run cannot leave the abstract disagreeing with Chapter 5
# the way it did when three runs were quoted across one document.
for text, stale in [
    ("The system was evaluated using a labelled fraud dataset and achieved ", False),
    (f"{FLAGGED['precision']*100:.1f}% precision", False),
    (f", {FLAGGED['recall']*100:.0f}% recall, and ", False),
    (f"an F1-score of {FLAGGED['f1']:.2f}", False),
    (". ", False),
    (f"Graph analysis successfully identified all {GRAPH['graph_flagged']} transactions "
     f"belonging to the 3 planted mule rings", False),
    (f", none of which the rule engine flagged on its own. During evaluation, "
     f"{CONF['BLOCK']['fraud']} transactions reached the predefined BLOCK threshold and no "
     f"legitimate transaction did. The three layers are complementary rather than "
     f"redundant: the rule engine alone flags {RULE_ONLY_TP} of the {COUNTS['fraud']} "
     f"fraudulent transactions, and all three together flag every one. The test set is "
     f"25% fraud against roughly one in a thousand in a live payment feed, so at that rate "
     f"the same detector's precision would fall to about "
     f"{REALISTIC['precision']*100:.0f}%.", False)]:
    r = _abs.add_run(text)
    r.font.size, r.font.name = Pt(BODY), FONT
    if stale:
        r.font.highlight_color = WD_COLOR_INDEX.YELLOW
new_page()
TOC_ANCHOR = doc.add_paragraph()
new_page()
LOF_ANCHOR = doc.add_paragraph()
new_page()
LOT_ANCHOR = doc.add_paragraph()

new_page()
para("LIST OF ABBREVIATIONS", CHAP, True, WD_ALIGN_PARAGRAPH.CENTER, 14)
term_table([
    ("API", "Application Programming Interface"), ("AUC", "Area Under the ROC Curve"),
    ("CI", "Continuous Integration"), ("CORS", "Cross-Origin Resource Sharing"),
    ("DFD", "Data Flow Diagram"), ("DPDP", "Digital Personal Data Protection"),
    ("ER", "Entity Relationship"), ("F1", "Harmonic mean of precision and recall"),
    ("FN", "False Negative"), ("FP", "False Positive"),
    ("FPR", "False-Positive Rate"), ("GNN", "Graph Neural Network"),
    ("HTTP", "Hypertext Transfer Protocol"), ("INR", "Indian Rupee"),
    ("JSON", "JavaScript Object Notation"), ("LLM", "Large Language Model"),
    ("ODM", "Object-Document Mapper"), ("p95", "95th percentile"),
    ("RAG", "Retrieval-Augmented Generation"), ("RBI", "Reserve Bank of India"),
    ("REST", "Representational State Transfer"), ("SHAP", "SHapley Additive exPlanations"),
    ("SRS", "Software Requirements Specification"), ("TP", "True Positive"),
    ("TTL", "Time To Live"), ("UML", "Unified Modeling Language"),
])

FRONT_MATTER = ["CERTIFICATE", "ACKNOWLEDGEMENT", "ABSTRACT", "TABLE OF CONTENTS",
                "LIST OF FIGURES", "LIST OF TABLES", "LIST OF ABBREVIATIONS"]
start_body_numbering()

# ───────────────────────── CHAPTER 1 ─────────────────────────
chapter("Introduction", new_page_first=False)
section("1.1 Background and Context")
para("Card and account-to-account payments are authorised in the time it takes a customer "
     "to finish tapping a card or confirming a transfer. The bank's fraud controls have to "
     "decide inside that window whether to let the payment through, hold it for a person "
     "to look at, or refuse it. Getting that decision wrong in one direction loses money; "
     "getting it wrong in the other blocks a legitimate customer.")
para("Much of the fraud that matters is invisible in a single payment. A money-mule ring "
     "moves funds around a loop of accounts and keeps a small fee at each hop, which leaves "
     "every individual transfer looking ordinary. Synthetic identities surface as a handful "
     "of accounts that appear unrelated until you notice they share a device or a network "
     "address. Catching either one means looking at how accounts relate to each other, and "
     "not only at the payment currently in front of the system.")
para("In India the Reserve Bank's 2024 Master Directions on fraud risk management require "
     "regulated entities to maintain frameworks for the prevention, early detection and "
     "timely reporting of fraud [1]. Detection that a bank cannot explain is hard to act on "
     "under such a framework: an analyst has to be able to say why a transaction was held.")
section("1.2 Problem Statement")
para("Design and build a decision service that accepts one financial transaction, scores its "
     "risk from 0 to 100 and returns APPROVE, REVIEW or BLOCK, such that:")
bullets([
    "the decision is returned within a 500 millisecond budget;",
    "coordinated fraud that no single-transaction rule can see (circular flows, shared "
    "devices and addresses, proximity to known fraud) contributes to the score;",
    "every decision carries a written explanation that is consistent with the signals that "
    "actually fired; and",
    "the detection is measured on labelled data, with its limits stated, rather than "
    "asserted.",
])
section("1.3 Motivation")
para("Every common approach to transaction fraud satisfies some of these requirements at "
     "the cost of others. Hand-written rules are fast and auditable, and they look at one "
     "transaction at a time, which is exactly the blind spot a mule ring exploits. A "
     "supervised model learns patterns no rule author would think to write down, but it "
     "wants a large labelled dataset that a student project does not have, and what it "
     "offers by way of reasoning is a list of feature weights or a fixed reason code. "
     "Language models write the fluent explanation the other two cannot. The cost showed up "
     "as soon as we measured it: a local model took 13 to 14 seconds on a single "
     "transaction, and at its default settings it scored the same transaction five "
     "different ways in five runs.")
para("Indus11 therefore gives each technique only the part of the problem it is suited to. "
     "Rules and graph queries decide. The language model explains afterwards, working from "
     "the evidence the other two layers have already produced.")
section("1.4 Objectives")
bullets([
    "Score each transaction from 0 to 100 as the sum of a rule layer (0–40), a graph layer "
    "(0–30) and a retrieval-augmented language-model layer (0–30), and map the score to "
    "APPROVE, REVIEW or BLOCK.",
    "Return the rule-and-graph decision within 500 ms and attach the language-model score "
    "and explanation afterwards.",
    "Detect money-mule cycles, shared-device and shared-address clusters and proximity to "
    "known fraud accounts in a Neo4j transaction graph.",
    "Ground the written explanation in the triggered flags and withhold an explanation that "
    "does not refer to them.",
    "Provide an analyst dashboard with live statistics, flagged transactions and a decision "
    "override.",
    "Measure precision, recall and F1 on a labelled dataset and report what they would be at "
    "a realistic fraud rate.",
])
section("1.5 Scope")
para("Indus11 takes one transaction over a REST interface, analyses it with three detection "
     "layers, and returns a composite score, a decision and an explanation. An analyst works "
     "from a web dashboard, where the statistics, the flagged transactions and the override "
     "control all live. What the system does not do matters as much for a reader judging it: "
     "it moves no money and settles no payments, it is not a core banking system, and it "
     "files nothing with a regulator. All the data it has processed is synthetic. Training a "
     "supervised model was out of reach in one semester and is listed as future work.")
section("1.6 Research/Design Questions")
table("Design questions and where they are answered",
      ["ID", "Question", "Answered in"],
      [["Q1", "Can the approve/review/block decision be returned within 500 ms when one layer "
              "depends on a language model that takes seconds?", "Sections 4.9, 5.6"],
       ["Q2", "Does relationship analysis catch fraud that single-transaction rules cannot?",
        "Section 5.5"],
       ["Q3", "Can a generated explanation be kept consistent with the evidence that "
              "produced the decision?", "Sections 3.5, 6.6"],
       ["Q4", "How much of the measured precision survives at a realistic fraud rate?",
        "Section 5.8"],
       ["Q5", "Does an identical transaction always receive an identical score?",
        "Section 5.6"]],
      widths=[0.5, 4.3, 1.2],
      note="The three questions the project set out to answer, each paired with the section that reports the measurement answering it.")
section("1.7 Contributions")
bullets([
    "A five-layer decision pipeline in which the rule engine and graph analyzer decide "
    "concurrently within the latency budget and the language-model layer runs afterwards "
    "without delaying the response.",
    "An explanation step that gives the language model the triggered flags as confirmed "
    "facts, followed by a guard that withholds an explanation which ignores them.",
    "Time-windowed, chronologically ordered cycle detection in Cypher, which reduced the "
    "circular-flow pattern's false-positive rate from 44.9 to 10.3 per cent and its query "
    "time from 260 ms to about 20 ms.",
    "An evaluation harness that replays a labelled dataset through the live API, sweeps the "
    "decision thresholds and reports precision at a realistic fraud prevalence.",
    "An analyst dashboard and a one-command local stack, with 101 automated tests run in "
    "continuous integration.",
])
section("1.8 Report Organization")
para("Chapter 2 reviews existing approaches, technologies and commercial systems and "
     "identifies the gap this project addresses. Chapter 3 describes the proposed "
     "methodology: the architecture, components, data flow, scoring algorithm and its "
     "mathematical form. Chapter 4 covers the implementation, from the environment and "
     "dataset to the modules and user interface. Chapter 5 sets out the evaluation and its "
     "results, and Chapter 6 discusses them, including an analysis of the errors. Chapter 7 "
     "considers security, privacy, ethics and deployment risk, and Chapter 8 concludes. "
     "References and appendices follow.")

# ───────────────────────── CHAPTER 2 ─────────────────────────
chapter("Literature Review")
section("2.1 Existing Approaches")
sub("Rule-based systems")
para("The oldest form of transaction screening is still the most widespread: a set of "
     "explicit rules covering a blacklist, velocity limits, amount thresholds and "
     "merchant-category restrictions. A rule runs fast, returns the same answer every time "
     "and can be read by an auditor. What it cannot do is look past the transaction in "
     "front of it and that account's own history, so activity coordinated across several "
     "accounts passes unnoticed.")
sub("Supervised machine learning")
para("Supervised models learn fraud patterns from labelled historical transactions. One "
     "such study, by Vijayanand and Smrithy, trained a voting ensemble on the synthetic "
     "PaySim mobile-money dataset of 6,362,620 records and used SHAP values to explain "
     "individual predictions [4]. Work of this kind depends on a large labelled dataset, "
     "and where fraud is rare it depends further on careful treatment of class imbalance. "
     "The explanation it produces is a feature attribution.")
sub("Network and graph-based detection")
para("APATE, the system built by Van Vlasselaer and colleagues, drew features from the "
     "network of cardholders and merchants as well as from the transaction itself; those "
     "combined models were their strongest, reaching an AUC above 0.98 on more than three "
     "million card transactions [2]. A later extension by Lebichot and colleagues propagated "
     "fraud labels across the transaction graph semi-supervised, which multiplied precision "
     "among the top 100 alerts by three on a real e-commerce dataset [3]. Both results are "
     "the basis for this project's graph layer and its fraud-label propagation, and the "
     "patterns themselves follow the shapes Neo4j documents for fraud analytics [16].")
sub("Graph neural networks")
para("More recent work learns directly on the graph. Two reviews of graph neural networks "
     "for financial fraud detection report that they capture relational patterns tabular "
     "models miss [5], [6]. There is a catch, documented by Dou and colleagues: fraudsters "
     "camouflage themselves by connecting to legitimate nodes, and CARE-GNN was proposed to "
     "resist exactly that [7]. On Bitcoin transactions, Weber and colleagues put graph "
     "convolutional networks to work on anti-money-laundering [8].")
sub("Language models and retrieval")
para("Retrieval-augmented generation supplies a language model with documents retrieved "
     "from a knowledge base as context for its answer [9]. A 2024 survey of large language "
     "models in finance reviews their use across financial tasks and discusses the "
     "reliability concerns that come with them [10].")
section("2.2 Existing Technologies/Methods")
table("Technologies and methods considered",
      ["Method", "Strength", "Weakness", "Use in Indus11"],
      [["Rule engine", "Fast, deterministic, auditable", "One transaction at a time",
        "Layer 2, 0–40 points"],
       ["Supervised ensemble", "Learns subtle patterns", "Needs large labelled data",
        "Not used; future work"],
       ["Graph database queries", "Finds cycles and shared identities", "Query cost grows "
        "with the graph", "Layer 3 in Neo4j, 0–30 points"],
       ["Graph neural network", "Learns relational patterns", "Needs labels and training",
        "Not used"],
       ["SHAP or LIME [11], [12]", "Per-prediction attribution", "Explains a model, not the "
        "evidence", "Not used"],
       ["Retrieval + language model", "Written explanation from context", "Slow, can "
        "invent details", "Layer 4, after the decision"]],
      size=10,
      note="The detection methods weighed for this system, what each is good and poor at, and whether Indus11 ended up using it.")
section("2.3 Recent Research")
para("The reviews by Motie and Raahemi [5] and by Cheng and colleagues [6] document how "
     "quickly graph neural networks have become the dominant research direction for "
     "financial fraud, and both note the difficulty of obtaining realistic labelled graph "
     "data. The CARE-GNN work [7] is a reminder that graph signals can be gamed by a "
     "fraudster who links to legitimate accounts, which bears on this project's shared-device "
     "and cluster-proximity checks. On the language-model side, the survey by Nie and "
     "colleagues [10] treats hallucination and reliability as open problems for financial "
     "use, which is the failure the explanation guard in this project is designed to catch.")
para("Two public datasets recur in this literature. PaySim is a simulator of mobile-money "
     "transactions calibrated on a real service [17], and the IEEE-CIS fraud detection "
     "dataset was released through a public competition [18]. Neither was used in this "
     "semester's evaluation, which relies on a synthetic dataset built for the planted "
     "patterns; validating against one of them is future work.")
section("2.4 Comparative Analysis")
para("The comparison below places Indus11 beside three commercial platforms, using their "
     "public product descriptions [13], [14], [15]. The commercial systems have not been "
     "measured by this team, so the table compares design choices, not accuracy.")
table("Commercial fraud platforms compared with Indus11",
      ["Aspect", "FICO Falcon", "Feedzai", "Featurespace ARIC", "Indus11"],
      [["Core method", "Neural networks on consortium card data",
        "Machine-learning platform", "Adaptive behavioural analytics",
        "Rules, graph queries, retrieval + LLM"],
       ["Graph analysis", "Entity linking", "Network features", "Behavioural profiles",
        "Native: cycles, shared device and IP, cluster proximity"],
       ["Explanation", "Reason codes", "Reason codes and attributions",
        "Model reporting", "Written, checked against triggered flags"],
       ["New fraud pattern", "Retraining", "Retraining or rules", "Self-learning",
        "Add a knowledge-base document"],
       ["Training data", "Large consortium", "Large labelled set", "Behavioural history",
        "None for rules and graph"],
       ["Deployment", "Licensed", "Licensed", "Licensed (Visa since 2024)",
        "Open-source stack, runs locally"]],
      size=9.5,
      note="Three commercial platforms set against Indus11 on method, graph analysis and explainability, from vendor material rather than measurement.")
section("2.5 Research/Technical Gap")
bullets([
    "Commercial explanations are reason codes from a fixed vocabulary; the analyst still has "
    "to assemble the story.",
    "Generated explanations are fluent, but nothing in a typical retrieval-augmented "
    "pipeline checks them against the evidence that produced the decision.",
    "Graph neural networks need labelled graph data and training infrastructure that a small "
    "team or a new deployment does not have, and a language model measured at 13–14 seconds "
    "cannot sit inside an authorisation decision.",
])
section("2.6 Positioning of Proposed Work")
para("Indus11 does not compete with consortium-trained models on accuracy; it occupies a "
     "narrower position. Rules and graph queries, needing no training data, decide inside the "
     "latency budget, and a local language model then explains that decision from the flags "
     "they produced.")

# ───────────────────────── CHAPTER 3 ─────────────────────────
chapter("Proposed Methodology")
section("3.1 System Overview")
para("A payment system submits a transaction to POST /api/v1/transactions/analyze. The "
     "service loads the sender's and receiver's profiles, then runs the rule engine and the "
     "graph analyzer against the transaction at the same time. Their two scores become a "
     "provisional decision, which is stored and returned to the caller. Only then does a "
     "background task go to the retrieval-augmented language model for a score and an "
     "explanation, recompute the composite and update the stored record. The analyst's view "
     "of all this is a dashboard: the decision mix, the flagged transactions, and the "
     "control that overrides a decision under review. The actors and the services each of "
     "them uses are drawn in the use case diagram of the specification.")
section("3.2 System Architecture")
para("Five layers make up the system (Figure 3.1). The FastAPI gateway is Layer 1, which "
     "validates the request and loads profiles from Redis, falling back to MongoDB when the "
     "cache misses. Scoring happens in parallel across Layers 2 and 3. Their totals go to "
     "Layer 5, the decision engine, which adds them up and maps the result to a decision. "
     "That leaves Layer 4, the retrieval-augmented pipeline, which runs once the response "
     "has already been sent. It sat inside the request path until the first project review, "
     "where its latency was judged incompatible with a payment decision.")
figure("01-architecture.png", "System architecture — five-layer pipeline",
      note="The five layers a transaction passes through. The three scoring layers run concurrently and read four separate stores; their scores meet in the decision engine, which returns the band and the explanation.")
section("3.3 System Components")
table("System components",
      ["Component", "Technology", "Responsibility"],
      [["Gateway", "FastAPI, Pydantic", "Validation, profile loading, rate limiting"],
       ["Rule engine", "Python, Redis", "Blacklist, velocity, amount, merchant, risk tier"],
       ["Graph analyzer", "Neo4j, Cypher", "Shared device and IP, cycles, cluster proximity"],
       ["RAG pipeline", "ChromaDB, LangChain, Ollama", "Retrieval, LLM score and explanation"],
       ["Decision engine", "Python", "Composite score, decision band, explanation guard"],
       ["Document store", "MongoDB, Beanie", "Accounts and the audit trail of decisions"],
       ["Dashboard", "React, Vite, Recharts", "Statistics, flagged transactions, override"]],
      size=10,
      note="Each component of the pipeline, the technology it is built on, and the single responsibility it holds.")
section("3.4 Workflow/Data Flow")
para("Figure 3.2 decomposes the system into seven processes and five data stores. The "
     "activity and sequence diagrams in the specification follow one transaction across the "
     "participants and show the calls in the order they occur, including the point at which "
     "the response is returned and the background work begins.")
figure("final-dfd1.png", "Data flow diagram — Level 1",
      note="The same pipeline seen as data rather than components: the processes that turn a submitted transaction into a stored decision, and the stores each one reads from and writes to.")
section("3.5 Proposed Algorithm/Model")
para("The scoring model is additive and transparent: each check that fires adds a fixed "
     "number of points and a flag that names it, and each layer is capped at its budget. "
     "Algorithm 1 gives the request path.")
sub("Algorithm 1: Analyse a transaction")
code_block("""input : transaction tx
output: provisional decision, returned to the caller
1  sender, receiver <- load_profile(tx.sender), load_profile(tx.receiver)
2  (R, rule_flags), (G, graph_flags) <- in parallel:
       rule_engine(tx, sender, receiver), graph_analyzer(tx)
3  S <- min(R + G, 100);  decision <- band(S, failed layers)
4  insert record(tx, S, decision, rag_pending = true)     # 409 if tx_id exists
5  schedule background (4 at a time, 180 s limit):
6      (L, text) <- rag_pipeline(tx, sender, rule_flags + graph_flags)
           on error or timeout: L <- 0, language model marked failed
7      S <- min(R + G + L, 100);  decision <- band(S, failed layers)
8      if flags fired and text names none of them: text <- flag list only
9      update record(S, decision, text, failed layers, rag_pending = false)
10 return decision, S, flags

band(S, F): APPROVE if S < 40, REVIEW if S < 70, else BLOCK;
            an APPROVE becomes REVIEW when any layer in F failed""")
para("The graph layer's cycle check (Algorithm 2) looks for a path of two to four transfers "
     "that leaves the sender and returns to it, restricted to the last 72 hours and to hops in "
     "time order, and stops at the first match. The specification decomposes the rule "
     "engine's checks in its level 2 data flow diagram and gives the lifecycle of a stored "
     "record in its state diagram.")
sub("Algorithm 2: Circular-flow and mule check")
code_block("""cutoff <- tx.timestamp - 72 h
if exists path (a {id: tx.sender}) -[SENT*2..4]-> (a)
       where every hop.timestamp >= cutoff and hops are in time order:
    G <- G + 12, flag CIRCULAR_FLOW
    if some such path has every amount within 75-100% of the previous hop:
        G <- G + 8, flag MONEY_MULE_PATTERN""")
section("3.6 Mathematical Formulation")
para("Let R, G and L be the rule, graph and language-model scores of a transaction. The rule "
     "score is the sum of the weights w of the rules that fire, capped at 40, except that a "
     "blacklisted sender or receiver sets it to 40 directly:")
eq("R = 40 if blacklisted, otherwise min( Σ w_i , 40 )", "3.1")
eq("G = min( Σ w_j , 30 ),     L ∈ [0, 30]", "3.2")
eq("S = min( R + G + L , 100 )", "3.3")
para("The decision band uses a review threshold τ_r = 40 and a block threshold τ_b = 70:")
eq("D(S) = APPROVE if S < τ_r;   REVIEW if τ_r ≤ S < τ_b;   BLOCK if S ≥ τ_b", "3.4")
para("If a layer could not run it contributes no points, and a D(S) of APPROVE is raised to "
     "REVIEW: a layer that never looked at the transaction is missing evidence, not evidence "
     "that it is safe. A BLOCK reached by the layers that did run is kept.")
para("For account a with monthly average μ_a, the velocity count n_a is the number of its "
     "transactions in the last 600 seconds, and the two account-level rules fire when")
eq("n_a > 5      and      x > 3 μ_a  (with μ_a > 0)", "3.5")
para("The banking anomaly rules use the sender's history kept in Redis: the time of its last "
     "payment t_prev, whether it has paid this receiver before, the number of distinct payees "
     "p_24 in the last day and the amount I_24 it received in the last day. With x the amount "
     "and T = ₹10,00,000 the reporting threshold, they fire when")
eq("0.9 T ≤ x < T;  t − t_prev ≥ 180 d;  new payee ∧ x ≥ ₹50,000;  "
   "I_24 ≥ ₹10,000 ∧ 0.8 I_24 ≤ x ≤ 1.1 I_24;  p_24 > 5", "3.5a", size=8)
para("A cycle of k hops with timestamps t_1 … t_k and amounts a_1 … a_k counts as circular "
     "flow, and as a mule chain, when")
eq("2 ≤ k ≤ 4,   t − 72 h ≤ t_1 ≤ t_2 ≤ … ≤ t_k;     0.75 a_i ≤ a_(i+1) ≤ a_i", "3.6")
para("With TP, FP and FN the true positives, false positives and false negatives, the "
     "evaluation uses")
eq("P = TP / (TP + FP),     R = TP / (TP + FN),     F1 = 2PR / (P + R)", "3.7")
para("Precision depends on the fraud prevalence π of the traffic, whereas recall r and the "
     "false-positive rate f do not. Holding r and f fixed, the precision the same detector "
     "would show at prevalence π is")
eq("P(π) = r π / ( r π + f (1 − π) )", "3.8")
section("3.7 Parameters and Configuration")
table("Parameters and their configured values",
      ["Parameter", "Value", "Where set"],
      [["Review / block thresholds", "40 / 70", "REVIEW_THRESHOLD, BLOCK_THRESHOLD"],
       ["Layer budgets (rule / graph / LLM)", "40 / 30 / 30", "Layer code"],
       ["Rule weights", "Blacklist 40, velocity 15, amount 12, merchant 8, tier 5 or 2; the 25 "
        "banking anomaly weights are listed in Table 4.5", "rule_engine.py"],
       ["Banking anomaly thresholds", "Reporting limit ₹10,00,000; UPI limit ₹1,00,000; large "
        "payment ₹50,000; dormant 180 days; 24 h history windows; impossible travel 900 km/h over "
        "at least 100 km", "rule_engine.py"],
       ["Velocity window and limit", "600 s, more than 5", "rule_engine.py"],
       ["Amount anomaly multiplier", "3 × monthly average", "rule_engine.py"],
       ["Graph weights", "Device 15, cycle 12, cluster 10, mule 8, IP 8", "graph_analyzer.py"],
       ["Cycle length and window", "2–4 hops, 72 h", "graph_analyzer.py"],
       ["Retrieved patterns", "3 nearest of 58", "rag_pipeline.py"],
       ["Language model", "llama3 via Ollama, temperature 0", "rag_pipeline.py"],
       ["Background concurrency and timeout", "4 tasks, 180 s", "transactions.py"],
       ["Profile cache TTL", "300 s", "transactions.py"],
       ["Rate limits", "120/min overall, 30/min on analyse", "rate_limit.py"]],
      size=10,
      note="Every tunable value the system runs on, the setting used for the reported results, and the file or environment variable that holds it.")
para("The 40/30/30 split follows the certainty of each layer's evidence. The rule engine "
     "checks facts, the graph layer infers from structure, and the language model infers from "
     "similarity. The rule budget sits below the block threshold on purpose: no single layer "
     "can block a transaction, and a blacklisted account lands exactly on the review "
     "boundary.")
section("3.8 Security/Privacy Considerations")
bullets([
    "The three routes that change stored state (the decision override, the blacklist toggle "
    "and fraud-label propagation), together with the component status and restart routes, "
    "require a shared key in the X-API-Key header, compared in constant time.",
    "Browser access is restricted to configured origins, and every client is rate-limited.",
    "Every request is validated against a schema; the merchant category must be one of 11 "
    "fixed values and the free-text fields are length-capped, so submitted text cannot be "
    "used to redirect the language model's assessment.",
    "The flags given to the language model come from the system's own layers, not from the "
    "request.",
    "The language model runs locally, so transaction details are not sent to an external "
    "service in the default configuration.",
    "Only synthetic data is processed; credentials are read from environment variables and "
    "never committed.",
])
section("3.9 Assumptions")
bullets([
    "The four data stores are reachable. If one is not, the affected layer is recorded as "
    "failed, the others still score, and a transaction that would have been approved is held "
    "for review.",
    "An account with no stored profile is treated as elevated risk rather than as safe.",
    "The synthetic dataset is adequate for comparing configurations with one another, not "
    "for predicting production accuracy.",
    "Thresholds are tunable per deployment; the values in this report are the defaults.",
])

# ───────────────────────── CHAPTER 4 ─────────────────────────
chapter("Implementation")
section("4.1 Hardware Requirements")
table("Hardware requirements and the development machine",
      ["Item", "Minimum", "Development machine"],
      [["Processor", "64-bit x86 or ARM", "Apple M4 (arm64)"],
       ["Memory", "8 GB", "16 GB"],
       ["Graphics processor", "Not required", "None used"],
       ["Disk", "About 5 GB free", "Solid-state"]],
      note="The minimum machine the stack needs, beside the machine on which every measurement in this report was produced.")
section("4.2 Software Requirements")
table("Software used and versions",
      ["Software", "Version", "Purpose"],
      [["Python", "3.12.13", "Backend runtime"],
       ["FastAPI / Uvicorn", "0.111.0 / 0.29.0", "REST API and server"],
       ["Pydantic", "2.7.4", "Request and response schemas"],
       ["Motor / Beanie", "3.7.1 / 1.30.0", "Async MongoDB driver and ODM"],
       ["MongoDB", "7.0.28", "Document store"],
       ["Neo4j (driver / server)", "5.20.0 / 2026.05.0", "Transaction graph"],
       ["Redis", "8.8.0 (redis-py 5.0.4)", "Profile cache, velocity window"],
       ["LangChain / ChromaDB", "0.2.1 / 0.5.0", "Retrieval pipeline and vector store"],
       ["Ollama / llama3", "0.33.2", "Local language model"],
       ["slowapi", "0.1.9", "Rate limiting"],
       ["React / Vite / Recharts", "18.3 / 5.2 / 2.12", "Dashboard"],
       ["Node.js", "26.5.0", "Dashboard build"],
       ["pytest / httpx", "8.2.1 / 0.27.0", "Tests and evaluation client"]],
      size=10,
      note="Every runtime and library the system depends on, pinned to the exact version the reported results were produced with.")
para("Each of these is used as its own documentation describes. The API follows the FastAPI "
     "conventions for dependency injection and background tasks [20]; the graph queries are "
     "written against the Cypher manual [21]; the vector store follows the ChromaDB "
     "collection and query interface [22]; and the local model is served by Ollama [23] "
     "running Meta's Llama 3 [24]. No component is used in a way its documentation does not "
     "describe, which matters for a project that has to be reproducible on another machine.")
section("4.3 Development Environment")
para("Development took place on macOS 26.5 on an Apple M4 machine with no graphics "
     "processor. The backend runs from a Python 3.12 virtual environment, with MongoDB, "
     "Neo4j and Redis installed as Homebrew services. One command, scripts/run_local.sh, "
     "brings up the databases, the API and the dashboard together; it also clears a stale "
     "Neo4j process file that had twice stopped the database from starting. Docker Compose "
     "defines the same stack for anyone who prefers it. The source lives in Git on GitHub, "
     "where a continuous-integration workflow runs the test suite on every push. PlantUML "
     "and Graphviz draw the diagrams. This report is itself generated from Python with "
     "python-docx and converted with LibreOffice.")
section("4.4 Dataset/Input Data")
para("No real customer or payment data is used anywhere in this project. Everything the "
     "system and its evaluation consume comes from three synthetic sources, each generated "
     "deterministically so that every team member is working with the same data (Table 4.3).")
table("Synthetic data sources",
      ["Source", "Contents", "Generator"],
      [["Transaction graph", "500 accounts; 3 mule rings of 4, 5 and 3 accounts, each cycling "
        "4 times and losing 5–12% per hop; 2 shared-device clusters; 1 shared-IP cluster of 8 "
        "accounts; 940 background transfers; 5 known fraud accounts", "scripts/seed_neo4j.py"],
       ["Account profiles", "20 accounts across standard, elevated and high risk tiers, 2 "
        "blacklisted, averages in INR", "scripts/seed_mongo.py"],
       ["Evaluation set", f"{COUNTS['total']} labelled transactions: 36 mule-ring hops, 10 "
        f"shared-device and 6 shared-IP transactions ({COUNTS['fraud']} fraud) and "
        f"{COUNTS['legit']} ordinary transactions", "scripts/evaluate.py"],
       ["Knowledge base", "58 fraud-pattern documents typed as synthetic identity, money mule, "
        "account takeover, wire fraud and others", "app/services/fraud_kb.py"]],
      size=10,
      note="The three generated datasets the system was built and measured on, what each contains, and the script that produces it deterministically.")
para("The entity relationship diagram in the specification relates the stored entities "
     "across the two stores that hold them.")
section("4.5 Data Preprocessing")
bullets([
    "Schema validation rejects a non-positive amount, a currency code longer than three "
    "characters, a merchant category outside the fixed list and over-long free text before "
    "any analysis runs.",
    "Seeded account averages are stored in rupees (the original synthetic values multiplied "
    "by 80), so the amount-anomaly rule compares like with like.",
    "An unknown account is given a default profile with elevated risk and a zero average, "
    "which disables the amount rule for it rather than dividing by nothing.",
    "Timestamps are stored in ISO 8601 form, which sorts chronologically as text; this lets "
    "the cycle query prune by time during path expansion.",
    "The retrieval query is built from the amount, merchant category, risk tier and device, "
    "and the language model's reply is parsed by scanning for the first complete JSON object, "
    "because the local model sometimes echoes an example before its answer.",
    "Stored explanations are truncated to 2,000 characters.",
])
section("4.6 Module Implementation")
table("Modules and responsibilities",
      ["Module", "File", "Owner"],
      [["Gateway and persistence", "app/api/routes/transactions.py", "Joshi Om"],
       ["Rule engine", "app/services/rule_engine.py", "Joshi Om"],
       ["Cache and velocity window", "app/core/redis_client.py", "Joshi Om"],
       ["API-key guard, rate limiting", "app/core/security.py, rate_limit.py", "Joshi Om"],
       ["Graph analyzer, label propagation", "app/services/graph_analyzer.py", "Krish Gajera"],
       ["Graph API", "app/api/routes/graph.py", "Krish Gajera"],
       ["Synthetic graph dataset", "scripts/seed_neo4j.py", "Krish Gajera"],
       ["RAG pipeline, knowledge base", "app/services/rag_pipeline.py, fraud_kb.py",
        "Drashti Dedaniya"],
       ["Decision engine", "app/services/decision_engine.py", "Drashti Dedaniya"],
       ["Dashboard", "dashboard/src", "Drashti Dedaniya"],
       ["Evaluation harness", "scripts/evaluate.py", "Team"]],
      size=10,
      note="Each module of the system, the file it lives in, and the team member who owns it.")
sub("Rule engine")
para("The rule engine is one asynchronous function that receives the transaction and both "
     "profiles. It returns the maximum score immediately for a blacklisted party; otherwise it "
     "records the transaction in a Redis sorted set keyed by account, counts the entries "
     "within the last ten minutes, and applies the amount, merchant and risk-tier rules. "
     "Twenty-five banking anomaly rules follow, taken from the red-flag indicators FIU-IND and "
     "the RBI publish for suspicious-transaction reporting, FATF money-laundering typologies "
     "and card-network fraud patterns. They read each account's recent history from Redis "
     "(last payment, payees, devices, IP addresses, location, merchant categories, money in "
     "and out over 24 hours) in the same round trip that records the payment, so every read "
     "describes the account before this transaction. If "
     "Redis cannot be reached, the layer is marked as failed with RULE_ENGINE_ERROR and the "
     "error, rather than failing the whole request.")
para("Fifty banking anomalies were catalogued. Thirty-five are detected, thirty by the rule "
     "engine and five by the graph analyzer, and are listed in Table 4.5 with the "
     "points each awards. The rule engine's total stays capped at 40, so many rules firing together "
     "cannot decide a transaction on their own.")
table("Banking anomalies detected",
      ["#", "Anomaly", "Layer", "Points"],
      [['1', 'Blacklisted sender or receiver', 'Rule', '40'],
       ['2', 'Velocity burst, more than 5 payments in 10 min', 'Rule', '15'],
       ['3', "Amount over 3 × the account's average", 'Rule', '12'],
       ['4', 'High-risk merchant category', 'Rule', '8'],
       ['5', 'High or elevated customer risk tier', 'Rule', '5 / 2'],
       ['6', 'Structuring just under the ₹10 lakh reporting limit', 'Rule', '10'],
       ['7', 'Dormant account reactivated after 180 days', 'Rule', '10'],
       ['8', 'Large first payment to a new beneficiary', 'Rule', '8'],
       ['9', 'Pass-through: 80–110% of money received in 24 h sent on', 'Rule', '12'],
       ['10', 'Fan-out to more than 5 payees in 24 h', 'Rule', '8'],
       ['11', 'Large payment between 00:00 and 04:59 IST', 'Rule', '5'],
       ['12', 'Smurfing: payments under ₹10 lakh totalling over it in 24 h', 'Rule', '12'],
       ['13', 'Fan-in: more than 10 senders into one account in 24 h', 'Rule', '8'],
       ['14', 'Payment of ₹10 or less followed within an hour by ₹10,000 or more', 'Rule', '10'],
       ['15', 'Impossible travel: over 900 km/h between located payments', 'Rule', '12'],
       ['16', 'New device on an established account, ₹50,000 or more', 'Rule', '8'],
       ['17', 'New IP address on an established account, ₹50,000 or more', 'Rule', '6'],
       ['18', 'Device hopping: more than 3 devices in 24 h', 'Rule', '8'],
       ['19', 'Daily outflow over 10 × the usual payment', 'Rule', '8'],
       ['20', 'Three or more round-amount payments in 24 h', 'Rule', '5'],
       ['21', 'Same amount to the same payee three or more times in 24 h', 'Rule', '8'],
       ['22', 'Back-and-forth: receiver paid the sender in the last 24 h', 'Rule', '8'],
       ['23', 'Repeated payments just under the ₹1 lakh UPI limit', 'Rule', '6'],
       ['24', "A new account's first payment is ₹50,000 or more", 'Rule', '6'],
       ['25', 'First-ever payment to a high-risk merchant category', 'Rule', '6'],
       ['26', 'Foreign currency on an Indian account', 'Rule', '4'],
       ['27', 'Receiver in a FATF high-risk jurisdiction', 'Rule', '10'],
       ['28', 'Payment note uses scam phrases (KYC, OTP, lottery, refund…)', 'Rule', '8'],
       ['29', 'More than 10 payers to one merchant ID in 10 min', 'Rule', '10'],
       ['30', 'Account draining: three payments of ₹50,000 or more in 1 h', 'Rule', '10'],
       ['31', 'Device shared by more than 2 accounts', 'Graph', '15'],
       ['32', 'IP address shared by more than 3 accounts', 'Graph', '8'],
       ['33', 'Circular flow back to the sender within 4 hops and 72 h', 'Graph', '12'],
       ['34', 'Mule chain keeping 75–100% at each hop', 'Graph', '8'],
       ['35', 'Receiver within two links of a known fraud account', 'Graph', '10']],
      widths=[0.35, 3.4, 0.75, 0.6], size=9,
      note="All thirty-five banking anomalies the system detects, each with the layer that catches it and the points it contributes to the composite score. The fifteen types that are still not detected are set out in Section 6.6 with the data each would need.")
para("The remaining fifteen need data this system never receives, and are recorded here "
     "rather than dropped. Five want channel or balance information: cash spread across "
     "branches, a deposit followed by a withdrawal in another city, an account emptied to "
     "near zero, volume out of line with a declared income, and a salary account taking "
     "third-party credits. Four want identity and account-change records: several accounts "
     "sharing a PAN, phone or address, a contact detail changed just before a large payment, "
     "a SIM swap, and a beneficiary added and paid within minutes. Three want logs the "
     "system does not hold: failed logins or one-time-password attempts, a history of "
     "chargebacks, and loan disbursal records. The last three are outside a transaction "
     "monitor altogether: cheque kiting, trade-based laundering through mis-invoicing, and "
     "sanctions or politically-exposed-person matching, each of which needs a source of its "
     "own.")

sub("Graph analyzer")
para("The graph analyzer first merges the transaction, its accounts, device and address into "
     "Neo4j, then runs four checks in one session: shared device, circular flow with the mule "
     "sub-check, shared address, and receiver proximity to a known fraud account through "
     "connection edges. A failure marks the layer as failed with GRAPH_ANALYZER_ERROR and the "
     "error, instead of failing the request.")
sub("Retrieval-augmented pipeline")
para("The pipeline retrieves the three most similar of 58 pattern documents from ChromaDB and "
     "sends the transaction, the retrieved patterns and the flags already raised by the other "
     "two layers to llama3 at temperature zero. It returns a score capped at 30 and an "
     "explanation. If the model cannot be reached, fails or times out, the layer is marked as "
     "failed with RAG_PIPELINE_ERROR.")
sub("Decision engine")
para("The decision engine sums the three scores, caps the total at 100, applies the bands and "
     "prefixes the explanation with the list of triggered signals. Unless the language-model "
     "result is still pending, it checks that the explanation names at least one triggered "
     "flag and otherwise shows the flag list alone.")
para("When a layer is marked as failed, the engine names it in the explanation, records it "
     "with the transaction, and raises an APPROVE to REVIEW. Only flags from layers that ran "
     "count as evidence for the explanation check, and a failed language model contributes no "
     "text.")
section("4.7 Algorithm/Model Implementation")
para("Two excerpts show how the algorithms of Section 3.5 are implemented. The cycle query "
     "prunes hops by an ISO 8601 cutoff during expansion and stops at the first match, because "
     "only existence matters:")
para("The explanation guard matches the first five letters of each distinctive word in the "
     "flag codes, so that prose saying “blacklist” satisfies BLACKLISTED_ACCOUNT, while "
     "ignoring generic words such as “risk” that ordinary prose contains:")
code_block("""def _explanation_matches_flags(explanation, all_flags):
    text = explanation.lower()
    return any(
        word[:5] in text
        for flag in all_flags
        for word in re.split(r"[^A-Za-z]+", flag.lower())
        if len(word) >= 4 and word not in GENERIC_FLAG_WORDS
    )""")
section("4.8 Prototype/User Interface")
para("The analyst dashboard is a React page served by Vite (Figure 4.1), laid out as an "
     "analytics console with a light and a dark theme. Six figures run across the top: "
     "transactions scored, the number flagged, the number blocked, the rupee value flagged, "
     "the average risk score and the count of layer failures.")
para("Below them sit the charts, all of them computed over every stored transaction by a "
     "single aggregation route, GET /api/v1/stats/overview. They cover decisions per active "
     "day and the decision mix, the Neo4j entity counts, decisions within each merchant "
     "category, how often each flag fired on a flagged transaction, the distribution of "
     "scores, the flag rate by amount band, and the precision, recall and F1 of the latest "
     "evaluation. Their colours were checked for colour-blind separation rather than chosen "
     "by eye: green and red failed that check, so an approval is drawn in teal instead.")
para("The Analyze transaction button opens a side panel. It shows the rule-and-graph "
     "decision straight away, marks the language-model layer as still scoring, and swaps in "
     "the final score and explanation once the background task finishes.")
figure(SHOT, "Dashboard — key figures, decisions by day, decision mix, category and signal breakdowns",
      note="The analyst's opening screen: totals across the top, decisions per active day, the approve, review and block mix, and risk broken down by merchant category and by amount band.")
para("The review queue (Figure 4.2) lists recent REVIEW and BLOCK decisions with filters, "
     "search and sorting, and shows the signals that fired as labels, with a failed layer "
     "marked in the row. Selecting a row opens a side panel with the transaction's details, its "
     "signals grouped by the layer that raised them, the model's explanation and a one-hop "
     "drawing of the sender's graph neighbourhood; a transaction under review can be approved "
     "or blocked from there. Every decision carries a text label and an icon as well as a colour.")
figure(os.path.join(ASSETS, "dashboard-flags.png"), "Dashboard — review queue with triggered signals",
       note="The queue a person works from. Every row carries the transaction, its composite score, the decision and the signals that fired, so the reason for the hold is readable without opening the record.")
section("4.9 System Integration")
para("The layers are integrated in the analyse route. "
     "The language-model layer is scheduled with FastAPI background tasks after the "
     "record is inserted; a semaphore allows four at once, each with a 180-second timeout, "
     "after which that layer is recorded as failed and the decision is banded again. The "
     "unique index on the transaction identifier turns a retried submission into a 409 "
     "response rather than a duplicate record. The dashboard polls the record every three "
     "seconds until the pending flag clears, and the API documents its eighteen routes on an "
     "OpenAPI page.")
para("Two component routes support recovery: one reports whether Redis, Neo4j, ChromaDB "
     "and Ollama are answering, the other restarts a scoring component by dropping its client "
     "and rechecking its dependency. Both require the API key, and neither starts or stops a "
     "database process. A failed layer appears on the dashboard as a highlighted panel with "
     "its error and a button calling the restart route; the transaction stays in review, and "
     "later transactions use the restarted component.")

# ───────────────────────── CHAPTER 5 ─────────────────────────
chapter("Experimental Setup and Evaluation")
section("5.1 Experimental Setup")
table("Experimental setup",
      ["Item", "Setting"],
      [["Machine", "Apple M4, 16 GB, no graphics processor, macOS 26.5"],
       ["Stack", "Local MongoDB, Neo4j, Redis, ChromaDB; llama3 via Ollama"],
       ["Dataset", f"{COUNTS['total']} labelled synthetic transactions ({COUNTS['fraud']} "
                   f"fraud, {COUNTS['legit']} legitimate)"],
       ["Procedure", "Replayed through the live API, 4 at a time, then waited for every "
                     "language-model result"],
       ["Thresholds", "REVIEW 40, BLOCK 70"],
       ["Run date", EVAL["generated_at"][:10]]],
      widths=[1.4, 4.6],
      note="The machine, the software stack and the labelled dataset on which every figure in this chapter was produced.")
para("The harness posts every labelled transaction to the analyse endpoint and waits for "
     "the background layer to finish before recording a result. An earlier version recorded "
     "the immediate response instead, which omitted the language model from every "
     "transaction and under-reported recall badly; that fault is described in Section 6.6.")
para("The figures throughout this chapter come from a single run, made after all thirty "
     "rules were in place. An earlier run measured the pipeline when it had five, and its "
     "numbers are quoted only where a before-and-after comparison says so. The stored "
     "records hold the composite score, the decision, the triggered flags and the score each "
     "layer contributed, so both the headline metrics and the per-layer analysis in Section "
     "5.5 are read from what the pipeline awarded rather than reconstructed from flag "
     "weights.")
section("5.2 Evaluation Metrics")
para("Precision is the share of flagged transactions that are fraudulent and recall the "
     "share of fraud that is flagged, both by Equation 3.7, with F1 their harmonic mean. "
     "Flagged means REVIEW or BLOCK; the stricter blocked view counts only BLOCK. Latency is "
     "reported as mean, median, p95 and maximum, and determinism as the spread of scores when "
     "one transaction is submitted repeatedly.")
section("5.3 Experimental Results")
table("Confusion matrix at REVIEW 40, BLOCK 70",
      ["Decision", "Actually fraud", "Actually legitimate"],
      [[d, CONF[d]["fraud"], CONF[d]["legit"]] for d in ("APPROVE", "REVIEW", "BLOCK")],
      widths=[1.6, 1.6, 1.8],
      note="Every decision on the labelled set against its true label. No fraud appears in the approved row; most of the fraud that was caught lands in review rather than block.")
table("Headline results",
      ["Measure", "Value"],
      [["Precision (flagged)", f"{FLAGGED['precision']:.3f}"],
       ["Recall (flagged)", f"{FLAGGED['recall']:.3f}"],
       ["F1 (flagged)", f"{FLAGGED['f1']:.3f}"],
       ["False-positive rate", f"{REALISTIC['false_positive_rate']:.4f}"],
       ["Precision at 0.1% prevalence", f"{REALISTIC['precision']:.3f}"],
       ["Ring transactions flagged by the graph layer",
        f"{GRAPH['graph_flagged']} of {GRAPH['ring_transactions']}"],
       ["BLOCK decisions", f"{CONF['BLOCK']['fraud'] + CONF['BLOCK']['legit']}"]],
      widths=[3.2, 1.8],
      note="Precision, recall, F1 and the false-positive rate for flagged transactions, all computed from the confusion matrix above.")
para(f"The composite scores of the two classes barely overlap (Figure 5.1). All but "
     f"{CONF['REVIEW']['legit'] + CONF['BLOCK']['legit']} legitimate transactions scored "
     f"below 40, most of them below 10, while every fraudulent transaction reached 40 or "
     f"above and {CONF['BLOCK']['fraud']} of them reached the block threshold of 70.")
figure(os.path.join(ASSETS, "score-distribution.png"), "Composite score by true label",
       note="How far the composite score separates fraudulent from legitimate transactions on the labelled set. The overlap near the review threshold is what sends genuine transactions to a person.")
_by = lambda p: [r for r in LAYERS if r["pattern"] == p]
para("Four scenarios were also run against the live system on 11 September 2026, each with "
     "account identifiers not used before (Table 5.6).")
table("Scenario tests on the running system",
      ["Scenario", "Rule + graph + LLM", "Decision"],
      [["Retail purchase on a fresh device", "0 + 0 + 0 = 0", "APPROVE"],
       ["Blacklisted sender, ₹5,000 groceries", "40 + 0 + 28 = 68", "REVIEW"],
       ["₹7,04,000 wire into a device and IP cluster", "25 + 30 + 28 = 83", "BLOCK"],
       ["Fourth transfer around a new three-account ring", "10 + 20 + 28 = 58", "REVIEW"]],
      widths=[3.0, 1.9, 1.1],
      note="Four transactions submitted to the running system, showing the points each layer contributed and the decision that came back.")
section("5.4 Comparison with Existing/Baseline Methods")
para("Two baselines are available. The first is the conventional approach this project "
     "started from: single-transaction rules alone. At the configured review threshold the "
     "rule engine by itself flags one transaction in the evaluation set, and that one is "
     "legitimate; it catches none of the 52 frauds (Table 5.7). The second is the same "
     "pipeline as measured before the first review's changes (Table 5.8).")
table("Rule-only baseline against the full pipeline",
      ["Configuration", "Precision", "Recall", "F1"],
      [["Rules only", "0.000", "0.000", "0.000"],
       ["Full pipeline", f"{FLAGGED['precision']:.3f}", f"{FLAGGED['recall']:.3f}",
        f"{FLAGGED['f1']:.3f}"]],
      widths=[2.0, 1.2, 1.2, 1.2],
      note="The rule engine on its own against all three layers over the same data. Single-transaction rules catch none of this fraud, which is why the other two layers exist.")
table("The pipeline at three points in its development",
      ["Measure", "Before Review 1", "Five rules", "Thirty rules"],
      [["Precision", "0.938", "0.978", f"{FLAGGED['precision']:.3f}"],
       ["Recall", "0.865", "0.865", f"{FLAGGED['recall']:.3f}"],
       ["F1", "0.900", "0.918", f"{FLAGGED['f1']:.3f}"],
       ["Legitimate transactions flagged", "3", "1",
        f"{CONF['REVIEW']['legit'] + CONF['BLOCK']['legit']}"],
       ["Ring transactions flagged", "35 of 36", "36 of 36",
        f"{GRAPH['graph_flagged']} of {GRAPH['ring_transactions']}"],
       ["Mean response time", "14,046 ms", "124 ms", "124 ms"]],
      widths=[2.2, 1.2, 1.0, 1.1],
      note="The same measurements taken at three stages: before Review 1, after five rules, and after thirty. Precision climbs as the banking anomaly rules are added.")
para("The first column is the pipeline as it stood at Review 1, with the language model "
     "inside the decision path. The second is the same five-rule pipeline after the "
     "circular-flow query was given its time window. The third is the pipeline measured in "
     "this chapter, with the twenty-five banking anomaly rules added. Only the third column "
     "describes the system as submitted.")
para("Published results are not directly comparable, because they are measured on different "
     "data. APATE was evaluated on real card transactions [2], and the ensemble of "
     "Vijayanand and Smrithy on PaySim [4], where fraud is about 0.13 per cent of records, "
     "so an accuracy figure on that data is dominated by the legitimate class and says "
     "little about how much fraud a detector catches. "
     "Comparing Indus11 with them would require running it on the same dataset, which is "
     "listed as future work.")
section("5.5 Component/Ablation Analysis")
para(f"Removing layers from the composite score, with the thresholds unchanged, shows what "
     f"each contributes (Table 5.9 and Figure 5.2). The rule engine alone reaches the review "
     f"threshold on the blacklisted cases and nothing else, because its budget of 40 is the "
     f"threshold itself and only the blacklist rule awards all of it at once. Neither the "
     f"graph layer nor the language model flags anything alone, their budgets of 30 sitting "
     f"below the threshold by design. Any two layers together catch roughly two thirds of "
     f"the fraud. All three are needed for the "
     f"{FLAGGED['recall']*100:.0f} per cent recall reported above.")
table("Ablation by layer combination (REVIEW at 40)",
      ["Layers", "Precision", "Recall", "F1", "TP", "FP"],
      [[a["layers"], f"{a['precision']:.3f}", f"{a['recall']:.3f}", f"{a['f1']:.3f}",
        a["tp"], a["fp"]] for a in ABLATION],
      widths=[1.4, 1.0, 1.0, 1.0, 0.6, 0.6],
      note="Each combination of layers measured separately, with true and false positive counts, at a review threshold of 40.")
figure(os.path.join(ASSETS, "ablation.png"), "Precision, recall and F1 by layer combination",
       note="The ablation of Table 5.7 drawn as bars: what each combination of layers achieves alone and in company, with the review threshold held at 40.")
para("Figure 5.3 shows where the points come from for each planted pattern. Mule-ring and "
     "shared-IP transactions receive most of their points from the graph and language-model "
     "layers. Shared-device transactions receive graph points but only two language-model "
     "points on average, which is why seven of the ten fall below 40. Legitimate traffic "
     "averages 6.4 points in total.")
figure(os.path.join(ASSETS, "layer-points-by-pattern.png"), "Mean layer points by planted pattern",
       note="The average points each layer contributes to every planted fraud pattern, showing which layer is carrying which pattern rather than assuming all three share the work.")
_fraud = [r for r in LAYERS if r["label"] == "fraud"]
_legit = [r for r in LAYERS if r["label"] == "legit"]
section("5.6 Performance Analysis")
table("Response time after the decision-path split (29 requests)",
      ["Measure", "Value"],
      [["Mean", "124 ms"], ["Median", "114 ms"], ["95th percentile", "189 ms"],
       ["Maximum", "287 ms"], ["Within the 500 ms budget", "29 of 29"],
       ["Rule engine", "8 ms"], ["Graph analyzer", "about 20 ms"],
       ["Language-model layer (after the response)", "13–14 s"]],
      widths=[3.2, 1.6],
      note="Response time over 29 requests once the language-model layer was moved off the decision path, with the cost of each layer shown separately.")
para("The response time fell from 14,046 ms to a mean of 124 ms when the language model was "
     "moved out of the request path. The graph layer's cycle query needed separate work, "
     "summarised in Table 5.12.")
table("Circular-flow check: correctness and cost",
      ["Version", "False-positive share", "Query time"],
      [["No time window", "44.9%", "260 ms"],
       ["72 h window, counting every path", "0.0%", "1,800 ms"],
       ["72 h window, existence check", "10.3%", "about 20 ms"]],
      widths=[2.8, 1.6, 1.3],
      note="Three versions of the cycle query: the time window that removes most false positives, and the existence check that makes the query affordable.")
para("Determinism was measured by submitting one wire transfer five times. At Ollama's default "
     "temperature the language-model scores were 26, 20, 20, 21 and 22. With the temperature "
     "set to zero all five were 20.")
section("5.7 Scalability Analysis")
para("The main scaling risk is growth of the transaction graph. Without a time window, "
     "1,486 stored transactions produced 51,146 closed paths of two to four hops, because any "
     "account that both sends and receives money eventually forms one; cost and false "
     "positives both grew with history. Restricting cycles to 72 hours and to time order "
     "bounds the paths a query examines, and stopping at the first match keeps the check near "
     "20 ms.")
bullets([
    "The service keeps no state between requests, so API instances could be added behind a "
    "load balancer; this has not been tested.",
    "Background language-model work is capped at four concurrent tasks. Replaying 208 "
    "transactions without the cap started 208 model calls at once and stopped the API process.",
    "Latency comes from 29 sequential requests on one machine; sustained load and "
    "concurrent-user tests have not been run.",
    "Transactions are retained indefinitely; the query is bounded, but the graph itself is not.",
])
section("5.8 Discussion")
para(f"The synthetic set is 25 per cent fraud because a test set needs enough fraud to "
     f"measure; a payment feed is nearer one in a thousand. Holding this run's recall of "
     f"{FLAGGED['recall']:.3f} and false-positive rate of "
     f"{REALISTIC['false_positive_rate']:.4f} constant, Equation 3.8 gives a precision of "
     f"{REALISTIC['precision']:.3f} at that prevalence: about eight false alarms for every "
     f"fraud caught. That figure, not the synthetic one, is what a deployment would staff "
     f"against.")
para(f"{CONF['BLOCK']['fraud']} fraudulent transactions reached the block threshold and no "
     f"legitimate one did, so at the configured bands the system would refuse only "
     f"transactions it was right about. The highest score in the set was 98. The threshold "
     f"sweep finds a marginally better F1 at a review threshold of "
     f"{SUGGESTED['review_threshold']} and a block threshold of "
     f"{SUGGESTED['block_threshold']}, but those bands came from this same 208-row set, and "
     f"tuning against the data a result is reported on is how a number stops meaning "
     f"anything. The configured 40 and 70 were left in place.")

# ───────────────────────── CHAPTER 6 ─────────────────────────
chapter("Results and Discussion")
section("6.1 Key Findings")
bullets([
    f"The full pipeline flags {FLAGGED['recall']*100:.1f} per cent of the fraud with "
    f"{FLAGGED['precision']*100:.1f} per cent precision on the synthetic set; at a realistic "
    f"fraud rate the precision would be about {REALISTIC['precision']*100:.0f} per cent.",
    "Only the blacklist rule flags anything on its own. Every other detection needs two or "
    "three layers agreeing, which is what the layer budgets were sized to force.",
    "The decision is returned in 124 ms on average, all 29 measured requests within 500 ms.",
    "An identical transaction now scores identically.",
    "The graph layer flagged all 36 mule-ring transactions, but its circular-flow check fired "
    f"on {CYCLE_HITS} of them; the rest were caught through proximity to known fraud accounts.",
    f"{CONF['BLOCK']['fraud']} transactions reached the block threshold, all of them "
    f"fraudulent; no legitimate transaction did.",
])
section("6.2 Comparative Results")
para(f"Against its own earlier state (Table 5.8) the pipeline is about 113 times faster in "
     f"its response and now misses no fraud at all, where it had missed seven. Precision "
     f"moved from 0.978 to {FLAGGED['precision']:.3f} over the same period, which is one "
     f"additional false alarm among 156 legitimate transactions and is within the margin "
     f"such a small set can resolve. Against the rule engine on its own (Table 5.9) the "
     f"difference is between catching 5 of the 52 planted frauds and catching all of them. "
     f"Against the commercial platforms (Table 2.2) the comparison remains one of design, "
     f"since they have not been measured on this data.")
section("6.3 Advantages")
bullets([
    "Every point of a score can be traced to a named check, and every layer's contribution is "
    "stored with the decision.",
    "The rule and graph layers need no training data, and a new fraud pattern is added to the "
    "knowledge base as a written document.",
    "The language model cannot delay the decision or block a transaction on its own.",
    "A failed data store or model is recorded against its layer, holds the transaction for "
    "review, and can be restarted from the dashboard once the service is back.",
    "The whole stack runs locally on one machine without a graphics processor.",
])
section("6.4 Limitations")
bullets([
    "Accuracy is measured on synthetic data in which fraud is far denser than in reality.",
    "The circular-flow check does not match the transfer that closes a ring (Section 6.6).",
    "Shared-device fraud is caught only once the banking anomaly rules add their points; "
    "the graph evidence alone leaves it below the threshold.",
    "Explanations for transactions flagged only by a risk tier are always withheld "
    "(Section 6.6).",
    "Only a shared key protects the routes that change state; there is no per-user "
    "authentication.",
    "Latency has been measured for sequential requests only.",
])
section("6.5 Practical Applicability")
para("In its current form Indus11 fits as an analyst triage aid rather than an automatic "
     "authorisation control: it holds transactions for review, explains why, and blocks "
     "nothing on its own at the default thresholds. Before it could screen live payments it "
     "would need validation on a real or public dataset, per-user authentication and audit "
     "logging, a sustained load test, a retention policy for the graph and the fixes described "
     "in the next section.")
section("6.6 Error/Failure Analysis")
sub("Missed fraud")
para("No fraudulent transaction was missed in this run; the lowest score any of them received "
     "was 48, comfortably above the review threshold. That was not true of the five-rule "
     "pipeline, which missed seven. All seven were shared-device transactions to crypto "
     "exchanges scoring 27 apiece: 10 rule points for the merchant and the elevated sender "
     "tier, 15 graph points for the shared device, and 2 from the language model, which did "
     "not treat a shared device as strong evidence even though the flag was handed to it as "
     "a confirmed signal. The banking anomaly rules added since then award points to those "
     "same transactions for a first payment to a high-risk merchant category and for a new "
     "device on an established account, which is what lifts them over the threshold.")
sub("False positives")
para("Two legitimate transactions were flagged, both for review rather than block. The first "
     "scored 68: 40 rule points because its receiver, ACC-015, is blacklisted in the account "
     "store, plus 28 from the language model. The evaluation generator draws receivers for "
     "ordinary traffic at random and does not exclude blacklisted accounts, so this row is "
     "arguably mislabelled rather than a detector error.")
para("The second scored 42, from 2 rule points for an elevated sender tier, 12 graph points "
     "for a circular flow, and 28 from the language model. This one is a genuine false "
     "alarm. Three other legitimate transactions also triggered the circular-flow check and "
     "stayed below the threshold, which is the pattern discussed next.")
sub("Graph signals on legitimate traffic")
para("Three legitimate transactions triggered CIRCULAR_FLOW (12 points each) but stayed at 16 "
     "overall and were approved. The circular-flow check itself has a structural limitation: "
     "it walks a cycle outward from the sender and requires each hop to be later than the "
     "last, but the transfer that closes a ring is always the newest hop, so it never matches. "
     "A ring is recognised only when its originator sends again. Following the path back from "
     "the receiver to the sender would catch the closing transfer.")
sub("Withheld explanations")
para("For 139 of the 156 legitimate transactions the written explanation was withheld and "
     "only the flag list was shown. Their only flag was ELEVATED_RISK_SENDER_TIER, and every "
     "word of that code is in the guard's list of generic words, so no explanation can ever "
     "satisfy it. The guard should skip flags that contain no distinctive word.")
sub("Inaccurate explanation content")
para("The guard checks that an explanation names a flag, not that each statement in it is "
     "true. In a live test the explanation for a ₹5,000 purchase by a blacklisted account "
     "described the amount as exceeding the account's monthly average, which is ₹88,000. One "
     "stored explanation described a rupee transaction in dollars.")
sub("Operational failures found and fixed")
bullets([
    "Unbounded background work: 208 simultaneous model calls stopped the API; now capped at four.",
    "A hung model call held its slot forever and left records pending; each call now times out "
    "after 180 seconds.",
    "A timed-out model call cleared only the pending flag and left the placeholder text on four "
    "records; it is now recorded as a failed layer and the decision is banded again.",
    "The rule engine had no error handling, so a Redis outage failed the whole request; it now "
    "marks its layer as failed.",
    "The evaluation harness measured the response before the language-model layer finished; "
    "it now waits for it.",
])

# ───────────────────────── CHAPTER 7 ─────────────────────────
chapter("Security, Ethical and Practical Considerations")
section("7.1 Security")
para("The controls in place are those in Section 3.8: a shared key on the component routes and the three routes that "
     "change state, compared in constant time; origin restriction; per-client rate limits; "
     "schema validation with a fixed merchant vocabulary and length caps that limit prompt "
     "injection; and parameterised database queries. Four gaps remain. The first is that "
     "there is no per-user authentication, so everyone holding the key has full override "
     "rights and no action can be attributed to a person. Traffic in the local "
     "configuration is unencrypted, and the example configuration still ships default "
     "database passwords. Finally, the language model's output is validated only for "
     "referring to a flag; whether what it says about that flag is accurate goes unchecked.")
section("7.2 Privacy")
para("The project processes no real personal data. Running it on real transactions would "
     "mean processing digital personal data within the meaning of India's Digital Personal "
     "Data Protection Act, 2023 [19], which brings obligations: establish a lawful basis, "
     "hold only what the decision needs, and secure what is held. Two of the design choices "
     "already point that way. The language model runs locally by default, so transaction "
     "details never reach a third-party service, and no payment instrument data is stored "
     "at all. Two others would have to be revisited, since records are currently kept "
     "indefinitely and the optional external model provider would send transaction details "
     "off the premises.")
section("7.3 Ethics")
para("A fraud decision affects a customer who usually cannot see why their payment was "
     "stopped. The design keeps a person in the loop: no single layer can block, nothing was "
     "blocked automatically in evaluation, and every flagged transaction reaches an analyst "
     "with the evidence listed. The explanation is presented as an aid to that analyst, and "
     "the errors described in Section 6.6 show why it should not be read as a finding on its "
     "own.")
section("7.4 Bias/Fairness")
para("The system uses no demographic attributes, but some of its signals can act as proxies. "
     "Households and shared workplaces use one device, so the shared-device check can penalise "
     "people who share phones or computers. Unknown accounts are treated as elevated risk, "
     "which places new customers at a disadvantage. The risk tier and country code are "
     "inherited from account data whose origin a real deployment would need to audit. None "
     "of these effects was measured, because the synthetic data carries no demographic "
     "information.")
section("7.5 Legal/Regulatory Issues")
para("The RBI's 2024 Master Directions on fraud risk management set expectations for fraud "
     "prevention, early detection and reporting in regulated entities, including adherence "
     "to the principles of natural justice before an account or person is classified as "
     "fraudulent [1]. A decision-support tool such as Indus11 would sit inside such a "
     "framework, not replace it: its REVIEW outcome and stored evidence support an analyst's "
     "examination, but the classification remains the institution's. The Digital Personal "
     "Data Protection Act, 2023 governs the personal data such a tool would process [19]. The "
     "prototype has not been assessed for compliance with either.")
section("7.6 Safety and Reliability")
bullets([
    "A failed layer is named in the explanation and recorded with the transaction, and a "
    "transaction it would have approved is held for review.",
    "A failed component can be restarted from the dashboard once its service is back.",
    "Background model calls are bounded in number and time, so a hung call cannot stall later "
    "transactions.",
    "A retried submission returns a conflict response instead of creating a duplicate decision.",
    "Scores are deterministic for identical input.",
    "101 automated tests, which need no database or network, run on every push.",
])
section("7.7 Deployment Risks")
table("Deployment risks",
      ["Risk", "Effect", "Mitigation or next step"],
      [["Synthetic-only validation", "Real precision unknown", "Evaluate on a public dataset"],
       ["Language-model outage or slowness", "No explanations", "Timeout; layer failed, held for review"],
       ["Graph growth", "Slower queries, more cycles", "Retention or archival policy"],
       ["Shared API key", "No attribution of overrides", "Per-user authentication"],
       ["Default credentials", "Unauthorised database access", "Set secrets per environment"],
       ["Residual prompt injection", "Distorted LLM score", "LLM capped at 30 points"],
       ["Threshold choice", "Missed fraud or blocked customers", "Tune on real data"]],
      size=10,
      note="What could go wrong once the system is deployed, the effect of each, and the mitigation already in place or planned.")

# ───────────────────────── CHAPTER 8 ─────────────────────────
chapter("Conclusion", numbered=False)
section("Conclusion")
para("Indus11 returns an approve, review or block decision in 124 ms on average by letting "
     "deterministic rules and graph queries decide, then attaches a language-model "
     "explanation built from the evidence those layers found. On a labelled synthetic dataset "
     f"of {COUNTS['total']} transactions it flagged {FLAGGED['recall']*100:.1f} per cent of "
     f"the fraud at {FLAGGED['precision']*100:.1f} per cent precision, and the ablation shows "
     "that no single layer, the rule engine included, detects the planted fraud alone.")
para(f"The work also produced negative results, recorded rather than hidden. Precision "
     f"would fall to about {REALISTIC['precision']*100:.0f} per cent at a realistic fraud "
     f"rate, the figure a deployment would staff against. The cycle check still misses the "
     f"transfer that closes a ring, so ring detection rests partly on proximity to known "
     f"fraud. The guard withholds every explanation for transactions flagged only by risk "
     f"tier. And 156 legitimate transactions are too few to resolve a false-alarm rate that "
     f"matters at one fraud in a thousand.")
section("Limitations")
bullets([
    "Synthetic data only, with far denser fraud than a real feed.",
    "Ring closure is not detected on the closing transfer, so the check under-reports.",
    "Guard defect for tier-only flags; explanation accuracy not verified.",
    "Shared-key protection only; latency measured without concurrent load.",
])
section("Future Work")
bullets([
    "Evaluate on PaySim or IEEE-CIS for a realistic precision figure.",
    "Detect a ring on the transfer that closes it, and re-evaluate.",
    "Skip flags with no distinctive word in the guard, and check explanations against the "
    "transaction's values.",
    "Resolve the block-threshold trade-off from recorded scores.",
    "Add per-user authentication, audit logging and a sustained load test.",
    "Bound the transaction graph with a retention policy, and add a supervised classifier "
    "as a fourth scoring signal.",
])

# ────────────────── REFERENCES ──────────────────
chapter("References", numbered=False)
for i, r in enumerate([
    "Reserve Bank of India, “Reserve Bank of India (Fraud Risk Management in Commercial Banks "
    "(including Regional Rural Banks) and All India Financial Institutions) Directions, 2024,” "
    "RBI/DOS/2024-25/118, 15 July 2024. [Online]. Available: "
    "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12702",
    "V. Van Vlasselaer, C. Bravo, O. Caelen, T. Eliassi-Rad, L. Akoglu, M. Snoeck and "
    "B. Baesens, “APATE: A novel approach for automated credit card transaction fraud detection "
    "using network-based extensions,” Decision Support Systems, vol. 75, pp. 38–48, 2015. "
    "[Online]. Available: https://doi.org/10.1016/j.dss.2015.04.013",
    "B. Lebichot, F. Braun, O. Caelen and M. Saerens, “A graph-based, semi-supervised, credit "
    "card fraud detection system,” in Complex Networks & Their Applications V, Springer, 2017, "
    "pp. 721–733. [Online]. Available: https://link.springer.com/chapter/10.1007/978-3-319-50901-3_57",
    "D. Vijayanand and G. S. Smrithy, “Explainable AI-enhanced ensemble learning for financial "
    "fraud detection in mobile money transactions,” Intelligent Decision Technologies, "
    "vol. 19, no. 1, pp. 52–67, 2025. [Online]. Available: "
    "https://doi.org/10.1177/18724981241289751",
    "S. Motie and B. Raahemi, “Financial fraud detection using graph neural networks: A "
    "systematic review,” Expert Systems with Applications, vol. 240, art. 122156, 2024. "
    "[Online]. Available: https://doi.org/10.1016/j.eswa.2023.122156",
    "D. Cheng, Y. Zou, S. Xiang and C. Jiang, “Graph neural networks for financial fraud "
    "detection: a review,” Frontiers of Computer Science, vol. 19, 2025. [Online]. Available: "
    "https://doi.org/10.1007/s11704-024-40474-y",
    "Y. Dou, Z. Liu, L. Sun, Y. Deng, H. Peng and P. S. Yu, “Enhancing graph neural "
    "network-based fraud detectors against camouflaged fraudsters,” in Proc. 29th ACM Int. "
    "Conf. on Information & Knowledge Management (CIKM), 2020. [Online]. Available: "
    "https://doi.org/10.1145/3340531.3411903",
    "M. Weber, G. Domeniconi, J. Chen, D. K. I. Weidele, C. Bellei, T. Robinson and "
    "C. E. Leiserson, “Anti-money laundering in Bitcoin: Experimenting with graph convolutional "
    "networks for financial forensics,” KDD Workshop on Anomaly Detection in Finance, 2019. "
    "[Online]. Available: https://arxiv.org/abs/1908.02591",
    "P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin et al., “Retrieval-augmented "
    "generation for knowledge-intensive NLP tasks,” Advances in Neural Information Processing "
    "Systems, vol. 33, 2020. [Online]. Available: https://arxiv.org/abs/2005.11401",
    "Y. Nie, Y. Kong, X. Dong, J. M. Mulvey, H. V. Poor, Q. Wen and S. Zohren, “A survey of "
    "large language models for financial applications: Progress, prospects and challenges,” "
    "2024. [Online]. Available: https://arxiv.org/abs/2406.11903",
    "S. M. Lundberg and S.-I. Lee, “A unified approach to interpreting model predictions,” "
    "Advances in Neural Information Processing Systems, vol. 30, 2017. [Online]. Available: "
    "https://arxiv.org/abs/1705.07874",
    "M. T. Ribeiro, S. Singh and C. Guestrin, “‘Why should I trust you?’ Explaining the "
    "predictions of any classifier,” in Proc. 22nd ACM SIGKDD, 2016. [Online]. Available: "
    "https://arxiv.org/abs/1602.04938",
    "FICO, “FICO Falcon Fraud Manager,” product page. [Online]. Available: "
    "https://www.fico.com/en/products/fico-falcon-fraud-manager",
    "Feedzai, “RiskOps platform,” product overview. [Online]. Available: https://feedzai.com",
    "Visa Inc., “Visa completes acquisition of Featurespace,” press release, December 2024. "
    "[Online]. Available: https://investor.visa.com/news/news-details/2024/"
    "Visa-Completes-Acquisition-of-Featurespace/default.aspx",
    "Neo4j, “Graph databases for fraud detection & analytics.” [Online]. Available: "
    "https://neo4j.com/use-cases/fraud-detection/",
    "E. A. Lopez-Rojas, A. Elmir and S. Axelsson, “PaySim: A financial mobile money simulator "
    "for fraud detection,” in Proc. 28th European Modeling and Simulation Symposium (EMSS), "
    "2016. [Online]. Available: https://www.msc-les.org/proceedings/emss/2016/EMSS2016_249.pdf",
    "IEEE Computational Intelligence Society and Vesta Corporation, “IEEE-CIS Fraud Detection,” "
    "Kaggle competition, 2019. [Online]. Available: https://www.kaggle.com/c/ieee-fraud-detection",
    "Ministry of Electronics and Information Technology, Government of India, “The Digital "
    "Personal Data Protection Act, 2023 (No. 22 of 2023).” [Online]. Available: "
    "https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf",
    "S. Ramírez, “FastAPI documentation.” [Online]. Available: https://fastapi.tiangolo.com",
    "Neo4j, Inc., “Cypher manual.” [Online]. Available: https://neo4j.com/docs/cypher-manual/current/",
    "Chroma, “Chroma documentation.” [Online]. Available: https://docs.trychroma.com",
    "Ollama, “Ollama.” [Online]. Available: https://ollama.com",
    "Meta, “Introducing Meta Llama 3,” April 2024. [Online]. Available: "
    "https://ai.meta.com/blog/meta-llama-3/",
], 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.left_indent = Inches(0.45)
    p.paragraph_format.first_line_indent = Inches(-0.45)
    p.paragraph_format.line_spacing = LINE
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(f"[{i}]  {r}")
    run.font.size, run.font.name = Pt(BODY), FONT

# ────────────────── APPENDICES ──────────────────
chapter("Appendices", numbered=False)
section("Appendix A — Reproducing the Results")
code_block("""# 1. Start the stack natively with a fresh seed (or: docker compose up --build)
./scripts/run_local.sh --seed

# 2. Replay the labelled dataset (over an hour with the language model)
python -m scripts.evaluate

# 3. Measure response latency on the decision path
python -m scripts.benchmark_latency

# 4. Per-layer split and charts used in Chapter 5
python docs/report_assets.py --from-api

# 5. Run the automated test suite (no databases required)
pytest -q

# 6. Build this report
python docs/make_srs_pdf.py report""")


# ────────────────── back-fill lists of figures and tables ──────────────────
fill(LOT_ANCHOR, "LIST OF TABLES", tables)
fill(LOF_ANCHOR, "LIST OF FIGURES", figures)
fill_contents(TOC_ANCHOR, FRONT_MATTER)

# The PDF driver needs the heading list to look each page number up, and the
# table spans to check no table was split across a page break.
with open(os.path.join(HERE, "report-toc-entries.json"), "w") as f:
    json.dump(FRONT_MATTER + [t for _, t in contents], f, indent=2)
with open(os.path.join(HERE, "report-table-spans.json"), "w") as f:
    json.dump(table_spans, f, indent=2)

page_numbers()
refresh_fields_on_open()
doc.save(OUT)
print(f"Saved {OUT}")
print(f"  figures: {len(figures)}   tables: {len(tables)}   "
      f"contents entries: {len(FRONT_MATTER) + len(contents)}"
      f"{'' if TOC_PAGES else '   (page numbers not filled in yet)'}")
