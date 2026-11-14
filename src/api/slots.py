"""Slot availability endpoints.

`control_status` is the stored state (ACTIVE / ADMIN_RESERVED / MAINTENANCE / INACTIVE).
The live `status` (AVAILABLE / RESERVED / OCCUPIED / MAINTENANCE / INACTIVE) is computed
here from bookings and booking_events and is never stored.
"""

from flask import Blueprint, jsonify, request, current_app
from src.services.db import get_connection

slots_bp = Blueprint("slots", __name__, url_prefix="/api/slots")

# Live state: an open ENTRY event (no matching EXIT) means the vehicle is inside.
_LIVE_STATUS_SQL = """
    CASE
        WHEN s.control_status = 'INACTIVE' THEN 'INACTIVE'
        WHEN s.control_status = 'MAINTENANCE' THEN 'MAINTENANCE'
        WHEN s.control_status = 'ADMIN_RESERVED' THEN 'RESERVED'
        WHEN EXISTS (
            SELECT 1 FROM bookings b
            JOIN booking_events e ON e.booking_id = b.booking_id AND e.event_type = 'ENTRY'
            WHERE b.slot_id = s.slot_id
              AND b.booking_status IN ('HELD','CONFIRMED')
              AND NOT EXISTS (SELECT 1 FROM booking_events x
                              WHERE x.booking_id = b.booking_id AND x.event_type = 'EXIT')
        ) THEN 'OCCUPIED'
        WHEN EXISTS (
            SELECT 1 FROM bookings b
            WHERE b.slot_id = s.slot_id AND b.booking_status IN ('HELD','CONFIRMED')
        ) THEN 'RESERVED'
        ELSE 'AVAILABLE'
    END
"""


@slots_bp.get("/floors")
def floors():
    """Floors with live capacity counts (used by the booking wizard)."""
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            f"""SELECT f.floor_id, f.floor_code, f.floor_status,
                       COUNT(s.slot_id) AS total_slots,
                       SUM(CASE WHEN {_LIVE_STATUS_SQL} = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_slots
                FROM floors f
                LEFT JOIN parking_slots s ON s.floor_id = f.floor_id
                WHERE f.floor_status != 'INACTIVE'
                GROUP BY f.floor_id, f.floor_code, f.floor_status
                ORDER BY f.floor_code"""
        ).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    finally:
        conn.close()


@slots_bp.get("/vehicle-types")
def vehicle_types():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            """SELECT vehicle_type_id, type_name, hourly_rate, overstay_rate, is_active
               FROM vehicle_types WHERE is_active = 1 ORDER BY vehicle_type_id"""
        ).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    finally:
        conn.close()


@slots_bp.get("/availability")
def availability():
    """Slots with live status.

    Query params: floor_id, vehicle_type_id (both optional).
    """
    floor_id = request.args.get("floor_id", type=int)
    vehicle_type_id = request.args.get("vehicle_type_id", type=int)

    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        sql = f"""
            SELECT s.slot_id, s.slot_number, s.floor_id, s.vehicle_type_id,
                   s.control_status, {_LIVE_STATUS_SQL} AS status,
                   f.floor_code, f.floor_status,
                   vt.type_name AS vehicle_type, vt.hourly_rate, vt.overstay_rate
            FROM parking_slots s
            JOIN floors f ON f.floor_id = s.floor_id
            JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
            WHERE 1=1
        """
        params = []
        if floor_id is not None:
            sql += " AND s.floor_id = ?"
            params.append(floor_id)
        if vehicle_type_id is not None:
            sql += " AND s.vehicle_type_id = ?"
            params.append(vehicle_type_id)
        sql += " ORDER BY s.floor_id, s.slot_number"

        items = []
        for r in conn.execute(sql, params).fetchall():
            item = dict(r)
            item["hourly_rate"] = float(item["hourly_rate"])
            item["overstay_rate"] = float(item["overstay_rate"])
            item["color"] = {
                "AVAILABLE": "green", "RESERVED": "amber", "OCCUPIED": "red",
                "MAINTENANCE": "grey", "INACTIVE": "grey",
            }.get(item["status"], "grey")
            items.append(item)
        return jsonify({
            "items": items,
            "floor_id": floor_id,
            "vehicle_type_id": vehicle_type_id,
            "total": len(items),
        })
    finally:
        conn.close()


@slots_bp.get("/<int:slot_id>")
def get_slot(slot_id):
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            f"""SELECT s.*, {_LIVE_STATUS_SQL} AS status,
                       f.floor_code, vt.type_name AS vehicle_type
                FROM parking_slots s
                JOIN floors f ON f.floor_id = s.floor_id
                JOIN vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
                WHERE s.slot_id = ?""",
            (slot_id,),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Slot not found", "code": 404}), 404
        return jsonify(dict(row))
    finally:
        conn.close()

