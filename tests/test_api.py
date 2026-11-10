import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.ords_client import ords

USER_ID = 1004  # Harshitha M N


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def fresh_db():
    ords.reset_database()


def login(client, login_id, password):
    return client.post("/api/auth/login", json={"login_id": login_id, "password": password})


def test_login_admin_and_user(client):
    admin = login(client, "pawan.simha", "admin123")
    assert admin.status_code == 200
    assert admin.json()["user"]["role"] == "ADMIN"
    assert admin.json()["token"]

    user = login(client, "harshitha@qspark.com", "user123")
    assert user.status_code == 200
    assert user.json()["user"]["role"] == "USER"
    assert user.json()["user"]["wallet_balance"] == 500.0

    assert login(client, "pawan.simha", "wrong").status_code == 401


def test_slots_and_floor_filter(client):
    everything = client.get("/api/slots").json()["items"]
    assert len(everything) == 240

    floor_b2 = client.get("/api/slots", params={"floor_id": 2}).json()["items"]
    assert len(floor_b2) == 60
    assert {slot["floor_code"] for slot in floor_b2} == {"B2"}


def test_booking_debits_wallet(client):
    response = client.post(
        "/api/bookings",
        json={
            "user_id": USER_ID,
            "slot_id": 6,
            "vehicle_number": "KA-01-AB-1234",
            "duration_hours": 2,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["base_amount"] == 10.0
    assert body["previous_wallet_balance"] == 500.0
    assert body["new_wallet_balance"] == 490.0
    assert body["status"] == "CONFIRMED"

    token = login(client, "harshitha", "user123").json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["wallet_balance"] == 490.0

    slots = client.get("/api/slots", params={"floor_id": 1}).json()["items"]
    reserved = next(slot for slot in slots if slot["slot_id"] == 6)
    assert reserved["status"] == "RESERVED"


def test_insufficient_wallet_is_rejected(client):
    payload = {
        "user_id": USER_ID,
        "vehicle_number": "KA-05-CD-5678",
        "duration_hours": 8,
    }
    for slot_id in range(46, 52):  # 6 x car 8h = 480 of the 500 balance
        assert client.post("/api/bookings", json={**payload, "slot_id": slot_id}).status_code == 201

    rejected = client.post("/api/bookings", json={**payload, "slot_id": 52})
    assert rejected.status_code == 402
    assert "Insufficient" in rejected.json()["error"]


def test_checkout_with_overstay_penalty(client):
    created = client.post(
        "/api/bookings",
        json={
            "user_id": USER_ID,
            "slot_id": 6,
            "vehicle_number": "KA-01-AB-1234",
            "duration_hours": 2,
        },
    ).json()

    response = client.put(
        f"/api/bookings/{created['booking_id']}/checkout",
        json={"simulated_late_hours": 3.5},  # 2h window + 1.5h late
    )
    assert response.status_code == 200
    body = response.json()
    assert body["overstay_hours"] == 1.5
    assert body["penalty_charged"] == 15.0  # BIKE ₹10/hr
    assert body["final_total_amount"] == 25.0
    assert body["new_wallet_balance"] == 475.0
    assert body["status"] == "COMPLETED"


def test_cancellation_refunds_wallet(client):
    created = client.post(
        "/api/bookings",
        json={
            "user_id": USER_ID,
            "slot_id": 46,
            "vehicle_number": "KA-02-EF-9012",
            "duration_hours": 3,
        },
    ).json()
    assert created["base_amount"] == 30.0

    response = client.put(f"/api/bookings/{created['booking_id']}/cancel")
    assert response.status_code == 200
    body = response.json()
    assert body["refunded_amount"] == 30.0
    assert body["restored_wallet_balance"] == 500.0
    assert body["slot_status"] == "AVAILABLE"
    assert body["status"] == "CANCELLED"


def test_audit_track_inserts_without_audit_log(client):
    before = client.get("/api/analytics/audit").json()["items"]
    payload = {
        "admin_name": "pawan.simha",
        "modified_table": "QSPARK_USERS",
        "modified_column": "wallet_balance",
        "why_modified": "manual correction",
    }
    first = client.post("/api/admin/audit-track", json=payload)
    assert first.status_code == 201
    second = client.post("/api/admin/audit-track", json=payload)
    assert second.status_code == 201
    assert second.json()["track_id"] == first.json()["track_id"] + 1
    assert first.json()["status"] == "SAVED"

    after = client.get("/api/analytics/audit").json()["items"]
    assert len(after) == len(before)


def test_root_health_alias(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "simulation"}


def test_live_auth_falls_back_to_local_replica(tmp_path):
    from src.services.ords_client import OrdsClient

    live = OrdsClient(simulation_mode=False, db_path=tmp_path / "live.db")
    user = live.authenticate_user("harshitha@qspark.com", "user123")
    assert user["user_id"] == USER_ID
    assert live.get_user(USER_ID)["username"] == "harshitha"
    assert live.authenticate_user("harshitha@qspark.com", "wrong") is None

    def unreachable(*args, **kwargs):
        raise ConnectionError("ORDS offline")

    live._request = unreachable
    assert isinstance(live.list_bookings(USER_ID), list)


def test_live_list_bookings_normalizes_decimal_user_id(tmp_path):
    from src.services.ords_client import OrdsClient

    live = OrdsClient(simulation_mode=False, db_path=tmp_path / "bookings.db")
    live._request = lambda *args, **kwargs: {"items": [{"booking_id": 1, "user_id": 1.004}]}
    assert live.list_bookings(USER_ID)[0]["user_id"] == USER_ID
