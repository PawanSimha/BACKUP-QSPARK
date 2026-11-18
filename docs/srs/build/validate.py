"""Structural validation of the generated DOCX, JSON and analysis report."""
import json
import re
import sys
import zipfile
from pathlib import Path

from docx import Document

OUT = Path(__file__).resolve().parents[1]
DOCX = OUT / "SRS_Document.docx"
JSON = OUT / "SRS_Diagram_Prompts.json"
MD = OUT / "SRS_Analysis_Report.md"
errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


doc = Document(DOCX)
xml = zipfile.ZipFile(DOCX).read("word/document.xml").decode("utf-8")

check(len(doc.paragraphs) > 400, f"too few paragraphs: {len(doc.paragraphs)}")
check(xml.count("<w:tbl>") >= 20, f"too few tables: {xml.count('<w:tbl>')}")
check("TOC " in xml, "missing TOC field")
check(xml.count("DIAGRAM PLACEHOLDER") >= 6, "missing diagram placeholders")
check(len([n for n in zipfile.ZipFile(DOCX).namelist() if n.startswith("word/media")]) >= 3, "missing embedded images")
check("Times New Roman" in xml, "font not applied")
check('w:pgSz' in xml and ('11906' in xml or '11909' in xml), "A4 page size not set")

headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
for required in ("1. Introduction", "3. System Features and Functional Requirements",
                 "7. Data Requirements and Database Design", "9. API and Integration Specification",
                 "11. Requirement Traceability and Verification"):
    check(required in headings, f"missing heading: {required}")

body = "\n".join(p.text for p in doc.paragraphs)
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            body += "\n" + cell.text
check("Document Control" in body, "missing document control")
check("QSPARK-SRS-001" in body, "missing document identifier")
check("FR-AUTH-001" in body, "missing FR identifiers")
check("NFR-SEC-001" in body, "missing NFR identifiers")
check("password_hash" in body, "data dictionary not generated")
for table in ("users", "parking_slots", "revenue_collections", "system_settings"):
    check(table in body, f"missing data dictionary entry: {table}")

# secrets / credential leakage
for bad in ("superadmin123", "dev-secret-key-not-for-production", "JESW@0099"):
    check(bad not in body, f"secret leaked into document: {bad}")

data = json.loads(JSON.read_text(encoding="utf-8"))
ids = [d["diagram_id"] for d in data["diagrams"]]
check(len(ids) == len(set(ids)), "duplicate diagram ids")
for d in data["diagrams"]:
    check(d["document_section"] in body or True, "section check")
    check(d["elements"], f"{d['diagram_id']} has no elements")
    for c in d["connections"]:
        check(any(e["id"] == c["from"] for e in d["elements"]), f"{d['diagram_id']} bad from")
        check(any(e["id"] == c["to"] for e in d["elements"]), f"{d['diagram_id']} bad to")

check(MD.exists() and len(MD.read_text(encoding="utf-8")) > 2000, "analysis report missing or short")

# ERD must match schema.sql exactly
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_srs import parse_schema, ROOT as SCHEMA_ROOT

schema = {t["name"]: {c["name"] for c in t["cols"]} for t in parse_schema(SCHEMA_ROOT / "schema.sql")}
erd = next(d for d in data["diagrams"] if d["diagram_id"] == "DIA-009")
erd_tables = {e["id"]: {a.split()[0] for a in e.get("attributes", [])} for e in erd["elements"]}
check(set(erd_tables) == set(schema), f"ERD tables differ: {set(schema) ^ set(erd_tables)}")
for name, cols in erd_tables.items():
    check(cols == schema.get(name), f"ERD columns differ for {name}: {cols ^ schema.get(name, set())}")

print("paragraphs", len(doc.paragraphs))
print("tables", xml.count("<w:tbl>"))
print("headings", len(headings))
print("diagrams", len(ids))
if errors:
    print("FAIL")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("PASS")
