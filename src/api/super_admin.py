"""Super Admin endpoints: admin management, floors, slots, analytics, system control."""

import csv
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, make_response
from src.services.db import get_connection, transaction
from src.core.security import require_role, get_current_user, generate_user_password
from src.api.reports import occupancy_csv as _occ_csv, revenue_csv as _rev_csv

super_admin_bp = Blueprint("super_admin", __name__, url_prefix="/api/super-admin")
# Alias: /api/super-admin/reports/occupancy.csv and /revenue.csv
super_admin_bp.add_url_rule("/reports/occupancy.csv", "sa_occupancy_csv", _occ_csv, methods=["GET"])
super_admin_bp.add_url_rule("/reports/revenue.csv", "sa_revenue_csv", _rev_csv, methods=["GET"])


def _audit(conn, action_type, entity_type, entity_id, old_values, new_values, actor_id):
    conn.execute(
        """INSERT INTO audit_logs
           (action_type, entity_type, entity_id, old_values, new_values, created_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (action_type, entity_type, entity_id, old_values, new_values, actor_id),
    )


# ---------------------------------------------------------------------------
# Admin management
# ---------------------------------------------------------------------------
@super_admin_bp.post("/admins")
@require_role("SUPER_ADMIN")
def create_admin():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip() or None
    gender = data.get("gender")
    company_name = data.get("company_name")
    username = (data.get("username") or "").strip()
    password = generate_user_password(full_name, phone)

    if not all([full_name, phone, username, password]):
        return jsonify({"error": "full_name, phone, username, password required", "code": 400}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters", "code": 400}), 400
    if gender and gender not in ("MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"):
        return jsonify({"error": "Invalid gender", "code": 400}), 400

    from werkzeug.security import generate_password_hash
    actor = get_current_user()

    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            if conn.execute("SELECT 1 FROM users WHERE username = ? OR (email IS NOT NULL AND email = ?)",
                            (username, email)).fetchone():
                return jsonify({"error": "Username or email already exists", "code": 409}), 409
            n = conn.execute("SELECT COUNT(*) FROM users WHERE role IN ('ADMIN','SUPER_ADMIN')").fetchone()[0]
            admin_id = f"ADM{n+1:03d}"
            conn.execute(
                """INSERT INTO users
                   (admin_id, full_name, email, phone, gender, company_name, username,
                    password_hash, role, wallet_balance, account_status, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ADMIN', 1000, 'ACTIVE', ?)""",
                (admin_id, full_name, email, phone, gender, company_name, username,
                 generate_password_hash(password), actor["user_id"]),
            )
            new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            _audit(conn, "CREATE_ADMIN", "users", new_id, None,
                   f"admin_id={admin_id}, username={username}", actor["user_id"])
        return jsonify({"message": "Admin created", "user_id": new_id, "admin_id": admin_id}), 201
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@super_admin_bp.get("/admins")
@require_role("SUPER_ADMIN")
def list_admins():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            """SELECT user_id, admin_id, full_name, phone, email, gender, company_name,
                      username, account_status, wallet_balance, created_at
               FROM users WHERE role IN ('ADMIN','SUPER_ADMIN') ORDER BY role, admin_id"""
        ).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    finally:
        conn.close()


@super_admin_bp.get("/admins/<int:user_id>")
@require_role("SUPER_ADMIN")
def get_admin(user_id):
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            """SELECT user_id, admin_id, full_name, phone, email, gender, company_name,
                      username, account_status, wallet_balance, created_at
               FROM users WHERE user_id = ? AND role IN ('ADMIN','SUPER_ADMIN')""",
            (user_id,),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Admin not found", "code": 404}), 404
        return jsonify(dict(row))
    finally:
        conn.close()


@super_admin_bp.put("/admins/<int:user_id>")
@require_role("SUPER_ADMIN")
def update_admin(user_id):
    data = request.get_json(silent=True) or {}
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute(
                "SELECT * FROM users WHERE user_id = ? AND role = 'ADMIN'", (user_id,)
            ).fetchone()
            if old is None:
                return jsonify({"error": "Admin not found or not editable", "code": 404}), 404
            fields, params = [], []
            for col in ("full_name", "phone", "email", "gender", "company_name", "username"):
                if col in data:
                    fields.append(f"{col} = ?")
                    params.append(data[col])
            if not fields:
                return jsonify({"error": "No updatable fields", "code": 400}), 400
            params.extend([actor["user_id"], user_id])
            conn.execute(
                f"UPDATE users SET {', '.join(fields)}, updated_by = ?, updated_at = datetime('now') WHERE user_id = ?",
                params,
            )
            _audit(conn, "UPDATE_ADMIN", "users", user_id, str(dict(old)), str(data), actor["user_id"])
        return jsonify({"message": "Admin updated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@super_admin_bp.delete("/admins/<int:user_id>")
@require_role("SUPER_ADMIN")
def delete_admin(user_id):
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute(
                "SELECT user_id FROM users WHERE user_id = ? AND role = 'ADMIN'", (user_id,)
            ).fetchone()
            if old is None:
                return jsonify({"error": "Admin not found", "code": 404}), 404
            conn.execute(
                "UPDATE users SET account_status = 'DELETED', updated_by = ?, updated_at = datetime('now') WHERE user_id = ?",
                (actor["user_id"], user_id),
            )
            _audit(conn, "DELETE_ADMIN", "users", user_id, None, "soft-deleted", actor["user_id"])
        return jsonify({"message": "Admin deactivated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@super_admin_bp.patch("/admins/<int:user_id>/status")
@require_role("SUPER_ADMIN")
def set_admin_status(user_id):
    data = request.get_json(silent=True) or {}
    status = data.get("account_status")
    if status not in ("ACTIVE", "BLOCKED"):
        return jsonify({"error": "account_status must be ACTIVE or BLOCKED", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute(
                "SELECT account_status FROM users WHERE user_id = ? AND role = 'ADMIN'", (user_id,)
            ).fetchone()
            if old is None:
                return jsonify({"error": "Admin not found", "code": 404}), 404
            conn.execute(
                "UPDATE users SET account_status = ?, updated_by = ?, updated_at = datetime('now') WHERE user_id = ?",
                (status, actor["user_id"], user_id),
            )
            action = "BLOCK_ADMIN" if status == "BLOCKED" else "UNBLOCK_ADMIN"
            _audit(conn, action, "users", user_id, old["account_status"], status, actor["user_id"])
        return jsonify({"message": f"Admin {status.lower()}"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


# ---------------------------------------------------------------------------
# Wallet management (any user)
# ---------------------------------------------------------------------------
@super_admin_bp.post("/users/<int:user_id>/wallet-adjustments")
@require_role("SUPER_ADMIN")
def wallet_adjustment(user_id):
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")
    description = data.get("description", "Super Admin adjustment")
    try:
        amount = round(float(amount), 2)
    except (TypeError, ValueError):
        return jsonify({"error": "amount required", "code": 400}), 400
    if amount == 0:
        return jsonify({"error": "amount must be non-zero", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            user = conn.execute("SELECT wallet_balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if user is None:
                return jsonify({"error": "User not found", "code": 404}), 404
            before = float(user["wallet_balance"])
            after = round(before + amount, 2)
            if after < 0:
                return jsonify({"error": "Wallet balance cannot be negative", "code": 400}), 400
            conn.execute("UPDATE users SET wallet_balance = ?, updated_by = ? WHERE user_id = ?",
                         (after, actor["user_id"], user_id))
            ref = "TXN-ADJ-" + datetime.now().strftime("%Y%m%d%H%M%S%f") + f"-{user_id}"
            conn.execute(
                """INSERT INTO wallet_transactions
                   (transaction_reference, user_id, transaction_type, direction, amount, balance_after, description, created_by)
                   VALUES (?, ?, 'ADMIN_ADJUSTMENT', ?, ?, ?, ?, ?)""",
                (ref, user_id, "CREDIT" if amount > 0 else "DEBIT", abs(amount), after, description, actor["user_id"]),
            )
            _audit(conn, "WALLET_ADJUSTMENT", "users", user_id, str(before), str(after), actor["user_id"])
        return jsonify({"user_id": user_id, "previous_balance": before, "new_balance": after, "adjustment": amount})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@super_admin_bp.get("/users/<int:user_id>/wallet")
@require_role("SUPER_ADMIN")
def get_wallet(user_id):
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        user = conn.execute("SELECT user_id, wallet_balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if user is None:
            return jsonify({"error": "User not found", "code": 404}), 404
        rows = conn.execute(
            """SELECT transaction_id, transaction_reference, transaction_type, direction,
                      amount, balance_after, description, created_at
               FROM wallet_transactions WHERE user_id = ? ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
        return jsonify({"user_id": user_id, "wallet_balance": float(user["wallet_balance"]),
                        "transactions": [dict(r) for r in rows]})
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Floor management
# ---------------------------------------------------------------------------
@super_admin_bp.post("/floors")
@require_role("SUPER_ADMIN")
def create_floor():
    data = request.get_json(silent=True) or {}
    code = (data.get("floor_code") or "").strip().upper()
    if not code:
        return jsonify({"error": "floor_code required", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            if conn.execute("SELECT 1 FROM floors WHERE floor_code = ?", (code,)).fetchone():
                return jsonify({"error": "Floor code exists", "code": 409}), 409
            conn.execute("INSERT INTO floors (floor_code, floor_status, created_by) VALUES (?, 'OPEN', ?)",
                         (code, actor["user_id"]))
            fid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            _audit(conn, "FLOOR_CREATED", "floors", fid, None, code, actor["user_id"])
        return jsonify({"floor_id": fid, "floor_code": code}), 201
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@super_admin_bp.put("/floors/<int:floor_id>")
@require_role("SUPER_ADMIN")
def update_floor(floor_id):
    data = request.get_json(silent=True) or {}
    status = data.get("floor_status")
    if status not in ("OPEN", "CLOSED", "MAINTENANCE", "INACTIVE"):
        return jsonify({"error": "Invalid floor_status", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT floor_status FROM floors WHERE floor_id = ?", (floor_id,)).fetchone()
            if old is None:
                return jsonify({"error": "Floor not found", "code": 404}), 404
            conn.execute("UPDATE floors SET floor_status = ?, updated_by = ?, updated_at = datetime('now') WHERE floor_id = ?",
                         (status, actor["user_id"], floor_id))
            _audit(conn, "FLOOR_UPDATED", "floors", floor_id, old["floor_status"], status, actor["user_id"])
        return jsonify({"message": "Floor updated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@super_admin_bp.delete("/floors/<int:floor_id>")
@require_role("SUPER_ADMIN")
def delete_floor(floor_id):
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT floor_status FROM floors WHERE floor_id = ?", (floor_id,)).fetchone()
            if old is None:
                return jsonify({"error": "Floor not found", "code": 404}), 404
            active = conn.execute(
                """SELECT COUNT(*) FROM bookings b JOIN parking_slots s ON s.slot_id = b.slot_id
                   WHERE s.floor_id = ? AND b.booking_status IN ('HELD','CONFIRMED')""",
                (floor_id,),
            ).fetchone()[0]
            if active > 0:
                return jsonify({"error": "Cannot deactivate floor with active bookings", "code": 409}), 409
            conn.execute("UPDATE floors SET floor_status = 'INACTIVE', updated_by = ?, updated_at = datetime('now') WHERE floor_id = ?",
                         (actor["user_id"], floor_id))
            _audit(conn, "FLOOR_DEACTIVATED", "floors", floor_id, old["floor_status"], "INACTIVE", actor["user_id"])
        return jsonify({"message": "Floor deactivated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


# ---------------------------------------------------------------------------
# Slot management
# ---------------------------------------------------------------------------
@super_admin_bp.post("/floors/<int:floor_id>/slots")
@require_role("SUPER_ADMIN")
def create_slot(floor_id):
    data = request.get_json(silent=True) or {}
    number = (data.get("slot_number") or "").strip()
    vtype_id = data.get("vehicle_type_id")
    if not number or not vtype_id:
        return jsonify({"error": "slot_number and vehicle_type_id required", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            if conn.execute("SELECT 1 FROM floors WHERE floor_id = ?", (floor_id,)).fetchone() is None:
                return jsonify({"error": "Floor not found", "code": 404}), 404
            if conn.execute("SELECT 1 FROM vehicle_types WHERE vehicle_type_id = ?", (vtype_id,)).fetchone() is None:
                return jsonify({"error": "Vehicle type not found", "code": 404}), 404
            if conn.execute("SELECT 1 FROM parking_slots WHERE floor_id = ? AND slot_number = ?",
                            (floor_id, number)).fetchone():
                return jsonify({"error": "Slot number exists on this floor", "code": 409}), 409
            conn.execute(
                """INSERT INTO parking_slots (floor_id, vehicle_type_id, slot_number, control_status, created_by)
                   VALUES (?, ?, ?, 'ACTIVE', ?)""",
                (floor_id, vtype_id, number, actor["user_id"]),
            )
            sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            _audit(conn, "SLOT_CREATED", "parking_slots", sid, None, number, actor["user_id"])
        return jsonify({"slot_id": sid, "slot_number": number}), 201
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@super_admin_bp.put("/slots/<int:slot_id>")
@require_role("SUPER_ADMIN")
def update_slot(slot_id):
    data = request.get_json(silent=True) or {}
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT * FROM parking_slots WHERE slot_id = ?", (slot_id,)).fetchone()
            if old is None:
                return jsonify({"error": "Slot not found", "code": 404}), 404
            fields, params = [], []
            if "slot_number" in data:
                fields.append("slot_number = ?"); params.append(data["slot_number"])
            if "control_status" in data:
                cs = data["control_status"]
                if cs not in ("ACTIVE", "ADMIN_RESERVED", "MAINTENANCE", "INACTIVE"):
                    return jsonify({"error": "Invalid control_status", "code": 400}), 400
                if cs != "ACTIVE":
                    active = conn.execute(
                        """SELECT COUNT(*) FROM bookings WHERE slot_id = ? AND booking_status IN ('HELD','CONFIRMED')""",
                        (slot_id,),
                    ).fetchone()[0]
                    if active > 0:
                        return jsonify({"error": "Slot has an active booking; release it before changing its state", "code": 409}), 409
                fields.append("control_status = ?"); params.append(cs)
            if not fields:
                return jsonify({"error": "No updatable fields", "code": 400}), 400
            params.extend([actor["user_id"], slot_id])
            conn.execute(
                f"UPDATE parking_slots SET {', '.join(fields)}, updated_by = ?, updated_at = datetime('now') WHERE slot_id = ?",
                params,
            )
            _audit(conn, "SLOT_UPDATED", "parking_slots", slot_id, str(dict(old)), str(data), actor["user_id"])
        return jsonify({"message": "Slot updated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@super_admin_bp.delete("/slots/<int:slot_id>")
@require_role("SUPER_ADMIN")
def delete_slot(slot_id):
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT control_status FROM parking_slots WHERE slot_id = ?", (slot_id,)).fetchone()
            if old is None:
                return jsonify({"error": "Slot not found", "code": 404}), 404
            active = conn.execute(
                "SELECT COUNT(*) FROM bookings WHERE slot_id = ? AND booking_status IN ('HELD','CONFIRMED')",
                (slot_id,),
            ).fetchone()[0]
            if active > 0:
                return jsonify({"error": "Cannot deactivate slot with active booking", "code": 409}), 409
            conn.execute("UPDATE parking_slots SET control_status = 'INACTIVE', updated_by = ?, updated_at = datetime('now') WHERE slot_id = ?",
                         (actor["user_id"], slot_id))
            _audit(conn, "SLOT_UPDATED", "parking_slots", slot_id, old["control_status"], "INACTIVE", actor["user_id"])
        return jsonify({"message": "Slot deactivated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


# ---------------------------------------------------------------------------
# Super Admin booking control
# ---------------------------------------------------------------------------
@super_admin_bp.post("/bookings/<string:ref>/cancel")
@require_role("SUPER_ADMIN")
def cancel_any_booking(ref):
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            b = conn.execute(
                """SELECT b.*, u.wallet_balance FROM bookings b
                   JOIN users u ON u.user_id = b.user_id WHERE b.booking_reference = ?""",
                (ref,),
            ).fetchone()
            if b is None:
                return jsonify({"error": "Booking not found", "code": 404}), 404
            if b["booking_status"] not in ("HELD", "CONFIRMED"):
                return jsonify({"error": "Only HELD or CONFIRMED bookings can be cancelled", "code": 409}), 409
            entered = conn.execute(
                """SELECT COUNT(*) FROM booking_events WHERE booking_id = ? AND event_type = 'ENTRY'
                   AND NOT EXISTS (SELECT 1 FROM booking_events e2 WHERE e2.booking_id = booking_events.booking_id AND e2.event_type = 'EXIT')""",
                (b["booking_id"],),
            ).fetchone()[0]
            if entered > 0:
                return jsonify({"error": "Cannot cancel: vehicle has entered and not exited", "code": 409}), 409
            now = datetime.now()
            from_dt = datetime.fromisoformat(b["booked_from"])
            hours_before = (from_dt - now).total_seconds() / 3600.0
            if hours_before > 24:
                refund_pct = 100.0
            elif hours_before >= 1:
                refund_pct = 50.0
            else:
                refund_pct = 0.0
            paid = float(b["estimated_amount"])
            refund = round(paid * refund_pct / 100, 2)
            if b["booking_status"] == "HELD":
                refund = 0.0
            cust_wallet = float(b["wallet_balance"])
            new_cust = round(cust_wallet + refund, 2)
            if refund > 0:
                conn.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_cust, b["user_id"]))
                cref = "TXN-SACRF-" + datetime.now().strftime("%Y%m%d%H%M%S%f") + f"-{b['booking_id']}"
                conn.execute(
                    """INSERT INTO wallet_transactions
                       (transaction_reference, user_id, booking_id, transaction_type, direction, amount, balance_after, created_by)
                       VALUES (?, ?, ?, 'CANCELLATION_REFUND', 'CREDIT', ?, ?, ?)""",
                    (cref, b["user_id"], b["booking_id"], refund, new_cust, actor["user_id"]),
                )
                cid = conn.execute("SELECT transaction_id FROM wallet_transactions WHERE transaction_reference = ?", (cref,)).fetchone()[0]
                sa = conn.execute("SELECT user_id, wallet_balance FROM users WHERE role = 'SUPER_ADMIN'").fetchone()
                if sa:
                    sa_before = float(sa["wallet_balance"])
                    sa_after = round(sa_before - refund, 2)
                    conn.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (sa_after, sa["user_id"]))
                    sref = "TXN-SASRF-" + datetime.now().strftime("%Y%m%d%H%M%S%f") + f"-{b['booking_id']}"
                    conn.execute(
                        """INSERT INTO wallet_transactions
                           (transaction_reference, user_id, booking_id, transaction_type, direction, amount, balance_after, created_by)
                           VALUES (?, ?, ?, 'REVENUE_REFUND_REVERSAL', 'DEBIT', ?, ?, ?)""",
                        (sref, sa["user_id"], b["booking_id"], refund, sa_after, actor["user_id"]),
                    )
                    sid = conn.execute("SELECT transaction_id FROM wallet_transactions WHERE transaction_reference = ?", (sref,)).fetchone()[0]
                    conn.execute(
                        """INSERT INTO revenue_collections
                           (source_user_id, super_admin_user_id, booking_id, customer_wallet_transaction_id,
                            super_admin_wallet_transaction_id, collection_type, amount, created_by)
                           VALUES (?, ?, ?, ?, ?, 'REFUND_REVERSAL', ?, ?)""",
                        (b["user_id"], sa["user_id"], b["booking_id"], cid, sid, refund, actor["user_id"]),
                    )
            conn.execute("UPDATE bookings SET booking_status = 'CANCELLED', updated_by = ?, updated_at = datetime('now') WHERE booking_reference = ?",
                         (actor["user_id"], ref))
            _audit(conn, "BOOKING_CANCELLED", "bookings", b["booking_id"], b["booking_status"], "CANCELLED", actor["user_id"])
        return jsonify({"booking_reference": ref, "booking_status": "CANCELLED", "refund_amount": refund})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


# ---------------------------------------------------------------------------
# Live DB tables (read-only, whitelist)
# ---------------------------------------------------------------------------
ALLOWED_TABLES = {
    "users": ["user_id", "admin_id", "full_name", "email", "phone", "gender", "company_name",
              "username", "role", "wallet_balance", "account_status", "created_at"],
    "floors": "*",
    "vehicle_types": "*",
    "parking_slots": "*",
    "bookings": "*",
    "cancellation_rules": "*",
    "wallet_transactions": "*",
    "booking_events": "*",
    "audit_logs": "*",
    "revenue_collections": "*",
    "system_settings": "*",
}


@super_admin_bp.get("/db-tables/<table_name>")
@require_role("SUPER_ADMIN")
def db_table(table_name):
    if table_name not in ALLOWED_TABLES:
        return jsonify({"error": "Table not whitelisted", "code": 403}), 403
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 25, type=int)))
    offset = (page - 1) * per_page
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        cols = ALLOWED_TABLES[table_name]
        if cols == "*":
            rows = conn.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (per_page, offset)).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {', '.join(cols)} FROM {table_name} LIMIT ? OFFSET ?", (per_page, offset)
            ).fetchall()
        total = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        return jsonify({"table": table_name, "page": page, "per_page": per_page,
                        "total": total, "items": [dict(r) for r in rows]})
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@super_admin_bp.get("/analytics/overview")
@require_role("SUPER_ADMIN")
def analytics_overview():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        where = " WHERE 1=1"
        params = []
        if date_from:
            where += " AND DATE(created_at) >= ?"; params.append(date_from)
        if date_to:
            where += " AND DATE(created_at) <= ?"; params.append(date_to)

        total_customers = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'CUSTOMER' AND account_status = 'ACTIVE'"
        ).fetchone()[0]
        total_bookings = conn.execute(f"SELECT COUNT(*) FROM bookings{where}", params).fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM bookings WHERE booking_status = 'COMPLETED'").fetchone()[0]
        revenue = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN collection_type = 'REFUND_REVERSAL' THEN -amount ELSE amount END),0) FROM revenue_collections"
        ).fetchone()[0]
        total_slots = conn.execute("SELECT COUNT(*) FROM parking_slots").fetchone()[0]
        from src.api.slots import _LIVE_STATUS_SQL
        occupied = conn.execute(
            f"SELECT COUNT(*) FROM parking_slots s WHERE {_LIVE_STATUS_SQL} IN ('RESERVED','OCCUPIED')"
        ).fetchone()[0]
        return jsonify({
            "total_customers": total_customers,
            "total_bookings": total_bookings,
            "completed_bookings": completed,
            "net_revenue": round(float(revenue), 2),
            "total_slots": total_slots,
            "occupied_slots": occupied,
            "occupancy_percent": round(100 * occupied / total_slots, 2) if total_slots else 0,
        })
    finally:
        conn.close()


@super_admin_bp.get("/analytics/overtime")
@require_role("SUPER_ADMIN")
def analytics_overtime():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            """SELECT DATE(created_at) AS day, COUNT(*) AS count, COALESCE(SUM(amount),0) AS amount
               FROM wallet_transactions WHERE transaction_type = 'OVERTIME_DEBIT'
               GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 30"""
        ).fetchall()
        return jsonify({"overtime": [dict(r) for r in rows]})
    finally:
        conn.close()


@super_admin_bp.get("/analytics/floor-heatmap")
@require_role("SUPER_ADMIN")
def analytics_floor_heatmap():
    from src.api.slots import _LIVE_STATUS_SQL
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            f"""SELECT f.floor_id, f.floor_code, f.floor_status,
                      COUNT(s.slot_id) AS total_slots,
                      SUM(CASE WHEN {_LIVE_STATUS_SQL} IN ('RESERVED','OCCUPIED') THEN 1 ELSE 0 END) AS occupied_slots
               FROM floors f LEFT JOIN parking_slots s ON s.floor_id = f.floor_id
               GROUP BY f.floor_id ORDER BY f.floor_code"""
        ).fetchall()
        out = []
        for r in rows:
            total = int(r["total_slots"] or 0)
            occ = int(r["occupied_slots"] or 0)
            out.append({"floor_code": r["floor_code"], "floor_status": r["floor_status"],
                        "total_slots": total, "occupied_slots": occ,
                        "occupancy_percent": round(100 * occ / total, 2) if total else 0})
        return jsonify({"floors": out})
    finally:
        conn.close()


@super_admin_bp.get("/analytics/revenue")
@require_role("SUPER_ADMIN")
def analytics_revenue():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        where = ""
        params = []
        if date_from:
            where += " AND DATE(b.booked_from) >= ?"; params.append(date_from)
        if date_to:
            where += " AND DATE(b.booked_from) <= ?"; params.append(date_to)

        by_floor = conn.execute(
            f"""SELECT f.floor_code, COALESCE(SUM(rc.amount),0) AS amount
                FROM revenue_collections rc
                JOIN bookings b ON b.booking_id = rc.booking_id
                JOIN parking_slots s ON s.slot_id = b.slot_id
                JOIN floors f ON f.floor_id = s.floor_id
                WHERE 1=1{where} GROUP BY f.floor_code ORDER BY f.floor_code""",
            params,
        ).fetchall()
        by_vtype = conn.execute(
            f"""SELECT vt.type_name, COALESCE(SUM(rc.amount),0) AS amount
                FROM revenue_collections rc
                JOIN bookings b ON b.booking_id = rc.booking_id
                JOIN parking_slots s ON s.slot_id = b.slot_id
                JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
                WHERE 1=1{where} GROUP BY vt.type_name""",
            params,
        ).fetchall()
        by_day = conn.execute(
            f"""SELECT DATE(rc.created_at) AS day, COALESCE(SUM(rc.amount),0) AS amount
                FROM revenue_collections rc JOIN bookings b ON b.booking_id = rc.booking_id
                WHERE 1=1{where} GROUP BY DATE(rc.created_at) ORDER BY day""",
            params,
        ).fetchall()
        return jsonify({
            "by_floor": [dict(r) for r in by_floor],
            "by_vehicle_type": [dict(r) for r in by_vtype],
            "by_day": [dict(r) for r in by_day],
        })
    finally:
        conn.close()