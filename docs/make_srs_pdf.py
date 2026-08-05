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

    python docs/make_srs_pdf.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES_JSON = os.path.join(HERE, "toc-pages.json")
DOCX = os.path.expanduser("~/Downloads/Indus11_SRS.docx")
PDF = os.path.expanduser("~/Downloads/Indus11_SRS.pdf")
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
PYTHON = sys.executable

FRONT_MATTER = ["CERTIFICATE", "ACKNOWLEDGEMENT", "ABSTRACT",
                "LIST OF FIGURES", "LIST OF TABLES"]


def build():
    subprocess.run([PYTHON, os.path.join(HERE, "build_srs.py")], check=True)


def convert():
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                    "--outdir", os.path.dirname(PDF), DOCX],
                   check=True, capture_output=True)


def page_of_each_heading():
    """Map each heading to the printed page it first appears on."""
    with open(os.path.join(HERE, "toc-entries.json")) as f:
        headings = json.load(f)
    text = subprocess.run(["pdftotext", "-layout", PDF, "-"],
                          check=True, capture_output=True, text=True).stdout

    found = {}
    for number, page in enumerate(text.split("\f"), start=1):
        # The contents itself names every heading, and is the only place with
        # dot leaders, so skipping leader pages skips exactly those pages.
        if re.search(r"\.{5,}", page):
            continue
        for h in headings:
            if h not in found and h in page:
                found[h] = number
    missing = [h for h in headings if h not in found]
    if missing:
        raise SystemExit(f"could not locate in the PDF: {missing}")
    return found


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
    print(f"Saved {PDF}   ({len(pages)} contents entries numbered)")
