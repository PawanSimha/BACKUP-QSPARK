"""QR entry/exit flow tests: authorization, state sequence and duplicate protection."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.services.db import get_connection

LOGIN = {"cust1": "user123", "cust2": "user123", "admin1": "admin123", "superadmin": "super123"}


def login(client, username):
    return client.post("/api/auth/login", json={"username": username, "password": LOGIN[username]})


def hold(client, slot_id=1, vehicle="KA 04 A 2256",
         from_iso="2026-12-20T09:00:00", until_iso="2026-12-20T11:00:00"):
    return client.post("/api/bookings/hold", json={
        "slot_id": slot_id, "vehicle_number": vehicle, "vehicle_format": "std1",
        "booked_from": from_iso, "booked_until": until_iso,
    })


def confirmed(client):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    assert client.post(f"/api/bookings/{ref}/confirm").status_code == 200
    return ref


def events(db, ref):
    conn = get_connection(db)
    try:
        return [r["event_type"] for r in conn.execute(
            """SELECT e.event_type FROM booking_events e
               JOIN bookings b ON b.booking_id = e.booking_id
               WHERE b.booking_reference = ? ORDER BY e.event_id""", (ref,)).fetchall()]
    finally:
        conn.close()


def test_scan_requires_authentication(raw_client):
    assert raw_client.post("/api/qr/scan", json={"booking_reference": "QSP-X"}).status_code == 401


def test_unknown_reference_returns_404(client):
    login(client, "admin1")
    res = client.post("/api/qr/scan", json={"booking_reference": "QSP-DOES-NOT-EXIST"})
    assert res.status_code == 404


def test_held_booking_cannot_enter(client):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    login(client, "admin1")
    res = client.post("/api/qr/scan", json={"booking_reference": ref})
    assert res.status_code == 409
    assert "CONFIRMED" in res.get_json()["error"]


def test_cancelled_booking_cannot_enter(client):
    ref = confirmed(client)
    assert client.post(f"/api/bookings/{ref}/cancel").status_code == 200
    login(client, "admin1")
    assert client.post("/api/qr/scan", json={"booking_reference": ref}).status_code == 409


def test_expired_booking_cannot_enter(client, seeded_app):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    conn.execute("UPDATE bookings SET booking_status='EXPIRED' WHERE booking_reference=?", (ref,))
    conn.commit()
    conn.close()
    login(client, "admin1")
    assert client.post("/api/qr/scan", json={"booking_reference": ref}).status_code == 409


def test_other_customer_cannot_scan_someone_elses_booking(client, seeded_app):
    ref = confirmed(client)
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    conn.execute(
        "INSERT INTO users (full_name, phone, username, password_hash, role, wallet_balance, account_status) "
        "VALUES ('Other Customer', '9999900099', 'cust2', "
        "(SELECT password_hash FROM users WHERE username='cust1'), 'CUSTOMER', 500, 'ACTIVE')"
    )
    conn.commit()
    conn.close()
    client.post("/api/auth/logout")
    login(client, "cust2")
    assert client.post("/api/qr/scan", json={"booking_reference": ref}).status_code == 403


def test_second_scan_is_exit_then_duplicate_exit_is_rejected(client, seeded_app):
    ref = confirmed(client)
    login(client, "admin1")
    db = seeded_app.config["DATABASE_PATH"]

    first = client.post("/api/qr/scan", json={"booking_reference": ref, "scan_method": "MANUAL"})
    assert first.status_code == 200 and first.get_json()["action"] == "ENTRY"

    second = client.post("/api/qr/scan", json={"booking_reference": ref, "scan_method": "MANUAL"})
    assert second.status_code == 200 and second.get_json()["action"] == "EXIT"
    assert events(db, ref) == ["ENTRY", "EXIT"]

    conn = get_connection(db)
    tx_before = conn.execute("SELECT COUNT(*) FROM wallet_transactions").fetchone()[0]
    conn.close()

    third = client.post("/api/qr/scan", json={"booking_reference": ref, "scan_method": "MANUAL"})
    assert third.status_code == 409
    assert "already exited" in third.get_json()["error"]
    assert events(db, ref) == ["ENTRY", "EXIT"]
    conn = get_connection(db)
    assert conn.execute("SELECT COUNT(*) FROM wallet_transactions").fetchone()[0] == tx_before
    conn.close()


def test_entry_and_exit_set_slot_and_booking_state(client, seeded_app):
    ref = confirmed(client)
    login(client, "admin1")
    db = seeded_app.config["DATABASE_PATH"]
    client.post("/api/qr/scan", json={"booking_reference": ref})
    client.post("/api/qr/scan", json={"booking_reference": ref})

    conn = get_connection(db)
    booking = conn.execute(
        "SELECT booking_status, slot_id FROM bookings WHERE booking_reference=?", (ref,)
    ).fetchone()
    slot_state = conn.execute(
        "SELECT control_status FROM parking_slots WHERE slot_id=?", (booking["slot_id"],)
    ).fetchone()["control_status"]
    conn.close()
    assert booking["booking_status"] == "COMPLETED"
    assert slot_state == "ACTIVE"


def test_qr_generation_requires_confirmed_booking(client):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    assert client.post("/api/qr/generate", json={"booking_reference": ref}).status_code == 409

    assert client.post(f"/api/bookings/{ref}/confirm").status_code == 200
    res = client.post("/api/qr/generate", json={"booking_reference": ref})
    assert res.status_code == 200
    assert res.get_json()["qr_base64"]
