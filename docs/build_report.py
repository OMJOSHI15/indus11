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

# The member responsible for each chapter, printed under its heading. The guide
# asked for chapter-level ownership after the 15 September review.
CHAPTER_OWNERS = {
    "Introduction": "Joshi Om (24DCE052)",
    "Literature Review": "Joshi Om (24DCE052)",
    "Proposed Methodology": "Krish Gajera (24DCE040)",
    "Implementation": "Joshi Om (gateway, persistence, rule engine), Krish Gajera (graph analyzer), "
                      "Drashti Dedaniya (RAG pipeline, decision engine, dashboard)",
    "Experimental Setup and Evaluation": "Krish Gajera (24DCE040)",
    "Results and Discussion": "Drashti Dedaniya (24DCE029)",
    "Security, Ethical and Practical Considerations": "Joshi Om (24DCE052)",
    "Conclusion and Future Work": "Drashti Dedaniya (24DCE029)",
}
kit.CHAPTER_NOTE = lambda title: (
    f"Responsible: {CHAPTER_OWNERS[title]}" if title in CHAPTER_OWNERS else None)

# ═════════════════════════════ PROJECT REPORT BODY ═════════════════════════════
from docx.enum.text import WD_COLOR_INDEX

ASSETS = os.path.join(HERE, "report-assets")
with open(os.path.join(HERE, "eval-layer-scores.json")) as f:
    LAYERS = json.load(f)["rows"]
with open(os.path.join(ASSETS, "ablation.json")) as f:
    ABLATION = json.load(f)
CONF = EVAL["metrics"]["confusion"]
SUGGESTED = EVAL["suggested_thresholds"]


def mean(values):
    values = list(values)
    return sum(values) / len(values)


def sub(text):
    """Run-in label inside a section; not a heading, so not in the contents."""
    p = para(text, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, after=2)
    p.paragraph_format.keep_with_next = True
    return p


def eq(expression, number):
    p = para("", align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
    r = p.add_run(expression)
    r.italic, r.font.size, r.font.name = True, Pt(BODY), FONT
    r = p.add_run(f"        ({number})")
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
                p.paragraph_format.line_spacing = LINE
                p.paragraph_format.space_after = Pt(2)
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
     "Several of them — the latency of the language model inside the decision path, the "
     "behaviour of the dashboard when a data store is unavailable, and which graph pattern "
     "produces the most false positives — led directly to changes described in this "
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
for text, stale in [
    ("The system was evaluated using a labelled fraud dataset and achieved ", False),
    ("93.8% precision", True), (", 86.5% recall, and ", False), ("an F1-score of 0.90", True),
    (". ", False),
    ("Graph analysis successfully identified all 36 transactions belonging to the 3 "
     "planted mule rings", True),
    (", demonstrating the effectiveness of relationship-based fraud detection. During "
     "evaluation, no transaction reached the predefined BLOCK threshold because the "
     "seeded fraud accounts lacked stored historical profiles, preventing the "
     "amount-anomaly rule from contributing to their overall score. This identified a "
     "limitation in the current scoring mechanism rather than a characteristic of the "
     "dataset and highlights an area for future enhancement. Overall, the results "
     "demonstrate that integrating rule-based analysis, graph analytics, and "
     "RAG-based reasoning improves fraud detection while maintaining explainability "
     "and supporting financial investigators in making informed decisions.", False)]:
    r = _abs.add_run(text)
    r.font.size, r.font.name = Pt(BODY), FONT
    if stale:
        r.font.highlight_color = WD_COLOR_INDEX.YELLOW
para("KEYWORDS", SUB, True, WD_ALIGN_PARAGRAPH.LEFT, 4)
para("Fraud detection, explainable AI, graph analytics, retrieval-augmented generation, "
     "risk scoring", italic=True)

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

FRONT_MATTER = ["CERTIFICATE", "ACKNOWLEDGEMENT", "ABSTRACT", "KEYWORDS",
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
para("Much of the fraud that matters is also not visible in a single payment. A money-mule "
     "ring moves funds around a loop of accounts, keeping a small fee at each hop, so that "
     "each individual transfer looks ordinary. Synthetic identities show up as several "
     "unrelated-looking accounts operated from one device or one network address. Detecting "
     "these requires looking at relationships between accounts, not only at the payment in "
     "front of the system.")
para("In India the Reserve Bank's 2024 Master Directions on fraud risk management require "
     "regulated entities to maintain frameworks for the prevention, early detection and "
     "timely reporting of fraud [1]. Detection that a bank cannot explain is hard to act on "
     "under such a framework: an analyst has to be able to say why a transaction was held.")
section("1.2 Problem Statement")
para("Design and build a decision service that accepts one financial transaction, scores its "
     "risk from 0 to 100 and returns APPROVE, REVIEW or BLOCK, such that:")
bullets([
    "the decision is returned within a 500 millisecond budget;",
    "coordinated fraud that no single-transaction rule can see — circular flows, shared "
    "devices and addresses, proximity to known fraud — contributes to the score;",
    "every decision carries a written explanation that is consistent with the signals that "
    "actually fired; and",
    "the detection is measured on labelled data, with its limits stated, rather than "
    "asserted.",
])
section("1.3 Motivation")
para("Each common approach to transaction fraud is strong at one of these requirements and "
     "weak at another. Hand-written rules are fast and auditable but examine one transaction "
     "at a time. Supervised models learn subtle patterns but need large labelled datasets and "
     "report their reasoning as feature weights or fixed reason codes. Large language models "
     "write fluent explanations, but in this project a local model took 13 to 14 seconds per "
     "transaction and, at its default settings, gave the same transaction five different "
     "scores in five runs. The motivation for Indus11 is to give each technique the part of "
     "the problem it is suited to: rules and graph queries decide, and the language model "
     "explains, after the decision, using the evidence the other two layers produced.")
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
para("Indus11 accepts one transaction over a REST interface, analyses it with three detection "
     "layers and returns a composite score, a decision and an explanation. A web dashboard "
     "lets an analyst view statistics, inspect a flagged transaction and override a review "
     "decision. The system does not move money or settle payments, is not a core banking "
     "system, performs no regulatory reporting and processes synthetic data only. Training a "
     "supervised model is outside the scope of this semester and is listed as future work.")
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
      widths=[0.5, 4.3, 1.2])
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
para("The oldest and still most widespread form of transaction screening is a set of "
     "explicit rules: a blacklist, velocity limits, amount thresholds and merchant-category "
     "restrictions. Rules are fast, deterministic and easy to audit, but each rule looks at "
     "one transaction and its account's history, so coordinated activity across accounts "
     "passes unnoticed.")
sub("Supervised machine learning")
para("Supervised models learn fraud patterns from labelled historical transactions. "
     "Vijayanand and Smrithy trained a voting ensemble on the synthetic PaySim mobile-money "
     "dataset of 6,362,620 records and used SHAP values to explain individual predictions "
     "[4]. Such models depend on large labelled datasets and, when fraud is rare, on careful "
     "treatment of class imbalance; their explanations take the form of feature "
     "attributions.")
sub("Network and graph-based detection")
para("Van Vlasselaer and colleagues showed with APATE that combining features derived from the "
     "network of cardholders and merchants with features of the transaction itself gave "
     "their best models, with AUC above 0.98 on more than three million card transactions "
     "[2]. Lebichot and "
     "colleagues extended that system with semi-supervised propagation of fraud labels "
     "across the transaction graph, multiplying precision among the top 100 alerts by three "
     "on a real e-commerce dataset [3]. These results are the basis for this project's graph "
     "layer and its fraud-label propagation.")
sub("Graph neural networks")
para("More recent work learns directly on the graph. Two reviews survey graph neural "
     "networks for financial fraud detection and report that they capture relational "
     "patterns that tabular models miss [5], [6]. Dou and colleagues showed that fraudsters "
     "camouflage themselves by connecting to legitimate nodes and proposed CARE-GNN to "
     "resist it [7]; Weber and colleagues applied graph convolutional networks to "
     "anti-money-laundering on Bitcoin transactions [8].")
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
      size=10)
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
      size=9.5)
section("2.5 Research/Technical Gap")
bullets([
    "Commercial explanations are reason codes from a fixed vocabulary; the analyst still has "
    "to assemble the story.",
    "Generated explanations are fluent but nothing in a typical retrieval-augmented pipeline "
    "checks them against the evidence that produced the decision.",
    "Graph neural networks need labelled graph data and training infrastructure that a small "
    "team or a new deployment does not have.",
    "A language model measured at 13–14 seconds cannot sit inside an authorisation decision.",
])
section("2.6 Positioning of Proposed Work")
para("Indus11 does not attempt to compete with consortium-trained models on accuracy. Its "
     "position is narrower: deterministic rules and graph queries that need no training data "
     "make the decision within the latency budget, and a local language model writes the "
     "explanation afterwards from the flags those layers produced, with a guard that "
     "withholds prose that ignores them. The evaluation is reported with its synthetic-data "
     "caveat and a prevalence-adjusted precision rather than the headline figure alone.")

# ───────────────────────── CHAPTER 3 ─────────────────────────
chapter("Proposed Methodology")
section("3.1 System Overview")
para("A payment system submits a transaction to POST /api/v1/transactions/analyze. The "
     "service loads the sender's and receiver's profiles, scores the transaction with the "
     "rule engine and the graph analyzer concurrently, combines their scores into a "
     "provisional decision, stores it and returns it. A background task then asks the "
     "retrieval-augmented language model for a score and an explanation, recomputes the "
     "composite score and updates the stored record. Analysts use a dashboard to watch the "
     "decision mix, inspect flagged transactions and override a decision under review. Figure "
     "3.1 shows the actors and the services each uses.")
figure("final-usecase.png", "Use case diagram")
section("3.2 System Architecture")
para("The system is organised as five layers (Figure 3.2). Layer 1, the FastAPI gateway, "
     "validates the request and loads profiles from Redis, falling back to MongoDB. Layers 2 "
     "and 3 score the transaction in parallel. Layer 5, the decision engine, adds the scores "
     "and maps the total to a decision. Layer 4, the retrieval-augmented pipeline, runs after "
     "the response has been sent. It was inside the request path until the first project "
     "review, where its latency was identified as incompatible with a payment decision.")
figure("01-architecture.png", "System architecture — five-layer pipeline")
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
      size=10)
figure("07-component.png", "Component diagram")
section("3.4 Workflow/Data Flow")
para("Figure 3.4 decomposes the system into seven processes and five data stores. Figure 3.5 "
     "follows one transaction across the participants, and Figure 3.6 shows the calls in the "
     "order they occur, including the point at which the response is returned and the "
     "background work begins.")
figure("final-dfd1.png", "Data flow diagram — Level 1")
figure("03-activity.png", "Activity diagram — transaction analysis workflow")
figure("04-sequence.png", "Sequence diagram — transaction analysis")
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
     "time order, and stops at the first match. Figure 3.7 decomposes the rule engine's "
     "checks, and Figure 3.8 gives the lifecycle of a stored record.")
sub("Algorithm 2: Circular-flow and mule check")
code_block("""cutoff <- tx.timestamp - 72 h
if exists path (a {id: tx.sender}) -[SENT*2..4]-> (a)
       where every hop.timestamp >= cutoff and hops are in time order:
    G <- G + 12, flag CIRCULAR_FLOW
    if some such path has every amount within 75-100% of the previous hop:
        G <- G + 8, flag MONEY_MULE_PATTERN""")
figure("12-dfd2.png", "Data flow diagram — Level 2, process 3.0 (rule engine)")
figure("06-state.png", "State diagram — lifecycle of a transaction")
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
eq("0.9 T ≤ x < T;   t − t_prev ≥ 180 d;   new payee ∧ x ≥ ₹50,000;   "
   "I_24 ≥ ₹10,000 ∧ 0.8 I_24 ≤ x ≤ 1.1 I_24;   p_24 > 5", "3.5a")
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
        "banking anomaly weights are listed in Tables 4.5 and 4.6", "rule_engine.py"],
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
      size=10)
para("The 40/30/30 split follows the certainty of each layer's evidence. The rule engine "
     "checks facts, the graph layer infers from structure, and the language model infers from "
     "similarity. The rule budget sits below the block threshold on purpose: no single layer "
     "can block a transaction, and a blacklisted account lands exactly on the review "
     "boundary.")
section("3.8 Security/Privacy Considerations")
bullets([
    "The three routes that change stored state — the decision override, the blacklist toggle "
    "and fraud-label propagation — and the component status and restart routes require a "
    "shared key in the X-API-Key header, compared in constant time.",
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
       ["Disk", "About 5 GB free", "Solid-state"]])
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
      size=10)
section("4.3 Development Environment")
para("Development took place on macOS 26.5 on an Apple M4 machine with no graphics "
     "processor. The backend runs from a Python 3.12 virtual environment, and MongoDB, Neo4j "
     "and Redis run as Homebrew services. The script scripts/run_local.sh starts the databases, "
     "the API and the dashboard with one command, and clears a stale Neo4j process file that "
     "had twice stopped the database from starting. The same stack is also defined for Docker "
     "Compose. Source code is kept in Git on GitHub, where a continuous-integration workflow "
     "runs the test suite on every push. Diagrams are drawn with PlantUML and Graphviz, and "
     "this report is generated from Python with python-docx and converted with LibreOffice.")
section("4.4 Dataset/Input Data")
para("No real customer or payment data is used. Three synthetic sources supply the system and "
     "its evaluation, all generated deterministically so that every team member works with the "
     "same data (Table 4.3).")
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
      size=10)
para("Figure 4.1 relates the stored entities across the two stores that hold them.")
figure("09-er.png", "Entity relationship diagram", max_h=5.2)
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
      size=10)
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
     "engine and five by the graph analyzer (Tables 4.5 and 4.6). The other fifteen need data this "
     "system does not receive, such as balances, KYC records, channels and login events, and "
     "are listed with that data in Table 4.7. The rule engine's total stays capped at 40, so "
     "many rules firing together cannot decide a transaction on their own.")
table("Banking anomalies detected (1 to 18)",
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
       ['18', 'Device hopping: more than 3 devices in 24 h', 'Rule', '8']],
      widths=[0.35, 4.3, 0.7, 0.65], size=9)
table("Banking anomalies detected (19 to 35)",
      ["#", "Anomaly", "Layer", "Points"],
      [['19', 'Daily outflow over 10 × the usual payment', 'Rule', '8'],
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
      widths=[0.35, 4.3, 0.7, 0.65], size=9)
table("Banking anomalies not detected, and the data each would need",
      ["#", "Anomaly", "Data needed"],
      [['36', 'Cash deposits spread across many branches', 'Channel and branch of each deposit'],
       ['37', 'Deposit followed by an ATM withdrawal in another city', 'Channel and ATM location'],
       ['38', 'Account emptied to near zero', 'Account balance'],
       ['39', 'Volume out of line with occupation or income', 'KYC profile'],
       ['40', 'Salary account receiving third-party credits', 'Account type'],
       ['41', 'Loan disbursal moved out immediately', 'Loan records'],
       ['42', 'Several accounts sharing a PAN, phone or address', 'KYC identity data'],
       ['43', 'Mobile number or e-mail changed before a large payment', 'Account change events'],
       ['44', 'SIM swap shortly before a transaction', 'Telecom operator data'],
       ['45', 'Failed logins or OTP attempts before a payment', 'Authentication logs'],
       ['46', 'Beneficiary added and paid within minutes', 'Beneficiary-added timestamp'],
       ['47', 'History of chargebacks or disputes', 'Dispute records'],
       ['48', 'Cheque kiting', 'Cheque clearing data (out of scope)'],
       ['49', 'Trade-based laundering through over- or under-invoicing', 'Trade documents (out of scope)'],
       ['50', 'Politically exposed person or sanctions match', 'External watch lists (out of scope)']],
      widths=[0.35, 3.3, 2.35], size=9)
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
code_block("""MATCH path = (a:Account {account_id: $sender})-[:SENT*2..4]->(a)
WHERE all(r IN relationships(path)
          WHERE r.timestamp IS NOT NULL AND r.timestamp >= $cutoff)
WITH [r IN relationships(path) | r.timestamp] AS times
WHERE all(i IN range(0, size(times) - 2) WHERE times[i + 1] >= times[i])
RETURN 1 AS hit
LIMIT 1""")
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
para("The analyst dashboard is a single React page served by Vite (Figure 4.2), laid out as an "
     "analytics console with a light and a dark theme. A row of six figures gives the "
     "transactions scored, the number flagged and blocked, the rupee value flagged, the average "
     "risk score and the count of layer failures. The charts below it are computed over every "
     "stored transaction by one aggregation route, GET /api/v1/stats/overview: decisions per "
     "active day, the decision mix, the Neo4j entity counts, decisions within each merchant "
     "category, how often each flag fired on flagged transactions, the score distribution, the "
     "flag rate by amount band, and precision, recall and F1 from the latest evaluation. Chart "
     "colours were checked for colour-blind separation; green and red failed, so an approval "
     "is shown in teal. The Analyze transaction button opens a side panel that shows the "
     "rule-and-graph decision immediately, marks the language-model layer as scoring, and "
     "replaces it with the final score and explanation when the background task finishes.")
figure(SHOT, "Dashboard — key figures, decisions by day, decision mix, category and signal breakdowns")
para("The review queue (Figure 4.3) lists recent REVIEW and BLOCK decisions with filters, "
     "search and sorting, and shows the signals that fired as labels, with a failed layer "
     "marked in the row. Selecting a row opens a side panel with the transaction's details, its "
     "signals grouped by the layer that raised them, the model's explanation and a one-hop "
     "drawing of the sender's graph neighbourhood; a transaction under review can be approved "
     "or blocked from there. Every decision carries a text label and an icon as well as a colour.")
figure(os.path.join(ASSETS, "dashboard-flags.png"), "Dashboard — review queue with triggered signals")
section("4.9 System Integration")
para("The layers are integrated in the analyse route. The rule engine and graph analyzer run "
     "under asyncio.gather, so the response waits for the slower of the two rather than their "
     "sum. The language-model layer is scheduled with FastAPI background tasks after the "
     "record is inserted; a semaphore allows four such tasks at once and each has a 180-second "
     "timeout, after which the language-model layer is recorded as failed and the decision is "
     "banded again. The unique index on the "
     "transaction identifier turns a retried submission into a 409 response rather than a "
     "duplicate record. The dashboard polls the stored record every three seconds until the "
     "pending flag clears. The API documents itself through its OpenAPI page (Figure 4.4).")
para("Two component routes support recovery. One reports whether Redis, Neo4j, ChromaDB and "
     "Ollama are answering; the other restarts a single scoring component by dropping its client "
     "and checking its dependency again. Both require the API key. They do not start or stop "
     "the database processes, which would mean running shell commands from a web request. A "
     "failed layer appears on the dashboard as a highlighted panel with its error and a button "
     "that calls the restart route; the transaction stays in review, and later transactions use "
     "the restarted component.")
figure(os.path.join(ASSETS, "api-docs.png"), "Interactive API documentation — 17 routes")
para("For deployment the stack is defined in Docker Compose as five containers, with the "
     "language model on the host (Figure 4.5).")
figure("08-deployment.png", "Deployment diagram — Docker Compose")

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
       ["Run date", "31 August 2026"]],
      widths=[1.4, 4.6])
para("The evaluation harness posts every labelled transaction to the analyse endpoint and "
     "waits for the background layer to finish before recording the result; an earlier "
     "version recorded the immediate response and under-reported recall as 0.462 instead of "
     "0.865. The 31 August run was recovered from the stored records after the harness hit "
     "its own time limit while the server was still scoring. The stored records hold the "
     "composite score, the decision and the triggered flags, so the headline metrics are "
     "measured directly. The per-layer split used in Section 5.5 is reconstructed from the "
     "recorded flags with the fixed layer weights; for every one of the 208 transactions the "
     "language-model score derived this way falls within its 0–30 range.")
section("5.2 Evaluation Metrics")
table("Metrics",
      ["Metric", "Definition"],
      [["Precision", "Flagged transactions that are fraud (Equation 3.7)"],
       ["Recall", "Fraud transactions that are flagged"],
       ["F1", "Harmonic mean of precision and recall"],
       ["Flagged view", "REVIEW or BLOCK counts as a detection"],
       ["Blocked view", "Only BLOCK counts as a detection"],
       ["False-positive rate", "Legitimate transactions that are flagged"],
       ["Prevalence-adjusted precision", "Precision at 0.1% fraud (Equation 3.8)"],
       ["Latency", "Mean, median, p95 and maximum response time"],
       ["Determinism", "Spread of scores for one transaction submitted repeatedly"]],
      widths=[2.0, 4.0])
section("5.3 Experimental Results")
table("Confusion matrix at REVIEW 40, BLOCK 70",
      ["Decision", "Actually fraud", "Actually legitimate"],
      [[d, CONF[d]["fraud"], CONF[d]["legit"]] for d in ("APPROVE", "REVIEW", "BLOCK")],
      widths=[1.6, 1.6, 1.8])
table("Headline results",
      ["Measure", "Value"],
      [["Precision (flagged)", f"{FLAGGED['precision']:.3f}"],
       ["Recall (flagged)", f"{FLAGGED['recall']:.3f}"],
       ["F1 (flagged)", f"{FLAGGED['f1']:.3f}"],
       ["False-positive rate", f"{REALISTIC['false_positive_rate']:.4f}"],
       ["Precision at 0.1% prevalence", f"{REALISTIC['precision']:.3f}"],
       ["Ring transactions flagged by the graph layer",
        f"{GRAPH['graph_flagged']} of {GRAPH['ring_transactions']}"],
       ["BLOCK decisions", "0 (highest score 68)"]],
      widths=[3.2, 1.8])
para("The composite scores of the two classes barely overlap (Figure 5.1). Every legitimate "
     "transaction but one scored below 40, most below 10; the fraudulent transactions "
     "cluster between 40 and 69, with seven below the review threshold.")
figure(os.path.join(ASSETS, "score-distribution.png"), "Composite score by true label")
_by = lambda p: [r for r in LAYERS if r["pattern"] == p]
table("Results by planted pattern",
      ["Pattern", "Transactions", "Flagged", "Mean score"],
      [[name, len(_by(p)), sum(r["composite_score"] >= 40 for r in _by(p)),
        f"{mean(r['composite_score'] for r in _by(p)):.1f}"]
       for name, p in [("Mule ring", "mule_ring"), ("Shared IP", "shared_ip"),
                       ("Shared device", "shared_device"), ("Legitimate", "normal")]],
      widths=[1.6, 1.3, 1.1, 1.3])
para("Four scenarios were also run against the live system on 11 September 2026, each with "
     "account identifiers not used before (Table 5.6).")
table("Scenario tests on the running system",
      ["Scenario", "Rule + graph + LLM", "Decision"],
      [["Retail purchase on a fresh device", "0 + 0 + 0 = 0", "APPROVE"],
       ["Blacklisted sender, ₹5,000 groceries", "40 + 0 + 28 = 68", "REVIEW"],
       ["₹7,04,000 wire into a device and IP cluster", "25 + 30 + 28 = 83", "BLOCK"],
       ["Fourth transfer around a new three-account ring", "10 + 20 + 28 = 58", "REVIEW"]],
      widths=[3.0, 1.9, 1.1])
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
      widths=[2.0, 1.2, 1.2, 1.2])
table("Pipeline before and after the Review 1 changes",
      ["Measure", "Before", "After"],
      [["Precision", "0.938", f"{FLAGGED['precision']:.3f}"],
       ["Recall", "0.865", f"{FLAGGED['recall']:.3f}"],
       ["F1", "0.900", f"{FLAGGED['f1']:.3f}"],
       ["Legitimate transactions flagged", "3", "1"],
       ["Ring transactions flagged", "35 of 36", "36 of 36"],
       ["Mean response time", "14,046 ms", "124 ms"]],
      widths=[2.6, 1.3, 1.3])
para("Published results are not directly comparable, because they are measured on different "
     "data. APATE was evaluated on real card transactions [2], and the ensemble of "
     "Vijayanand and Smrithy reported 99.904 per cent accuracy on PaySim [4], where fraud is "
     "about 0.13 per cent of records and accuracy is dominated by the legitimate class. "
     "Comparing Indus11 with them would require running it on the same dataset, which is "
     "listed as future work.")
section("5.5 Component/Ablation Analysis")
para("Removing layers from the composite score, with the thresholds unchanged, shows what each "
     "contributes (Table 5.9 and Figure 5.2). No layer on its own flags a fraudulent "
     "transaction: their budgets of 40, 30 and 30 are at or below the review threshold by "
     "design. Rules with graph analysis, or graph analysis with the language model, catch "
     "roughly half of the fraud. All three together are needed for 86.5 per cent recall.")
table("Ablation by layer combination (REVIEW at 40)",
      ["Layers", "Precision", "Recall", "F1", "TP", "FP"],
      [[a["layers"], f"{a['precision']:.3f}", f"{a['recall']:.3f}", f"{a['f1']:.3f}",
        a["tp"], a["fp"]] for a in ABLATION],
      widths=[1.4, 1.0, 1.0, 1.0, 0.6, 0.6])
figure(os.path.join(ASSETS, "ablation.png"), "Precision, recall and F1 by layer combination")
para("Figure 5.3 shows where the points come from for each planted pattern. Mule-ring and "
     "shared-IP transactions receive most of their points from the graph and language-model "
     "layers. Shared-device transactions receive graph points but only two language-model "
     "points on average, which is why seven of the ten fall below 40. Legitimate traffic "
     "averages 6.4 points in total.")
figure(os.path.join(ASSETS, "layer-points-by-pattern.png"), "Mean layer points by planted pattern")
_fraud = [r for r in LAYERS if r["label"] == "fraud"]
_legit = [r for r in LAYERS if r["label"] == "legit"]
table("Mean layer points by true label",
      ["Label", "Rule", "Graph", "LLM", "Composite"],
      [[name, f"{mean(r['rule_score'] for r in g):.1f}", f"{mean(r['graph_score'] for r in g):.1f}",
        f"{mean(r['rag_score'] for r in g):.1f}", f"{mean(r['composite_score'] for r in g):.1f}"]
       for name, g in (("Fraud", _fraud), ("Legitimate", _legit))],
      widths=[1.4, 0.9, 0.9, 0.9, 1.1])
section("5.6 Performance Analysis")
table("Response time after the decision-path split (29 requests)",
      ["Measure", "Value"],
      [["Mean", "124 ms"], ["Median", "114 ms"], ["95th percentile", "189 ms"],
       ["Maximum", "287 ms"], ["Within the 500 ms budget", "29 of 29"],
       ["Rule engine", "8 ms"], ["Graph analyzer", "about 20 ms"],
       ["Language-model layer (after the response)", "13–14 s"]],
      widths=[3.2, 1.6])
para("The response time fell from 14,046 ms to a mean of 124 ms when the language model was "
     "moved out of the request path. The graph layer's cycle query needed separate work, "
     "summarised in Table 5.12.")
table("Circular-flow check: correctness and cost",
      ["Version", "False-positive share", "Query time"],
      [["No time window", "44.9%", "260 ms"],
       ["72 h window, counting every path", "0.0%", "1,800 ms"],
       ["72 h window, existence check", "10.3%", "about 20 ms"]],
      widths=[2.8, 1.6, 1.3])
para("Determinism was measured by submitting one wire transfer five times. At Ollama's default "
     "temperature the language-model scores were 26, 20, 20, 21 and 22. With the temperature "
     "set to zero all five were 20.")
section("5.7 Scalability Analysis")
para("The main scaling risk found was growth of the transaction graph. Without a time window, "
     "1,486 stored transactions produced 51,146 closed paths of two to four hops, because any "
     "account that both sends and receives money eventually forms one; the cost and the false "
     "positives both grew with history. Restricting cycles to 72 hours and to time order bounds "
     "the paths a query can examine, and stopping at the first match keeps the check near "
     "20 ms on the seeded graph.")
bullets([
    "The service keeps no state between requests, so more API instances could be added "
    "behind a load balancer; this has not been tested.",
    "Background language-model work is capped at four concurrent tasks. Replaying 208 "
    "transactions without the cap started 208 model calls at once and stopped the API process.",
    "The measured latency comes from 29 sequential requests on one machine. Sustained load and "
    "concurrent-user tests have not been run.",
    "Transactions are retained indefinitely; the query is bounded, but the graph itself is not.",
])
section("5.8 Discussion")
para(f"The synthetic evaluation set is 25 per cent fraud because a test set needs enough fraud "
     f"to measure. A payment feed is nearer one fraudulent transaction in a thousand. Holding "
     f"this run's recall of {FLAGGED['recall']:.3f} and false-positive rate of "
     f"{REALISTIC['false_positive_rate']:.4f} constant, Equation 3.8 gives a precision of "
     f"{REALISTIC['precision']:.3f} at that prevalence: about eight false alarms for every "
     f"fraud caught. That figure, not the synthetic one, is what a deployment would staff "
     f"against.")
para(f"No transaction reached the block threshold; the highest score was 68. The threshold "
     f"sweep finds the best F1 with a review threshold of {SUGGESTED['review_threshold']} and "
     f"a block threshold of {SUGGESTED['block_threshold']}, but blocking at 40 would also "
     f"refuse the one flagged legitimate transaction outright. The configured bands were left "
     f"in place, and every detection reaches an analyst.")

# ───────────────────────── CHAPTER 6 ─────────────────────────
chapter("Results and Discussion")
section("6.1 Key Findings")
bullets([
    f"The full pipeline flags {FLAGGED['recall']*100:.1f} per cent of the fraud with "
    f"{FLAGGED['precision']*100:.1f} per cent precision on the synthetic set; at a realistic "
    f"fraud rate the precision would be about {REALISTIC['precision']*100:.0f} per cent.",
    "No layer detects fraud on its own; the combination of relationship evidence and the "
    "language model's assessment is what separates the classes.",
    "The decision is returned in 124 ms on average, all 29 measured requests within 500 ms.",
    "An identical transaction now scores identically.",
    "The graph layer flagged all 36 mule-ring transactions, but its circular-flow check fired "
    f"on {CYCLE_HITS} of them; the rest were caught through proximity to known fraud accounts.",
    "Nothing is blocked automatically at the configured thresholds.",
])
section("6.2 Comparative Results")
para("Against its own earlier state (Table 5.8) the pipeline gained precision and F1, lost two "
     "false positives and became about 113 times faster in its response, with recall "
     "unchanged. Against the rule-only baseline (Table 5.7) the difference is between detecting "
     "none of the planted fraud and detecting 45 of 52. Against the commercial platforms "
     "(Table 2.2) the comparison remains one of design, since they have not been measured on "
     "this data.")
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
    "Seven of the ten shared-device frauds were missed.",
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
para("All seven missed frauds are shared-device transactions to crypto exchanges, each scored "
     "27: 10 rule points for the merchant and the elevated sender tier, 15 graph points for "
     "the shared device and 2 from the language model. The model did not treat a shared device "
     "as strong evidence even though the flag was given to it as a confirmed signal.")
sub("False positive")
para("The one legitimate transaction flagged scored 42: 40 rule points because its receiver, "
     "ACC-015, is blacklisted in the account store, plus 2 from the language model. The "
     "evaluation generator draws receivers for ordinary traffic at random and did not exclude "
     "blacklisted accounts, so this row is arguably mislabelled rather than a detector error.")
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
     "injection; and parameterised database queries. Four gaps remain. There is no per-user "
     "authentication, so every holder of the key has full override rights and actions are "
     "not attributed to a person. Traffic is not encrypted in the local configuration. The "
     "example configuration ships default database passwords. And the language model's "
     "output is validated only for referring to a flag, not for accuracy.")
section("7.2 Privacy")
para("The project processes no real personal data. A deployment on real transactions would "
     "process digital personal data within the meaning of India's Digital Personal Data "
     "Protection Act, 2023 [19], and would need to establish its lawful basis, limit the data "
     "it holds to what the decision needs, and secure it. Two design choices help: the "
     "language model runs locally by default, so transaction details are not sent to a "
     "third-party service, and no payment instrument data is stored. Two would need "
     "attention: records are kept indefinitely, and the optional external model provider "
     "would send transaction details off the premises.")
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
      size=10)

# ───────────────────────── CHAPTER 8 ─────────────────────────
chapter("Conclusion and Future Work")
section("8.1 Conclusion")
para("Indus11 returns an approve, review or block decision for a financial transaction in "
     "124 ms on average by letting deterministic rules and graph queries decide, and attaches "
     "a language-model explanation afterwards that is given the evidence those layers found. "
     f"On a labelled synthetic dataset of {COUNTS['total']} transactions it flagged "
     f"{FLAGGED['recall']*100:.1f} per cent of the fraud at {FLAGGED['precision']*100:.1f} per "
     "cent precision, and the ablation shows that no single layer, including the rule engine "
     "that conventional systems rely on, detects the planted fraud alone.")
para("The work also produced negative results that are recorded rather than hidden: precision "
     f"would fall to about {REALISTIC['precision']*100:.0f} per cent at a realistic fraud rate, "
     "nothing reached the block threshold, the cycle check misses the transfer that closes a "
     "ring, and the explanation guard withholds every explanation for transactions flagged "
     "only by risk tier.")
section("8.2 Limitations")
bullets([
    "Evaluation on synthetic data only, with far denser fraud than a real feed.",
    "Shared-device fraud largely missed; ring closure not detected on the closing transfer.",
    "Explanation guard defect for tier-only flags; explanation accuracy not verified.",
    "Shared-key protection only; latency measured without concurrent load.",
])
section("8.3 Future Work")
bullets([
    "Evaluate on PaySim or the IEEE-CIS dataset to obtain a realistic precision figure.",
    "Detect a ring on the transfer that closes it, and re-run the evaluation.",
    "Skip flags with no distinctive word in the explanation guard, and check explanation "
    "statements against the transaction's actual values.",
    "Resolve the block-threshold trade-off from recorded scores.",
    "Add per-user authentication, structured audit logging and a sustained load test.",
    "Bound the transaction graph with a retention or archival policy.",
    "Add a supervised classifier as a fourth scoring signal.",
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
    "fraud detection in mobile money transactions,” Intelligent Decision Technologies, 2025. "
    "[Online]. Available: https://doi.org/10.1177/18724981241289751",
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
section("Appendix A — Sample Database Records")
para("One record from each store, read from the running system on 11 September 2026. The "
     "transaction's explanation is shortened where marked.")
for heading, block in [
    ("MongoDB — accounts collection", """{
  "account_id": "ACC-014",
  "owner_name": "Nadia Osei",
  "avg_monthly_transaction": 88000.0,
  "is_blacklisted": true,
  "country_code": "CA",
  "risk_tier": "high"
}"""),
    ("MongoDB — transactions collection", """{
  "tx_id": "REHEARSE-1789102514-2",
  "sender_account_id": "ACC-013",
  "receiver_account_id": "ACC-451",
  "amount": 704000.0,
  "currency": "INR",
  "merchant_category": "wire_transfer",
  "device_id": "DEV-FRAUD-A",
  "ip_address": "203.0.113.66",
  "composite_score": 83,
  "decision": "BLOCK",
  "explanation": "Triggered signals: AMOUNT_ANOMALY (₹704000 vs avg
      ₹52000); HIGH_RISK_MERCHANT (wire_transfer); HIGH_RISK_SENDER_TIER;
      SHARED_DEVICE (8 accounts on device DEV-FRAUD-A); SHARED_IP (12
      accounts on IP 203.0.113.66); FRAUD_CLUSTER_PROXIMITY (5 fraud
      neighbors); wire_fraud. A massive wire transfer [...]",
  "rag_pending": false,
  "created_at": "2026-09-11T04:55:16.568000"
}"""),
    ("Neo4j — node and relationships", """(:Account {account_id: "ACC-451", risk_label: "fraud"})
  -[:SENT {tx_id: "STX-00001", amount: 7197.13,
           timestamp: "2026-06-01T00:00:00"}]->
(:Account {account_id: "ACC-452"})

(:Account {account_id: "ACC-451"})
  -[:USED_DEVICE]->
(:Device {device_id: "DEV-FRAUD-A"})"""),
    ("Redis — velocity window", """key     velocity:ACC-953          (sorted set, 600 second window)
member  "1789103111.565832:1e9ec825"
score   1789103111.565832"""),
    ("ChromaDB — fraud_patterns collection", """id        p05
metadata  {"type": "money_mule"}
document  Mule fee skimming: funds pass through a chain of accounts with
          each hop forwarding 85-95% of the amount received, the remainder
          kept as the mule's cut. Amounts that shrink hop-by-hop are the
          signature."""),
]:
    para(heading, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, after=4).paragraph_format.keep_with_next = True
    code_block(block)

section("Appendix B — Automated Test Suite")
para("The 101 tests run without a database or network connection (pytest tests/ -q) and are "
     "grouped below by what they protect.")
for heading, items in [
    ("tests/test_fraud.py — scoring layers, decision engine, failures and security (79 tests)", [
        "Rule engine: blacklist returns the maximum score; amount-anomaly and velocity flags; a "
        "clean transaction scores zero.",
        "Banking anomalies: structuring only just under the threshold; dormancy after 180 days; "
        "a new beneficiary only for an account with history and a large amount; pass-through, "
        "fan-out and odd-hour boundaries in India time; all anomalies share the 40-point cap. "
        "Each of the other nineteen anomaly rules has one case that fires and one just outside "
        "its condition.",
        "Layer failures: Redis down marks the rule engine as failed and Neo4j down the graph "
        "analyzer; a failed layer raises an approval to review but keeps an earned block; a "
        "failed model contributes no text; error-flag words are not evidence; two failures are "
        "named in one sentence; a background timeout is recorded; multi-line errors are "
        "flattened; an exception with no message is still named.",
        "Component restart: an unknown component is rejected; restart resets the client and "
        "reports the dependency's status.",
        "API key: a wrong or missing key is rejected; the configured key is accepted.",
        "Dashboard statistics: flag codes are read from an explanation whose details contain "
        "full stops; per-decision counts are pivoted with their totals.",
        "RAG pipeline: the prompt carries the rule and graph flags, renders “(none)” when "
        "there are none, and returns a score and explanation on success and on failure.",
        "Decision engine: the approve, review and block bands; the composite cap at 100; the "
        "explanation guard's fallback, acceptance, generic-word handling, flag-detail matching "
        "and skipping while pending."]),
    ("tests/test_eval.py — evaluation harness (22 tests)", [
        "Classification bands match the decision engine.",
        "Precision, recall and F1, including empty inputs without division by zero.",
        "Confusion-matrix counting and the flagged versus blocked views.",
        "The threshold sweep, including reporting no block threshold when none is reachable.",
        "Ring recall, deterministic generation of the labelled set and namespaced run "
        "identifiers.",
        "Parsing the language model's JSON when it echoes an example or adds prose.",
        "Precision at realistic prevalence and its edge cases.",
        "PaySim replay: row-to-transaction mapping and the per-rule and threshold summary."]),
]:
    para(heading, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, after=4).paragraph_format.keep_with_next = True
    bullets(items)

section("Appendix C — Reproducing the Results")
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
