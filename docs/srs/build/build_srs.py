"""Build SRS_Document.docx from srs_content.md and the project's schema.sql.

Usage: python build/build_srs.py
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[3]
BUILD = Path(__file__).resolve().parent
OUT = BUILD.parent
DOCS = ROOT / "docs"
DIAGRAMS = DOCS / "diagrams"
FONT = "Times New Roman"

PROJECT = "QSPARK"
DOC_TITLE = "Software Requirements Specification"
VERSION = "1.0"
STATUS = "Draft"


# --------------------------------------------------------------------------- schema
DESCRIPTIONS = {
    "user_id": "Internal surrogate key for every account",
    "admin_id": "Public admin identifier; required for ADMIN and SUPER_ADMIN",
    "full_name": "Person's display name",
    "email": "Login/contact email; unique when present",
    "phone": "Contact mobile number",
    "gender": "Self-declared gender category",
    "company_name": "Company or workplace supplied at registration",
    "username": "Login identifier; unique when present",
    "password_hash": "Werkzeug PBKDF2-SHA256 password hash; never returned by APIs",
    "role": "CUSTOMER, ADMIN or SUPER_ADMIN",
    "wallet_balance": "Current internal wallet balance in INR",
    "account_status": "PENDING, ACTIVE, BLOCKED or DELETED (logical deletion)",
    "created_by": "Actor user_id that created the row",
    "created_at": "Row creation timestamp (UTC, SQLite datetime)",
    "updated_by": "Actor user_id of the last update",
    "updated_at": "Last update timestamp",
    "reserved1": "Reserved extension column",
    "reserved2": "Reserved extension column",
    "floor_id": "Surrogate key for a parking floor",
    "floor_code": "Short floor label such as B1; unique",
    "floor_status": "OPEN, CLOSED, MAINTENANCE or INACTIVE",
    "vehicle_type_id": "Surrogate key for a vehicle category",
    "type_name": "Vehicle category label (2-Wheeler, 4-Wheeler)",
    "hourly_rate": "Booking charge per hour in INR",
    "overstay_rate": "Overtime charge per started 30-minute unit in INR",
    "is_active": "1 = selectable, 0 = retired",
    "slot_id": "Surrogate key for a parking space",
    "slot_number": "Slot label unique within its floor",
    "control_status": "ACTIVE, ADMIN_RESERVED, MAINTENANCE or INACTIVE",
    "booking_id": "Surrogate key for a booking",
    "booking_reference": "Unique human/QR reference, e.g. QSP-20261118-101500-A1B2C3D4",
    "vehicle_format": "std1, std2, std3 or bhr plate pattern",
    "vehicle_number": "Normalised uppercase registration number",
    "booked_from": "Reservation start datetime",
    "booked_until": "Reservation end datetime",
    "hold_expires_at": "Deadline for confirming a HELD booking",
    "hourly_rate_applied": "Hourly rate captured when the booking was created",
    "overstay_rate_applied": "Overstay rate captured when the booking was created",
    "estimated_amount": "Charge computed at hold time",
    "booking_status": "HELD, CONFIRMED, COMPLETED, CANCELLED or EXPIRED",
    "applied_cancellation_rule_id": "Rule used to compute the refund",
    "rule_id": "Surrogate key for a cancellation rule",
    "rule_code": "Unique short rule code",
    "rule_name": "Human-readable rule name",
    "min_hours_before": "Lower bound of the notice window in hours",
    "max_hours_before": "Exclusive upper bound of the notice window in hours",
    "is_no_show": "1 = no-show rule, excluded from notice matching",
    "refund_percent": "Percentage of the paid amount refunded",
    "penalty_percent": "Percentage of the paid amount withheld",
    "description": "Free-text explanation or ledger note",
    "transaction_id": "Surrogate key for a ledger entry",
    "transaction_reference": "Unique ledger reference used for reconciliation",
    "transaction_type": "BOOKING_DEBIT, OVERTIME_DEBIT, CANCELLATION_REFUND, ADMIN_ADJUSTMENT, SUPER_ADMIN_REVENUE_CREDIT or REVENUE_REFUND_REVERSAL",
    "direction": "DEBIT or CREDIT",
    "amount": "Monetary amount in INR, always positive",
    "balance_after": "Wallet balance after applying the entry",
    "event_id": "Surrogate key for a gate event",
    "event_type": "ENTRY or EXIT",
    "scan_method": "QR or MANUAL",
    "event_note": "Operator/system note attached to the event",
    "audit_log_id": "Surrogate key for an audit record",
    "action_type": "Action code such as BOOKING_CANCELLED or SYSTEM_OFFLINE",
    "entity_type": "Affected table or logical entity",
    "entity_id": "Primary key of the affected row",
    "old_values": "JSON/text snapshot before the change",
    "new_values": "JSON/text snapshot after the change",
    "collection_id": "Surrogate key for a revenue collection",
    "source_user_id": "Customer whose wallet funded the collection",
    "super_admin_user_id": "Super Admin wallet that received the collection",
    "customer_wallet_transaction_id": "Customer ledger leg of the collection",
    "super_admin_wallet_transaction_id": "Super Admin ledger leg of the collection",
    "collection_type": "BOOKING_CHARGE, OVERTIME_CHARGE or REFUND_REVERSAL",
    "setting_id": "Surrogate key for a setting",
    "setting_key": "Unique setting name",
    "setting_value": "Setting value stored as text",
}


def parse_schema(path):
    text = path.read_text(encoding="utf-8")
    tables = []
    for m in re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\n\);", text, re.S):
        name, body = m.group(1), m.group(2)
        cols, fks, checks = [], [], []
        for raw in body.splitlines():
            line = raw.strip().rstrip(",")
            if not line:
                continue
            if line.upper().startswith("FOREIGN KEY"):
                fks.append(line)
                continue
            if line.upper().startswith(("CHECK", "UNIQUE", "PRIMARY KEY", "CONSTRAINT")):
                checks.append(line)
                continue
            parts = line.split(None, 1)
            if len(parts) < 2 or parts[0].upper() in ("FOREIGN", "CHECK", "UNIQUE"):
                continue
            col = parts[0].strip('"')
            rest = parts[1]
            base = rest.split()[0].upper()
            key = ""
            if "PRIMARY KEY" in rest.upper():
                key = "PK"
            elif "REFERENCES" in rest.upper():
                key = "FK"
            elif "UNIQUE" in rest.upper():
                key = "UQ"
            nullable = "NO" if "NOT NULL" in rest.upper() or key == "PK" else "YES"
            dm = re.search(r"DEFAULT\s+(\((?:[^()]|\([^()]*\))*\)|'[^']*'|\S+)", rest, re.I)
            default = dm.group(1).strip() if dm else ""
            if default.startswith("(") and default.endswith(")"):
                default = default[1:-1].strip()
            cons = []
            cm = re.search(r"CHECK\s*\((.*)\)", rest, re.S)
            if cm:
                cons.append("CHECK " + cm.group(1).strip())
            cols.append({
                "name": col, "type": base, "key": key, "nullable": nullable,
                "default": default, "constraints": "; ".join(cons),
            })
        tables.append({"name": name, "cols": cols, "fks": fks, "checks": checks})
    return tables


# --------------------------------------------------------------------------- helpers
def set_cell_bg(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def set_cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def add_field(paragraph, instr, placeholder=""):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(it)
    run._r.append(sep)
    run._r.append(txt)
    run._r.append(end)


def add_runs(paragraph, text, size=None, italic=False):
    """Very small **bold** inline parser; backticks become plain text."""
    text = text.replace("`", "")
    for part in re.split(r"(\*\*[^*]+\*\*)", text):
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        run = paragraph.add_run(part[2:-2] if bold else part)
        run.bold = bold
        run.font.name = FONT
        if size:
            run.font.size = Pt(size)
        if italic:
            run.italic = True


def add_bottom_border(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "808080")
    pBdr.append(bottom)
    pPr.append(pBdr)


# --------------------------------------------------------------------------- document
def constrain_table(table):
    tblPr = table._tbl.tblPr
    width = OxmlElement("w:tblW")
    width.set(qn("w:type"), "pct")
    width.set(qn("w:w"), "5000")
    tblPr.append(width)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "autofit")
    tblPr.append(layout)


def add_front_table(doc, rows, first_col_bold=False):
    table = doc.add_table(rows=0, cols=len(rows[0]))
    table.style = "Table Grid"
    constrain_table(table)
    for ri, cells in enumerate(rows):
        row = table.add_row()
        set_cant_split(row)
        for ci, text in enumerate(cells):
            cell = row.cells[ci]
            cell.text = ""
            par = cell.paragraphs[0]
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_after = Pt(2)
            rr = par.add_run(text)
            rr.font.name, rr.font.size = FONT, Pt(10)
            rr.bold = ri == 0 or (first_col_bold and ci == 0)
            if ri == 0:
                set_cell_bg(cell, "DCE6F1")
        if ri == 0:
            set_repeat_header(row)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_document_control(doc):
    doc.add_heading("Document Control", level=1)
    doc.add_heading("Document Information", level=2)
    add_front_table(doc, [
        ["Field", "Value"],
        ["Document title", f"{PROJECT} {DOC_TITLE}"],
        ["Document identifier", "QSPARK-SRS-001"],
        ["Version", VERSION],
        ["Status", STATUS],
        ["Issue date", "18 November 2026"],
        ["Author", "TBD"],
        ["Organisation", "TBD"],
        ["Classification", "Internal — Project Documentation"],
        ["Prepared by", "Reverse engineering of the existing implementation"],
    ], first_col_bold=True)

    doc.add_heading("Revision History", level=2)
    add_front_table(doc, [
        ["Version", "Date", "Author", "Description of change"],
        ["0.1", "18 Nov 2026", "TBD", "Initial analysis and outline"],
        ["1.0", "18 Nov 2026", "TBD", "Complete SRS, data dictionary, API inventory and traceability"],
    ])

    doc.add_heading("Approval", level=2)
    add_front_table(doc, [
        ["Role", "Name", "Signature", "Date"],
        ["Project sponsor", "", "", ""],
        ["Technical lead", "", "", ""],
        ["Quality assurance", "", "", ""],
    ])

    doc.add_heading("Distribution", level=2)
    add_front_table(doc, [
        ["Recipient", "Purpose"],
        ["Project stakeholders", "Scope review and sign-off"],
        ["Development team", "Implementation reference"],
        ["QA team", "Test design and verification"],
        ["Operations", "Deployment and support"],
    ])


def build():
    tables = parse_schema(ROOT / "schema.sql")
    doc = Document()

    core = doc.core_properties
    core.title = f"{PROJECT} {DOC_TITLE}"
    core.subject = "Reverse-engineered requirements specification for the QSPARK smart parking system"
    core.author = "TBD"
    core.category = "Software Requirements Specification"
    core.comments = f"Version {VERSION} ({STATUS})"

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(12)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    for name, size in (("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 12), ("Heading 4", 12)):
        st = styles[name]
        st.font.name = FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        st.paragraph_format.space_before = Pt(12)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.line_spacing = 1.15

    for name in ("List Bullet", "List Number"):
        st = styles[name]
        st.font.name = FONT
        st.font.size = Pt(12)

    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, attr, Inches(1))

    # header / footer
    hp = section.header.paragraphs[0]
    hp.paragraph_format.tab_stops.add_tab_stop(Inches(6.27), WD_TAB_ALIGNMENT.RIGHT)
    r = hp.add_run(f"{PROJECT}")
    r.font.name, r.font.size = FONT, Pt(9)
    hp.add_run("\t")
    r = hp.add_run(DOC_TITLE)
    r.font.name, r.font.size = FONT, Pt(9)
    add_bottom_border(hp)

    fp = section.footer.paragraphs[0]
    fp.paragraph_format.tab_stops.add_tab_stop(Inches(6.27), WD_TAB_ALIGNMENT.RIGHT)
    r = fp.add_run(f"Version {VERSION} — {STATUS}")
    r.font.name, r.font.size = FONT, Pt(9)
    fp.add_run("\t")
    r = fp.add_run("Page ")
    r.font.name, r.font.size = FONT, Pt(9)
    add_field(fp, "PAGE", "1")
    r = fp.add_run(" of ")
    r.font.name, r.font.size = FONT, Pt(9)
    add_field(fp, "NUMPAGES", "1")

    # ---- title page
    for _ in range(5):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(PROJECT)
    run.font.name, run.font.size, run.bold = FONT, Pt(36), True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Smart Parking Slot Booking and Management System")
    run.font.name, run.font.size = FONT, Pt(16)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(DOC_TITLE)
    run.font.name, run.font.size, run.bold = FONT, Pt(24), True

    doc.add_paragraph()
    meta = [
        ("Document version", VERSION),
        ("Document status", STATUS),
        ("Prepared date", "18 November 2026"),
        ("Organisation", "TBD"),
        ("Author / team", "TBD"),
        ("Classification", "Internal — Project Documentation"),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in meta:
        row = t.add_row().cells
        for cell, text, bold in ((row[0], k, True), (row[1], v, False)):
            cell.text = ""
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_after = Pt(2)
            rr = par.add_run(text)
            rr.font.name, rr.font.size, rr.bold = FONT, Pt(11), bold
        set_cell_bg(row[0], "EDF2F7")
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Prepared by reverse-engineering the existing implementation. No application code was modified.")
    run.font.name, run.font.size, run.italic = FONT, Pt(10), True
    doc.add_page_break()

    # ---- document control
    add_document_control(doc)
    doc.add_page_break()

    # ---- TOC placeholder
    h = doc.add_heading("Table of Contents", level=1)
    p = doc.add_paragraph()
    add_field(p, 'TOC \\o "1-3" \\h \\z \\u', "Right-click and select Update Field to build the table of contents.")
    doc.add_page_break()

    # ---- body
    content = (BUILD / "srs_content.md").read_text(encoding="utf-8")
    lines = content.splitlines()
    i = 0
    chapter = 0
    fig_no, tab_no = {}, {}
    current_chapter = 1

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if stripped == "[[PAGEBREAK]]":
            doc.add_page_break()
            i += 1
            continue

        if stripped.startswith("[[TABLE:"):
            m = re.match(r"\[\[TABLE:(.+)\]\]", stripped)
            PENDING_CAPTION["text"] = m.group(1).strip()
            i += 1
            continue

        if stripped.startswith("[[FIGURE:"):
            m = re.match(r"\[\[FIGURE:([^|]+)\|(.+)\]\]", stripped)
            fname, caption = m.group(1), m.group(2)
            path = DIAGRAMS / fname
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                p.add_run().add_picture(str(path), width=Inches(6.0))
            except Exception as exc:
                rr = p.add_run(f"[Image unavailable: {fname} ({exc})]")
                rr.font.name, rr.font.size = FONT, Pt(10)
            fig_no[current_chapter] = fig_no.get(current_chapter, 0) + 1
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.space_after = Pt(10)
            add_runs(cap, f"Figure {current_chapter}.{fig_no[current_chapter]}: {caption}", size=10, italic=True)
            i += 1
            continue

        if stripped.startswith("[[DIAGRAM:"):
            m = re.match(r"\[\[DIAGRAM:([^|]+)\|(.+)\]\]", stripped)
            did, caption = m.group(1), m.group(2)
            box = doc.add_table(rows=1, cols=1)
            box.style = "Table Grid"
            cell = box.rows[0].cells[0]
            cell.text = ""
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            rr = par.add_run(f"[DIAGRAM PLACEHOLDER — {did}]\n{caption}\nSpecification: SRS_Diagram_Prompts.json")
            rr.font.name, rr.font.size = FONT, Pt(10)
            fig_no[current_chapter] = fig_no.get(current_chapter, 0) + 1
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.space_after = Pt(10)
            add_runs(cap, f"Figure {current_chapter}.{fig_no[current_chapter]}: {caption}", size=10, italic=True)
            i += 1
            continue

        if stripped == "[[TABLE_INVENTORY]]":
            add_table_inventory(doc, tables, current_chapter, tab_no)
            i += 1
            continue

        if stripped == "[[SCHEMA_DICTIONARY]]":
            add_data_dictionary(doc, tables, tab_no)
            i += 1
            continue

        if stripped.startswith("[[CODE]]"):
            i += 1
            while i < len(lines) and lines[i].strip() != "[[/CODE]]":
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.3)
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(0)
                rr = p.add_run(lines[i])
                rr.font.name, rr.font.size = FONT, Pt(9)
                i += 1
            i += 1
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            doc.add_heading(text, level=min(level, 4))
            m = re.match(r"^(\d+)\.", text)
            if level == 1 and m:
                current_chapter = int(m.group(1))
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            add_md_table(doc, block, current_chapter, tab_no)
            continue

        if stripped.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.line_spacing = 1.25
            p.paragraph_format.space_after = Pt(2)
            add_runs(p, stripped[2:])
            i += 1
            continue

        if re.match(r"^\d+\. ", stripped):
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.line_spacing = 1.25
            p.paragraph_format.space_after = Pt(2)
            add_runs(p, re.sub(r"^\d+\. ", "", stripped))
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        p = doc.add_paragraph()
        add_runs(p, stripped)
        i += 1

    # ask Word to refresh fields on open
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)

    out = OUT / "SRS_Document.docx"
    doc.save(out)
    print(f"WROTE {out}")
    return out


PENDING_CAPTION = {"text": None}


def add_md_table(doc, block, chapter, counters):
    rows = []
    for line in block:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") and c for c in cells):
            continue
        rows.append(cells)
    if not rows:
        return
    width = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=width)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    constrain_table(table)
    for ri, cells in enumerate(rows):
        cells += [""] * (width - len(cells))
        row = table.add_row()
        set_cant_split(row)
        for ci, text in enumerate(cells):
            cell = row.cells[ci]
            cell.text = ""
            par = cell.paragraphs[0]
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_after = Pt(1)
            rr = par.add_run(text.replace("**", "").replace("`", ""))
            rr.font.name, rr.font.size = FONT, Pt(10)
            rr.bold = ri == 0
            if ri == 0:
                set_cell_bg(cell, "DCE6F1")
        if ri == 0:
            set_repeat_header(row)
    counters[chapter] = counters.get(chapter, 0) + 1
    caption = PENDING_CAPTION["text"]
    PENDING_CAPTION["text"] = None
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(8)
        add_runs(cap, f"Table {chapter}.{counters[chapter]}: {caption}", size=9, italic=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_table_inventory(doc, tables, chapter, counters):
    rows = [["Table Name", "Purpose", "Primary Key", "Important Relationships"]]
    purposes = {
        "users": "All account records for customers, admins and super admins",
        "floors": "Configurable parking floors",
        "vehicle_types": "Vehicle categories and their current rates",
        "parking_slots": "Individual spaces, floor/type assignment and control state",
        "bookings": "Reservations, vehicle data, applied rates and lifecycle state",
        "cancellation_rules": "Refund and penalty rules",
        "wallet_transactions": "Append-only wallet ledger",
        "booking_events": "Gate entry and exit events",
        "audit_logs": "Administrative and security-sensitive change history",
        "revenue_collections": "Customer charge paired with the Super Admin collection legs",
        "system_settings": "Key/value operational settings",
    }
    rels = {
        "users": "Self-references created_by/updated_by",
        "floors": "Referenced by parking_slots; created/updated by users",
        "vehicle_types": "Referenced by parking_slots",
        "parking_slots": "N:1 floors and vehicle_types",
        "bookings": "N:1 users, parking_slots, cancellation_rules",
        "cancellation_rules": "Referenced by bookings.applied_cancellation_rule_id",
        "wallet_transactions": "N:1 users, bookings",
        "booking_events": "N:1 bookings, users",
        "audit_logs": "N:1 users (actor)",
        "revenue_collections": "N:1 users (source, super admin), bookings, wallet_transactions (two legs)",
        "system_settings": "N:1 users (actor)",
    }
    for t in tables:
        pk = ", ".join(c["name"] for c in t["cols"] if c["key"] == "PK") or "—"
        rows.append([t["name"], purposes.get(t["name"], "—"), pk, rels.get(t["name"], "—")])
    add_md_table(doc, ["| " + " | ".join(r) + " |" for r in rows], chapter, counters)


def add_data_dictionary(doc, tables, counters):
    for n, t in enumerate(tables, start=1):
        doc.add_heading(f"7.4.{n} {t['name']}", level=4)
        rows = [["Column", "Data Type", "Key", "Nullable", "Default", "Description / Constraints"]]
        for c in t["cols"]:
            desc = DESCRIPTIONS.get(c["name"], "—")
            if c["constraints"]:
                desc += " " + c["constraints"]
            rows.append([c["name"], c["type"], c["key"], c["nullable"], c["default"] or "—", desc])
        lines = ["| " + " | ".join(r) + " |" for r in rows]
        PENDING_CAPTION["text"] = f"Data dictionary — {t['name']}"
        add_md_table(doc, lines, 7, counters)
        if t["fks"]:
            p = doc.add_paragraph()
            add_runs(p, "Foreign keys: " + "; ".join(t["fks"]), size=10)


if __name__ == "__main__":
    build()
