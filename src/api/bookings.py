"""Booking lifecycle endpoints: hold, confirm, cancel, get, my bookings."""

from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app
from src.services.db import get_connection, transaction
from src.core.pricing import calculate_fare

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api/bookings")


def _now():
    return datetime.now().replace(microsecond=0)


import uuid

def _gen_ref(prefix="QSP"):
    return f"{prefix}-{_now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8].upper()}"


def _system_online(conn):
    row = conn.execute(
        "SELECT setting_value FROM system_settings WHERE setting_key = 'SYSTEM_STATUS'"
    ).fetchone()
    return (row["setting_value"] if row else "ONLINE") == "ONLINE"


def _active_booking_exists(conn, vehicle_number, exclude_id=None):
    sql = """SELECT 1 FROM bookings WHERE vehicle_number = ?
             AND booking_status IN ('HELD','CONFIRMED')"""
    params = [vehicle_number]
    if exclude_id:
        sql += " AND booking_id != ?"
        params.append(exclude_id)
    return conn.execute(sql, params).fetchone() is not None


def _slot_has_overlap(conn, slot_id, from_iso, until_iso, exclude_id=None):
    sql = """SELECT 1 FROM bookings WHERE slot_id = ?
           AND booking_status IN ('HELD','CONFIRMED')
           AND booked_from < ? AND booked_until > ?"""
    params = [slot_id, until_iso, from_iso]
    if exclude_id:
        sql += " AND booking_id != ?"
        params.append(exclude_id)
    return conn.execute(sql, params).fetchone() is not None


def _has_open_entry(conn, booking_id):
    return conn.execute(
        """SELECT 1 FROM booking_events WHERE booking_id = ? AND event_type = 'ENTRY'
           AND NOT EXISTS (SELECT 1 FROM booking_events e2
                           WHERE e2.booking_id = booking_events.booking_id AND e2.event_type = 'EXIT')""",
        (booking_id,),
    ).fetchone() is not None


def _expire_held(conn):
    conn.execute(
        """UPDATE bookings SET booking_status = 'EXPIRED', updated_at = datetime('now')
           WHERE booking_status = 'HELD' AND hold_expires_at IS NOT NULL
             AND hold_expires_at < datetime('now')"""
    )


def _get_super_admin(conn):
    return conn.execute(
        "SELECT user_id, wallet_balance FROM users WHERE role = 'SUPER_ADMIN' LIMIT 1"
    ).fetchone()


def _record_wallet(conn, user_id, booking_id, txn_type, direction, amount, balance_after, description, actor):
    ref = _gen_ref("TXN")
    conn.execute(
        """INSERT INTO wallet_transactions
           (transaction_reference, user_id, booking_id, transaction_type, direction,
            amount, balance_after, description, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ref, user_id, booking_id, txn_type, direction, amount, balance_after, description, actor),
    )
    return ref


@bookings_bp.post("/hold")
def hold():
    """Create a HELD booking with BEGIN IMMEDIATE lock."""
    data = request.get_json(silent=True) or {}
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    slot_id = data.get("slot_id")
    vehicle_number = (data.get("vehicle_number") or "").strip().upper()
    vehicle_format = (data.get("vehicle_format") or "std1").strip()
    booked_from = data.get("booked_from")
    booked_until = data.get("booked_until")

    if not all([slot_id, vehicle_number, booked_from, booked_until]):
        return jsonify({"error": "slot_id, vehicle_number, booked_from, booked_until required", "code": 400}), 400
    if vehicle_format not in ("std1", "std2", "std3", "bhr"):
        return jsonify({"error": "Invalid vehicle_format", "code": 400}), 400

    try:
        from_dt = datetime.fromisoformat(booked_from)
        until_dt = datetime.fromisoformat(booked_until)
    except ValueError:
        return jsonify({"error": "Invalid datetime format", "code": 400}), 400

    if from_dt.hour < 5 or until_dt.hour > 23:
        return jsonify({"error": "Bookings allowed only between 05:00 and 23:00", "code": 400}), 400
    duration_hours = (until_dt - from_dt).total_seconds() / 3600.0
    if duration_hours <= 0:
        return jsonify({"error": "End time must be after start time", "code": 400}), 400
    if duration_hours > 18:
        return jsonify({"error": "Maximum booking duration is 18 hours", "code": 400}), 400

    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            role = session.get("role")
            if not _system_online(conn) and role not in ("ADMIN", "SUPER_ADMIN"):
                return jsonify({"error": "System is OFFLINE. Bookings are disabled.", "code": 503}), 503

            # Admins may book on behalf of a registered walk-in customer.
            booker_id = user_id
            if role in ("ADMIN", "SUPER_ADMIN") and data.get("user_id"):
                try:
                    booker_id = int(data["user_id"])
                except (TypeError, ValueError):
                    return jsonify({"error": "Invalid user_id", "code": 400}), 400

            booker = conn.execute(
                "SELECT account_status FROM users WHERE user_id = ?", (booker_id,)
            ).fetchone()
            if booker is None or booker["account_status"] != "ACTIVE":
                return jsonify({"error": "Account not active", "code": 403}), 403

            slot = conn.execute(
                """SELECT s.slot_id, s.slot_number, s.control_status, s.floor_id,
                          f.floor_status, vt.type_name, vt.hourly_rate, vt.overstay_rate
                   FROM parking_slots s
                   JOIN floors f ON f.floor_id = s.floor_id
                   JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
                   WHERE s.slot_id = ?""",
                (slot_id,),
            ).fetchone()
            if slot is None:
                return jsonify({"error": "Slot not found", "code": 404}), 404
            if slot["floor_status"] not in ("OPEN",):
                return jsonify({"error": "Floor is not open for bookings", "code": 409}), 409
            if slot["control_status"] != "ACTIVE":
                return jsonify({"error": "Slot is not available for booking", "code": 409}), 409

            from_iso = from_dt.isoformat(sep=" ")
            until_iso = until_dt.isoformat(sep=" ")
            if _slot_has_overlap(conn, slot_id, from_iso, until_iso):
                return jsonify({"error": "Slot already has an overlapping booking", "code": 409}), 409
            if _active_booking_exists(conn, vehicle_number):
                return jsonify({"error": "Vehicle already has an active booking", "code": 409}), 409

            hourly_rate = float(slot["hourly_rate"])
            overstay_rate = float(slot["overstay_rate"])
            estimated = calculate_fare(hourly_rate, duration_hours)
            ref = _gen_ref("QSP")

            conn.execute(
                """INSERT INTO bookings
                   (booking_reference, user_id, slot_id, vehicle_format, vehicle_number,
                    booked_from, booked_until, hold_expires_at, hourly_rate_applied,
                    overstay_rate_applied, estimated_amount, booking_status, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now','+30 minutes'), ?, ?, ?, 'HELD', ?)""",
                (ref, booker_id, slot_id, vehicle_format, vehicle_number, from_iso,
                 until_iso, hourly_rate, overstay_rate, estimated, user_id),
            )

        return jsonify({
            "booking_reference": ref,
            "user_id": booker_id,
            "slot_id": slot_id,
            "slot_number": slot["slot_number"],
            "vehicle_type": slot["type_name"],
            "vehicle_number": vehicle_number,
            "booked_from": from_iso,
            "booked_until": until_iso,
            "duration_hours": round(duration_hours, 2),
            "hourly_rate": hourly_rate,
            "estimated_amount": estimated,
            "booking_status": "HELD",
            "message": "Slot held. Confirm within 30 minutes.",
        }), 201
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@bookings_bp.post("/<string:ref>/confirm")
def confirm(ref):
    """Confirm HELD booking: atomic wallet debit + Super Admin credit + revenue + confirm."""
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            if not _system_online(conn) and session.get("role") not in ("ADMIN", "SUPER_ADMIN"):
                return jsonify({"error": "System is OFFLINE", "code": 503}), 503
            _expire_held(conn)

            b = conn.execute(
                """SELECT b.*, u.wallet_balance FROM bookings b
                   JOIN users u ON u.user_id = b.user_id
                   WHERE b.booking_reference = ?""",
                (ref,),
            ).fetchone()
            if b is None:
                return jsonify({"error": "Booking not found", "code": 404}), 404
            if b["user_id"] != user_id and session.get("role") not in ("ADMIN", "SUPER_ADMIN"):
                return jsonify({"error": "Not authorized", "code": 403}), 403
            if b["booking_status"] != "HELD":
                return jsonify({"error": f"Booking is {b['booking_status']}, not HELD", "code": 409}), 409

            # Revalidate allocation at confirm time; the earlier availability view is not trusted.
            slot_state = conn.execute(
                """SELECT s.control_status, f.floor_status
                   FROM parking_slots s JOIN floors f ON f.floor_id = s.floor_id
                   WHERE s.slot_id = ?""",
                (b["slot_id"],),
            ).fetchone()
            if slot_state is None or slot_state["control_status"] != "ACTIVE":
                return jsonify({"error": "That slot is no longer available. Choose another slot.", "code": 409}), 409
            if slot_state["floor_status"] != "OPEN":
                return jsonify({"error": "That floor is closed. Choose another slot.", "code": 409}), 409
            if _slot_has_overlap(conn, b["slot_id"], b["booked_from"], b["booked_until"],
                                 exclude_id=b["booking_id"]):
                return jsonify({"error": "Another booking now overlaps this slot. Choose another slot.", "code": 409}), 409

            amount = float(b["estimated_amount"])
            wallet = float(b["wallet_balance"])
            if wallet < amount:
                return jsonify({
                    "error": "Insufficient wallet balance",
                    "code": 402,
                    "wallet_balance": wallet,
                    "required": amount,
                }), 402

            sa = _get_super_admin(conn)
            if sa is None:
                return jsonify({"error": "Super Admin account missing", "code": 500}), 500

            new_balance = round(wallet - amount, 2)
            conn.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, b["user_id"]))
            cust_ref = _record_wallet(conn, b["user_id"], b["booking_id"], "BOOKING_DEBIT", "DEBIT",
                                      amount, new_balance, f"Booking {ref}", user_id)

            sa_wallet = float(sa["wallet_balance"])
            sa_new = round(sa_wallet + amount, 2)
            conn.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (sa_new, sa["user_id"]))
            sa_ref = _record_wallet(conn, sa["user_id"], b["booking_id"], "SUPER_ADMIN_REVENUE_CREDIT",
                                    "CREDIT", amount, sa_new, f"Revenue {ref}", user_id)

            conn.execute(
                """INSERT INTO revenue_collections
                   (source_user_id, super_admin_user_id, booking_id,
                    customer_wallet_transaction_id, super_admin_wallet_transaction_id,
                    collection_type, amount, created_by)
                   VALUES (?, ?, ?, ?, ?, 'BOOKING_CHARGE', ?, ?)""",
                (b["user_id"], sa["user_id"], b["booking_id"],
                 conn.execute("SELECT transaction_id FROM wallet_transactions WHERE transaction_reference = ?", (cust_ref,)).fetchone()[0],
                 conn.execute("SELECT transaction_id FROM wallet_transactions WHERE transaction_reference = ?", (sa_ref,)).fetchone()[0],
                 amount, user_id),
            )

            conn.execute(
                """UPDATE bookings SET booking_status = 'CONFIRMED', updated_by = ?, updated_at = datetime('now')
                   WHERE booking_id = ?""",
                (user_id, b["booking_id"]),
            )

        return jsonify({
            "booking_reference": ref,
            "booking_status": "CONFIRMED",
            "amount_debited": amount,
            "new_wallet_balance": new_balance,
            "qr_generated": True,
            "message": "Booking confirmed. QR generated.",
        })
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@bookings_bp.get("/<string:ref>")
def get_booking(ref):
    user_id = session.get("user_id")
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            """SELECT b.*, f.floor_code, s.slot_number, vt.type_name AS vehicle_type,
                      u.full_name, u.phone
               FROM bookings b
               JOIN parking_slots s ON s.slot_id = b.slot_id
               JOIN floors f ON f.floor_id = s.floor_id
               JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
               JOIN users u ON u.user_id = b.user_id
               WHERE b.booking_reference = ?""",
            (ref,),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Booking not found", "code": 404}), 404
        d = dict(row)
        role = session.get("role")
        if user_id and d["user_id"] != user_id and role not in ("ADMIN", "SUPER_ADMIN"):
            return jsonify({"error": "Not authorized", "code": 403}), 403
        events = conn.execute(
            "SELECT event_type, scan_method, created_at FROM booking_events WHERE booking_id = ? ORDER BY created_at",
            (d["booking_id"],),
        ).fetchall()
        d["events"] = [dict(e) for e in events]
        return jsonify(d)
    finally:
        conn.close()


def _calc_refund_percent(conn, hours_before):
    """Pick active cancellation rule by inclusive/exclusive boundaries.
    Returns (rule_id, refund_percent, penalty_percent)."""
    rules = conn.execute(
        "SELECT * FROM cancellation_rules WHERE is_active = 1 ORDER BY min_hours_before DESC NULLS LAST"
    ).fetchall()
    for r in rules:
        lo = r["min_hours_before"]
        hi = r["max_hours_before"]
        if r["is_no_show"]:
            continue
        if lo is not None and hours_before >= lo and (hi is None or hours_before < hi):
            return r["rule_id"], float(r["refund_percent"]), float(r["penalty_percent"])
    return None, 0.0, 0.0


@bookings_bp.post("/<string:ref>/cancel")
def cancel(ref):
    """Cancel own booking with refund rules and revenue reversal."""
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            b = conn.execute(
                """SELECT b.*, u.wallet_balance FROM bookings b
                   JOIN users u ON u.user_id = b.user_id
                   WHERE b.booking_reference = ?""",
                (ref,),
            ).fetchone()
            if b is None:
                return jsonify({"error": "Booking not found", "code": 404}), 404
            if b["user_id"] != user_id:
                return jsonify({"error": "Not authorized", "code": 403}), 403
            if b["booking_status"] not in ("HELD", "CONFIRMED"):
                return jsonify({"error": "Only HELD or CONFIRMED bookings can be cancelled", "code": 409}), 409
            if _has_open_entry(conn, b["booking_id"]):
                return jsonify({"error": "Cannot cancel: vehicle has entered and not exited", "code": 409}), 409

            now = _now()
            from_dt = datetime.fromisoformat(b["booked_from"])
            hours_before = (from_dt - now).total_seconds() / 3600.0
            rule_id, refund_pct, penalty_pct = _calc_refund_percent(conn, hours_before)

            paid = float(b["estimated_amount"]) if b["booking_status"] == "CONFIRMED" else 0.0
            refund_amount = round(paid * refund_pct / 100, 2)
            penalty_amount = round(paid * penalty_pct / 100, 2)
            net_credit = round(refund_amount - penalty_amount, 2)

            wallet = float(b["wallet_balance"])
            new_balance = round(wallet + net_credit, 2)

            if net_credit != 0:
                conn.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, user_id))
                cust_ref = _record_wallet(conn, user_id, b["booking_id"], "CANCELLATION_REFUND",
                                          "CREDIT" if net_credit > 0 else "DEBIT",
                                          abs(net_credit), new_balance, f"Cancellation {ref}", user_id)

                sa = _get_super_admin(conn)
                if sa:
                    sa_wallet = float(sa["wallet_balance"])
                    sa_new = round(sa_wallet - net_credit, 2)
                    conn.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (sa_new, sa["user_id"]))
                    sa_ref = _record_wallet(conn, sa["user_id"], b["booking_id"], "REVENUE_REFUND_REVERSAL",
                                            "DEBIT" if net_credit > 0 else "CREDIT",
                                            abs(net_credit), sa_new, f"Refund reversal {ref}", user_id)
                    conn.execute(
                        """INSERT INTO revenue_collections
                           (source_user_id, super_admin_user_id, booking_id,
                            customer_wallet_transaction_id, super_admin_wallet_transaction_id,
                            collection_type, amount, created_by)
                           VALUES (?, ?, ?, ?, ?, 'REFUND_REVERSAL', ?, ?)""",
                        (user_id, sa["user_id"], b["booking_id"],
                         conn.execute("SELECT transaction_id FROM wallet_transactions WHERE transaction_reference = ?", (cust_ref,)).fetchone()[0],
                         conn.execute("SELECT transaction_id FROM wallet_transactions WHERE transaction_reference = ?", (sa_ref,)).fetchone()[0],
                         abs(net_credit), user_id),
                    )
            else:
                new_balance = wallet

            conn.execute(
                """UPDATE bookings SET booking_status = 'CANCELLED', applied_cancellation_rule_id = ?,
                   updated_by = ?, updated_at = datetime('now') WHERE booking_id = ?""",
                (rule_id, user_id, b["booking_id"]),
            )
            conn.execute(
                """INSERT INTO audit_logs (action_type, entity_type, entity_id, old_values, new_values, created_by)
                   VALUES ('BOOKING_CANCELLED', 'bookings', ?, ?, 'CANCELLED', ?)""",
                (b["booking_id"], b["booking_status"], user_id),
            )

        return jsonify({
            "booking_reference": ref,
            "booking_status": "CANCELLED",
            "refund_amount": refund_amount,
            "penalty_amount": penalty_amount,
            "net_credit": net_credit,
            "new_wallet_balance": new_balance,
            "message": "Booking cancelled.",
        })
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500


@bookings_bp.get("/my")
def my_bookings():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Authentication required", "code": 401}), 401
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            """SELECT b.*, f.floor_code, s.slot_number, vt.type_name AS vehicle_type,
                      EXISTS (SELECT 1 FROM booking_events e
                              WHERE e.booking_id = b.booking_id AND e.event_type = 'ENTRY'
                                AND NOT EXISTS (SELECT 1 FROM booking_events x
                                                WHERE x.booking_id = b.booking_id AND x.event_type = 'EXIT')
                      ) AS has_entered
               FROM bookings b
               JOIN parking_slots s ON s.slot_id = b.slot_id
               JOIN floors f ON f.floor_id = s.floor_id
               JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
               WHERE b.user_id = ? ORDER BY b.booked_from DESC""",
            (user_id,),
        ).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    finally:
        conn.close()


@bookings_bp.get("/wallet/transactions/me")
def my_wallet_transactions():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Authentication required", "code": 401}), 401
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            """SELECT transaction_reference, transaction_type, direction, amount,
                      balance_after, description, created_at
               FROM wallet_transactions WHERE user_id = ? ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
        w = conn.execute("SELECT wallet_balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return jsonify({"wallet_balance": float(w["wallet_balance"]) if w else 0,
                        "transactions": [dict(r) for r in rows]})
    finally:
        conn.close()
