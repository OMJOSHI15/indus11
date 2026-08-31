"""
Build the weekly reports for one week, one file per team member.

The previous week's report is used as the template so the university's layout,
fonts and signature block carry over untouched; only the dates, the two bullet
lists and the references are rewritten.

References are held per member per week and checked against every earlier week
before a file is written. The guide's review found the same three sources
repeated in Weeks 1 and 2 and again in Weeks 3 and 4, so a repeat is an error
here rather than something to be noticed after submission.

    python docs/build_weekly.py
"""
import copy
import os
import re
import subprocess

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.text.paragraph import Paragraph

DOWNLOADS = os.path.expanduser("~/Downloads")
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

WEEK = 8
FROM_DATE, TO_DATE = "23-08-2026", "28-08-2026"   # Sunday to Friday
NEXT_FROM, NEXT_TO = "30-08-2026", "04-09-2026"   # Sunday to Friday

REPORTS = {
    "24DCE052": {
        "work": [
            "Benchmarked the split decision path against the running stack: the "
            "endpoint now answers in 124 ms on average and 189 ms at the 95th "
            "percentile, with all 29 sampled requests inside the 500 ms budget "
            "agreed at Review 1, against the 14,046 ms measured before the split.",
            "Traced and fixed two robustness faults that only appeared once the "
            "system was driven at volume: replaying the full evaluation set queued "
            "one language-model call per transaction with no limit and killed the "
            "API process, and a failed background task left its transaction marked "
            "pending forever instead of falling back to the decision already made.",
            "Found that the accuracy harness had been quietly measuring the wrong "
            "thing since the split — it scored the immediate response, which no "
            "longer includes the language model's contribution, understating recall "
            "as 0.462 against 0.865 for the same pipeline. It now waits for the "
            "background layer before recording a result.",
            "Wrote the comparison against FICO Falcon, Feedzai and Featurespace that "
            "the industry expert asked for at Review 1, including where this project "
            "does not compete: no consortium data, and accuracy measured on synthetic "
            "traffic far denser in fraud than a real feed.",
        ],
        "plans": [
            "Report the full accuracy re-run against the corrected harness.",
            "Rehearse the Review 2 demonstration end to end with the whole team.",
            "Measure throughput under sustained load rather than single-user latency.",
            "Decide whether the background language-model work should survive an API "
            "restart, which it currently does not.",
        ],
        "references": [
            "Amazon Web Services, \u201cTimeouts, retries and backoff with jitter,\u201d "
            "AWS Builders' Library, 2026. [Online]. Available: aws.amazon.com/builders-library",
            "B. Beyer et al., \u201cSite Reliability Engineering: load shedding and "
            "graceful degradation,\u201d O'Reilly, 2016.",
            "Python Software Foundation, \u201casyncio synchronization primitives,\u201d "
            "Python 3.12 documentation, 2026. [Online]. Available: docs.python.org",
            "Featurespace, \u201cARIC Risk Hub \u2014 adaptive behavioural analytics,\u201d 2026. "
            "[Online]. Available: featurespace.com",
        ],
    },
    "24DCE040": {
        "work": [
            "Measured which graph pattern actually produces the most false positives, "
            "the question left unanswered at Review 1, by replaying the 208-transaction "
            "labelled set through the graph layer. The answer contradicts what was said "
            "at the review: shared-device detection produced no false positives at all, "
            "while circular-flow produced 22 of them, a 44.9% false-positive rate.",
            "Established the cause: the cycle query had no time constraint, so it "
            "matched any path that eventually returned to the sender across the graph's "
            "whole history \u2014 1,486 transactions produced 51,146 such cycles, and any "
            "ordinary account that both sends and receives money forms one over time.",
            "Fixed it by constraining a cycle to a laundering-shaped window: every hop "
            "within 72 hours of the transaction and in chronological order. False "
            "positives fell from 44.9% to 10.3% with true detections essentially "
            "unchanged.",
            "Benchmarked the query afterwards and found the first version had made it "
            "seven times slower, 1,800 ms on a ring member, because it counted every "
            "matching path when the decision only needs to know whether one exists. "
            "Stopping at the first match and pruning by timestamp during expansion "
            "brought the whole graph layer to about 20 ms.",
            "Noted that this is the same root cause as the mentor's separate question "
            "about Neo4j at a million transactions \u2014 unbounded graph accumulation, "
            "surfacing as a false-positive problem before it becomes a storage one.",
        ],
        "plans": [
            "Tune the 72-hour window against the seeded data rather than leaving it at "
            "a first reasonable value.",
            "Investigate the three circular-flow false positives that remain.",
            "Write the retention and archival policy for the transaction graph, now "
            "that the windowing argument is settled.",
            "Add fan-in and fan-out mule patterns and measure the effect on ring recall.",
        ],
        "references": [
            "Neo4j, \u201cQuery tuning: planner, cardinality and expand pruning,\u201d Neo4j "
            "documentation, 2026. [Online]. Available: neo4j.com/docs/cypher-manual",
            "M. Weber et al., \u201cScalable graph learning for anti-money "
            "laundering: a first look,\u201d KDD Workshop on Anomaly Detection "
            "in Finance, 2019.",
            "L. Akoglu, H. Tong and D. Koutra, \u201cGraph-based anomaly detection and "
            "description: a survey,\u201d Data Mining and Knowledge Discovery, 2015.",
            "International Organization for Standardization, \u201cISO 8601 date and time "
            "representation,\u201d 2019.",
        ],
    },
    "24DCE029": {
        "work": [
            "Measured whether an identical transaction scores identically, which the "
            "industry expert asked at the follow-up session and was answered then as "
            "'two to five points apart'. Submitting the same wire transfer five times "
            "produced 26, 20, 20, 21 and 22 \u2014 a spread of six.",
            "Found the cause: the OpenAI client was created with temperature zero but "
            "the local Ollama client was not, so it ran at the default of roughly 0.8. "
            "At that setting the model also occasionally repeated a worked example "
            "verbatim instead of assessing the real transaction \u2014 one live wire "
            "transfer came back described as a small grocery purchase. Both clients now "
            "come from one helper with temperature zero, and five repeat submissions "
            "score identically.",
            "Closed a hole in the explanation-validation guard that let that grocery "
            "text through: the flag was HIGH_RISK_MERCHANT and the explanation "
            "contained the word 'risk', which was enough to satisfy the check. It now "
            "ignores generic risk vocabulary and matches on the flag's detail, so a "
            "wire-transfer flag is satisfied by an explanation that says 'wire "
            "transfer' and not by one that merely says 'risk'.",
            "Wired the dashboard to the pending state, so the language model's score "
            "and written explanation now appear on the analyst's screen as soon as they "
            "are ready rather than only after a manual refresh.",
        ],
        "plans": [
            "Show the same pending state in the flagged-transactions table, not only on "
            "the analyze panel.",
            "Add an end-to-end test for the explanation guard against real model output "
            "rather than fixture text.",
            "Continue the accessibility pass over the dashboard against contrast and "
            "keyboard requirements.",
            "Review whether a decision that changes after the language model lands "
            "should be visually marked as revised.",
        ],
        "references": [
            "A. Holtzman et al., \u201cThe curious case of neural text degeneration,\u201d "
            "ICLR, 2020.",
            "Ollama, \u201cModel parameters: temperature, top-k and top-p,\u201d Ollama "
            "documentation, 2026. [Online]. Available: github.com/ollama/ollama",
            "S. Minaee et al., \u201cLarge language models: a survey,\u201d 2024.",
            "Nielsen Norman Group, \u201cResponse times and the limits of human "
            "perception in interface feedback,\u201d 2026. [Online]. Available: nngroup.com",
        ],
    },
}

def _set_text(paragraph, text):
    """Replace a paragraph's text, keeping the first run's formatting."""
    for run in paragraph.runs[1:]:
        run._r.getparent().remove(run._r)
    if paragraph.runs:
        paragraph.runs[0].text = text
    else:
        paragraph.add_run(text)


def _rewrite(paragraphs, lines):
    """Replace a run of paragraphs with `lines`, cloning the first for format."""
    first = paragraphs[0]
    for extra in paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    _set_text(first, lines[0])
    cursor = first._p
    for line in lines[1:]:
        clone = copy.deepcopy(first._p)
        cursor.addnext(clone)
        cursor = clone
        _set_text(Paragraph(clone, first._parent), line)


def _reference_paragraphs(doc):
    """The numbered paragraphs that follow the References heading."""
    out, seen_heading = [], False
    for p in doc.paragraphs:
        if p.text.strip().startswith("References"):
            seen_heading = True
            continue
        if seen_heading:
            if re.match(r"^\d+\.", p.text.strip()):
                out.append(p)
            elif out:
                break
    return out


def _key(reference):
    """Compare references loosely: lower case, letters and digits only."""
    return re.sub(r"[^a-z0-9]+", "", reference.lower())[:60]


def earlier_references(student_id):
    """Every reference this student has already cited, keyed to its week."""
    seen = {}
    for week in range(1, WEEK):
        docx = os.path.join(DOWNLOADS, f"{student_id}_Week{week}.docx")
        pdf = os.path.join(DOWNLOADS, f"{student_id}_Week{week}.pdf")
        if os.path.exists(docx):
            lines = [re.sub(r"^\s*\d+\.\s*", "", p.text)
                     for p in _reference_paragraphs(Document(docx))]
        elif os.path.exists(pdf):
            text = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                                  check=True, capture_output=True, text=True).stdout
            lines = [re.sub(r"^\s*\d+\.\s*", "", ln)
                     for ln in text.splitlines() if re.match(r"^\s*\d+\.\s", ln)]
        else:
            continue
        for line in lines:
            seen.setdefault(_key(line), week)
    return seen


def _template_source(student_id):
    """The most recent earlier week's .docx still on disk. A submitted week's
    .docx is often cleaned out of Downloads afterward (only the PDF kept), so
    WEEK-1 isn't always there — walk back to whichever one is."""
    for week in range(WEEK - 1, 0, -1):
        path = os.path.join(DOWNLOADS, f"{student_id}_Week{week}.docx")
        if os.path.exists(path):
            return path
    raise SystemExit(f"{student_id}: no earlier week's .docx found to use as a template")


def build(student_id, spec):
    source = _template_source(student_id)
    doc = Document(source)

    dates = doc.tables[1]
    # The template's first column is a shade too narrow for the project ID, so
    # "PRJ_CE_5_2026_7" wraps onto a second line in some renderers. Widen it.
    for column, width in zip(dates._tbl.tblGrid.findall(qn("w:gridCol")), (3.2, 2.8)):
        column.set(qn("w:w"), str(int(width * 1440)))
    for row in dates.rows:
        row.cells[0].width = Inches(3.2)
        row.cells[1].width = Inches(2.8)
    _set_text(dates.cell(1, 0).paragraphs[0], f"From Date: {FROM_DATE}")
    _set_text(dates.cell(1, 1).paragraphs[0], f"To Date: {TO_DATE}")

    for p in doc.paragraphs:
        if p.text.startswith("Work done from Date:"):
            _set_text(p, f"Work done from Date: {FROM_DATE} to {TO_DATE}")
        elif p.text.startswith("Plans for next week:"):
            _set_text(p, f"Plans for next week: Date: {NEXT_FROM} to {NEXT_TO}")

    _rewrite(doc.tables[2].cell(0, 0).paragraphs,
             [f"•  {line}" for line in spec["work"]])
    _rewrite(doc.tables[3].cell(0, 0).paragraphs,
             [f"•  {line}" for line in spec["plans"]])
    _rewrite(_reference_paragraphs(doc),
             [f"{i}.  {r}" for i, r in enumerate(spec["references"], 1)])

    out = os.path.join(DOWNLOADS, f"{student_id}_Week{WEEK}.docx")
    doc.save(out)
    return out


if __name__ == "__main__":
    for student_id, spec in REPORTS.items():
        already = earlier_references(student_id)
        repeats = [r for r in spec["references"] if _key(r) in already]
        if repeats:
            raise SystemExit(f"{student_id}: already cited in an earlier week — {repeats}")
        out = build(student_id, spec)
        subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                        "--outdir", DOWNLOADS, out], check=True, capture_output=True)
        print(f"{student_id}: {os.path.basename(out)} + .pdf — "
              f"{len(spec['references'])} references, none of the "
              f"{len(already)} cited in Weeks 1-{WEEK - 1}")
