"""Admin endpoints: dashboard, master data, all bookings, wallet, slot control."""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from src.services.db import get_connection, transaction
from src.core.security import require_admin, get_current_user, generate_user_password
from werkzeug.security import generate_password_hash
from src.api.qr import scan as _qr_scan

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
# Alias: POST /api/admin/qr/scan (same handler as /api/qr/scan)
admin_bp.add_url_rule("/qr/scan", "admin_qr_scan", _qr_scan, methods=["POST"])


def _live_slot_status(conn, slot_id, control_status):
    """Compute live display status for a slot."""
    if control_status == "MAINTENANCE":
        return "MAINTENANCE"
    if control_status in ("ADMIN_RESERVED",):
        return "RESERVED"
    if control_status == "INACTIVE":
        return "INACTIVE"
    occupied = conn.execute(
        """SELECT 1 FROM booking_events e
           JOIN bookings b ON b.booking_id = e.booking_id
           WHERE b.slot_id = ? AND e.event_type = 'ENTRY'
             AND NOT EXISTS (SELECT 1 FROM booking_events x
                             WHERE x.booking_id = e.booking_id AND x.event_type = 'EXIT')""",
        (slot_id,),
    ).fetchone()
    if occupied:
        return "OCCUPIED"
    reserved = conn.execute(
        """SELECT 1 FROM bookings WHERE slot_id = ? AND booking_status IN ('HELD','CONFIRMED')""",
        (slot_id,),
    ).fetchone()
    if reserved:
        return "RESERVED"
    return "AVAILABLE"


# ---------------------------------------------------------------------------
# Dashboard KPIs
# ---------------------------------------------------------------------------
@admin_bp.get("/dashboard")
@require_admin
def dashboard():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        slots = conn.execute("SELECT slot_id, control_status FROM parking_slots").fetchall()
        counts = {"AVAILABLE": 0, "RESERVED": 0, "OCCUPIED": 0, "MAINTENANCE": 0}
        for s in slots:
            st = _live_slot_status(conn, s["slot_id"], s["control_status"])
            if st in counts:
                counts[st] += 1
        revenue = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN collection_type='REFUND_REVERSAL' THEN -amount ELSE amount END),0) AS r FROM revenue_collections"
        ).fetchone()
        users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'CUSTOMER' AND account_status = 'ACTIVE'"
        ).fetchone()[0]
        return jsonify({
            "total_slots": len(slots),
            "available_slots": counts["AVAILABLE"],
            "reserved_slots": counts["RESERVED"],
            "occupied_slots": counts["OCCUPIED"],
            "maintenance_slots": counts["MAINTENANCE"],
            "total_revenue": round(float(revenue["r"]), 2),
            "active_users": users,
        })
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# All bookings
# ---------------------------------------------------------------------------
@admin_bp.get("/bookings")
@require_admin
def all_bookings():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        sql = """
            SELECT b.booking_reference, b.booking_status, b.booked_from, b.booked_until,
                   b.estimated_amount, b.vehicle_number, b.vehicle_format,
                   u.username, u.full_name, u.role,
                   f.floor_code, s.slot_number, vt.type_name AS vehicle_type,
                   (SELECT created_at FROM booking_events be WHERE be.booking_id=b.booking_id AND be.event_type='ENTRY' LIMIT 1) AS entry_time,
                   (SELECT created_at FROM booking_events be WHERE be.booking_id=b.booking_id AND be.event_type='EXIT' LIMIT 1) AS exit_time
            FROM bookings b
            JOIN users u ON u.user_id = b.user_id
            JOIN parking_slots s ON s.slot_id = b.slot_id
            JOIN floors f ON f.floor_id = s.floor_id
            JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
            WHERE 1=1
        """
        params = []
        for q, clause in (
            ("date_from", " AND DATE(b.booked_from) >= ?"),
            ("date_to", " AND DATE(b.booked_from) <= ?"),
            ("status", " AND b.booking_status = ?"),
            ("floor", " AND f.floor_code = ?"),
            ("vehicle_type", " AND vt.type_name = ?"),
        ):
            v = request.args.get(q)
            if v:
                sql += clause
                params.append(v)
        us = request.args.get("user_search")
        if us:
            sql += " AND (LOWER(u.username) LIKE ? OR LOWER(u.full_name) LIKE ?)"
            params.extend([f"%{us.lower()}%", f"%{us.lower()}%"])
        sql += " ORDER BY b.booked_from DESC"
        rows = conn.execute(sql, params).fetchall()
        return jsonify({"items": [dict(r) for r in rows], "total": len(rows)})
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Users (customers) management
# ---------------------------------------------------------------------------
@admin_bp.get("/users")
@require_admin
def list_users():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            """SELECT user_id, admin_id, full_name, email, phone, gender, company_name,
                      username, role, wallet_balance, account_status, created_at
               FROM users ORDER BY role, user_id"""
        ).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    finally:
        conn.close()


@admin_bp.post("/users")
@require_admin
def create_customer():
    """Admin registers a walk-in customer. No password set (activation later)."""
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    gender = data.get("gender")
    company_name = data.get("company_name")
    email = (data.get("email") or "").strip() or None
    username = (data.get("username") or "").strip() or None
    if not full_name or not phone:
        return jsonify({"error": "full_name and phone required", "code": 400}), 400
    if gender and gender not in ("MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"):
        return jsonify({"error": "Invalid gender", "code": 400}), 400
    if not email and not username:
        # generate a username so login identifier exists
        username = "cust" + datetime.now().strftime("%Y%m%d%H%M%S")

    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            if email and conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                return jsonify({"error": "Email exists", "code": 409}), 409
            if username and conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
                return jsonify({"error": "Username exists", "code": 409}), 409
            conn.execute(
                """INSERT INTO users
                   (admin_id, full_name, email, phone, gender, company_name, username,
                    password_hash, role, wallet_balance, account_status, created_by)
                   VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, 'CUSTOMER', 1000, 'PENDING', ?)""",
                (
                    full_name, email, phone, gender, company_name, username,
                    generate_password_hash(generate_user_password(full_name, phone)),
                    actor["user_id"],
                ),
            )
            uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """INSERT INTO audit_logs (action_type, entity_type, entity_id, new_values, created_by)
                   VALUES ('CREATE_USER', 'users', ?, ?, ?)""",
                (uid, full_name, actor["user_id"]),
            )
        return jsonify({"user_id": uid, "username": username, "message": "Customer registered"}), 201
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@admin_bp.get("/users/<int:user_id>")
@require_admin
def get_user(user_id):
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            """SELECT user_id, admin_id, full_name, email, phone, gender, company_name,
                      username, role, wallet_balance, account_status, created_at
               FROM users WHERE user_id = ?""",
            (user_id,),
        ).fetchone()
        if row is None:
            return jsonify({"error": "User not found", "code": 404}), 404
        return jsonify(dict(row))
    finally:
        conn.close()


@admin_bp.put("/users/<int:user_id>")
@require_admin
def update_user(user_id):
    data = request.get_json(silent=True) or {}
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if old is None:
                return jsonify({"error": "User not found", "code": 404}), 404
            # Admin can only manage CUSTOMER accounts
            if old["role"] != "CUSTOMER" and actor["role"] != "SUPER_ADMIN":
                return jsonify({"error": "Admins may only manage customer accounts", "code": 403}), 403
            fields, params = [], []
            for col in ("full_name", "phone", "email", "gender", "company_name", "username", "account_status"):
                if col in data:
                    fields.append(f"{col} = ?")
                    params.append(data[col])
            if data.get("account_status") == "ACTIVE" and not old["password_hash"]:
                fields.append("password_hash = ?")
                params.append(generate_password_hash(old["username"] or f"customer{user_id}"))
            if not fields:
                return jsonify({"error": "No updatable fields", "code": 400}), 400
            params.extend([actor["user_id"], user_id])
            conn.execute(
                f"UPDATE users SET {', '.join(fields)}, updated_by = ?, updated_at = datetime('now') WHERE user_id = ?",
                params,
            )
            conn.execute(
                """INSERT INTO audit_logs (action_type, entity_type, entity_id, new_values, created_by)
                   VALUES ('UPDATE_USER', 'users', ?, ?, ?)""",
                (user_id, str(data), actor["user_id"]),
            )
        return jsonify({"message": "User updated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@admin_bp.delete("/users/<int:user_id>")
@require_admin
def delete_user(user_id):
    """Soft delete a customer."""
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if old is None:
                return jsonify({"error": "User not found", "code": 404}), 404
            if old["role"] != "CUSTOMER" and actor["role"] != "SUPER_ADMIN":
                return jsonify({"error": "Admins may only delete customer accounts", "code": 403}), 403
            conn.execute(
                "UPDATE users SET account_status = 'DELETED', updated_by = ?, updated_at = datetime('now') WHERE user_id = ?",
                (actor["user_id"], user_id),
            )
            conn.execute(
                """INSERT INTO audit_logs (action_type, entity_type, entity_id, new_values, created_by)
                   VALUES ('DELETE_USER', 'users', ?, 'DELETED', ?)""",
                (user_id, actor["user_id"]),
            )
        return jsonify({"message": "User deactivated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------
@admin_bp.post("/users/<int:user_id>/wallet-adjustments")
@require_admin
def wallet_adjustment(user_id):
    data = request.get_json(silent=True) or {}
    try:
        amount = round(float(data.get("amount")), 2)
    except (TypeError, ValueError):
        return jsonify({"error": "amount required", "code": 400}), 400
    if amount == 0:
        return jsonify({"error": "amount must be non-zero", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            u = conn.execute("SELECT wallet_balance, role FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if u is None:
                return jsonify({"error": "User not found", "code": 404}), 404
            if u["role"] != "CUSTOMER" and actor["role"] != "SUPER_ADMIN":
                return jsonify({"error": "Admins may only adjust customer wallets", "code": 403}), 403
            before = float(u["wallet_balance"])
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
                (ref, user_id, "CREDIT" if amount > 0 else "DEBIT", abs(amount), after,
                 data.get("description", "Admin adjustment"), actor["user_id"]),
            )
            conn.execute(
                """INSERT INTO audit_logs (action_type, entity_type, entity_id, old_values, new_values, created_by)
                   VALUES ('WALLET_ADJUSTMENT', 'users', ?, ?, ?, ?)""",
                (user_id, str(before), str(after), actor["user_id"]),
            )
        return jsonify({"user_id": user_id, "previous_balance": before, "new_balance": after, "adjustment": amount})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@admin_bp.get("/users/<int:user_id>/wallet")
@require_admin
def get_wallet(user_id):
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        u = conn.execute("SELECT user_id, wallet_balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if u is None:
            return jsonify({"error": "User not found", "code": 404}), 404
        rows = conn.execute(
            """SELECT transaction_reference, transaction_type, direction, amount, balance_after, description, created_at
               FROM wallet_transactions WHERE user_id = ? ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
        return jsonify({"user_id": user_id, "wallet_balance": float(u["wallet_balance"]),
                        "transactions": [dict(r) for r in rows]})
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Slot control status (Admin: ACTIVE / ADMIN_RESERVED / MAINTENANCE only)
# ---------------------------------------------------------------------------
@admin_bp.patch("/slots/<int:slot_id>/control-status")
@require_admin
def set_slot_control_status(slot_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("control_status")
    if new_status not in ("ACTIVE", "ADMIN_RESERVED", "MAINTENANCE"):
        return jsonify({"error": "control_status must be ACTIVE, ADMIN_RESERVED or MAINTENANCE", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT control_status FROM parking_slots WHERE slot_id = ?", (slot_id,)).fetchone()
            if old is None:
                return jsonify({"error": "Slot not found", "code": 404}), 404
            if new_status in ("MAINTENANCE", "ADMIN_RESERVED"):
                active = conn.execute(
                    "SELECT COUNT(*) FROM bookings WHERE slot_id = ? AND booking_status IN ('HELD','CONFIRMED')",
                    (slot_id,),
                ).fetchone()[0]
                if active > 0:
                    return jsonify({"error": "Slot is booked or occupied; cannot change", "code": 409}), 409
            conn.execute("UPDATE parking_slots SET control_status = ?, updated_by = ?, updated_at = datetime('now') WHERE slot_id = ?",
                         (new_status, actor["user_id"], slot_id))
            action = "SLOT_MAINTENANCE" if new_status == "MAINTENANCE" else "SLOT_RESERVED" if new_status == "ADMIN_RESERVED" else "SLOT_UPDATED"
            conn.execute(
                """INSERT INTO audit_logs (action_type, entity_type, entity_id, old_values, new_values, created_by)
                   VALUES (?, 'parking_slots', ?, ?, ?, ?)""",
                (action, slot_id, old["control_status"], new_status, actor["user_id"]),
            )
        return jsonify({"slot_id": slot_id, "control_status": new_status})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


# ---------------------------------------------------------------------------
# Cancellation rules (Admin + Super Admin)
# ---------------------------------------------------------------------------
@admin_bp.get("/cancellation-rules")
@require_admin
def list_rules():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute("SELECT * FROM cancellation_rules ORDER BY rule_code").fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    finally:
        conn.close()


@admin_bp.post("/cancellation-rules")
@require_admin
def create_rule():
    data = request.get_json(silent=True) or {}
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            conn.execute(
                """INSERT INTO cancellation_rules
                   (rule_code, rule_name, min_hours_before, max_hours_before, is_no_show,
                    refund_percent, penalty_percent, description, is_active, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (data.get("rule_code"), data.get("rule_name"), data.get("min_hours_before"),
                 data.get("max_hours_before"), int(data.get("is_no_show", 0)),
                 data.get("refund_percent", 0), data.get("penalty_percent", 0),
                 data.get("description"), int(data.get("is_active", 1)), actor["user_id"]),
            )
            rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return jsonify({"rule_id": rid, "message": "Rule created"}), 201
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@admin_bp.put("/cancellation-rules/<int:rule_id>")
@require_admin
def update_rule(rule_id):
    data = request.get_json(silent=True) or {}
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT rule_id FROM cancellation_rules WHERE rule_id = ?", (rule_id,)).fetchone()
            if old is None:
                return jsonify({"error": "Rule not found", "code": 404}), 404
            fields, params = [], []
            for col in ("rule_name", "min_hours_before", "max_hours_before", "is_no_show",
                        "refund_percent", "penalty_percent", "description", "is_active"):
                if col in data:
                    fields.append(f"{col} = ?"); params.append(data[col])
            if not fields:
                return jsonify({"error": "No updatable fields", "code": 400}), 400
            params.extend([actor["user_id"], rule_id])
            conn.execute(f"UPDATE cancellation_rules SET {', '.join(fields)}, updated_by = ?, updated_at = datetime('now') WHERE rule_id = ?", params)
        return jsonify({"message": "Rule updated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@admin_bp.delete("/cancellation-rules/<int:rule_id>")
@require_admin
def delete_rule(rule_id):
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT rule_id FROM cancellation_rules WHERE rule_id = ?", (rule_id,)).fetchone()
            if old is None:
                return jsonify({"error": "Rule not found", "code": 404}), 404
            conn.execute("UPDATE cancellation_rules SET is_active = 0, updated_by = ?, updated_at = datetime('now') WHERE rule_id = ?",
                         (actor["user_id"], rule_id))
        return jsonify({"message": "Rule deactivated"})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


# ---------------------------------------------------------------------------
# Master data: floors, vehicle types, slots
# ---------------------------------------------------------------------------
@admin_bp.get("/floors")
@require_admin
def list_floors():
    from src.api.slots import _LIVE_STATUS_SQL

    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            f"""SELECT f.floor_id, f.floor_code, f.floor_status,
                       COUNT(s.slot_id) AS total_slots,
                       SUM(CASE WHEN {_LIVE_STATUS_SQL} = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_slots,
                       SUM(CASE WHEN {_LIVE_STATUS_SQL} = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_slots
                FROM floors f LEFT JOIN parking_slots s ON s.floor_id = f.floor_id
                GROUP BY f.floor_id ORDER BY f.floor_code"""
        ).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    finally:
        conn.close()


@admin_bp.get("/vehicle-types")
@require_admin
def list_vehicle_types():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            """SELECT vehicle_type_id, type_name, hourly_rate, overstay_rate, is_active
               FROM vehicle_types ORDER BY vehicle_type_id"""
        ).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    finally:
        conn.close()


@admin_bp.get("/slots")
@require_admin
def list_slots():
    from src.api.slots import _LIVE_STATUS_SQL

    floor_id = request.args.get("floor_id", type=int)
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        sql = f"""SELECT s.slot_id, s.slot_number, s.floor_id, s.vehicle_type_id,
                         s.control_status, {_LIVE_STATUS_SQL} AS status,
                         f.floor_code, vt.type_name AS vehicle_type
                  FROM parking_slots s
                  JOIN floors f ON f.floor_id = s.floor_id
                  JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
                  WHERE 1=1"""
        params = []
        if floor_id is not None:
            sql += " AND s.floor_id = ?"
            params.append(floor_id)
        sql += " ORDER BY s.floor_id, s.slot_number"
        rows = conn.execute(sql, params).fetchall()
        return jsonify({"items": [dict(r) for r in rows], "total": len(rows)})
    finally:
        conn.close()


# Backward-compatible aliases still referenced by older templates.
@admin_bp.get("/master/floors")
@require_admin
def master_floors():
    return list_floors()


@admin_bp.get("/master/vehicle-types")
@require_admin
def master_vehicle_types():
    return list_vehicle_types()


@admin_bp.get("/master/slots")
@require_admin
def master_slots():
    return list_slots()


@admin_bp.get("/master/users")
@require_admin
def master_users():
    return list_users()


@admin_bp.get("/master/cancellation-rules")
@require_admin
def master_rules():
    return list_rules()


@admin_bp.put("/master/floors/<int:floor_id>")
@require_admin
def master_update_floor(floor_id):
    data = request.get_json(silent=True) or {}
    status = data.get("floor_status") or data.get("status")
    if status not in ("OPEN", "CLOSED", "MAINTENANCE", "INACTIVE"):
        return jsonify({"error": "Invalid floor status", "code": 400}), 400
    actor = get_current_user()
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        conn.execute("UPDATE floors SET floor_status = ?, updated_by = ? WHERE floor_id = ?",
                     (status, actor["user_id"], floor_id))
        conn.commit()
        return jsonify({"message": "Floor updated"})
    finally:
        conn.close()


@admin_bp.put("/master/slots/<int:slot_id>/status")
@require_admin
def master_update_slot_status(slot_id):
    data = request.get_json(silent=True) or {}
    status = data.get("control_status") or data.get("status")
    mapping = {"AVAILABLE": "ACTIVE", "RESERVED": "ADMIN_RESERVED",
               "MAINTENANCE": "MAINTENANCE", "INACTIVE": "INACTIVE", "ACTIVE": "ACTIVE"}
    new_status = mapping.get(status)
    if new_status is None:
        return jsonify({"error": "Invalid status", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = conn.execute("SELECT control_status FROM parking_slots WHERE slot_id = ?", (slot_id,)).fetchone()
            if old is None:
                return jsonify({"error": "Slot not found", "code": 404}), 404
            if new_status in ("MAINTENANCE", "ADMIN_RESERVED"):
                active = conn.execute(
                    "SELECT COUNT(*) FROM bookings WHERE slot_id = ? AND booking_status IN ('HELD','CONFIRMED')",
                    (slot_id,),
                ).fetchone()[0]
                if active > 0:
                    return jsonify({"error": "Slot is booked or occupied; cannot change", "code": 409}), 409
            conn.execute("UPDATE parking_slots SET control_status = ?, updated_by = ?, updated_at = datetime('now') WHERE slot_id = ?",
                         (new_status, actor["user_id"], slot_id))
            action = "SLOT_MAINTENANCE" if new_status == "MAINTENANCE" else "SLOT_RESERVED" if new_status == "ADMIN_RESERVED" else "SLOT_UPDATED"
            conn.execute(
                """INSERT INTO audit_logs (action_type, entity_type, entity_id, old_values, new_values, created_by)
                   VALUES (?, 'parking_slots', ?, ?, ?, ?)""",
                (action, slot_id, old["control_status"], new_status, actor["user_id"]),
            )
        return jsonify({"slot_id": slot_id, "control_status": new_status})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500