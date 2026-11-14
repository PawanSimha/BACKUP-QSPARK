"""Security helpers: password hashing, session auth, role guards."""

from functools import wraps
from flask import session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from src.services.db import get_connection


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using Werkzeug (PBKDF2-SHA256)."""
    return generate_password_hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain-text password against a stored hash."""
    return check_password_hash(password_hash, plain_password)


def generate_user_password(full_name: str, phone: str) -> str:
    """Prototype credential rule: <first-4-chars-of-name>@<last-4-chars-of-phone>."""
    name_part = (full_name or "").strip().split()[0][:4].upper() if (full_name or "").strip() else "USER"
    tail = (phone or "").strip()[-4:]
    return f"{name_part}@{tail}"


def get_current_user():
    """Return the current user dict from session, or None if not logged in."""
    if "user_id" not in session:
        return None
    return {
        "user_id": session["user_id"],
        "username": session.get("username"),
        "email": session.get("email"),
        "full_name": session.get("full_name"),
        "role": session.get("role"),
        "wallet_balance": session.get("wallet_balance"),
    }


def require_login(view_func):
    """Decorator: require authenticated user. Returns 401 if not logged in."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if get_current_user() is None:
            return jsonify({"error": "Authentication required", "code": 401}), 401
        return view_func(*args, **kwargs)

    return wrapper


def require_role(*allowed_roles):
    """Decorator: require specific role(s). Returns 403 if role mismatch.

    Usage: @require_role('ADMIN', 'SUPER_ADMIN')
    Usage: @require_role('CUSTOMER')
    Usage: @require_role('SUPER_ADMIN')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return jsonify({"error": "Authentication required", "code": 401}), 401
            if user["role"] not in allowed_roles:
                return jsonify(
                    {"error": "Role privileges required", "code": 403}
                ), 403
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def require_admin(view_func):
    """Decorator: require ADMIN or SUPER_ADMIN role."""
    return require_role("ADMIN", "SUPER_ADMIN")(view_func)


def login_user(user_row) -> None:
    """Store user data in Flask session after successful login."""
    session.clear()
    session["user_id"] = user_row["user_id"]
    session["username"] = user_row["username"]
    session["email"] = user_row["email"]
    session["full_name"] = user_row["full_name"]
    session["role"] = user_row["role"]
    session["wallet_balance"] = float(user_row["wallet_balance"])
    session.permanent = True


def logout_user() -> None:
    """Clear the Flask session."""
    session.clear()


def authenticate_user(username: str, plain_password: str):
    """Authenticate a user by username/email and password. Returns user row or None."""
    conn = get_connection(current_app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            """SELECT * FROM users
               WHERE (LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?))
                 AND account_status = 'ACTIVE'""",
            (username, username),
        ).fetchone()
        if row is None:
            return None
        if not row["password_hash"]:
            return None
        if not verify_password(plain_password, row["password_hash"]):
            return None
        return dict(row)
    finally:
        conn.close()
