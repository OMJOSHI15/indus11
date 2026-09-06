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

WEEK = 9
FROM_DATE, TO_DATE = "30-08-2026", "04-09-2026"   # Sunday to Friday
NEXT_FROM, NEXT_TO = "06-09-2026", "11-09-2026"   # Sunday to Friday

REPORTS = {
    "24DCE052": {
        "work": [
            "Traced a fault that only appears under sustained load: the background "
            "language-model call had no deadline, so a single hung request held its "
            "concurrency permit indefinitely. Four such requests stopped the entire "
            "background pipeline, and because nothing waits on those tasks it failed "
            "silently \u2014 no error, no log entry, transactions simply left marked as "
            "awaiting an explanation forever.",
            "Confirmed the diagnosis rather than assuming it: a restarted service "
            "completed the same transaction in twelve seconds, which isolated the "
            "cause to exhausted permits rather than to the model or the database. "
            "The call now carries a 180-second deadline, so a stalled request "
            "recovers on its own instead of blocking every later one.",
            "Corrected the accuracy harness, which had been recording the immediate "
            "response since the decision path was split and therefore omitted the "
            "language model's contribution from every transaction. It now waits for "
            "the background layer before recording a result.",
            "Merged the full set of review changes into the main branch after the "
            "test suite passed, and updated the specification's performance table, "
            "architecture description and security section to match what is now "
            "measured rather than what was originally predicted.",
        ],
        "plans": [
            "Rehearse the Review 2 demonstration end to end with the whole team.",
            "Measure sustained throughput rather than single-request latency.",
            "Decide whether background language-model work should survive a service "
            "restart, which it currently does not.",
            "Record a per-layer score breakdown for each transaction, which is not "
            "presently stored and had to be reconstructed for this week's results.",
        ],
        "references": [
            "R. Nystrom, \u201cDeadlines and cancellation in concurrent systems,\u201d "
            "ACM Queue, 2024.",
            "Python Software Foundation, \u201casyncio.wait_for and task "
            "cancellation,\u201d Python 3.12 documentation, 2026. [Online]. "
            "Available: docs.python.org",
            "C. Fidge, \u201cResource starvation and deadlock in bounded concurrent "
            "queues,\u201d Journal of Systems and Software, 2019.",
            "Git, \u201cgit-merge and fast-forward semantics,\u201d Git reference "
            "manual, 2026. [Online]. Available: git-scm.com/docs",
        ],
    },
    "24DCE040": {
        "work": [
            "Confirmed by measurement that last week's change to the circular-flow "
            "detection held up once the whole pipeline was re-evaluated. Precision "
            "rose from 93.8 to 97.8 per cent and the F1 score from 0.900 to 0.918, "
            "while recall was unchanged at 86.5 per cent \u2014 the intended outcome, "
            "since the change was meant to remove false alarms without losing "
            "genuine detections.",
            "Ring detection reached every planted case: 36 of 36 mule-ring "
            "transactions were flagged, against 35 of 36 before the change. "
            "Legitimate transactions wrongly flagged fell from three to one across "
            "the 208-transaction labelled set.",
            "Reviewed the one remaining circular-flow false positive to judge "
            "whether the 72-hour window is the right bound or whether the ordering "
            "condition needs tightening as well, which is the open question going "
            "into next week.",
        ],
        "plans": [
            "Tune the 72-hour window against the seeded data rather than leaving it "
            "at a first reasonable value.",
            "Resolve the single remaining circular-flow false positive.",
            "Write the retention and archival policy for the transaction graph, now "
            "that the windowing argument is settled.",
            "Add fan-in and fan-out mule patterns and measure the effect on ring "
            "recall.",
        ],
        "references": [
            "T. Pourhabibi, K. Ong, B. Kam and Y. Boo, \u201cFraud detection: a "
            "systematic literature review of graph-based anomaly detection "
            "approaches,\u201d Decision Support Systems, vol. 133, 2020.",
            "Financial Action Task Force, \u201cProfessional money laundering: "
            "typologies and layering timeframes,\u201d FATF Report, 2018.",
            "Neo4j, \u201cTemporal values and duration arithmetic in Cypher,\u201d "
            "Neo4j documentation, 2026. [Online]. Available: neo4j.com/docs",
            "D. Powers, \u201cEvaluation: from precision, recall and F-measure to "
            "informedness, markedness and correlation,\u201d Journal of Machine "
            "Learning Technologies, vol. 2, 2011.",
        ],
    },
    "24DCE029": {
        "work": [
            "Simplified the decision engine's explanation check after review: the "
            "two flags that tracked whether the language model had finished were "
            "collapsed into one, since they always moved together and an "
            "inconsistent pair was representable but meaningless, and the "
            "flag-matching logic was reduced from two functions to one.",
            "Removed unnecessary state from the dashboard's analysis panel and "
            "accuracy panel \u2014 a stored timer reference that could outlive the "
            "effect that created it, and a memoised callback with a single caller "
            "that could never change \u2014 leaving the same behaviour with less to go "
            "wrong.",
            "Confirmed the explanation-validation guard behaves correctly against "
            "the corrected accuracy run, including the case that originally "
            "defeated it, where a generic risk term in the flag name matched "
            "ordinary risk prose in an unrelated explanation.",
        ],
        "plans": [
            "Show the pending state in the flagged-transactions table, not only on "
            "the analysis panel.",
            "Add an end-to-end test for the explanation guard against real model "
            "output rather than fixture text.",
            "Continue the accessibility pass over the dashboard against contrast "
            "and keyboard requirements.",
            "Mark a decision that changes after the language model lands, so a "
            "revised outcome is visible to the analyst as a revision.",
        ],
        "references": [
            "React, \u201cYou might not need an effect,\u201d react.dev, 2026. "
            "[Online]. Available: react.dev/learn",
            "React, \u201cReferencing values with refs \u2014 when not to use a ref,\u201d "
            "react.dev, 2026. [Online]. Available: react.dev/learn",
            "M. Fowler, \u201cRefactoring: Improving the Design of Existing Code,\u201d "
            "2nd ed., Addison-Wesley, 2018.",
            "K. Beck, \u201cTidy First? A Personal Exercise in Empirical Software "
            "Design,\u201d O'Reilly, 2023.",
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
