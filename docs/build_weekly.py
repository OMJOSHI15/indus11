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

WEEK = 10
FROM_DATE, TO_DATE = "06-09-2026", "11-09-2026"   # Sunday to Friday
NEXT_FROM, NEXT_TO = "13-09-2026", "18-09-2026"   # Sunday to Friday

REPORTS = {
    "24DCE052": {
        "work": [
            "Found that the language model had never been shown what the rule and "
            "graph layers detected: it received only the raw transaction, so its "
            "explanation was written without knowledge of the signals printed beside "
            "it. The detected flags are now passed into the prompt as confirmed "
            "findings. On a transaction from a blacklisted sender using a device "
            "shared with eight accounts, the model previously scored 0 and called the "
            "activity ordinary; it now scores 20 and cites both signals.",
            "Added precision at realistic fraud prevalence to the evaluation. The "
            "reported 0.978 is measured on a test set that is 25 per cent fraud; "
            "holding the same recall (0.865) and false-positive rate (0.0064), a feed "
            "with 0.1 per cent fraud gives precision 0.119, about eight false alarms "
            "per fraud caught. The specification now states both figures.",
            "Completed the comparison against FICO Falcon, Feedzai and Featurespace "
            "that had been planned since Week 8.",
            "Measured each layer's contribution to recall. The per-layer scores were "
            "not stored during the 31 August run, so they were reconstructed from "
            "each record's flag codes and the fixed layer weights. No single layer "
            "flags any fraud on its own; rule and graph together reach 0.462 recall, "
            "graph and language model 0.481, and all three 0.865.",
            "Checked the specification against the implementation and corrected what "
            "had drifted: diagrams that still placed the language model inside the "
            "request, a functional requirement promising model reasoning in every "
            "immediate response, and the outdated test count. Drafted the project "
            "report in the eight-chapter structure the team was given.",
        ],
        "plans": [
            "Record a failed scoring layer as a failure rather than a score of zero, "
            "send such transactions to review, and allow the failed component to be "
            "restarted from the dashboard.",
            "Store the per-layer score on every transaction so the contribution "
            "analysis no longer has to be reconstructed.",
            "Begin a sustained soak test of the analysis endpoint; only a short "
            "sequential burst has been measured so far.",
            "Rehearse the Review 2 demonstration end to end.",
        ],
        "references": [
            "Z. Ji, N. Lee, R. Frieske et al., “Survey of hallucination in natural "
            "language generation,” ACM Computing Surveys, vol. 55, no. 12, 2023.",
            "T. Saito and M. Rehmsmeier, “The precision-recall plot is more "
            "informative than the ROC plot when evaluating binary classifiers on "
            "imbalanced datasets,” PLoS ONE, vol. 10, no. 3, 2015.",
            "A. Dal Pozzolo, O. Caelen, R. A. Johnson and G. Bontempi, “Calibrating "
            "probability with undersampling for unbalanced classification,” IEEE "
            "Symposium Series on Computational Intelligence, 2015.",
            "ISO/IEC/IEEE, “Systems and software engineering — Life cycle "
            "processes — Requirements engineering,” ISO/IEC/IEEE 29148:2018, "
            "2018.",
        ],
    },
    "24DCE040": {
        "work": [
            "Separated what the graph layer detects from what the circular-flow check "
            "detects. The graph layer flagged all 36 mule-ring transactions, but the "
            "circular-flow check fired on only 21 of them; the other 15 were caught by "
            "fraud-cluster proximity alone.",
            "Traced why: the cycle query walks outward from the sender and requires "
            "timestamps to rise along the path, but the transfer that closes a ring "
            "is always the newest edge, so it can never satisfy the condition. "
            "Confirmed in Neo4j that the same ring returns no match from the closing "
            "sender and one match from the originator. A ring is currently detected "
            "only when its originator sends again.",
            "Resolved last week's open question about the remaining false positive. "
            "Its graph score was zero; the transaction was flagged because the "
            "evaluation generator had chosen a blacklisted account as the receiver "
            "for normal traffic. The 72-hour window is therefore not the cause.",
            "Added the transfer timestamp to the graph data dictionary, since the "
            "72-hour window depends on it, and corrected the level-2 data flow "
            "diagram.",
        ],
        "plans": [
            "Rewrite the cycle query so it matches the transfer that closes a ring.",
            "Rerun the full evaluation and recount circular-flow detections once the "
            "query changes.",
            "Stop the evaluation generator from drawing blacklisted accounts as "
            "receivers for normal traffic.",
            "Add fan-in and fan-out mule patterns and measure their effect on ring "
            "recall.",
        ],
        "references": [
            "D. B. Johnson, “Finding all the elementary circuits of a directed "
            "graph,” SIAM Journal on Computing, vol. 4, no. 1, 1975.",
            "P. Holme and J. Saramäki, “Temporal networks,” Physics Reports, "
            "vol. 519, no. 3, 2012.",
            "A. Paranjape, A. R. Benson and J. Leskovec, “Motifs in temporal "
            "networks,” Proc. ACM International Conference on Web Search and Data "
            "Mining (WSDM), 2017.",
            "Neo4j, “Cypher Manual: variable-length and quantified path "
            "patterns,” Neo4j documentation, 2026. [Online]. Available: "
            "neo4j.com/docs",
        ],
    },
    "24DCE029": {
        "work": [
            "Redesigned the dashboard around one rule: colour carries meaning, never "
            "decoration. Only the three decisions (approve, review, block) are shown "
            "in saturated colour; buttons, links and panels use neutral tones so "
            "nothing competes with risk for the analyst's attention. The row of four "
            "equal summary cards became one lead figure and a proportional bar "
            "showing the decision mix.",
            "Continued the accessibility pass by measuring contrast instead of "
            "judging it by eye. The block colour measured 3.93:1 and the faint text "
            "3.24:1, both under the 4.5:1 WCAG AA minimum; they were raised to 4.69:1 "
            "and 5.06:1.",
            "Fixed the decision chart breaking on narrow screens. Its ring had fixed "
            "pixel sizes and overflowed its panel below about 500 pixels; it now "
            "scales with its container, and below 560 pixels the chart and legend "
            "stack vertically. Checked at 420 and 375 pixels.",
            "Found a flaw in the explanation guard. Flags describing only the "
            "sender's risk tier contain nothing but generic words, which the guard "
            "ignores, so their explanations are always withheld; this happened on 139 "
            "of the 156 legitimate transactions in the evaluation.",
        ],
        "plans": [
            "Fix the explanation guard so risk-tier flags can be matched.",
            "Show a visible failure notice, with a restart option, when a scoring "
            "layer fails during analysis.",
            "Show the pending state in the flagged-transactions table, not only on "
            "the analysis panel.",
            "Test the explanation guard against real model output rather than "
            "fixture text.",
        ],
        "references": [
            "W3C, “Understanding Success Criterion 1.4.3: Contrast (Minimum),” "
            "WCAG 2.2 Understanding Docs, 2024. [Online]. Available: "
            "w3.org/WAI/WCAG22/Understanding",
            "S. Few, “Information Dashboard Design: Displaying Data for "
            "At-a-Glance Monitoring,” 2nd ed., Analytics Press, 2013.",
            "C. Ware, “Information Visualization: Perception for Design,” 4th ed., "
            "Morgan Kaufmann, 2020.",
            "Recharts, “ResponsiveContainer API reference,” recharts.org, 2026. "
            "[Online]. Available: recharts.org/en-US/api",
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
