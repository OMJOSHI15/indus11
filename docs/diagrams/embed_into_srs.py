"""
Replace the ASCII-art diagram blocks in the SRS with the PlantUML renderings.

The SRS was first written with monospace box diagrams, which read as amateurish
in a submitted report. This walks the document, finds each diagram table by the
caption that follows it, and swaps the table for the corresponding PNG.

JSON records and shell commands are deliberately left as monospace blocks — a
fixed-width font is the correct presentation for those.

Render the diagrams first, then patch:

    plantuml -tpng docs/diagrams/*.puml
    python docs/diagrams/embed_into_srs.py
"""
import os
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph
from PIL import Image

SRS = os.path.expanduser("~/Downloads/Indus11_SRS.docx")
HERE = os.path.dirname(os.path.abspath(__file__))

# Caption title -> rendered diagram
DIAGRAMS = {
    "System architecture — five-layer pipeline": "01-architecture.png",
    "Use case diagram": "02-usecase.png",
    "Activity diagram — transaction analysis": "03-activity.png",
    "Sequence diagram — POST /transactions/analyze": "04-sequence.png",
    "Class diagram — schemas, models and services": "05-class.png",
    "State diagram — lifecycle of a transaction": "06-state.png",
    "Component diagram": "07-component.png",
    "Deployment diagram (Docker Compose topology)": "08-deployment.png",
    "Entity relationship diagram": "09-er.png",
    "Data Flow Diagram — Level 0 (context)": "10-dfd0.png",
    "Data Flow Diagram — Level 1": "11-dfd1.png",
    "Data Flow Diagram — Level 2 (process 3.0, Rule Engine)": "12-dfd2.png",
}

USABLE_W = 6.0   # 8.5in page - 1.5in left - 1.0in right margin
MAX_H = 7.2      # 11in page - 1.5in top - 1.5in bottom, less caption space


def fitted_width(png_path):
    """Scale to the text column, then bound by page height for tall diagrams."""
    with Image.open(png_path) as im:
        w_px, h_px = im.size
    width = USABLE_W
    height = width * h_px / w_px
    if height > MAX_H:
        height = MAX_H
        width = height * w_px / h_px
    return width


def main() -> int:
    if not os.path.exists(SRS):
        print(f"SRS not found at {SRS}")
        return 1

    doc = Document(SRS)
    body = doc.element.body
    children = list(body)
    replaced, missing = [], []

    for i, el in enumerate(children):
        if not el.tag.endswith("}tbl"):
            continue
        # The caption paragraph immediately follows the diagram table.
        caption = children[i + 1] if i + 1 < len(children) else None
        if caption is None or not caption.tag.endswith("}p"):
            continue
        # Paragraph.text, not itertext() — the latter repeats each run's text.
        text = Paragraph(caption, doc).text.strip()
        match = re.match(r"Figure \d+:\s*(.+)", text)
        if not match:
            continue
        title = match.group(1).strip()
        png = DIAGRAMS.get(title)
        if not png:
            continue
        path = os.path.join(HERE, png)
        if not os.path.exists(path):
            missing.append(png)
            continue

        # Build the picture paragraph at the end, then move it into place.
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(3)
        p.add_run().add_picture(path, width=Inches(fitted_width(path)))
        el.addprevious(p._p)
        el.getparent().remove(el)
        replaced.append(title)

    doc.save(SRS)
    print(f"Embedded {len(replaced)} rendered diagrams into {SRS}")
    for t in replaced:
        print(f"  - {t}")
    if missing:
        print(f"Missing renders (run plantuml first): {', '.join(missing)}")
    not_found = set(DIAGRAMS) - set(replaced)
    if not_found:
        print("Captions not matched in the document:")
        for t in sorted(not_found):
            print(f"  ! {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
