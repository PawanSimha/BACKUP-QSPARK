"""Comprehensive tests for the QSPARK 11-table schema."""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from werkzeug.security import generate_password_hash
from src.services.db import get_connection
from tests.conftest import seed_base


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def hold(client, slot_id=1, vehicle="KA 04 A 2256", fmt="std1",
         from_iso="2026-12-20T09:00:00", until_iso="2026-12-20T11:00:00"):
    return client.post("/api/bookings/hold", json={
        "slot_id": slot_id, "vehicle_number": vehicle, "vehicle_format": fmt,
        "booked_from": from_iso, "booked_until": until_iso,
    })


def test_customer_login(client):
    r = login(client, "cust1", "user123")
    assert r.status_code == 200 and r.get_json()["user"]["role"] == "CUSTOMER"


def test_admin_login(client):
    r = login(client, "admin1", "admin123")
    assert r.status_code == 200 and r.get_json()["user"]["role"] == "ADMIN"


def test_super_admin_login(client):
    r = login(client, "superadmin", "super123")
    assert r.status_code == 200 and r.get_json()["user"]["role"] == "SUPER_ADMIN"


def test_customer_cannot_access_admin(client):
    login(client, "cust1", "user123")
    assert client.get("/api/admin/dashboard").status_code == 403


def test_admin_cannot_access_super_admin(client):
    login(client, "admin1", "admin123")
    assert client.get("/api/super-admin/admins").status_code == 403


def test_invalid_login(client):
    assert login(client, "cust1", "wrong").status_code == 401


def test_me_requires_session(raw_client):
    assert raw_client.get("/api/auth/me").status_code == 401


def test_slot_availability(client):
    r = client.get("/api/slots/availability?floor_id=1&vehicle_type_id=1")
    assert r.status_code == 200 and r.get_json()["total"] == 3


def test_hold_success(client):
    login(client, "cust1", "user123")
    r = hold(client)
    assert r.status_code == 201
    assert r.get_json()["booking_status"] == "HELD"
    assert r.get_json()["estimated_amount"] == 10.0


def test_double_booking_rejected(client):
    login(client, "cust1", "user123")
    assert hold(client).status_code == 201
    assert hold(client, slot_id=1, vehicle="DL 03 CA 1234").status_code == 409


def test_duplicate_vehicle_rejected(client):
    login(client, "cust1", "user123")
    assert hold(client, slot_id=1, vehicle="KA 04 A 2256").status_code == 201
    r2 = hold(client, slot_id=2, vehicle="KA 04 A 2256",
              from_iso="2026-12-20T10:00:00", until_iso="2026-12-20T12:00:00")
    assert r2.status_code == 409


def test_hold_on_maintenance_slot_rejected(client, seeded_app):
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    conn.execute("UPDATE parking_slots SET control_status='MAINTENANCE' WHERE slot_id=1")
    conn.commit(); conn.close()
    login(client, "cust1", "user123")
    assert hold(client).status_code == 409


def test_confirm_creates_wallet_and_revenue(client, seeded_app):
    login(client, "cust1", "user123")
    ref = hold(client).get_json()["booking_reference"]
    r = client.post(f"/api/bookings/{ref}/confirm")
    assert r.status_code == 200
    assert r.get_json()["new_wallet_balance"] == 990.0
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    tx = conn.execute("SELECT transaction_type, direction FROM wallet_transactions").fetchall()
    types = {(t["transaction_type"], t["direction"]) for t in tx}
    assert ("BOOKING_DEBIT", "DEBIT") in types
    assert ("SUPER_ADMIN_REVENUE_CREDIT", "CREDIT") in types
    rc = conn.execute("SELECT COUNT(*) FROM revenue_collections WHERE collection_type='BOOKING_CHARGE'").fetchone()[0]
    conn.close()
    assert rc == 1


def test_insufficient_wallet_blocks_confirm(client, seeded_app):
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    conn.execute("UPDATE users SET wallet_balance = 1 WHERE username='cust1'")
    conn.commit(); conn.close()
    login(client, "cust1", "user123")
    ref = hold(client).get_json()["booking_reference"]
    assert client.post(f"/api/bookings/{ref}/confirm").status_code == 402


def test_wallet_cannot_go_negative_via_adjustment(client):
    login(client, "admin1", "admin123")
    assert client.post("/api/admin/users/1/wallet-adjustments", json={"amount": -5000}).status_code == 400


def test_cancel_refund_more_24h(client, seeded_app):
    login(client, "cust1", "user123")
    ref = hold(client, from_iso="2026-12-25T10:00:00", until_iso="2026-12-25T12:00:00").get_json()["booking_reference"]
    client.post(f"/api/bookings/{ref}/confirm")
    r = client.post(f"/api/bookings/{ref}/cancel")
    assert r.status_code == 200
    data = r.get_json()
    assert data["booking_status"] == "CANCELLED"
    assert data["refund_amount"] == 10.0
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    rr = conn.execute("SELECT COUNT(*) FROM revenue_collections WHERE collection_type='REFUND_REVERSAL'").fetchone()[0]
    conn.close()
    assert rr == 1


def test_customer_sees_only_own_bookings(client):
    login(client, "cust1", "user123")
    hold(client)
    r = client.get("/api/bookings/my")
    assert r.status_code == 200
    assert all(i["user_id"] == 1 for i in r.get_json()["items"])


def _confirmed(client):
    ref = hold(client).get_json()["booking_reference"]
    client.post(f"/api/bookings/{ref}/confirm")
    return ref


def test_qr_entry(client):
    login(client, "cust1", "user123")
    ref = _confirmed(client)
    login(client, "admin1", "admin123")
    r = client.post("/api/qr/scan", json={"booking_reference": ref})
    assert r.status_code == 200 and r.get_json()["action"] == "ENTRY"


def test_exit_completes_booking(client, seeded_app):
    login(client, "cust1", "user123")
    ref = _confirmed(client)
    login(client, "admin1", "admin123")
    client.post("/api/qr/scan", json={"booking_reference": ref})
    r = client.post("/api/qr/scan", json={"booking_reference": ref})
    assert r.status_code == 200 and r.get_json()["action"] == "EXIT"
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    st = conn.execute("SELECT booking_status FROM bookings WHERE booking_reference=?", (ref,)).fetchone()["booking_status"]
    events = [e["event_type"] for e in conn.execute("SELECT event_type FROM booking_events ORDER BY event_id").fetchall()]
    conn.close()
    assert st == "COMPLETED"
    assert events == ["ENTRY", "EXIT"]


def test_overtime_blocks_exit_when_unaffordable(client, seeded_app):
    login(client, "cust1", "user123")
    ref = hold(client, from_iso="2026-12-20T09:00:00", until_iso="2026-12-20T09:30:00").get_json()["booking_reference"]
    client.post(f"/api/bookings/{ref}/confirm")
    login(client, "admin1", "admin123")
    client.post("/api/qr/scan", json={"booking_reference": ref})
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    conn.execute("UPDATE users SET wallet_balance=0.01 WHERE username='cust1'")
    conn.execute("UPDATE bookings SET booked_from=datetime('now','-5 hours'), booked_until=datetime('now','-3 hours') WHERE booking_reference=?", (ref,))
    conn.commit(); conn.close()
    r = client.post("/api/qr/scan", json={"booking_reference": ref})
    assert r.status_code == 409
    assert r.get_json()["action"] == "EXIT_BLOCKED"


def test_admin_cannot_maintain_booked_slot(client):
    login(client, "cust1", "user123")
    hold(client, slot_id=1)
    login(client, "admin1", "admin123")
    assert client.patch("/api/admin/slots/1/control-status", json={"control_status": "MAINTENANCE"}).status_code == 409


def test_admin_can_maintain_free_slot(client):
    login(client, "admin1", "admin123")
    assert client.patch("/api/admin/slots/2/control-status", json={"control_status": "MAINTENANCE"}).status_code == 200


def test_super_admin_creates_admin(client):
    login(client, "superadmin", "super123")
    r = client.post("/api/super-admin/admins", json={
        "full_name": "New Admin", "phone": "9999912345", "email": "newadmin@qspark.com",
        "username": "newadmin", "password": "Password123",
    })
    assert r.status_code == 201
    assert r.get_json()["admin_id"].startswith("ADM")


def test_super_admin_block_unblock_admin(client):
    login(client, "superadmin", "super123")
    assert client.patch("/api/super-admin/admins/2/status", json={"account_status": "BLOCKED"}).status_code == 200
    assert client.patch("/api/super-admin/admins/2/status", json={"account_status": "ACTIVE"}).status_code == 200


def test_admin_registers_walkin_customer(client):
    login(client, "admin1", "admin123")
    r = client.post("/api/admin/users", json={
        "full_name": "Walk In", "phone": "9999988888", "gender": "MALE", "company_name": "X",
    })
    assert r.status_code == 201


def test_admin_cannot_create_admin_account(client):
    login(client, "admin1", "admin123")
    r = client.post("/api/super-admin/admins", json={
        "full_name": "X", "phone": "1", "username": "x", "password": "Password123",
    })
    assert r.status_code == 403


def test_super_admin_cannot_cancel_entered_booking(client):
    login(client, "cust1", "user123")
    ref = _confirmed(client)
    login(client, "admin1", "admin123")
    client.post("/api/qr/scan", json={"booking_reference": ref})
    login(client, "superadmin", "super123")
    assert client.post(f"/api/super-admin/bookings/{ref}/cancel").status_code == 409


def test_super_admin_cancels_future_booking(client):
    login(client, "cust1", "user123")
    ref = _confirmed(client)
    login(client, "superadmin", "super123")
    r = client.post(f"/api/super-admin/bookings/{ref}/cancel")
    assert r.status_code == 200 and r.get_json()["booking_status"] == "CANCELLED"


def test_floor_deactivation_blocked_with_active_booking(client):
    login(client, "cust1", "user123")
    hold(client, slot_id=1)
    login(client, "superadmin", "super123")
    assert client.delete("/api/super-admin/floors/1").status_code == 409


def test_super_admin_can_view_whitelisted_tables(client):
    login(client, "superadmin", "super123")
    r = client.get("/api/super-admin/db-tables/users")
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert items and "password_hash" not in items[0]


def test_db_table_rejects_unknown_table(client):
    login(client, "superadmin", "super123")
    assert client.get("/api/super-admin/db-tables/sqlite_master").status_code == 403


def test_system_offline_blocks_customer_booking(client):
    login(client, "superadmin", "super123")
    assert client.patch("/api/system/super-admin/system/status", json={"system_status": "OFFLINE"}).status_code == 200
    login(client, "cust1", "user123")
    assert hold(client).status_code == 503
    login(client, "superadmin", "super123")
    assert client.patch("/api/system/super-admin/system/status", json={"system_status": "ONLINE"}).status_code == 200


def test_admin_wallet_adjustment_creates_records(client, seeded_app):
    login(client, "admin1", "admin123")
    assert client.post("/api/admin/users/1/wallet-adjustments", json={"amount": 100}).status_code == 200
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    t = conn.execute("SELECT COUNT(*) FROM wallet_transactions WHERE transaction_type='ADMIN_ADJUSTMENT'").fetchone()[0]
    a = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action_type='WALLET_ADJUSTMENT'").fetchone()[0]
    conn.close()
    assert t >= 1 and a >= 1


def test_super_admin_wallet_adjustment(client, seeded_app):
    login(client, "superadmin", "super123")
    assert client.post("/api/super-admin/users/2/wallet-adjustments", json={"amount": 50}).status_code == 200
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    a = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action_type='WALLET_ADJUSTMENT'").fetchone()[0]
    conn.close()
    assert a >= 1


def test_csv_reports(client):
    login(client, "superadmin", "super123")
    r1 = client.get("/api/admin/reports/occupancy-csv")
    r2 = client.get("/api/admin/reports/revenue-csv")
    assert r1.status_code == 200 and r1.mimetype == "text/csv"
    assert r2.status_code == 200 and r2.mimetype == "text/csv"


def test_exactly_11_tables(app):
    conn = get_connection(app.config["DATABASE_PATH"])
    names = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()}
    conn.close()
    expected = {"users", "floors", "vehicle_types", "parking_slots", "bookings",
                "cancellation_rules", "wallet_transactions", "booking_events",
                "audit_logs", "revenue_collections", "system_settings"}
    assert expected == names


def test_six_mandatory_columns_order(app):
    conn = get_connection(app.config["DATABASE_PATH"])
    for t in ["users", "floors", "vehicle_types", "parking_slots", "bookings",
              "cancellation_rules", "wallet_transactions", "booking_events",
              "audit_logs", "revenue_collections", "system_settings"]:
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
        assert cols[-6:] == ["created_by", "created_at", "updated_by", "updated_at", "reserved1", "reserved2"], t
    conn.close()


def test_concurrent_double_booking(app, seeded_app):
    results = []

    def worker(vehicle):
        with app.test_client() as c:
            c.post("/api/auth/login", json={"username": "cust1", "password": "user123"})
            r = c.post("/api/bookings/hold", json={
                "slot_id": 3, "vehicle_number": vehicle, "vehicle_format": "std1",
                "booked_from": "2026-12-21T09:00:00", "booked_until": "2026-12-21T11:00:00",
            })
            results.append(r.status_code)

    t1 = threading.Thread(target=worker, args=("KA 01 A 1111",))
    t2 = threading.Thread(target=worker, args=("KA 01 A 2222",))
    t1.start(); t2.start(); t1.join(); t2.join()
    assert results.count(201) == 1
    assert results.count(409) == 1