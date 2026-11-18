"""Content QA: captions, dictionary coverage and table shapes."""
import re
from pathlib import Path

from docx import Document

OUT = Path(__file__).resolve().parents[1]
doc = Document(OUT / "SRS_Document.docx")
paras = [p.text for p in doc.paragraphs]

figs = [p for p in paras if re.match(r"^Figure \d+\.\d+:", p)]
tabs = [p for p in paras if re.match(r"^Table \d+\.\d+:", p)]
print("figure captions", len(figs))
print("table captions", len(tabs))
for p in figs:
    print("  ", p[:95])
dupes = {t for t in tabs if tabs.count(t) > 1}
print("duplicate captions", len(dupes))
print("dictionary tables", sum(1 for p in paras if p.startswith("Data dictionary —")))
print("schema headings", sum(1 for p in paras if re.match(r"^7\.4\.\d+ ", p)))
print("API rows", sum(1 for t in doc.tables for r in t.rows if r.cells[0].text.startswith("API-")))
print("FR rows", sum(1 for t in doc.tables for r in t.rows if r.cells[0].text.startswith(("FR-", "NFR-"))))
print("tables", len(doc.tables))
empty = [i for i, t in enumerate(doc.tables) if len(t.rows) < 2]
print("empty tables", empty)
print("largest table rows", max(len(t.rows) for t in doc.tables))
print("word count approx", sum(len(p.split()) for p in paras))
print("sections", len(doc.sections))
sec = doc.sections[0]
print("page inches", round(sec.page_width.inches, 2), round(sec.page_height.inches, 2))
print("margins", [round(getattr(sec, m).inches, 2) for m in ("top_margin", "bottom_margin", "left_margin", "right_margin")])
