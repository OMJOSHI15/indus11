"""
Produce the printable SRS: ~/Downloads/Indus11_SRS.docx and .pdf.

Word fills a TOC field only when a person opens the document and presses F9, so
a PDF converted straight from the .docx has an empty contents page. This builds
the contents as ordinary text instead, in two passes:

  1. build and convert with the page-number column blank,
  2. read each heading's page out of that PDF, write docs/toc-pages.json,
  3. build and convert again, now with the numbers filled in.

The two passes paginate identically because pass 1 already reserves one line per
entry; only the short page number is added.

    python docs/make_srs_pdf.py            the SRS
    python docs/make_srs_pdf.py report     the project report (docs/build_report.py)
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# target -> (builder script, output file stem, prefix of its bookkeeping JSON files)
TARGETS = {"srs": ("build_srs.py", "Indus11_SRS", ""),
           "report": ("build_report.py", "Indus11_Project_Report", "report-")}
SCRIPT, STEM, PREFIX = TARGETS[sys.argv[1] if len(sys.argv) > 1 else "srs"]
PAGES_JSON = os.path.join(HERE, f"{PREFIX}toc-pages.json")
DOCX = os.path.expanduser(f"~/Downloads/{STEM}.docx")
PDF = os.path.expanduser(f"~/Downloads/{STEM}.pdf")
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
PYTHON = sys.executable

FRONT_MATTER = ["CERTIFICATE", "ACKNOWLEDGEMENT", "ABSTRACT",
                "LIST OF FIGURES", "LIST OF TABLES"]


def build():
    subprocess.run([PYTHON, os.path.join(HERE, SCRIPT)], check=True)


def convert():
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                    "--outdir", os.path.dirname(PDF), DOCX],
                   check=True, capture_output=True)


def page_of_each_heading():
    """Map each heading to the printed page it first appears on."""
    with open(os.path.join(HERE, f"{PREFIX}toc-entries.json")) as f:
        headings = json.load(f)
    text = subprocess.run(["pdftotext", "-layout", PDF, "-"],
                          check=True, capture_output=True, text=True).stdout

    found = {}
    for number, page in enumerate(text.split("\f"), start=1):
        # The contents itself names every heading, and is the only place with
        # dot leaders, so skipping leader pages skips exactly those pages.
        if re.search(r"\.{5,}", page):
            continue
        # A long chapter title wraps onto two centred lines, so compare with
        # runs of whitespace collapsed rather than line by line.
        flat = re.sub(r"\s+", " ", page)
        for h in headings:
            if h not in found and h in flat:
                found[h] = number
    missing = [h for h in headings if h not in found]
    if missing:
        raise SystemExit(f"could not locate in the PDF: {missing}")

    body_start = found["CHAPTER 1: INTRODUCTION"]
    return {h: (roman(n) if n < body_start else str(n - body_start + 1))
            for h, n in found.items()}


ROMAN = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]


def roman(n):
    """Lower-case roman numeral, for the front matter's page labels."""
    out = ""
    for value, digit in ROMAN:
        while n >= value:
            out += digit
            n -= value
    return out


def check_tables_are_not_split():
    """Report any table whose first and last row land on different pages."""
    with open(os.path.join(HERE, f"{PREFIX}table-spans.json")) as f:
        spans = json.load(f)
    text = subprocess.run(["pdftotext", "-layout", PDF, "-"],
                          check=True, capture_output=True, text=True).stdout
    pages = text.split("\f")
    # A cell's text may be wrapped by the extractor, so compare with all
    # whitespace stripped out rather than line by line.
    flat = [re.sub(r"\s+", "", page) for page in pages]
    split = []
    for label, (first, last) in spans.items():
        on = [n for n, page in enumerate(flat, start=1)
              # With its colon, so a prose reference ("see Table 5.6") or a longer
              # label ("Table 5.11") is not mistaken for the caption.
              if re.sub(r"\s+", "", label) + ":" in page]
        if not on:
            continue
        caption_page = on[-1]              # the list of tables comes earlier
        if re.sub(r"\s+", "", last) not in flat[caption_page - 1]:
            split.append(label)
    return split


if __name__ == "__main__":
    if os.path.exists(PAGES_JSON):
        os.remove(PAGES_JSON)
    build()
    convert()
    pages = page_of_each_heading()
    with open(PAGES_JSON, "w") as f:
        json.dump(pages, f, indent=2, sort_keys=True)
    build()
    convert()
    split = check_tables_are_not_split()
    print(f"Saved {PDF}   ({len(pages)} contents entries numbered)")
    print("  tables split across a page break: " + (", ".join(split) if split else "none"))
