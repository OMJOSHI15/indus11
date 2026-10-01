"""
Build the companion glossary: ~/Downloads/Indus11_Glossary.docx

The guide asked that every member be able to account for every word in the
report. This explains each term the report uses, grouped the way a reader meets
them, with the figures read from the same evaluation file the report reads so
the two cannot drift apart.

    python docs/build_glossary.py
"""
import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.expanduser("~/Downloads/Indus11_Glossary.docx")

with open(os.path.join(HERE, "eval-results.json")) as f:
    EVAL = json.load(f)
CONF, FLAG = EVAL["metrics"]["confusion"], EVAL["metrics"]["flagged"]
REAL, COUNTS = EVAL["metrics"]["realistic"], EVAL["counts"]

FONT = "Times New Roman"
BODY, SUB, CHAP = 12, 14, 16
INK = RGBColor(0, 0, 0)

doc = Document()
for _s in doc.sections:
    _s.left_margin = _s.right_margin = Inches(1.0)
    _s.top_margin = _s.bottom_margin = Inches(1.0)


def para(text="", size=BODY, bold=False, italic=False,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=6, spacing=1.5, indent=0.0):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = spacing
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.size, r.font.name, r.font.color.rgb = Pt(size), FONT, INK
    return p


def heading(text):
    # The break is a property of the heading, not a paragraph of its own: a
    # break paragraph lands on the new page when the previous one is full and
    # spends a whole page showing nothing.
    p = para(text.upper(), CHAP, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)
    p.paragraph_format.page_break_before = True
    return p


def group(text):
    para(text, SUB, True, align=WD_ALIGN_PARAGRAPH.LEFT, after=4)


def term(name, meaning, answer=None):
    """One entry: the word, what it means, and what to say if an examiner asks."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.line_spacing = 1.5
    r = p.add_run(f"{name} — ")
    r.bold = True
    r.font.size, r.font.name, r.font.color.rgb = Pt(BODY), FONT, INK
    r = p.add_run(meaning)
    r.font.size, r.font.name, r.font.color.rgb = Pt(BODY), FONT, INK
    if answer:
        para(f"If asked: {answer}", 10.5, italic=True, after=4, spacing=1.0, indent=0.3)


# ────────────────────────── TITLE ──────────────────────────
para("INDUS11", CHAP, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("Glossary of Every Term Used in the Project Report",
     SUB, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("Companion document for the final review, 3 October 2026",
     11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)
para("PRJ_CE_5_2026_7 · Joshi Om (24DCE052) · Krish Gajera (24DCE040) · "
     "Drashti Dedaniya (24DCE029)", 11, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)
para("Every term the report uses is explained here in plain words. Where a term "
     "carries a number, the number is the one the report prints, read from the same "
     "evaluation file, so the two cannot disagree. Entries marked \"If asked\" give the "
     "answer to the question an examiner is most likely to put.",
     after=10)

# ───────────────────── 1. THE DECISION ─────────────────────
heading("1. The decision the system makes")
term("Transaction",
     "One payment: who sent it, who received it, how much, in which currency, from "
     "which device and network address, and under which merchant category. This is the "
     "only input the system takes.")
term("APPROVE",
     f"The decision returned when the composite score is below 40. The payment goes "
     f"through with no person involved. In the evaluation {CONF['APPROVE']['legit']} "
     f"legitimate transactions and {CONF['APPROVE']['fraud']} fraudulent ones were "
     f"approved.",
     "No fraud was approved in this run. That is what recall of 1.000 means.")
term("REVIEW",
     f"Returned when the score is 40 to 69. The payment is held for a human analyst. "
     f"{CONF['REVIEW']['fraud']} frauds and {CONF['REVIEW']['legit']} legitimate "
     f"transactions landed here.",
     "Review is not a failure. It is the system saying it has evidence but not enough "
     "to refuse on its own.")
term("BLOCK",
     f"Returned when the score is 70 or above. The payment is refused. "
     f"{CONF['BLOCK']['fraud']} frauds and {CONF['BLOCK']['legit']} legitimate "
     f"transactions reached this band.",
     "No legitimate transaction was ever blocked, so at these settings the system "
     "refuses only transactions it was right about.")
term("Composite score",
     "A single number from 0 to 100 formed by adding the three layer scores and "
     "capping the total at 100. It is what the decision bands are applied to. "
     "Equation 3.3 in the report.")
term("Decision band",
     "The rule that turns a score into a decision: below 40 approve, 40 to 69 review, "
     "70 and above block. Equation 3.4.")
term("Threshold",
     "The boundary between two bands. The review threshold is 40 and the block "
     "threshold is 70. Both are settings, not discoveries; they live in the "
     "environment file as REVIEW_THRESHOLD and BLOCK_THRESHOLD.",
     "A sweep suggested 45 and 50 would score slightly better, but those came from the "
     "same 208 rows the result is reported on, so they were not adopted.")
term("Layer budget",
     "The most points a layer may contribute: 40 for rules, 30 for the graph, 30 for "
     "the language model. No single layer can reach the block threshold of 70 alone.",
     "That is deliberate. Blocking a customer should need agreement from more than one "
     "kind of evidence.")
term("Explanation",
     "The sentence returned with every decision saying why, written by the language "
     "model from the flags the other two layers raised.")

# ───────────────────── 2. THE FIVE LAYERS ─────────────────────
heading("2. The five layers")
term("Pipeline",
     "The whole path a transaction takes from arrival to stored decision. Indus11's "
     "pipeline has five layers; three of them score, one prepares and one decides.")
term("Layer 1 — Gateway",
     "The FastAPI entry point. It checks the request matches the expected shape, loads "
     "both account profiles from Redis and falls back to MongoDB when the cache is "
     "cold, and applies rate limiting. It scores nothing.")
term("Layer 2 — Rule engine",
     "Deterministic checks on this transaction and the sender's recent history: "
     "blacklist, velocity, amount anomaly, merchant category, risk tier, and the "
     "twenty-five banking anomaly rules. Scores 0 to 40.",
     "Deterministic means the same input always gives the same points. Nothing is "
     "learned or guessed.")
term("Layer 3 — Graph analyzer",
     "Cypher queries over Neo4j looking for patterns that involve more than one "
     "transaction: shared devices, shared addresses, circular flows, mule chains and "
     "proximity to a known fraud account. Scores 0 to 30.",
     "This is the layer that sees what a single payment cannot show.")
term("Layer 4 — RAG pipeline",
     "Retrieves the three most similar fraud-pattern documents from ChromaDB, sends "
     "them with the transaction and the flags already raised to a local language "
     "model, and takes back a score and an explanation. Scores 0 to 30.")
term("Layer 5 — Decision engine",
     "Adds the three layer scores, caps the total at 100, maps it to a band, and "
     "applies the explanation guard and the failed-layer rule.")
term("Concurrency",
     "Running work at the same time rather than one after another. The rule engine and "
     "graph analyzer run concurrently, so the response waits for the slower of the two "
     "and not for their sum.")
term("Background task",
     "Work the server does after it has already answered. The language-model layer runs "
     "this way because it takes 13 to 14 seconds, far beyond the 500 ms budget.",
     "The caller gets a provisional decision immediately; the record is updated when "
     "the model finishes, and the dashboard polls until it does.")
term("Provisional decision",
     "The decision returned from the rule and graph layers alone, before the language "
     "model has run. It can be revised upward once the model's score arrives.")
term("Explanation guard",
     "A check that refuses to publish an explanation that does not mention any flag "
     "that actually fired. It prevents fluent text that has nothing to do with the "
     "evidence.",
     "It is a real safeguard with a known defect: for transactions flagged only by risk "
     "tier it withholds every explanation. That is recorded in the limitations.")
term("Failed layer",
     "A layer that could not run — its database was unreachable or it timed out. It "
     "contributes no points, and an APPROVE is raised to REVIEW.",
     "A layer that never looked at the transaction is missing evidence, not evidence "
     "that the transaction is safe.")

# ───────────────────── 3. THE MEASUREMENTS ─────────────────────
heading("3. The measurements")
term("Labelled dataset",
     f"A set of transactions where the truth is already known, so the system's answers "
     f"can be marked right or wrong. Indus11's has {COUNTS['total']} transactions: "
     f"{COUNTS['fraud']} fraudulent and {COUNTS['legit']} legitimate.")
term("Confusion matrix",
     "The table of every decision against its true label. Rows are what the system "
     "said, columns are what was true. Every metric below is computed from it.")
term("True positive (TP)",
     "A fraudulent transaction the system flagged. Correctly caught.")
term("False positive (FP)",
     "A legitimate transaction the system flagged. A false alarm, which costs a "
     "customer and an analyst's time.")
term("False negative (FN)",
     "A fraudulent transaction the system approved. Missed fraud, which costs money.")
term("True negative (TN)",
     "A legitimate transaction the system approved. The ordinary case.")
term("Precision",
     f"Of everything the system flagged, the share that really was fraud: TP divided by "
     f"TP plus FP. Measured at {FLAG['precision']:.3f}.",
     "High precision means the analyst is rarely sent a transaction that turns out to "
     "be fine.")
term("Recall",
     f"Of all the fraud present, the share the system caught: TP divided by TP plus FN. "
     f"Measured at {FLAG['recall']:.3f}.",
     "Recall of 1.000 means nothing labelled fraud was approved. It does not mean the "
     "system is perfect; it means it missed none in this set.")
term("F1 score",
     f"The harmonic mean of precision and recall, a single number balancing the two. "
     f"Measured at {FLAG['f1']:.3f}. Equation 3.7.",
     "The harmonic mean is used rather than the average because it punishes a low "
     "value in either one.")
term("Accuracy",
     "The share of all decisions that matched the label, approvals included. It is "
     "reported on the dashboard but read beside precision and recall, never instead of "
     "them.",
     "On a set that is mostly legitimate, a detector that flags nothing still scores "
     "high accuracy. That is why it is not the headline figure.")
term("Flagged view",
     "Counting a detection as REVIEW or BLOCK together. This is the view the headline "
     "figures use, because both outcomes stop the payment.")
term("Blocked view",
     "The stricter count, treating only BLOCK as a detection. Precision rises to 1.000 "
     "and recall falls, because review catches more than block does.")
term("False-positive rate",
     f"The share of legitimate transactions that were flagged: {REAL['false_positive_rate']:.4f}, "
     f"or about 1.3 in every 100.")
term("Prevalence",
     "How common fraud is in the traffic being scored. The test set is 25 per cent "
     "fraud; a real payment feed is nearer one in a thousand.")
term("Prevalence-adjusted precision",
     f"What precision this same detector would show at realistic prevalence, holding "
     f"recall and false-positive rate constant: {REAL['precision']:.3f}, about "
     f"{REAL['precision']*100:.0f} per cent. Equation 3.8.",
     "This is the honest figure. About eight false alarms for every fraud caught is "
     "what a deployment would staff against, not the 96 per cent.")
term("Ablation",
     "Switching parts off to see what each contributes. Each layer alone and each pair "
     "was measured separately.",
     "The rule engine alone reaches F1 0.172 and the graph and language layers alone "
     "reach zero. All three together reach 0.981. No layer carries the result by "
     "itself.")
term("Baseline",
     "The simpler system a result is compared against — here the rule engine on its "
     "own, which is what conventional fraud systems rely on.")
term("Latency",
     "How long a request takes to answer. Reported as mean 124 ms, median 114 ms, "
     "95th percentile 189 ms and maximum 287 ms over 29 requests.")
term("p95 (95th percentile)",
     "The value 95 out of 100 requests came in under. It describes the slow tail that "
     "an average hides.")
term("Determinism",
     "Giving the same answer for the same input every time. The language model was "
     "measured at scores of 26, 20, 20, 21, 22 at its default setting, and 20 five "
     "times out of five with temperature set to zero.")

# ───────────────────── 4. FRAUD AND BANKING ─────────────────────
heading("4. Fraud and banking terms")
term("Money mule",
     "An account used to move someone else's criminal money, often belonging to a "
     "person recruited for the purpose.")
term("Mule ring",
     "A loop of mule accounts passing funds around so the money returns near where it "
     "started, each hop keeping a small fee. The seeded data has three rings, of four, "
     "five and three accounts.")
term("Circular flow",
     "Money that leaves an account and comes back to it through other accounts. "
     "Detected as a path of two to four transfers within 72 hours, in time order. "
     "Worth 12 graph points.")
term("Fee skimming",
     "Each hop in a ring keeps a percentage, so amounts shrink along the chain. The "
     "mule check looks for each hop retaining 75 to 100 per cent of the one before.")
term("Hop",
     "One transfer in a chain. A four-hop cycle is four transfers returning to the "
     "sender.")
term("Structuring",
     "Splitting a payment to stay just under a reporting limit. Detected between 90 "
     "and 100 per cent of the ₹10,00,000 limit.")
term("Smurfing",
     "Many small payments that together exceed a limit, spread so no single one draws "
     "attention. Detected when payments under ₹10 lakh total more than it within 24 "
     "hours.")
term("Pass-through",
     "Money arriving and leaving almost immediately, the signature of an account used "
     "only to relay funds. Detected at 80 to 110 per cent of the amount received in 24 "
     "hours being sent on.")
term("Fan-out",
     "One account paying many beneficiaries in a short window — more than five payees "
     "in 24 hours.")
term("Fan-in",
     "Many accounts paying into one — more than ten senders in 24 hours.")
term("Account takeover",
     "A genuine account operated by someone other than its owner, usually visible as a "
     "sudden change of device, address or behaviour.")
term("Account draining",
     "Emptying an account quickly: three payments of ₹50,000 or more within an hour.")
term("Dormant account",
     "An account that has been inactive, here for 180 days, and suddenly transacts "
     "again.")
term("Impossible travel",
     "Two located payments so far apart in distance and so close in time that the same "
     "person could not have made both — over 900 km/h between them.")
term("Device hopping",
     "One account seen on more than three devices within 24 hours.")
term("Synthetic identity",
     "A fabricated customer built from a mix of real and invented details, which looks "
     "ordinary until its accounts are seen to share a device or address.")
term("Blacklist",
     "A list of accounts already known to be fraudulent. A blacklisted sender or "
     "receiver sets the rule score straight to 40, landing exactly on the review "
     "boundary.")
term("Risk tier",
     "A standing classification of a customer as standard, elevated or high risk, "
     "worth 2 or 5 points.")
term("Merchant category",
     "What kind of business the payment is to — wire transfer, crypto exchange, "
     "groceries. Some categories are higher risk, worth 8 points.")
term("Velocity",
     "How fast an account is transacting. The rule fires at more than five payments in "
     "ten minutes.")
term("New beneficiary",
     "A payee this account has never paid before. A large first payment to one is "
     "worth 8 points.")
term("UPI limit",
     "The ₹1,00,000 per-transaction ceiling on India's Unified Payments Interface. "
     "Repeated payments just below it suggest deliberate avoidance.")
term("Reporting limit",
     "The ₹10,00,000 threshold above which a transaction attracts regulatory "
     "reporting.")
term("Fraud cluster proximity",
     "The receiver sits within two relationship links of an account already labelled "
     "fraudulent. Worth 10 graph points.")
term("Label propagation",
     "Spreading a known fraud label outward across the graph, marking accounts within "
     "two hops as fraud-adjacent with a cluster identifier.")
term("CEO fraud",
     "A payment instruction that impersonates a senior executive to rush a transfer "
     "through.")
term("KYC / OTP scam phrases",
     "Wording in a payment note typical of social-engineering scams — KYC, OTP, "
     "lottery, refund. Worth 8 points.")

# ───────────────────── 5. TECHNOLOGY ─────────────────────
heading("5. Technology")
term("API (Application Programming Interface)",
     "The defined set of requests one program can make of another. Indus11 publishes "
     "eighteen such routes.")
term("REST",
     "A convention for APIs over HTTP where each address names a thing and the HTTP "
     "verb says what to do with it.")
term("Endpoint / route",
     "One address the API answers on, such as POST /api/v1/transactions/analyze.")
term("FastAPI",
     "The Python web framework the service is built on. It validates requests and "
     "generates the OpenAPI documentation automatically.")
term("Uvicorn",
     "The server process that actually runs the FastAPI application.")
term("Pydantic",
     "The library that defines the shape of every request and response and rejects "
     "anything that does not match.")
term("Schema",
     "The declared structure of a message or record: which fields exist and of what "
     "type.")
term("OpenAPI",
     "The machine-readable description of every route, which the service publishes at "
     "/docs as a browsable page.")
term("JSON",
     "The text format requests and responses are written in.")
term("MongoDB",
     "The document database holding accounts and the full record of every analysed "
     "transaction.")
term("Document database",
     "A store that keeps whole records as documents rather than as rows split across "
     "tables.")
term("Beanie / Motor",
     "Motor is the asynchronous MongoDB driver; Beanie is the object-document mapper "
     "layered on it, so Python classes map to stored documents.")
term("ODM (Object-Document Mapper)",
     "The translation layer between Python objects and database documents.")
term("Index",
     "A structure that makes lookups fast and can enforce uniqueness. The unique index "
     "on the transaction identifier is what turns a resubmitted transaction into a 409 "
     "response instead of a duplicate record.")
term("Neo4j",
     "The graph database holding accounts, devices and addresses as nodes and the "
     "transfers and shared identifiers between them as relationships.")
term("Graph database",
     "A store built for relationships, where asking what connects to what is cheap.")
term("Node / relationship",
     "A node is a thing — an account, a device. A relationship is a link between two "
     "of them, such as SENT or USED_DEVICE.")
term("Cypher",
     "Neo4j's query language, in which the patterns searched for are drawn as shapes.")
term("Redis",
     "The in-memory cache holding account profiles and the rolling history each rule "
     "reads.")
term("Sorted set",
     "A Redis structure keeping entries in score order. Timestamps are used as the "
     "score, which makes a rolling ten-minute window an exact range query.")
term("TTL (Time To Live)",
     "How long a cached value stays before expiring. Account profiles are cached for "
     "300 seconds.")
term("ChromaDB",
     "The vector store holding 58 fraud-pattern documents that the RAG layer searches.")
term("Vector store / embedding",
     "An embedding turns text into a list of numbers that places similar meanings near "
     "each other; a vector store holds them so the nearest can be found quickly.")
term("Retrieval",
     "Fetching the most similar stored documents for the transaction at hand — the "
     "three nearest of 58.")
term("RAG (Retrieval-Augmented Generation)",
     "Giving a language model retrieved reference material along with the question, so "
     "its answer is grounded in that material rather than in memory alone.")
term("LangChain",
     "The library that wires retrieval and the model call together.")
term("LLM (Large Language Model)",
     "A model trained to produce text. Here it scores the transaction and writes the "
     "explanation.")
term("Ollama",
     "The runtime that serves the language model locally, so no transaction data "
     "leaves the machine.")
term("llama3",
     "The specific open-weights model used, run through Ollama.")
term("Temperature",
     "How much randomness the model is allowed. Set to zero so the same transaction "
     "produces the same score.")
term("Few-shot examples",
     "Worked examples placed in the prompt to anchor the scale and format the model "
     "should answer in.")
term("Prompt",
     "The full text sent to the model: the transaction, the retrieved patterns, the "
     "flags already raised and the instructions.")
term("asyncio.gather",
     "The Python call that runs several asynchronous operations at once and waits for "
     "them all — how the rule and graph layers run concurrently.")
term("Semaphore",
     "A counter limiting how many things happen at once. Four background model calls "
     "are allowed; without the cap, replaying 208 transactions started 208 model calls "
     "and stopped the API process.")
term("Timeout",
     "A limit on how long to wait. The language-model layer is given 180 seconds, after "
     "which it is marked failed.")
term("Rate limiting",
     "Capping how many requests a caller may make: 120 a minute overall and 30 a minute "
     "on the analyse route.")
term("409 response",
     "The HTTP status meaning conflict. Returned when a transaction identifier already "
     "exists, so a retry does not create a second record.")
term("API key",
     "The shared secret required on every route that changes data.",
     "It is shared across users, so an override cannot be attributed to a person. That "
     "is listed as a deployment risk.")
term("CORS",
     "The browser rule governing which sites may call the API.")
term("React",
     "The JavaScript library the analyst dashboard is built with.")
term("Docker Compose",
     "A file defining the whole stack as five containers so it can be started "
     "anywhere with one command.")
term("Container",
     "A packaged application with its dependencies, run in isolation from the host.")
term("pytest",
     "The Python testing framework. The suite has 113 tests and needs no database or "
     "network.")
term("CI (Continuous Integration)",
     "The service that runs the whole test suite automatically on every push to "
     "GitHub.")

# ───────────────── 6. METHOD, DATA AND DOCUMENTS ─────────────────
heading("6. Method, data and documents")
term("Synthetic data",
     "Transactions generated by the team rather than taken from a bank. No real "
     "customer or payment data appears anywhere in this project.",
     "This is the project's main limitation, and it is stated rather than hidden. "
     "Validating on PaySim or IEEE-CIS is the first item of future work.")
term("Seeded / deterministic generation",
     "The generator starts from a fixed seed, so it produces the same dataset every "
     "time and anyone can reproduce the results.")
term("Planted pattern",
     "A fraud deliberately placed in the generated data so it is known where the "
     "answer should be — the mule rings, the shared-device clusters.")
term("Ground truth / label",
     "The known correct answer for each transaction, against which decisions are "
     "marked.")
term("Evaluation harness",
     "The script that replays the labelled set through the live API, waits for the "
     "background layer, and writes the results file the report reads.",
     "An earlier version recorded the immediate response, which omitted the language "
     "model and under-reported recall. That fault is described in Section 6.6.")
term("Threshold sweep",
     "Trying every threshold pair to see which scores best. It suggested 45 and 50.",
     "Not adopted. They were derived from the same 208 rows the result is reported on, "
     "and tuning against the data you then report on is how a number stops meaning "
     "anything.")
term("Supervised classifier",
     "A model trained on labelled examples. Indus11 uses none; it is listed as future "
     "work, because it needs labelled data the team does not have.")
term("GNN (Graph Neural Network)",
     "A learned model over graph structure. Considered and rejected: it needs labelled "
     "graph data and training infrastructure a small team does not have.")
term("SHAP (SHapley Additive exPlanations)",
     "A standard technique for attributing a model's output to its inputs, mentioned "
     "in the literature review as how others explain learned models.")
term("AUC (Area Under the ROC Curve)",
     "A threshold-independent measure of separation between classes, named in the "
     "literature review.")
term("Baseline comparison",
     "Measuring the proposed system against a simpler one on identical data.")
term("SRS (Software Requirements Specification)",
     "The companion document holding the full requirement set and the complete diagram "
     "set. The report points to it rather than repeating it.")
term("DFD (Data Flow Diagram)",
     "A diagram of data moving between processes and stores. Level 0 is the system as "
     "one box; Level 1 opens it into seven processes and five stores.")
term("Gane–Sarson notation",
     "The specific DFD drawing convention the guide asked for at the proposal review.")
term("UML (Unified Modeling Language)",
     "The standard family of software diagrams — use case, class, activity, sequence, "
     "state, component and deployment.")
term("Use case diagram",
     "Who uses the system and what they can do with it.")
term("Class diagram",
     "The code's structures and how they relate.")
term("Activity diagram",
     "The order of steps in a workflow, including which run in parallel.")
term("Sequence diagram",
     "The calls between parts in time order, including when the response is returned "
     "and the background work begins.")
term("ER (Entity Relationship)",
     "The data model: which records exist and how they reference each other.")
term("Pseudocode",
     "Algorithm written in plain structured English rather than a real language, used "
     "for Algorithms 1 and 2.")

# ───────────────── 7. REGULATION ─────────────────
heading("7. Regulation and standards")
term("RBI (Reserve Bank of India)",
     "India's central bank. Its 2024 Master Directions on fraud risk management require "
     "regulated entities to maintain frameworks for prevention, early detection and "
     "timely reporting — reference [1], the reason explainability matters here.")
term("Master Directions",
     "The RBI's consolidated binding instructions to regulated entities on a subject.")
term("FIU-IND",
     "India's Financial Intelligence Unit, which publishes the red-flag indicators the "
     "banking anomaly rules were taken from.")
term("FATF",
     "The Financial Action Task Force, the inter-governmental body whose "
     "money-laundering typologies and high-risk jurisdiction list the rules draw on.")
term("STR (Suspicious Transaction Report)",
     "The report a bank files when a transaction meets reporting criteria.")
term("DPDP (Digital Personal Data Protection)",
     "India's data protection law, discussed in Chapter 7 because a real deployment "
     "would process personal data.")
term("Explainability",
     "Being able to say why a decision was made, in terms a person can act on. A "
     "regulatory requirement, not a convenience.")

# ───────────────── 8. THE NUMBERS TO KNOW ─────────────────
heading("8. The numbers every member must know")
group("If you remember nothing else")
for label, value in [
    ("Dataset", f"{COUNTS['total']} labelled transactions — {COUNTS['fraud']} fraud, "
                f"{COUNTS['legit']} legitimate"),
    ("Precision", f"{FLAG['precision']:.3f} — of what we flagged, this share was really fraud"),
    ("Recall", f"{FLAG['recall']:.3f} — no fraud was approved"),
    ("F1", f"{FLAG['f1']:.3f}"),
    ("Honest precision", f"{REAL['precision']:.3f} at one fraud in a thousand — "
                         f"about eight false alarms per fraud caught"),
    ("False-positive rate", f"{REAL['false_positive_rate']:.4f}"),
    ("Blocked", f"{CONF['BLOCK']['fraud']} fraud, {CONF['BLOCK']['legit']} legitimate"),
    ("Review", f"{CONF['REVIEW']['fraud']} fraud, {CONF['REVIEW']['legit']} legitimate"),
    ("Approved", f"{CONF['APPROVE']['fraud']} fraud, {CONF['APPROVE']['legit']} legitimate"),
    ("Thresholds", "review 40, block 70; layer budgets 40 / 30 / 30"),
    ("Latency", "mean 124 ms, median 114 ms, p95 189 ms, max 287 ms, all within 500 ms"),
    ("Language model", "13–14 s, which is why it runs after the response"),
    ("Graph layer", "36 of 36 planted ring transactions flagged"),
    ("Anomalies", "50 catalogued, 35 detected, 15 not — each with the data it would need"),
    ("Knowledge base", "58 fraud-pattern documents, 3 retrieved per transaction"),
    ("Tests", "113 automated tests, run in continuous integration on every push"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.5
    r = p.add_run(f"{label}: ")
    r.bold = True
    r.font.size, r.font.name, r.font.color.rgb = Pt(BODY), FONT, INK
    r = p.add_run(value)
    r.font.size, r.font.name, r.font.color.rgb = Pt(BODY), FONT, INK

para()
group("The four questions that are actually hard")
term("Why is precision 96 per cent here but 7 per cent in deployment?",
     "Because the test set is 25 per cent fraud and a real feed is nearer one in a "
     "thousand. Recall and false-positive rate do not change with prevalence; precision "
     "does. Equation 3.8 converts between them. The 7 per cent is the figure a bank "
     "would staff against, and it is in the report deliberately.")
term("Your data is synthetic — does any of this mean anything?",
     "It means the pipeline detects the patterns it was built to detect, and the "
     "ablation shows no single layer does it alone. It does not establish real-world "
     "accuracy, which is why the prevalence-adjusted figure is reported and why "
     "evaluating on PaySim or IEEE-CIS is the first item of future work.")
term("Recall is 1.000. Is the system perfect?",
     "No. It missed no fraud in this 208-row set. With 156 legitimate transactions the "
     "set is too small to resolve a false-alarm rate that matters at one fraud in a "
     "thousand, and the cycle check still misses the transfer that closes a ring.")
term("What does the language model actually add?",
     "On the ablation it scores nothing alone, because it is capped at 30 and cannot "
     "reach the review threshold by itself. Its contribution is the explanation and the "
     "points that push borderline transactions over 40 — and the guard makes sure the "
     "explanation matches the evidence.")

doc.save(OUT)
print(f"Saved {OUT}")
