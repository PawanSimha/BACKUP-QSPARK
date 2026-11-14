"""Authentication endpoints with real database validation."""

from flask import Blueprint, request, jsonify, session, current_app, redirect
from src.core.security import (
    authenticate_user,
    login_user,
    logout_user,
    get_current_user,
    require_login,
    require_role,
)
from src.services.db import get_connection

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    """Customer / Admin / Super Admin login.

    Supports both JSON (API) and form data (HTML form).
    Role is loaded from the database, never trusted from frontend.
    """
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        if request.is_json:
            return jsonify({"error": "Username and password required", "code": 400}), 400
        return redirect("/login?error=empty_credentials")

    user = authenticate_user(username, password)
    if user is None:
        current_app.logger.warning(
            "Authentication failed for username=%r from %s", username, request.remote_addr
        )
        if request.is_json:
            return jsonify({"error": "Invalid username/email or password", "code": 401}), 401
        return redirect("/login?error=invalid_credentials")

    login_user(user)
    current_app.logger.info("Login ok: user_id=%s role=%s", user["user_id"], user["role"])
    if request.is_json:
        return jsonify(
            {
                "user": {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "role": user["role"],
                    "wallet_balance": float(user["wallet_balance"]),
                    "phone": user.get("phone"),
                },
            }
        )
    return redirect("/booking")


@auth_bp.get("/me")
@require_login
def me():
    """Get current user details from session."""
    user = get_current_user()
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            """SELECT user_id, admin_id, full_name, email, phone, gender, company_name,
                      username, role, wallet_balance, account_status, created_at
               FROM users WHERE user_id = ?""",
            (user["user_id"],),
        ).fetchone()
        if row:
            return jsonify(dict(row))
    finally:
        conn.close()
    return jsonify(user)


@auth_bp.patch("/me")
@require_login
def update_me():
    """Self-service update of contact details only."""
    from src.services.db import transaction

    data = request.get_json(silent=True) or {}
    user = get_current_user()
    allowed = {}
    if "full_name" in data:
        full_name = (data.get("full_name") or "").strip()
        if not full_name:
            return jsonify({"error": "full_name cannot be empty", "code": 400}), 400
        allowed["full_name"] = full_name
    if "phone" in data:
        phone = (data.get("phone") or "").strip()
        if not phone.isdigit() or len(phone) != 10:
            return jsonify({"error": "phone must be 10 digits", "code": 400}), 400
        allowed["phone"] = phone
    if "gender" in data:
        gender = data.get("gender")
        if gender not in (None, "", "MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"):
            return jsonify({"error": "Invalid gender", "code": 400}), 400
        allowed["gender"] = gender or None
    if "company_name" in data:
        allowed["company_name"] = (data.get("company_name") or "").strip() or None
    if not allowed:
        return jsonify({"error": "No updatable fields", "code": 400}), 400

    fields = ", ".join(f"{col} = ?" for col in allowed)
    try:
        with transaction(current_app.config["DATABASE_PATH"]) as conn:
            conn.execute(
                f"UPDATE users SET {fields}, updated_by = ?, updated_at = datetime('now') WHERE user_id = ?",
                list(allowed.values()) + [user["user_id"], user["user_id"]],
            )
    except Exception:
        return jsonify({"error": "Could not update profile", "code": 500}), 500

    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            """SELECT user_id, admin_id, full_name, email, phone, gender, company_name,
                      username, role, wallet_balance, account_status, created_at
               FROM users WHERE user_id = ?""",
            (user["user_id"],),
        ).fetchone()
        return jsonify(dict(row))
    finally:
        conn.close()


@auth_bp.post("/logout")
@require_login
def logout():
    """Logout the current user; HTML form posts return to the sign-in page."""
    logout_user()
    if request.is_json or request.accept_mimetypes.best == "application/json":
        return jsonify({"message": "Logged out"})
    return redirect("/login")


@auth_bp.post("/setup-admin")
def setup_admin():
    """Create initial admin accounts via secure environment variables.

    This is a one-time setup endpoint. Passwords are read from env vars
    and hashed using Werkzeug. Never expose in production without
    proper security review.
    """
    import os
    from werkzeug.security import generate_password_hash

    super_admin_username = os.getenv("QSPARK_SUPER_ADMIN_USERNAME", "superadmin")
    super_admin_password = os.getenv("QSPARK_SUPER_ADMIN_PASSWORD", None)

    if not super_admin_password:
        return jsonify({"error": "Super admin password not configured", "code": 500}), 500

    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        # Check if Super Admin already exists
        existing = conn.execute(
            "SELECT user_id FROM users WHERE role = 'SUPER_ADMIN'"
        ).fetchone()
        if existing:
            return jsonify({"error": "Super Admin already exists", "code": 409}), 409

        pwd_hash = generate_password_hash(super_admin_password)

        conn.execute(
            """INSERT INTO users
               (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "SADM001",
                "Super Admin",
                f"{super_admin_username}@qspark.com",
                "9999900000",
                super_admin_username,
                pwd_hash,
                "SUPER_ADMIN",
                10000.00,
                "ACTIVE",
            ),
        )

        # Create first default admin
        conn.execute(
            """INSERT INTO users
               (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "ADM001",
                "Default Admin",
                "admin1@qspark.com",
                "9999900001",
                "admin1",
                generate_password_hash(os.getenv("QSPARK_ADMIN1_PASSWORD", "admin123")),
                "ADMIN",
                1000.00,
                "ACTIVE",
            ),
        )

        # Create second default admin
        conn.execute(
            """INSERT INTO users
               (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "ADM002",
                "Default Admin",
                "admin2@qspark.com",
                "9999900002",
                "admin2",
                generate_password_hash(os.getenv("QSPARK_ADMIN2_PASSWORD", "admin123")),
                "ADMIN",
                1000.00,
                "ACTIVE",
            ),
        )

        conn.execute("COMMIT")
        return jsonify({"message": "Initial accounts created successfully"}), 201
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return jsonify({"error": str(e), "code": 500}), 500
    finally:
        conn.close()
