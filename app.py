"""QSPARK Flask application factory."""

import logging
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "src" / "templates"),
        static_folder=str(BASE_DIR / "src" / "static"),
    )

    env = os.getenv("APP_ENV", "development").lower()
    secret = os.getenv("SECRET_KEY")
    if not secret:
        if env == "production":
            raise RuntimeError("SECRET_KEY must be set when APP_ENV=production")
        secret = "dev-secret-key-not-for-production"
        app.logger.warning("SECRET_KEY missing; using a development-only key.")

    app.config["ENV_NAME"] = env
    app.config["SECRET_KEY"] = secret
    app.config["DATABASE_PATH"] = os.getenv(
        "DATABASE_PATH", str(BASE_DIR / "database" / "parking_local.db")
    )
    app.config["SESSION_TIMEOUT"] = int(os.getenv("SESSION_TIMEOUT", "3600"))
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=app.config["SESSION_TIMEOUT"])
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(1 * 1024 * 1024)))

    # Session cookie hardening. `Secure` is enabled only when asked (HTTPS deployment)
    # so plain-HTTP local development keeps working.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"

    # CSRF tokens stay valid for the whole session; the session cookie itself is what expires.
    app.config["WTF_CSRF_TIME_LIMIT"] = None
    app.config["WTF_CSRF_SSL_STRICT"] = env == "production"

    csrf = CSRFProtect(app)  # noqa: F841 - initialized for side effects

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(self), geolocation=(), microphone=()")
        return response

    @app.context_processor
    def _csrf_context():
        return {"csrf_token": generate_csrf}

    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    from src.api.auth import auth_bp
    from src.api.slots import slots_bp
    from src.api.bookings import bookings_bp
    from src.api.qr import qr_bp
    from src.api.admin import admin_bp
    from src.api.reports import reports_bp
    from src.api.super_admin import super_admin_bp
    from src.api.system import system_bp

    for bp in (auth_bp, slots_bp, bookings_bp, qr_bp, admin_bp,
               reports_bp, super_admin_bp, system_bp):
        app.register_blueprint(bp)

    with app.app_context():
        from src.services.db import init_db

        init_db(app.config["DATABASE_PATH"])

    def _current_user():
        """Fresh user record from the database, or None when not signed in."""
        uid = session.get("user_id")
        if uid is None:
            return None
        # Server-side session expiry enforcement
        import time
        now = time.time()
        created = session.get("session_created_at")
        last = session.get("last_activity_at")
        absolute_max = 20 * 60
        if created is None or now - float(created) > absolute_max:
            session.clear()
            return None
        # idle timeout from system settings (default 20 min)
        idle = 20 * 60
        try:
            from src.services.db import get_connection
            _c = get_connection(app.config["DATABASE_PATH"])
            try:
                r = _c.execute("SELECT setting_value FROM system_settings WHERE setting_key='SESSION_IDLE_TIMEOUT'").fetchone()
                if r:
                    idle = int(r["setting_value"]) * 60
            finally:
                _c.close()
        except Exception:
            pass
        if last is None or now - float(last) > idle:
            session.clear()
            return None
        session["last_activity_at"] = now
        from src.services.db import get_connection

        conn = get_connection(app.config["DATABASE_PATH"])
        try:
            row = conn.execute(
                """SELECT user_id, admin_id, full_name, email, phone, username, role,
                          wallet_balance, account_status, gender, company_name, created_at
                   FROM users WHERE user_id = ?""",
                (uid,),
            ).fetchone()
        finally:
            conn.close()
        if row is None or row["account_status"] != "ACTIVE":
            session.clear()
            return None
        user = dict(row)
        session["wallet_balance"] = float(user["wallet_balance"] or 0)
        session["role"] = user["role"]
        return user

    def _system_online():
        from src.services.db import get_connection

        conn = get_connection(app.config["DATABASE_PATH"])
        try:
            row = conn.execute(
                "SELECT setting_value FROM system_settings WHERE setting_key = 'SYSTEM_STATUS'"
            ).fetchone()
            return (row["setting_value"] if row else "ONLINE") == "ONLINE"
        finally:
            conn.close()

    def page(template, roles=None, **context):
        """Render an authenticated page, or bounce to login."""
        user = _current_user()
        if user is None:
            return redirect("/login?error=login_required")
        if roles and user["role"] not in roles:
            return render_template("error.html", user=user, code=403,
                                   message="You do not have access to this page."), 403
        return render_template(template, user=user,
                               system_online=_system_online(), **context)

    # ---------------------------------------------------------------- public
    @app.get("/health")
    def health():
        return {"status": "ok", "service": "QSPARK"}

    @app.get("/favicon.ico")
    def favicon():
        """Browsers request this root path directly; the file lives under /static."""
        return redirect("/static/images/favicon.ico")

    @app.get("/")
    def root():
        return redirect("/login" if not session.get("user_id") else "/dashboard")

    @app.get("/login")
    def login_page():
        if session.get("user_id") and _current_user():
            return redirect("/dashboard")
        return render_template("login.html", user=None, error=request.args.get("error"))

    # -------------------------------------------------------------- customer
    @app.get("/dashboard")
    def dashboard_page():
        return page("dashboard.html")

    @app.get("/booking")
    def booking_page():
        return page("booking.html")

    @app.get("/bookings/my")
    def my_bookings_page():
        return page("my_bookings.html")

    @app.get("/wallet")
    def wallet_page():
        return page("wallet.html")

    @app.get("/profile")
    def profile_page():
        return page("profile.html")

    @app.get("/confirm/<string:ref>")
    def confirm_page(ref):
        return page("confirm.html", booking_reference=ref)

    # ----------------------------------------------------------------- admin
    @app.get("/admin/dashboard")
    def admin_dashboard_page():
        return page("admin_dashboard.html", roles=("ADMIN", "SUPER_ADMIN"))

    @app.get("/admin/bookings")
    @app.get("/admin/bookings/page")
    def admin_bookings_page():
        return page("admin_bookings.html", roles=("ADMIN", "SUPER_ADMIN"))

    @app.get("/admin/customers")
    def admin_customers_page():
        return page("admin_customers.html", roles=("ADMIN", "SUPER_ADMIN"))

    @app.get("/admin/slots")
    def admin_slots_page():
        return page("admin_slots.html", roles=("ADMIN", "SUPER_ADMIN"))

    @app.get("/admin/analytics")
    def admin_analytics_page():
        return page("admin_analytics.html", roles=("ADMIN", "SUPER_ADMIN"))

    @app.get("/admin/master")
    def admin_master_page():
        return page("admin_master.html", roles=("ADMIN", "SUPER_ADMIN"))

    @app.get("/admin/qr-scan")
    def admin_qr_scan_page():
        return page("qr_scan.html", roles=("ADMIN", "SUPER_ADMIN"))

    # ----------------------------------------------------------- super admin
    @app.get("/super-admin/dashboard")
    def super_admin_dashboard_page():
        return page("super_admin_dashboard.html", roles=("SUPER_ADMIN",))

    @app.get("/super-admin/admins")
    def super_admin_admins_page():
        return page("super_admin_admins.html", roles=("SUPER_ADMIN",))

    @app.get("/super-admin/infrastructure")
    def super_admin_infrastructure_page():
        return page("super_admin_infrastructure.html", roles=("SUPER_ADMIN",))

    @app.get("/super-admin/analytics")
    def super_admin_analytics_page():
        return page("super_admin_analytics.html", roles=("SUPER_ADMIN",))

    @app.get("/super-admin/data")
    def super_admin_data_page():
        return page("super_admin_data.html", roles=("SUPER_ADMIN",))

    @app.get("/super-admin/system")
    def super_admin_system_page():
        return page("super_admin_system.html", roles=("SUPER_ADMIN",))

    # ---------------------------------------------------------------- errors
    def _wants_json():
        return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"

    @app.errorhandler(404)
    def not_found(_):
        if _wants_json():
            return jsonify({"error": "Not found", "code": 404}), 404
        return render_template("error.html", user=_current_user(), code=404,
                               message="That page does not exist."), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error on %s", request.path)
        if _wants_json():
            return jsonify({"error": "Internal server error", "code": 500}), 500
        return render_template("error.html", user=_current_user(), code=500,
                               message="Something went wrong on our side. Please retry."), 500

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        app.logger.warning("CSRF rejected: %s %s (%s)", request.method, request.path, e.description)
        if _wants_json():
            return jsonify({
                "error": "Your form session expired or the security token is missing. Reload the page and try again.",
                "code": 400,
                "csrf": True,
            }), 400
        return render_template("error.html", user=_current_user(), code=400,
                               message="Your form session expired. Reload the page and try again."), 400

    @app.errorhandler(413)
    def too_large(_):
        if _wants_json():
            return jsonify({"error": "Request payload too large", "code": 413}), 413
        return render_template("error.html", user=_current_user(), code=413,
                               message="That request was too large."), 413

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"error": str(e.description) if hasattr(e, "description") else "Conflict", "code": 409}), 409

    return app
