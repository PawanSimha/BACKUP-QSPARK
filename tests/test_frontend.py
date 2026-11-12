"""Frontend integration tests: page rendering and the endpoints the pages call."""

import pytest

CUSTOMER_PAGES = ["/dashboard", "/booking", "/bookings/my", "/wallet", "/profile"]
ADMIN_PAGES = [
    "/admin/dashboard", "/admin/bookings", "/admin/customers",
    "/admin/slots", "/admin/analytics", "/admin/master", "/admin/qr-scan",
]
SUPER_PAGES = [
    "/super-admin/dashboard", "/super-admin/admins", "/super-admin/infrastructure",
    "/super-admin/analytics", "/super-admin/data", "/super-admin/system",
]


def login(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.get_data(as_text=True)
    return res.get_json()


@pytest.fixture
def customer(client):
    login(client, "cust1", "user123")
    return client


@pytest.fixture
def admin(client):
    login(client, "admin1", "admin123")
    return client


@pytest.fixture
def superadmin(client):
    login(client, "superadmin", "super123")
    return client


@pytest.mark.parametrize("path", CUSTOMER_PAGES)
def test_customer_pages_render(customer, path):
    res = customer.get(path)
    assert res.status_code == 200
    assert b'alt="QSPARK"' in res.data


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_admin_pages_render(admin, path):
    res = admin.get(path)
    assert res.status_code == 200


@pytest.mark.parametrize("path", SUPER_PAGES)
def test_super_admin_pages_render(superadmin, path):
    res = superadmin.get(path)
    assert res.status_code == 200


def test_anonymous_pages_redirect_to_login(raw_client):
    for path in CUSTOMER_PAGES + ADMIN_PAGES + SUPER_PAGES:
        res = raw_client.get(path)
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]


def test_customer_cannot_open_admin_page(customer):
    assert customer.get("/admin/dashboard").status_code == 403


def test_admin_cannot_open_super_admin_page(admin):
    assert admin.get("/super-admin/system").status_code == 403


def test_login_page_and_static_assets(raw_client):
    res = raw_client.get("/login")
    assert res.status_code == 200
    assert b"Sign in" in res.data
    for asset in ("/static/css/app.css", "/static/js/core/api.js", "/static/js/core/ui.js"):
        assert raw_client.get(asset).status_code == 200


def test_unknown_page_returns_html_404(raw_client):
    res = raw_client.get("/does-not-exist")
    assert res.status_code == 404
    assert b"Page not found" in res.data


def test_profile_update_validates_and_persists(customer):
    bad = customer.patch("/api/auth/me", json={"phone": "123"})
    assert bad.status_code == 400
    ok = customer.patch("/api/auth/me", json={"full_name": "Test Customer", "phone": "9999900001"})
    assert ok.status_code == 200
    assert ok.get_json()["phone"] == "9999900001"


def test_admin_master_endpoints(admin):
    floors = admin.get("/api/admin/floors").get_json()
    types = admin.get("/api/admin/vehicle-types").get_json()
    slots = admin.get("/api/admin/slots?floor_id=1").get_json()
    assert floors["items"][0]["total_slots"] == 4
    assert {t["type_name"] for t in types["items"]} == {"BIKE", "CAR"}
    assert len(slots["items"]) == 4
    assert all(s["status"] == "AVAILABLE" for s in slots["items"])


def test_reports_occupancy_matches_live_state(admin):
    data = admin.get("/api/admin/reports/occupancy").get_json()
    for floor in data["floor_heatmaps"]:
        assert 0 <= floor["occupied_slots"] <= floor["total_slots"]
        assert floor["occupied_slots"] == 0


def test_super_admin_analytics_overview(superadmin):
    data = superadmin.get("/api/super-admin/analytics/overview").get_json()
    assert data["total_slots"] == 4
    assert data["occupied_slots"] == 0
    assert data["occupancy_percent"] == 0


def test_super_admin_db_table_hides_password_hash(superadmin):
    data = superadmin.get("/api/super-admin/db-tables/users").get_json()
    assert data["items"]
    assert all("password_hash" not in row for row in data["items"])


def test_super_admin_db_table_rejects_unknown_table(superadmin):
    assert superadmin.get("/api/super-admin/db-tables/sqlite_master").status_code == 403


def test_super_admin_floor_and_slot_crud(superadmin):
    created = superadmin.post("/api/super-admin/floors", json={"floor_code": "B2"})
    assert created.status_code == 201
    floor_id = created.get_json()["floor_id"]

    slot = superadmin.post(
        f"/api/super-admin/floors/{floor_id}/slots",
        json={"slot_number": "B2-01", "vehicle_type_id": 1},
    )
    assert slot.status_code == 201
    slot_id = slot.get_json()["slot_id"]

    patched = superadmin.put(f"/api/super-admin/slots/{slot_id}", json={"control_status": "MAINTENANCE"})
    assert patched.status_code == 200

    removed = superadmin.delete(f"/api/super-admin/slots/{slot_id}")
    assert removed.status_code == 200
    assert superadmin.delete(f"/api/super-admin/floors/{floor_id}").status_code == 200


def test_super_admin_system_toggle(superadmin):
    assert superadmin.patch("/api/system/super-admin/system/status",
                            json={"system_status": "OFFLINE"}).get_json()["system_status"] == "OFFLINE"
    assert superadmin.get("/api/system/status").get_json()["system_status"] == "OFFLINE"
    assert superadmin.patch("/api/system/super-admin/system/status",
                            json={"system_status": "ONLINE"}).status_code == 200
    assert superadmin.patch("/api/system/super-admin/system/status",
                            json={"system_status": "PAUSED"}).status_code == 400


def test_super_admin_report_downloads(superadmin):
    for path in ("/api/super-admin/reports/occupancy.csv", "/api/super-admin/reports/revenue.csv"):
        res = superadmin.get(path)
        assert res.status_code == 200
        assert res.mimetype == "text/csv"
        assert b"floor_code" in res.data
