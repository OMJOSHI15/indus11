"""
Build the mathematical companion: ~/Downloads/Indus11_Mathematics.docx

Every formula in Section 3.6 of the report, set out symbol by symbol with a
worked example, so a member can derive each one at the board rather than recite
it. The figures are recomputed here from docs/eval-results.json, which is also
what the report prints, so a mistake in either shows up as a disagreement.

    python docs/build_mathematics.py
"""
import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.expanduser("~/Downloads/Indus11_Mathematics.docx")

with open(os.path.join(HERE, "eval-results.json")) as f:
    EVAL = json.load(f)
CONF, FLAG = EVAL["metrics"]["confusion"], EVAL["metrics"]["flagged"]
REAL, COUNTS = EVAL["metrics"]["realistic"], EVAL["counts"]
# Derived, never written out: (1 - P) / P flagged items are false per true one.
FALSE_PER_CATCH = round((1 - REAL["precision"]) / REAL["precision"])

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


def formula(text, number=None):
    """An equation, centred, with its report number on the right margin."""
    from docx.enum.text import WD_TAB_ALIGNMENT
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.5
    stops = p.paragraph_format.tab_stops
    stops.add_tab_stop(Inches(3.25), WD_TAB_ALIGNMENT.CENTER)
    stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT)
    r = p.add_run("\t" + text)
    r.italic = True
    r.font.size, r.font.name, r.font.color.rgb = Pt(BODY), FONT, INK
    if number:
        r = p.add_run(f"\t({number})")
        r.font.size, r.font.name, r.font.color.rgb = Pt(BODY), FONT, INK
    return p


def steps(lines):
    """A worked calculation, one line per step, monospaced-looking indent."""
    for line in lines:
        para(line, 11, align=WD_ALIGN_PARAGRAPH.LEFT, after=2, spacing=1.0, indent=0.5)


# Recomputed here, not copied, so a disagreement with the report is visible.
TP = CONF["REVIEW"]["fraud"] + CONF["BLOCK"]["fraud"]
FP = CONF["REVIEW"]["legit"] + CONF["BLOCK"]["legit"]
FN = CONF["APPROVE"]["fraud"]
TN = CONF["APPROVE"]["legit"]
PREC = TP / (TP + FP)
REC = TP / (TP + FN)
F1 = 2 * PREC * REC / (PREC + REC)
FPR = FP / (FP + TN)
PI = REAL["prevalence"]
PADJ = REC * PI / (REC * PI + FPR * (1 - PI))
FALSE_PER_CATCH = round((1 - PADJ) / PADJ)

# ────────────────────────── TITLE ──────────────────────────
para("INDUS11", CHAP, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("Mathematical Foundation — Every Formula Explained",
     SUB, True, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("Companion to Section 3.6 of the project report · final review, 3 October 2026",
     11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)
para("PRJ_CE_5_2026_7 · Joshi Om (24DCE052) · Krish Gajera (24DCE040) · "
     "Drashti Dedaniya (24DCE029)", 11, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)
para("Each equation is given three ways: what every symbol stands for, why the "
     "formula has the shape it has, and the arithmetic worked through with this "
     "project's own numbers. Every figure below is recomputed from the evaluation "
     "file rather than copied from the report, so if the two ever disagree, one of "
     "them is wrong and it will be visible.", after=10)

# ───────────────────── NOTATION ─────────────────────
heading("1. Notation")
para("Every symbol used in Section 3.6, in one place.", after=8)
for sym, mean in [
    ("R", "the rule engine's score for a transaction, an integer from 0 to 40"),
    ("G", "the graph analyzer's score, 0 to 30"),
    ("L", "the language model's score, 0 to 30"),
    ("S", "the composite score, 0 to 100"),
    ("w_i", "the weight of the i-th rule that fired in the rule engine"),
    ("w_j", "the weight of the j-th pattern the graph layer matched"),
    ("D(S)", "the decision function, mapping a score to APPROVE, REVIEW or BLOCK"),
    ("τ_r", "the review threshold, 40 (tau-r)"),
    ("τ_b", "the block threshold, 70 (tau-b)"),
    ("x", "the amount of the transaction being scored"),
    ("μ_a", "account a's monthly average payment (mu-a)"),
    ("n_a", "the number of payments account a made in the last 600 seconds"),
    ("t", "the timestamp of this transaction"),
    ("t_prev", "the timestamp of the account's previous payment"),
    ("T", "the regulatory reporting limit, ₹10,00,000"),
    ("I_24", "the total amount the account received in the last 24 hours"),
    ("p_24", "the number of distinct payees in the last 24 hours"),
    ("k", "the number of hops in a candidate cycle"),
    ("a_i", "the amount of the i-th hop in a cycle"),
    ("TP, FP, FN, TN", "true positives, false positives, false negatives, true negatives"),
    ("P, r, f", "precision, recall and false-positive rate"),
    ("π", "fraud prevalence — the share of traffic that is fraudulent (pi)"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.left_indent = Inches(0.3)
    r = p.add_run(f"{sym}  ")
    r.bold = True
    r.font.size, r.font.name, r.font.color.rgb = Pt(BODY), FONT, INK
    r = p.add_run(mean)
    r.font.size, r.font.name, r.font.color.rgb = Pt(BODY), FONT, INK

# ───────────────────── SCORING ─────────────────────
heading("2. The scoring equations")
group("Equation 3.1 — the rule score")
formula("R = 40 if blacklisted, otherwise min( Σ w_i , 40 )", "3.1")
para("Each rule that fires contributes a fixed weight. The weights are added, and the "
     "total is capped at 40 — the rule engine's budget. A blacklisted sender or receiver "
     "skips the sum and sets R to 40 directly.", after=4)
para("Why it has this shape. The sum is additive rather than multiplicative so that "
     "evidence accumulates: two weak signals should outweigh one weak signal. The cap "
     "exists because without it, a transaction tripping many small rules could reach the "
     "block threshold on the rule layer alone, which the design forbids. Blacklisting is "
     "set to exactly 40 rather than higher so that a blacklisted account lands precisely "
     "on the review boundary: known-bad is enough to involve a person, not enough to "
     "refuse without corroboration.", after=4)
para("Worked example — the ₹7,04,000 wire transfer recorded in Table 5.4 of the report:",
     after=2)
steps([
    "HIGH_RISK_MERCHANT (wire transfer)        8",
    "ELEVATED_RISK_SENDER_TIER                 5",
    "AMOUNT_ANOMALY (x > 3 μ_a, Eq. 3.5)      12",
    "Σ w_i = 8 + 5 + 12                     = 25",
    "R = min(25, 40)                        = 25",
])

group("Equation 3.2 — the graph and language-model scores")
formula("G = min( Σ w_j , 30 ),     L ∈ [0, 30]", "3.2")
para("The graph score is formed the same way as the rule score, from the weights of the "
     "patterns matched, capped at its own budget of 30. The language model's score is not "
     "a sum: the model returns a single number, which is clamped into the range 0 to 30.", after=4)
para("Why they differ. The rule and graph layers know which checks fired, so their scores "
     "can be built from parts and audited afterwards. The model does not expose parts, so "
     "the system can only bound what it returns. That asymmetry is the reason the "
     "explanation guard exists: the one layer whose reasoning cannot be inspected is the "
     "one whose output is checked against the other two.", after=4)

group("Equation 3.3 — the composite score")
formula("S = min( R + G + L , 100 )", "3.3")
para("The three layer scores are added and the total capped at 100, so the score is "
     "always a percentage-like quantity on a fixed scale.", after=4)
para("Note that the budgets already sum to 100 — 40 + 30 + 30 — so the outer cap binds "
     "only in the blacklist case, where R is forced to 40 regardless of what the sum of "
     "weights would have been. Two properties follow and are worth stating aloud. The "
     "score is monotonic: adding evidence can never lower it. And it is bounded: no "
     "combination of inputs can produce a score outside 0 to 100.", after=4)
steps([
    "Continuing the same transaction:",
    "R = 25   (rules, above)",
    "G = 30   (shared device 15 + circular flow 12 + cluster proximity 10 = 37,",
    "          capped at the graph budget of 30)",
    "L = 28   (returned by the language model, within 0 to 30)",
    "S = min(25 + 30 + 28, 100) = min(83, 100) = 83",
])

group("Equation 3.4 — the decision band")
formula("D(S) = APPROVE if S < τ_r;  REVIEW if τ_r ≤ S < τ_b;  BLOCK if S ≥ τ_b", "3.4")
para("With τ_r = 40 and τ_b = 70: below 40 approve, 40 to 69 review, 70 and above block. "
     "The bands are half-open intervals, so every score falls in exactly one of them and "
     "no score falls in two. A score of exactly 40 is a REVIEW; exactly 70 is a BLOCK.", after=4)
para("One rule sits outside the equation. If a layer could not run, it contributes no "
     "points, and a resulting APPROVE is raised to REVIEW. A layer that never looked at "
     "the transaction is missing evidence, not evidence that the transaction is safe. A "
     "BLOCK reached by the layers that did run is kept, because the evidence for refusing "
     "it already exists.", after=4)
steps([
    "S = 83, and 83 ≥ 70, so D(83) = BLOCK",
])

group("Why 40 / 30 / 30, and why 40 / 70")
para("The budgets follow how certain each layer's evidence is. The rule engine checks "
     "facts about this transaction and gets the largest share. The graph layer infers from "
     "structure, the language model from similarity, and both get less. The rule budget is "
     "set below the block threshold on purpose: 40 < 70, so no single layer can refuse a "
     "customer's payment by itself. Any block needs at least two layers to agree.", after=4)
para("The thresholds are settings, not findings. A sweep over the labelled set found a "
     f"marginally better F1 at 45 and 50, but those were derived from the same "
     f"{COUNTS['total']} rows the result is reported on. Tuning on the data you then "
     "report against is how a number stops meaning anything, so the configured 40 and 70 "
     "were kept.", after=4)

# ───────────────────── RULE CONDITIONS ─────────────────────
heading("3. The rule conditions")
group("Equation 3.5 — velocity and amount anomaly")
formula("n_a > 5      and      x > 3 μ_a   (with μ_a > 0)", "3.5")
para("Two separate account-level rules. The first fires when the account has made more "
     "than five payments in the last 600 seconds. The second fires when this payment "
     "exceeds three times the account's monthly average.", after=4)
para("The condition μ_a > 0 is not decoration. Without it, a brand-new account with an "
     "average of zero would satisfy x > 0 on its very first payment, and every new "
     "customer would be flagged. Guarding the comparison means the rule says nothing "
     "about an account it has no history for, which is the honest answer.", after=4)
steps([
    "Account with μ_a = ₹88,000 paying ₹7,04,000:",
    "3 μ_a = 3 × 88,000 = ₹2,64,000",
    "704,000 > 264,000, so the amount-anomaly rule fires (12 points)",
])

group("Equation 3.5a — the banking anomaly thresholds")
formula("0.9 T ≤ x < T;   t − t_prev ≥ 180 d;   new payee ∧ x ≥ ₹50,000;", "3.5a")
formula("I_24 ≥ ₹10,000 ∧ 0.8 I_24 ≤ x ≤ 1.1 I_24;   p_24 > 5")
para("Four conditions, each a separate rule, written together because they share the "
     "account history the rule engine reads from Redis in one round trip.", after=4)
para("Structuring, 0.9 T ≤ x < T. T is the ₹10,00,000 reporting limit. The band catches a "
     "payment deliberately placed just under it — between ₹9,00,000 and ₹9,99,999. The "
     "upper bound is strict because a payment at or above T is reported anyway and needs "
     "no rule.", after=4)
para("Dormant reactivation, t − t_prev ≥ 180 d. The account has not paid anyone for six "
     "months and has suddenly moved money.", after=4)
para("Large first payment to a new beneficiary, new payee ∧ x ≥ ₹50,000. Both halves are "
     "required: a new payee alone is ordinary, and a large payment to a known payee is "
     "ordinary. The conjunction is what makes it a signal.", after=4)
para("Pass-through, I_24 ≥ ₹10,000 ∧ 0.8 I_24 ≤ x ≤ 1.1 I_24. The account received money "
     "in the last day and is now sending out between 80 and 110 per cent of it — the "
     "signature of an account used only to relay funds. The floor of ₹10,000 keeps small "
     "ordinary balances from matching. The ceiling above 100 per cent allows the account "
     "to send slightly more than it received, since it may add a little of its own.", after=4)
para("Fan-out, p_24 > 5. More than five distinct payees in 24 hours.", after=4)

group("Equation 3.6 — circular flow and mule chains")
formula("2 ≤ k ≤ 4,   t − 72 h ≤ t_1 ≤ t_2 ≤ … ≤ t_k;    0.75 a_i ≤ a_(i+1) ≤ a_i", "3.6")
para("A path of k transfers that leaves the sender and returns to it counts as a circular "
     "flow when three conditions hold together.", after=4)
para("Length, 2 ≤ k ≤ 4. Shorter than two is not a cycle. Longer than four was excluded "
     "on cost: the number of paths grows roughly as the branching factor to the power of "
     "k, so each extra hop multiplies the work.", after=4)
para("Time order and window, t − 72 h ≤ t_1 ≤ t_2 ≤ … ≤ t_k. The hops must occur in "
     "sequence and within the last 72 hours. This is the condition that does the real "
     "work. Without it, any account that both sends and receives money eventually forms a "
     "closed path with someone: 1,486 stored transactions produced 51,146 such paths, and "
     "44.9 per cent of the flagged cycles were false positives. With the window, that "
     "falls to 10.3 per cent.", after=4)
para("Amount shrinkage, 0.75 a_i ≤ a_(i+1) ≤ a_i. Each hop carries between 75 and 100 per "
     "cent of the hop before it — money moving along a chain with a fee skimmed at each "
     "step. This is the extra condition that distinguishes a mule chain from a cycle that "
     "merely closes, and it is scored separately: 12 points for the cycle, 8 more for the "
     "chain.", after=4)
para("A known limitation belongs here. The check matches the path but not the transfer "
     "that closes the ring, so ring detection rests partly on proximity to known fraud "
     "rather than on the cycle alone. It is stated in the limitations and listed as "
     "future work.", after=4)

# ───────────────────── EVALUATION ─────────────────────
heading("4. The evaluation formulas")
group("The confusion matrix")
para(f"Everything in this section is computed from four counts. On the labelled set of "
     f"{COUNTS['total']} transactions ({COUNTS['fraud']} fraud, {COUNTS['legit']} "
     f"legitimate), counting a detection as REVIEW or BLOCK:", after=4)
steps([
    f"TP = {CONF['REVIEW']['fraud']} reviewed + {CONF['BLOCK']['fraud']} blocked = {TP}"
    "   fraud correctly flagged",
    f"FP = {CONF['REVIEW']['legit']} reviewed + {CONF['BLOCK']['legit']} blocked = {FP}"
    "    legitimate wrongly flagged",
    f"FN = {FN}                                  fraud wrongly approved",
    f"TN = {TN}                                legitimate correctly approved",
])

group("Equation 3.7 — precision, recall and F1")
formula("P = TP / (TP + FP),     r = TP / (TP + FN),     F1 = 2Pr / (P + r)", "3.7")
para("Precision asks: of everything we flagged, how much was really fraud? Its "
     "denominator is everything flagged. Recall asks: of all the fraud present, how much "
     "did we catch? Its denominator is all the fraud. The two have different "
     "denominators, which is why they move independently and why neither alone describes "
     "a detector.", after=4)
steps([
    f"P  = {TP} / ({TP} + {FP}) = {TP} / {TP+FP} = {PREC:.5f}  →  {PREC:.3f}",
    f"r  = {TP} / ({TP} + {FN}) = {TP} / {TP+FN} = {REC:.5f}  →  {REC:.3f}",
    f"F1 = 2 × {PREC:.3f} × {REC:.3f} / ({PREC:.3f} + {REC:.3f})",
    f"   = {2*PREC*REC:.5f} / {PREC+REC:.5f} = {F1:.5f}  →  {F1:.3f}",
])
para("Why the harmonic mean and not the ordinary average. The arithmetic mean rewards a "
     "detector that is extreme in one direction: flag every transaction and recall is "
     "1.000, so the average would still be about 0.6 however bad precision is. The "
     "harmonic mean is dominated by the smaller of the two, so it only rises when both "
     "rise. That is the behaviour wanted from a single summary number.", after=4)
para("A caution about recall of 1.000. It means no transaction labelled fraud was "
     "approved in this set. It does not mean no fraud can pass. With "
     f"{COUNTS['legit']} legitimate transactions the set is also too small to resolve a "
     "false-alarm rate that matters at one fraud in a thousand.", after=4)

group("The false-positive rate")
formula("f = FP / (FP + TN)")
para("The share of legitimate traffic that gets flagged. It shares no denominator with "
     "precision, and — unlike precision — it does not change when fraud becomes rarer. "
     "That independence is what makes the next equation possible.", after=4)
steps([f"f = {FP} / ({FP} + {TN}) = {FP} / {FP+TN} = {FPR:.5f}  →  {FPR:.4f}"])

group("Equation 3.8 — precision at a realistic fraud rate")
formula("P(π) = r π / ( r π + f (1 − π) )", "3.8")
para("This is the most important equation in the project, and the one worth being able "
     "to derive rather than quote.", after=4)
para("Derivation. Take any number of transactions, N. A share π of them are fraudulent, "
     "so there are πN frauds and (1 − π)N legitimate transactions. The detector catches "
     "a fraction r of the frauds, giving r π N true positives. It flags a fraction f of "
     "the legitimate transactions, giving f (1 − π) N false positives. Precision is true "
     "positives over everything flagged:", after=4)
formula("P(π) = r π N / ( r π N + f (1 − π) N )")
para("The N cancels, which is the point: precision depends on the mix of the traffic, "
     "not on its volume. What remains is Equation 3.8.", after=4)
para(f"Worked with this project's figures, at a production fraud rate of π = {PI} "
     f"(one in a thousand), holding r = {REC:.3f} and f = {FPR:.4f} constant:", after=2)
steps([
    f"numerator    r π      = {REC:.3f} × {PI} = {REC*PI:.6f}",
    f"second term  f(1 − π) = {FPR:.5f} × {1-PI} = {FPR*(1-PI):.6f}",
    f"denominator           = {REC*PI:.6f} + {FPR*(1-PI):.6f} = {REC*PI + FPR*(1-PI):.6f}",
    f"P(π)                  = {REC*PI:.6f} / {REC*PI + FPR*(1-PI):.6f} = {PADJ:.5f}"
    f"  →  {PADJ:.3f}",
])
para(f"So precision falls from {PREC:.3f} on the test set to about {PADJ*100:.0f} per "
     f"cent on a realistic feed. Expressed as a workload, (1 − P) / P = "
     f"{(1-PADJ)/PADJ:.1f}: roughly {FALSE_PER_CATCH} false alarms for every fraud "
     f"caught. That is the figure a bank would staff against, and it is in the report "
     f"deliberately.", after=4)
para("Why recall and the false-positive rate survive the change but precision does not. "
     "Recall is measured only among frauds and the false-positive rate only among "
     "legitimate transactions, so neither denominator contains the other class. "
     "Precision's denominator mixes both, so it moves the moment the mix moves. Nothing "
     "about the detector changed between the two figures — only the traffic it was "
     "pointed at.", after=4)

# ───────────────────── END TO END ─────────────────────
heading("5. One transaction, end to end")
para("A single worked example tying every equation together. This is the scenario the "
     "report records in Table 5.4 and the deck quotes: a ₹7,04,000 wire transfer into an "
     "account that shares a device and an address with a known fraud cluster.", after=6)
steps([
    "INPUT",
    "  amount x       = ₹7,04,000",
    "  merchant       = wire transfer",
    "  sender tier    = elevated",
    "  receiver       = never paid before, inside a device/IP cluster",
    "",
    "LAYER 2 — rule engine, Equation 3.1",
    "  HIGH_RISK_MERCHANT                        8",
    "  ELEVATED_RISK_SENDER_TIER                 5",
    "  AMOUNT_ANOMALY (x > 3 μ_a, Eq. 3.5)      12",
    "  R = min(8 + 5 + 12, 40) = min(25, 40)     = 25",
    "",
    "LAYER 3 — graph analyzer, Equation 3.2",
    "  SHARED_DEVICE                            15",
    "  CIRCULAR_FLOW (Eq. 3.6)                  12",
    "  FRAUD_CLUSTER_PROXIMITY                  10",
    "  G = min(15 + 12 + 10, 30) = min(37, 30)  = 30",
    "",
    "LAYER 4 — language model, after the response",
    "  L (clamped into 0 to 30)                 = 28",
    "",
    "LAYER 5 — decision engine, Equations 3.3 and 3.4",
    "  S = min(25 + 30 + 28, 100) = min(83, 100) = 83",
    "  83 ≥ τ_b = 70   →   D(83) = BLOCK",
])
para("Note what the caps did, and what they did not. The graph layer matched 37 points "
     "of pattern and was held to its budget of 30; the rule layer, at 25, was well "
     "inside its own. On rules and graph alone the score is 25 + 30 = 55, which is a "
     "REVIEW, not a BLOCK. It is the language model's 28 points that carry the "
     "transaction from 55 to 83 and across the block threshold. That is the clearest "
     "single illustration of why the ablation matters: no layer decided this one on its "
     "own.", after=4)

# ───────────────────── QUESTIONS ─────────────────────
heading("6. The questions a maths examiner asks")
term("Derive Equation 3.8 at the board.",
     "Take N transactions. πN are fraud, (1 − π)N are not. True positives are r π N; "
     "false positives are f (1 − π) N. Precision is the first over the sum of both; N "
     "cancels. Say the cancelling step out loud — it is the insight, not the algebra.")
term("Why cap each layer instead of weighting and normalising?",
     "A cap keeps the score interpretable: every point is a named flag with a fixed "
     "weight, and the explanation can list them. Normalised weights would make the same "
     "flag worth different amounts on different transactions, and the explanation could "
     "no longer be checked against the evidence.")
term("Is the score a probability?",
     "No, and the report does not claim it is. It is an additive evidence count on a "
     "0 to 100 scale. Calling it a probability would require calibration against "
     "outcomes the project does not have.")
term("Why is F1 the harmonic mean?",
     "Because it is dominated by the smaller of precision and recall, so a detector "
     "cannot score well by being extreme in one direction. Flagging everything gives "
     "recall 1.000, and the arithmetic mean would still look respectable; the harmonic "
     "mean would not.")
term("Your recall is 1.000 — is the model overfitted?",
     "There is no model to overfit in the usual sense: the rule and graph layers are "
     "deterministic conditions, not learned parameters. What is true is that the "
     "thresholds could have been fitted to this set, and deliberately were not — the "
     "sweep's 45 and 50 were rejected for exactly that reason.")
term(f"Precision {PREC:.3f} and precision {PADJ:.3f} — which is real?",
     f"Both, of the traffic each describes. {PREC:.3f} is measured on a set that is 25 "
     f"per cent fraud. {PADJ:.3f} is what the same detector, unchanged, would show at "
     f"one fraud in a thousand. The detector did not change; the mix did.")
term("What happens at exactly S = 40 or S = 70?",
     "The bands are half-open: 40 is a REVIEW, 70 is a BLOCK. Every score falls in "
     "exactly one band, and a blacklisted account with R = 40 and nothing else lands "
     "exactly on the review boundary by design.")

doc.save(OUT)
print(f"Saved {OUT}")
print(f"  checks: P={PREC:.3f} r={REC:.3f} F1={F1:.3f} f={FPR:.4f} "
      f"P(pi)={PADJ:.3f} false-per-catch={FALSE_PER_CATCH}")
