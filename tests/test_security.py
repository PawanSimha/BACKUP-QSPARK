"""CSRF, session and security-header tests (CSRF enabled for this module)."""

import os
import re
import tempfile

import pytest

from app import create_app
from src.services.db import init_db
from tests.conftest import seed_base

TOKEN_RE = re.compile(r'name="csrf-token" content="([^"]+)"')


@pytest.fixture
def secure_app():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    app = create_app()
    app.config.update(
        TESTING=True,
        DATABASE_PATH=db_path,
        WTF_CSRF_ENABLED=True,
        SECRET_KEY="security-test-secret",
    )
    seed_base(db_path)
    yield app
    try:
        os.remove(db_path)
    except PermissionError:
        pass


def get_token(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    match = TOKEN_RE.search(html)
    assert match, f"no CSRF meta tag on {path}"
    return match.group(1)


def login_secure(client, username, password, landing="/dashboard"):
    """Sign in with a real CSRF token, then return the fresh token for the next page."""
    token = get_token(client)
    res = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRFToken": token},
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    return get_token(client, landing)


def test_login_without_token_is_rejected(secure_app):
    client = secure_app.test_client()
    res = client.post("/api/auth/login", json={"username": "cust1", "password": "user123"})
    assert res.status_code == 400
    assert res.get_json()["csrf"] is True


def test_login_with_invalid_token_is_rejected(secure_app):
    client = secure_app.test_client()
    res = client.post(
        "/api/auth/login",
        json={"username": "cust1", "password": "user123"},
        headers={"X-CSRFToken": "not-a-real-token"},
    )
    assert res.status_code == 400
    assert res.get_json()["csrf"] is True


def test_login_with_valid_token_works(secure_app):
    client = secure_app.test_client()
    token = login_secure(client, "cust1", "user123")
    assert token


def test_state_changing_api_requires_token(secure_app):
    client = secure_app.test_client()
    login_secure(client, "cust1", "user123")
    res = client.post("/api/bookings/hold", json={
        "slot_id": 1, "vehicle_number": "KA 04 A 2256",
        "booked_from": "2026-12-20T09:00:00", "booked_until": "2026-12-20T11:00:00",
    })
    assert res.status_code == 400 and res.get_json()["csrf"] is True


def test_state_changing_api_with_token_works(secure_app):
    client = secure_app.test_client()
    token = login_secure(client, "cust1", "user123")
    res = client.post(
        "/api/bookings/hold",
        json={
            "slot_id": 1, "vehicle_number": "KA 04 A 2256",
            "booked_from": "2026-12-20T09:00:00", "booked_until": "2026-12-20T11:00:00",
        },
        headers={"X-CSRFToken": token},
    )
    assert res.status_code == 201


def test_read_requests_do_not_need_a_token(secure_app):
    client = secure_app.test_client()
    login_secure(client, "cust1", "user123")
    assert client.get("/api/bookings/my").status_code == 200


def test_logout_form_requires_and_accepts_a_token(secure_app):
    client = secure_app.test_client()
    token = login_secure(client, "cust1", "user123")

    missing = client.post("/api/auth/logout")
    assert missing.status_code == 400

    ok = client.post("/api/auth/logout", data={"csrf_token": token})
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/login")


def test_admin_operation_with_token(secure_app):
    client = secure_app.test_client()
    token = login_secure(client, "admin1", "admin123", "/admin/dashboard")
    res = client.patch(
        "/api/admin/slots/2/control-status",
        json={"control_status": "MAINTENANCE"},
        headers={"X-CSRFToken": token},
    )
    assert res.status_code == 200


def test_super_admin_operation_with_token(secure_app):
    client = secure_app.test_client()
    token = login_secure(client, "superadmin", "super123", "/super-admin/dashboard")
    res = client.post(
        "/api/super-admin/floors",
        json={"floor_code": "C1"},
        headers={"X-CSRFToken": token},
    )
    assert res.status_code == 201


def test_login_page_issues_a_token_and_assets_are_served(secure_app):
    client = secure_app.test_client()
    html = client.get("/login").get_data(as_text=True)
    assert "cdn.tailwindcss.com" not in html
    assert "css/tailwind.css" in html
    assert TOKEN_RE.search(html)
    assert client.get("/static/css/tailwind.css").status_code == 200


def test_security_headers_are_present(secure_app):
    client = secure_app.test_client()
    res = client.get("/login")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "same-origin"
    assert "camera=(self)" in res.headers["Permissions-Policy"]


def test_production_requires_a_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app()


def test_session_cookie_flags(secure_app):
    client = secure_app.test_client()
    token = get_token(client)
    res = client.post(
        "/api/auth/login",
        json={"username": "cust1", "password": "user123"},
        headers={"X-CSRFToken": token},
    )
    cookie = res.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert secure_app.config["SESSION_COOKIE_SECURE"] is False  # local HTTP default
    assert secure_app.config["MAX_CONTENT_LENGTH"] == 1 * 1024 * 1024
    assert secure_app.config["WTF_CSRF_TIME_LIMIT"] is None
