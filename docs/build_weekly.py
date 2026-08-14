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

WEEK = 6
FROM_DATE, TO_DATE = "11-08-2026", "17-08-2026"
NEXT_FROM, NEXT_TO = "18-08-2026", "24-08-2026"

REPORTS = {
    "24DCE052": {
        "work": [
            "Drafted Chapters 1 to 3 of the Software Requirements Specification: purpose "
            "and scope, product perspective, user classes, operating environment, design "
            "constraints and assumptions.",
            "Wrote the functional requirements as a traceable table of 32 requirements, "
            "Applied the guide's exact formatting spec to the SRS: 2.54 cm margins on all "
            "four sides and 1.5 line spacing on every paragraph, including tables, "
            "captions and headings, with no exceptions left.",
            "Found and fixed three compounding bugs in the automated page-split checker "
            "(a colliding match on a repeated module name, a reading-order mismatch from "
            "wrapped table cells, and a wrap in the anchor cell itself), then used the "
            "corrected checker to find two tables that genuinely split across a page "
            "break at the new spacing.",
            "Split the 17-row functional requirements table into two and the 25-row "
            "definitions table into two, so every table in the document fits on a single "
            "page.",
            "Inserted the team's final abstract into the SRS after two review passes, "
            "catching a non-existent graph node in the first draft and an explanation for "
            "the empty BLOCK row that contradicted a claim made elsewhere in the same "
            "document.",
            "Presented Indus11 at Review 1 to the internal guide and industry expert Het "
            "Shah; answered questions on LLM latency versus deployability, RAG score "
            "determinism, authentication scope, and false positive and false negative "
            "behaviour.",
            "Prepared and submitted the individual Review 1 summary report.",
        ],
        "plans": [
            "Split the API's decision path per the industry expert's Review 2 suggestion, "
            "so the rule and graph layers return within a 500 ms budget independent of "
            "the LLM call.",
            "Add the FICO Falcon / Feedzai / Featurespace comparison table to the "
            "Literature Review.",
            "Add graph-layer degrade-on-failure handling for a Neo4j outage, matching the "
            "pattern already used for the RAG layer's fallback.",
            "Validate the LLM's written explanation against the actual triggered flags "
            "before it is returned.",
        ],
        "references": [
            "ECMA International, “Office Open XML File Formats (ECMA-376),” 6th ed., 2021.",
            "Microsoft, “Change the margins in a Word document,” Microsoft 365 "
            "documentation, 2026. [Online]. Available: support.microsoft.com",
            "python-docx, “python-docx documentation,” 2026. [Online]. "
            "Available: python-docx.readthedocs.io",
            "The Document Foundation, “LibreOffice documentation,” 2026. [Online]. "
            "Available: documentation.libreoffice.org",
        ],
    },
    "24DCE040": {
        "work": [
            "Presented the graph layer at Review 1; confirmed to the industry expert Het "
            "Shah that the class and activity diagrams were split into two figures each "
            "after measuring their rendered text had dropped to roughly 5 pt at print "
            "size.",
            "Answered the mentor's question on which fraud-graph pattern produces the "
            "most false positives, identifying shared-device detection as the main "
            "source, since multiple legitimate users on one device can trigger an "
            "unwarranted flag from an unrelated transaction.",
            "Began evaluating a retention or time-windowed approach for the "
            "circular-flow query, in response to the expert's question on graph and "
            "query behaviour after a million transactions with no deletion path.",
            "Reviewed the six diagrams now embedded in both the SRS and the review deck "
            "against the guide's earlier notation comments, to confirm nothing regressed "
            "after the deck's font-size and layout fixes.",
        ],
        "plans": [
            "Decide and document a stated retention or archival policy for the "
            "transaction graph, rather than leaving indefinite retention implicit.",
            "Add fan-in and fan-out mule detection patterns and measure the effect on "
            "ring recall.",
            "Benchmark the Cypher circular-flow query against the fully seeded graph to "
            "quantify how its cost grows with graph size.",
            "Investigate the seven undetected frauds from the accuracy evaluation.",
        ],
        "references": [
            "Neo4j, “Cypher performance and query tuning,” Neo4j developer "
            "documentation, 2026. [Online]. Available: neo4j.com/developer",
            "Neo4j, “Data modelling guidelines for graph growth and retention,” Neo4j "
            "developer documentation, 2026. [Online]. Available: neo4j.com/developer",
            "Neo4j, “APOC (Awesome Procedures on Cypher) library documentation,” 2026. "
            "[Online]. Available: neo4j.com/labs/apoc",
            "S. Ranka, “Graph database performance at scale,” O'Reilly, 2024.",
        ],
    },
    "24DCE029": {
        "work": [
            "Verified the dashboard against the live backend rather than the sample-data "
            "fallback: brought up MongoDB, Neo4j and Redis as local services and the "
            "FastAPI app, confirmed the dashboard's status badge switches to \"Live\" "
            "with real analyzed-transaction counts, and confirmed the graceful "
            "\"API offline\" fallback still renders correctly when the backend is "
            "unreachable.",
            "Presented at Review 1; answered the industry expert's question on the "
            "dashboard's behaviour when Neo4j is down, and confirmed this case is not "
            "yet handled rather than deflecting the question.",
            "Prepared and submitted the individual Review 1 summary report.",
            "Reviewed the Team Contributions slide against the team's actual current "
            "work split and corrected two attribution lines that had been swapped "
            "between members.",
        ],
        "plans": [
            "Add a visible per-layer status indicator to the dashboard, so a degraded "
            "layer (for example Neo4j down) is not invisible to the analyst.",
            "Add the decision-history timeline to the transaction detail view.",
            "Rehearse the Review 2 demonstration once the decision-path split lands.",
            "Run an accessibility pass over the dashboard against contrast and keyboard "
            "requirements.",
        ],
        "references": [
            "MDN Web Docs, “Using the Fetch API,” Mozilla, 2026. [Online]. "
            "Available: developer.mozilla.org",
            "Vite, “Env variables and modes,” Vite documentation, 2026. [Online]. "
            "Available: vitejs.dev",
            "React, “Synchronizing with Effects,” react.dev, 2026. [Online]. "
            "Available: react.dev",
            "Redis, “Caching with Redis,” Redis documentation, 2026. [Online]. "
            "Available: redis.io/docs",
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
