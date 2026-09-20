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
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph

HERE = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS = os.path.expanduser("~/Downloads")
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

WEEK = 11
FROM_DATE, TO_DATE = "13-09-2026", "18-09-2026"   # Sunday to Friday
NEXT_FROM, NEXT_TO = "20-09-2026", "25-09-2026"   # Sunday to Friday

REPORTS = {
    "24DCE052": {
        "work": [
"Took up the suggestion to work from the anomalies banks themselves watch for. Catalogued fifty "
            "anomaly types from the red-flag indicators the financial intelligence unit and "
            "the central bank publish, and from the international money-laundering "
            "typologies, then implemented twenty-five of them in the rule engine. They "
            "include amounts kept just under the ten-lakh reporting limit, several smaller "
            "payments that together cross it, a dormant account becoming active, money "
            "received and passed straight on, payments to many different beneficiaries in a "
            "day, a first payment to a new beneficiary, a payment from a new device or "
            "location, two payments too far apart to be the same person, and a payment note "
            "written in the language of a scam.",
            "Kept the fifteen anomalies we cannot detect in the report rather than quietly "
            "dropping them, each with the data it would need: account balances, know-your-"
            "customer records, the channel a payment came through, login attempts. Thirty-"
            "five of the fifty are now detected, five of them by the graph layer.",
            "Found a fault in one of the earlier anomaly rules by replaying scenarios "
            "through the running system rather than trusting the unit tests: the "
            "pass-through rule fired on any large payment that happened to follow a small "
            "credit, so it reported forwarding seven lakh of the twenty-five thousand "
            "received. It now requires the payment to be between eighty and a hundred and "
            "ten per cent of what arrived.",
            "Began the second suggestion, to measure the system on real data rather than "
            "our own. Chose the "
            "PaySim mobile-money dataset because it is the only public one with both a "
            "sender and a receiver on every row, which is what the relationship rules need; "
            "card datasets have no receiver. Wrote the replay that scores it and reports "
            "each rule's hit rate, and stated in it what does not carry over, so the results "
            "cannot be read as more than they are.",
            "Named the member responsible for each chapter on the chapter's own page, the "
            "third suggestion, and rebuilt both documents with the new rules, their "
            "thresholds and the stores they read described.",
        ],
        "plans": [
            "Run the replay once the dataset is downloaded and report each rule's true and "
            "false alarms on it.",
            "Retire or retune the rules the dataset shows are noise rather than signal.",
            "Fill the payment history from the stored transactions, so an existing account "
            "is not treated as new the first time it pays after a restart.",
            "Re-measure accuracy on our own labelled set, which now predates twenty-five "
            "rules.",
        ],
        "references": [
            "Financial Intelligence Unit – India, “Red flag indicators for "
            "suspicious transaction reports,” FIU-IND, 2023. [Online]. Available: "
            "fiuindia.gov.in",
            "Financial Action Task Force, “Money laundering through the physical "
            "transportation of cash and the use of money mules,” FATF Typologies "
            "Report, 2020.",
            "E. A. Lopez-Rojas, A. Elmir and S. Axelsson, “PaySim: a financial mobile "
            "money simulator for fraud detection,” Proc. 28th European Modeling and "
            "Simulation Symposium, 2016.",
            "Reserve Bank of India, “Master direction – know your customer "
            "(KYC) direction, 2016 (as amended),” RBI, 2026. [Online]. Available: "
            "rbi.org.in",
        ],
    },
    "24DCE040": {
        "work": [
            "Worked through the graph layer's answer to the guide's suggestions. The first "
            "of them, that the detection should follow the anomalies banks actually watch "
            "for, already matches what this layer looks for: a device or an address shared "
            "by several accounts, money returning to its sender within four hops and "
            "seventy-two hours, a chain in which each hop keeps most of what it received, "
            "and a receiver sitting within two links of an account already known to be "
            "fraudulent.",
            "Designed the correction to the cycle check, which is the layer's known "
            "weakness. The query walks outward from the sender and requires the times along "
            "the path to rise, and the transfer that closes a ring is always the newest, so "
            "it can never match; a ring is therefore only caught when its first account "
            "pays again. The fix is to search backwards from the receiver as well, and to "
            "treat the closing transfer as the newest edge of the path rather than the next "
            "one after it.",
            "Set out what that correction will cost to verify: the whole labelled set has "
            "to be scored again, because today's figure of thirty-six rings flagged belongs "
            "to the layer as a whole and only twenty-one of them came from the cycle check "
            "itself. The rest were caught by the receiver's closeness to a known fraud "
            "account, and that distinction has to survive into the next measurement.",
            "Planned how the public dataset will reach this layer. Its rows carry a sender "
            "and a receiver but no device or address, so shared-identity checks cannot be "
            "measured on it; the accounts and transfers can still be loaded so that the "
            "cycle and proximity checks are tested on payments we did not generate.",
        ],
        "plans": [
            "Rewrite the cycle query so it also matches the transfer that closes a ring, "
            "rather than only the one that opens the next lap.",
            "Re-measure ring detection after that change and report the cycle check's own "
            "share, not the layer's total.",
            "Add fan-in and fan-out mule shapes to the generated network and see whether "
            "they are caught.",
            "Load the accounts from the public dataset into the network so the relationship "
            "checks can be measured on data we did not generate.",
        ],
        "references": [
            "R. Tarjan, \u201cDepth-first search and linear graph algorithms,\u201d SIAM "
            "Journal on Computing, vol. 1, no. 2, 1972.",
            "X. Li, S. Liu, Z. Li et al., \u201cFlowScope: spotting money laundering "
            "based on graphs,\u201d Proc. AAAI Conference on Artificial Intelligence, "
            "vol. 34, 2020.",
            "L. Akoglu, H. Tong and D. Koutra, \u201cGraph based anomaly detection and "
            "description: a survey,\u201d Data Mining and Knowledge Discovery, vol. 29, "
            "no. 3, 2015.",
            "Financial Action Task Force, \u201cProfessional money laundering,\u201d FATF "
            "Report, 2018.",
        ],
    },
    "24DCE029": {
        "work": [
            "Rebuilt the analyst screen as a working console, since it had been showing "
            "very little of what the system records. It now opens on the number of "
            "transactions waiting for review and shows decisions per day, the decision mix, "
            "the entities in the transaction graph, risk by merchant category, how often "
            "each signal fires, the score distribution, the share flagged at each amount "
            "band, and the accuracy of the last evaluation.",
            "Added one aggregation endpoint behind it so those figures are computed across "
            "every stored transaction rather than the twenty most recent, which is what the "
            "previous screen had been showing.",
            "Put the review queue first, since it is the one list an analyst works from, and "
            "replaced its clipped explanation column with the signals that fired, each "
            "labelled, and a marker when a scoring layer failed. Selecting a row opens a "
            "panel with the signals grouped by the layer that raised them, the written "
            "explanation, and a drawing of the accounts, devices and addresses one hop "
            "around the sender.",
            "Chose the chart colours by measurement rather than by eye. The usual green and "
            "red fail for the most common form of colour blindness, so approved is shown in "
            "teal; every palette was checked against the light and the dark background "
            "before use, and a light or dark setting is remembered between visits.",
            "Corrected a fault that had made every timestamp five and a half hours early: "
            "the database returns times without a zone, and the browser had been reading "
            "them as local.",
        ],
        "plans": [
            "Show the pending state in the queue as well as on the analysis panel.",
            "Test the explanation check against real model output rather than fixture text.",
            "Add the new banking anomalies to the signal breakdown so the chart groups them "
            "by the rule family they belong to.",
            "Continue the accessibility pass over the rebuilt screen, keyboard order first.",
        ],
        "references": [
            "T. Munzner, “Visualization Analysis and Design,” CRC Press, 2014.",
            "M. Okabe and K. Ito, “Color universal design: how to make figures and "
            "presentations that are friendly to colorblind people,” J*FLY, 2008. "
            "[Online]. Available: jfly.uni-koeln.de",
            "A. Cairo, “The Truthful Art: Data, Charts, and Maps for "
            "Communication,” New Riders, 2016.",
            "ECMA International, “Date-time string format and time zone offsets,” "
            "ECMAScript Language Specification, 2025. [Online]. Available: ecma-"
            "international.org",
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
    """The most recent earlier week's .docx still on disk, or None. A submitted
    week's .docx is often cleaned out of Downloads afterward (only the PDF is
    kept), so WEEK-1 isn't always there — walk back to whichever one is, and
    fall back to rebuilding the layout when every one of them is gone."""
    for week in range(WEEK - 1, 0, -1):
        path = os.path.join(DOWNLOADS, f"{student_id}_Week{week}.docx")
        if os.path.exists(path):
            return path
    return None


# ── Rebuilding the university layout ──────────────────────────────────────────
# Used when no earlier .docx survives. The two header logos were lifted out of a
# submitted Week 10 PDF (pdfimages) and live in docs/weekly-template/, so the
# layout can be rebuilt without one. Copying an earlier .docx is still preferred
# — it carries the exact original styles — so this runs only as a fallback.
TEMPLATE_DIR = os.path.join(HERE, "weekly-template")
TIMES, TITLE_FONT = "Times New Roman", "Calibri"


def _run(paragraph, text, size=11, bold=False, font=TIMES):
    r = paragraph.add_run(text)
    r.font.name, r.font.size, r.bold = font, Pt(size), bold
    r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    return r


def _line(doc, text="", size=11, bold=False, align=None, after=6, font=TIMES, space_before=0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(space_before)
    if align is not None:
        p.alignment = align
    if text:
        _run(p, text, size, bold, font)
    return p


def _boxed(doc, lines):
    """One bordered cell holding the bullet list, as in the original form."""
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    cell = t.cell(0, 0)
    cell.text = ""
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _run(p, f"\u2022  {line}", 11)
    return t


def build_from_scratch(student_id, spec):
    """Rebuild the weekly-report layout: header with both logos, the details
    table, the two bordered lists, references and the signature line."""
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin"):
        setattr(section, side, Inches(1))
    section.top_margin = section.bottom_margin = Inches(0.8)

    head = doc.add_table(rows=1, cols=3)
    head.autofit = False
    # Default cell padding would push the right-hand logo past the margin.
    margins = OxmlElement("w:tblCellMar")
    for side in ("top", "left", "bottom", "right"):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), "0")
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    head._tbl.tblPr.append(margins)
    widths = (0.8, 4.9, 0.8)     # 6.5 in of usable width between 1 in margins
    for column, w in zip(head._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        column.set(qn("w:w"), str(int(w * 1440)))
    for i, w in enumerate(widths):
        head.rows[0].cells[i].width = Inches(w)
    head.cell(0, 0).paragraphs[0].add_run().add_picture(
        os.path.join(TEMPLATE_DIR, "charusat.png"), width=Inches(0.6))
    middle = head.cell(0, 1).paragraphs[0]
    middle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(middle, "CHAROTAR UNIVERSITY OF SCIENCE & TECHNOLOGY", 11.5, True)
    second = head.cell(0, 1).add_paragraph()
    second.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(second, "DEVANG PATEL INSTITUTE OF ADVANCE TECHNOLOGY AND RESEARCH", 8.5, True)
    right = head.cell(0, 2).paragraphs[0]
    right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right.add_run().add_picture(os.path.join(TEMPLATE_DIR, "depstar.png"), width=Inches(0.7))

    _line(doc, "WEEKLY REPORT", 16, True, WD_ALIGN_PARAGRAPH.CENTER, after=10,
          font=TITLE_FONT, space_before=16)

    details = doc.add_table(rows=3, cols=2)
    details.style = "Table Grid"
    rows = [(f"Project  ID: PRJ_CE_5_2026_7", f"Student ID: {student_id}"),
            (f"From Date: {FROM_DATE}", f"To Date: {TO_DATE}"),
            ("Semester: 5 th", "Internship ID:")]
    for r, (left_text, right_text) in enumerate(rows):
        for c, text in ((0, left_text), (1, right_text)):
            cell = details.cell(r, c)
            cell.text = ""
            cell.paragraphs[0].paragraph_format.space_after = Pt(2)
            _run(cell.paragraphs[0], text, 11, True)
    for column, w in zip(details._tbl.tblGrid.findall(qn("w:gridCol")), (3.2, 2.8)):
        column.set(qn("w:w"), str(int(w * 1440)))
    for row in details.rows:
        row.cells[0].width, row.cells[1].width = Inches(3.2), Inches(2.8)

    _line(doc, f"Work done from Date: {FROM_DATE} to {TO_DATE}", 12, True, after=8, space_before=14)
    _boxed(doc, spec["work"])
    _line(doc, f"Plans for next week: Date: {NEXT_FROM} to {NEXT_TO}", 12, True,
          after=8, space_before=14)
    _boxed(doc, spec["plans"])

    _line(doc, "References:", 12, True, after=6, space_before=14)
    for i, reference in enumerate(spec["references"], 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.left_indent = Inches(0.3)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _run(p, f"{i}.  {reference}", 11)

    _line(doc, after=0, space_before=36)
    signature = doc.add_table(rows=1, cols=2)
    for i, text in enumerate(("Signature of Student", "Signature of Mentor")):
        cell = signature.cell(0, i)
        cell.text = ""
        cell.width = Inches(3.0)
        _run(cell.paragraphs[0], text, 12, True)

    out = os.path.join(DOWNLOADS, f"{student_id}_Week{WEEK}.docx")
    doc.save(out)
    return out


def build(student_id, spec):
    source = _template_source(student_id)
    if source is None:
        return build_from_scratch(student_id, spec)
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
