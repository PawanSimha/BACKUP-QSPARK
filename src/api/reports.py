"""Report endpoints: occupancy heat-map and revenue per floor."""

from flask import Blueprint, request, jsonify, session, current_app
from src.services.db import get_connection
from src.core.security import require_admin, require_role
from src.api.slots import _LIVE_STATUS_SQL

reports_bp = Blueprint("reports", __name__, url_prefix="/api/admin/reports")


@reports_bp.get("/occupancy")
@require_admin
def occupancy():
    """Occupancy heat-map per floor per hour, date-range filterable."""
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        sql = f"""
            SELECT f.floor_code,
                   f.floor_status,
                   COUNT(s.slot_id) AS total_slots,
                   SUM(CASE WHEN {_LIVE_STATUS_SQL} IN ('RESERVED','OCCUPIED') THEN 1 ELSE 0 END) AS occupied_slots
            FROM floors f
            LEFT JOIN parking_slots s ON s.floor_id = f.floor_id
            WHERE 1=1
        """
        params = []
        if date_from:
            sql += " AND EXISTS (SELECT 1 FROM bookings b WHERE b.slot_id = s.slot_id AND DATE(b.booked_from) >= ?)"
            params.append(date_from)
        if date_to:
            sql += " AND EXISTS (SELECT 1 FROM bookings b WHERE b.slot_id = s.slot_id AND DATE(b.booked_from) <= ?)"
            params.append(date_to)
        sql += " GROUP BY f.floor_id, f.floor_code ORDER BY f.floor_code"

        rows = conn.execute(sql, params).fetchall()
        heatmaps = []
        for r in rows:
            total = int(r["total_slots"]) if r["total_slots"] else 0
            occupied = int(r["occupied_slots"]) if r["occupied_slots"] else 0
            heatmaps.append(
                {
                    "floor_code": r["floor_code"],
                    "floor_status": r["floor_status"],
                    "total_slots": total,
                    "occupied_slots": occupied,
                    "occupancy_percent": round(100 * occupied / total, 2) if total else 0.0,
                }
            )

        return jsonify({"floor_heatmaps": heatmaps, "date_from": date_from, "date_to": date_to})
    finally:
        conn.close()


@reports_bp.get("/revenue")
@require_admin
def revenue():
    """Revenue per floor, date-range filterable."""
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        sql = """
            SELECT f.floor_code,
                   COUNT(DISTINCT b.booking_id) AS booking_count,
                   COALESCE(SUM(rc.amount), 0) AS total_revenue,
                   COALESCE(SUM(CASE WHEN rc.collection_type = 'REFUND_REVERSAL' THEN -rc.amount ELSE rc.amount END), 0) AS net_revenue
            FROM revenue_collections rc
            JOIN bookings b ON b.booking_id = rc.booking_id
            JOIN parking_slots s ON s.slot_id = b.slot_id
            JOIN floors f ON f.floor_id = s.floor_id
            WHERE 1=1
        """
        params = []
        if date_from:
            sql += " AND DATE(rc.created_at) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND DATE(rc.created_at) <= ?"
            params.append(date_to)
        sql += " GROUP BY f.floor_id, f.floor_code ORDER BY f.floor_code"

        rows = conn.execute(sql, params).fetchall()
        results = []
        grand_total = 0.0
        for r in rows:
            total = round(float(r["total_revenue"]), 2)
            grand_total += total
            results.append(
                {
                    "floor_code": r["floor_code"],
                    "booking_count": int(r["booking_count"]),
                    "total_revenue": total,
                    "net_revenue": round(float(r["net_revenue"]), 2),
                }
            )

        return jsonify(
            {
                "floor_revenue": results,
                "grand_total": round(grand_total, 2),
                "date_from": date_from,
                "date_to": date_to,
            }
        )
    finally:
        conn.close()


@reports_bp.get("/revenue-summary")
@require_role("SUPER_ADMIN")
def revenue_summary():
    """Super Admin revenue summary with overhead filtering."""
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        sql = """
            SELECT rc.collection_type,
                   COUNT(rc.collection_id) AS count,
                   COALESCE(SUM(rc.amount), 0) AS total_amount
            FROM revenue_collections rc
            WHERE 1=1
        """
        params = []
        if date_from:
            sql += " AND DATE(rc.created_at) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND DATE(rc.created_at) <= ?"
            params.append(date_to)
        sql += " GROUP BY rc.collection_type"

        rows = conn.execute(sql, params).fetchall()
        results = []
        for r in rows:
            results.append(
                {
                    "collection_type": r["collection_type"],
                    "count": int(r["count"]),
                    "total_amount": round(float(r["total_amount"]), 2),
                }
            )

        return jsonify({"revenue_summary": results})
    finally:
        conn.close()


@reports_bp.get("/occupancy-csv")
@require_role("SUPER_ADMIN")
def occupancy_csv():
    """Download occupancy report as CSV."""
    import csv
    import io
    from flask import make_response

    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        sql = f"""
            SELECT f.floor_code,
                   COUNT(s.slot_id) AS total_slots,
                   SUM(CASE WHEN {_LIVE_STATUS_SQL} IN ('RESERVED','OCCUPIED') THEN 1 ELSE 0 END) AS occupied_slots,
                   ROUND(100.0 * SUM(CASE WHEN {_LIVE_STATUS_SQL} IN ('RESERVED','OCCUPIED') THEN 1 ELSE 0 END) / COUNT(s.slot_id), 2) AS occupancy_percent
            FROM floors f
            LEFT JOIN parking_slots s ON s.floor_id = f.floor_id
            WHERE 1=1
        """
        params = []
        if date_from:
            sql += " AND EXISTS (SELECT 1 FROM bookings b WHERE b.slot_id = s.slot_id AND DATE(b.booked_from) >= ?)"
            params.append(date_from)
        if date_to:
            sql += " AND EXISTS (SELECT 1 FROM bookings b WHERE b.slot_id = s.slot_id AND DATE(b.booked_from) <= ?)"
            params.append(date_to)
        sql += " GROUP BY f.floor_id ORDER BY f.floor_code"

        rows = conn.execute(sql, params).fetchall()

        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(["floor_code", "total_slots", "occupied_slots", "occupancy_percent"])
        for r in rows:
            writer.writerow([r["floor_code"], r["total_slots"], r["occupied_slots"], r["occupancy_percent"]])

        output = si.getvalue()
        response = make_response(output)
        response.mimetype = "text/csv"
        response.headers[
            "Content-Disposition"
        ] = f'attachment; filename="occupancy_report_{date_from}_{date_to}.csv"'
        return response
    finally:
        conn.close()


@reports_bp.get("/revenue-csv")
@require_role("SUPER_ADMIN")
def revenue_csv():
    """Download revenue report as CSV."""
    import csv
    import io
    from flask import make_response

    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        sql = """
            SELECT f.floor_code,
                   rc.collection_type,
                   COUNT(rc.collection_id) AS count,
                   SUM(rc.amount) AS total_amount
            FROM revenue_collections rc
            JOIN bookings b ON rc.booking_id = b.booking_id
            JOIN parking_slots s ON s.slot_id = b.slot_id
            JOIN floors f ON f.floor_id = s.floor_id
            WHERE 1=1
        """
        params = []
        if date_from:
            sql += " AND DATE(rc.created_at) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND DATE(rc.created_at) <= ?"
            params.append(date_to)
        sql += " GROUP BY f.floor_code, rc.collection_type ORDER BY f.floor_code, rc.collection_type"

        rows = conn.execute(sql, params).fetchall()

        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(["floor_code", "collection_type", "count", "total_amount"])
        for r in rows:
            writer.writerow([r["floor_code"], r["collection_type"], r["count"], r["total_amount"]])

        output = si.getvalue()
        response = make_response(output)
        response.mimetype = "text/csv"
        response.headers[
            "Content-Disposition"
        ] = f'attachment; filename="revenue_report_{date_from}_{date_to}.csv"'
        return response
    finally:
        conn.close()
