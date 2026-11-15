"""QR code generation and admin scan entry/exit endpoints (events-based)."""

import qrcode
import io
import base64
import math
import uuid
from datetime import datetime
import logging
from flask import Blueprint, request, jsonify, session, current_app
from src.services.db import get_connection, transaction

qr_bp = Blueprint("qr", __name__, url_prefix="/api/qr")
logger = logging.getLogger(__name__)


def _now():
    return datetime.now().replace(microsecond=0)


def _entry_event(conn, booking_id):
    return conn.execute(
        "SELECT * FROM booking_events WHERE booking_id = ? AND event_type = 'ENTRY' ORDER BY created_at LIMIT 1",
        (booking_id,),
    ).fetchone()


def _exit_event(conn, booking_id):
    return conn.execute(
        "SELECT * FROM booking_events WHERE booking_id = ? AND event_type = 'EXIT' ORDER BY created_at LIMIT 1",
        (booking_id,),
    ).fetchone()


def _overstay(overstay_rate, booked_until_iso, exit_iso):
    end = datetime.fromisoformat(booked_until_iso)
    exit_dt = datetime.fromisoformat(exit_iso)
    delta = (exit_dt - end).total_seconds() / 3600.0
    if delta <= 0:
        return 0.0, 0.0
    hours = round(math.ceil(delta * 2) / 2, 2)
    return hours, round(hours * overstay_rate, 2)


@qr_bp.post("/generate")
def generate():
    current_app.logger.info("QR generate requested ref=%r user=%s", request.get_json(silent=True), session.get('user_id'))
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Authentication required", "code": 401}), 401
    data = request.get_json(silent=True) or {}
    ref = data.get("booking_reference")
    if not ref:
        return jsonify({"error": "booking_reference required", "code": 400}), 400

    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        b = conn.execute(
            "SELECT * FROM bookings WHERE booking_reference = ?", (ref,)
        ).fetchone()
        if b is None:
            return jsonify({"error": "Booking not found", "code": 404}), 404
        if b["user_id"] != user_id and session.get("role") not in ("ADMIN", "SUPER_ADMIN"):
            return jsonify({"error": "Not authorized", "code": 403}), 403
        if b["booking_status"] != "CONFIRMED":
            return jsonify({"error": "Booking not confirmed", "code": 409}), 409

        img = qrcode.make(ref)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        qr_b64 = base64.b64encode(buf.read()).decode("utf-8")
        current_app.logger.info("QR generated ref=%s", ref)
        return jsonify({"booking_reference": ref, "qr_base64": qr_b64, "qr_data": ref})
    finally:
        conn.close()


@qr_bp.post("/scan")
def scan():
    """First scan -> ENTRY, second scan -> EXIT (upon overtime settlement)."""
    data = request.get_json(silent=True) or {}
    ref = data.get("booking_reference")
    method = (data.get("scan_method") or "QR").upper()
    current_app.logger.info("QR scan requested ref=%r method=%s user=%s", ref, method, session.get('user_id'))
    if method not in ("QR", "MANUAL"):
        method = "QR"
    if not ref:
        return jsonify({"error": "booking_reference required", "code": 400}), 400

    scanner_id = session.get("user_id")
    scanner_role = session.get("role")
    if scanner_id is None:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            b = conn.execute(
                """SELECT b.*, s.slot_id, s.slot_number,
                          vt.overstay_rate, u.full_name, u.phone, u.wallet_balance
                   FROM bookings b
                   JOIN parking_slots s ON s.slot_id = b.slot_id
                   JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
                   JOIN users u ON u.user_id = b.user_id
                   WHERE b.booking_reference = ?""",
                (ref,),
            ).fetchone()
            if b is None:
                return jsonify({"error": "Booking not found", "code": 404}), 404

            is_owner = b["user_id"] == scanner_id
            if scanner_role not in ("ADMIN", "SUPER_ADMIN") and not is_owner:
                return jsonify({"error": "Not authorized to scan this booking", "code": 403}), 403

            entry = _entry_event(conn, b["booking_id"])
            exit_ev = _exit_event(conn, b["booking_id"])

            # --- ENTRY ---
            if entry is None:
                if b["booking_status"] != "CONFIRMED":
                    return jsonify({"error": "Booking must be CONFIRMED to enter", "code": 409}), 409
                now_iso = _now().isoformat(sep=" ")
                conn.execute(
                    """INSERT INTO booking_events (booking_id, event_type, scan_method, created_by)
                       VALUES (?, 'ENTRY', ?, ?)""",
                    (b["booking_id"], method, scanner_id),
                )
                return jsonify({
                    "action": "ENTRY",
                    "booking_reference": ref,
                    "user_name": b["full_name"],
                    "vehicle_number": b["vehicle_number"],
                    "slot_number": b["slot_number"],
                    "entry_time": now_iso,
                    "message": "Entry granted",
                })

            # --- EXIT ---
            if exit_ev is not None:
                return jsonify({"error": "Vehicle already exited", "code": 409,
                                "exit_time": exit_ev["created_at"]}), 409

            now_iso = _now().isoformat(sep=" ")
            hours, amount = _overstay(float(b["overstay_rate"]), b["booked_until"], now_iso)

            wallet = float(b["wallet_balance"]) if b["wallet_balance"] is not None else 0.0
            if amount > 0:
                if wallet < amount:
                    return jsonify({
                        "action": "EXIT_BLOCKED",
                        "booking_reference": ref,
                        "overstay_hours": hours,
                        "overstay_amount": amount,
                        "wallet_balance": wallet,
                        "message": f"Overtime due Rs {amount}. Pay to unblock exit.",
                    }), 409

                # Atomic overtime settlement
                new_wallet = round(wallet - amount, 2)
                conn.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_wallet, b["user_id"]))
                cust_ref = f"TXN-OT-{_now():%Y%m%d%H%M%S}-{b['booking_id']}-{uuid.uuid4().hex[:6].upper()}"
                conn.execute(
                    """INSERT INTO wallet_transactions
                       (transaction_reference, user_id, booking_id, transaction_type, direction, amount, balance_after, created_by)
                       VALUES (?, ?, ?, 'OVERTIME_DEBIT', 'DEBIT', ?, ?, ?)""",
                    (cust_ref, b["user_id"], b["booking_id"], amount, new_wallet, scanner_id),
                )
                cid = conn.execute("SELECT transaction_id FROM wallet_transactions WHERE transaction_reference = ?", (cust_ref,)).fetchone()[0]

                sa = conn.execute("SELECT user_id, wallet_balance FROM users WHERE role = 'SUPER_ADMIN' LIMIT 1").fetchone()
                if sa:
                    sa_wallet = float(sa["wallet_balance"])
                    sa_new = round(sa_wallet + amount, 2)
                    conn.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (sa_new, sa["user_id"]))
                    sa_ref = f"TXN-OT-SA-{_now():%Y%m%d%H%M%S}-{b['booking_id']}-{uuid.uuid4().hex[:6].upper()}"
                    conn.execute(
                        """INSERT INTO wallet_transactions
                           (transaction_reference, user_id, booking_id, transaction_type, direction, amount, balance_after, created_by)
                           VALUES (?, ?, ?, 'SUPER_ADMIN_REVENUE_CREDIT', 'CREDIT', ?, ?, ?)""",
                        (sa_ref, sa["user_id"], b["booking_id"], amount, sa_new, scanner_id),
                    )
                    sid = conn.execute("SELECT transaction_id FROM wallet_transactions WHERE transaction_reference = ?", (sa_ref,)).fetchone()[0]
                    conn.execute(
                        """INSERT INTO revenue_collections
                           (source_user_id, super_admin_user_id, booking_id, customer_wallet_transaction_id,
                            super_admin_wallet_transaction_id, collection_type, amount, created_by)
                           VALUES (?, ?, ?, ?, ?, 'OVERTIME_CHARGE', ?, ?)""",
                        (b["user_id"], sa["user_id"], b["booking_id"], cid, sid, amount, scanner_id),
                    )

            conn.execute(
                """INSERT INTO booking_events (booking_id, event_type, scan_method, event_note, created_by)
                   VALUES (?, 'EXIT', ?, ?, ?)""",
                (b["booking_id"], method, f"overstay_hours={hours}, overstay_amount={amount}", scanner_id),
            )
            conn.execute(
                "UPDATE parking_slots SET control_status = 'ACTIVE' WHERE slot_id = ?",
                (b["slot_id"],),
            )
            conn.execute(
                """UPDATE bookings SET booking_status = 'COMPLETED', updated_by = ?, updated_at = datetime('now')
                   WHERE booking_id = ?""",
                (scanner_id, b["booking_id"]),
            )

        return jsonify({
            "action": "EXIT",
            "booking_reference": ref,
            "user_name": b["full_name"],
            "vehicle_number": b["vehicle_number"],
            "slot_number": b["slot_number"],
            "exit_time": now_iso,
            "overstay_hours": hours,
            "overstay_amount": amount,
            "message": "Exit granted",
        })
    except Exception as e:
        current_app.logger.exception("QR scan failed ref=%r: %s", ref, e)
        return jsonify({"error": str(e), "code": 500}), 500
