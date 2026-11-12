"""System status control endpoints."""

from flask import Blueprint, jsonify, request, current_app, session
from src.services.db import get_connection, transaction
from src.core.security import require_role, get_current_user

system_bp = Blueprint("system", __name__, url_prefix="/api/system")


def _get_status(conn):
    row = conn.execute(
        "SELECT setting_value FROM system_settings WHERE setting_key = 'SYSTEM_STATUS'"
    ).fetchone()
    return row["setting_value"] if row else "ONLINE"


@system_bp.get("/status")
def status():
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        return jsonify({"system_status": _get_status(conn)})
    finally:
        conn.close()


@system_bp.patch("/super-admin/system/status")
@require_role("SUPER_ADMIN")
def set_status():
    data = request.get_json(silent=True) or {}
    value = (data.get("system_status") or "").upper()
    if value not in ("ONLINE", "OFFLINE"):
        return jsonify({"error": "system_status must be ONLINE or OFFLINE", "code": 400}), 400
    actor = get_current_user()
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            old = _get_status(conn)
            conn.execute(
                "UPDATE system_settings SET setting_value = ?, updated_by = ?, updated_at = datetime('now') WHERE setting_key = 'SYSTEM_STATUS'",
                (value, actor["user_id"]),
            )
            action = "SYSTEM_ONLINE" if value == "ONLINE" else "SYSTEM_OFFLINE"
            conn.execute(
                """INSERT INTO audit_logs (action_type, entity_type, old_values, new_values, created_by)
                   VALUES (?, 'system_settings', ?, ?, ?)""",
                (action, old, value, actor["user_id"]),
            )
        return jsonify({"system_status": value})
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500