"""Booking allocation safety: state gates, confirm-time revalidation, occupied sessions."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.services.db import get_connection

LOGIN = {"cust1": "user123", "admin1": "admin123", "superadmin": "super123"}


def login(client, username):
    return client.post("/api/auth/login", json={"username": username, "password": LOGIN[username]})


def hold(client, slot_id=1, vehicle="KA 04 A 2256",
         from_iso="2026-12-20T09:00:00", until_iso="2026-12-20T11:00:00"):
    return client.post("/api/bookings/hold", json={
        "slot_id": slot_id, "vehicle_number": vehicle, "vehicle_format": "std1",
        "booked_from": from_iso, "booked_until": until_iso,
    })


def sql(db, statement, params=()):
    conn = get_connection(db)
    try:
        cur = conn.execute(statement, params)
        conn.commit()
        return cur
    finally:
        conn.close()


def test_hold_rejected_on_inactive_floor(client, seeded_app):
    db = seeded_app.config["DATABASE_PATH"]
    sql(db, "UPDATE floors SET floor_status='INACTIVE' WHERE floor_id=1")
    login(client, "cust1")
    assert hold(client).status_code == 409


def test_hold_rejected_on_inactive_slot(client, seeded_app):
    db = seeded_app.config["DATABASE_PATH"]
    sql(db, "UPDATE parking_slots SET control_status='INACTIVE' WHERE slot_id=1")
    login(client, "cust1")
    assert hold(client).status_code == 409


def test_hold_rejected_on_admin_reserved_slot(client, seeded_app):
    db = seeded_app.config["DATABASE_PATH"]
    sql(db, "UPDATE parking_slots SET control_status='ADMIN_RESERVED' WHERE slot_id=1")
    login(client, "cust1")
    assert hold(client).status_code == 409


def test_maintenance_slot_cannot_be_booked(client, seeded_app):
    db = seeded_app.config["DATABASE_PATH"]
    sql(db, "UPDATE parking_slots SET control_status='MAINTENANCE' WHERE slot_id=2")
    login(client, "cust1")
    assert hold(client, slot_id=2).status_code == 409


def test_confirm_revalidates_slot_taken_out_of_service(client, seeded_app):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    db = seeded_app.config["DATABASE_PATH"]
    sql(db, "UPDATE parking_slots SET control_status='MAINTENANCE' WHERE slot_id=1")

    res = client.post(f"/api/bookings/{ref}/confirm")
    assert res.status_code == 409
    assert "another slot" in res.get_json()["error"]

    conn = get_connection(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM wallet_transactions").fetchone()[0] == 0
        status = conn.execute("SELECT booking_status FROM bookings WHERE booking_reference=?", (ref,)).fetchone()[0]
    finally:
        conn.close()
    assert status == "HELD"


def test_confirm_revalidates_floor_state(client, seeded_app):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    sql(seeded_app.config["DATABASE_PATH"], "UPDATE floors SET floor_status='CLOSED' WHERE floor_id=1")
    res = client.post(f"/api/bookings/{ref}/confirm")
    assert res.status_code == 409
    assert "closed" in res.get_json()["error"].lower()


def test_cannot_cancel_an_active_parking_session(client):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    assert client.post(f"/api/bookings/{ref}/confirm").status_code == 200
    login(client, "admin1")
    assert client.post("/api/qr/scan", json={"booking_reference": ref}).get_json()["action"] == "ENTRY"

    client.post("/api/auth/logout")
    login(client, "cust1")
    res = client.post(f"/api/bookings/{ref}/cancel")
    assert res.status_code == 409
    assert "entered" in res.get_json()["error"].lower()


def test_occupied_slot_cannot_be_released_by_admin(client, seeded_app):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    client.post(f"/api/bookings/{ref}/confirm")
    login(client, "admin1")
    client.post("/api/qr/scan", json={"booking_reference": ref})

    res = client.patch("/api/admin/slots/1/control-status", json={"control_status": "MAINTENANCE"})
    assert res.status_code == 409

    client.post("/api/auth/logout")
    login(client, "superadmin")
    res = client.put("/api/super-admin/slots/1", json={"control_status": "INACTIVE"})
    assert res.status_code == 409


def test_overlapping_holds_are_serialised(app, seeded_app):
    import threading

    statuses = []

    def worker(vehicle):
        with seeded_app.test_client() as c:
            login(c, "cust1")
            statuses.append(hold(c, slot_id=3, vehicle=vehicle).status_code)

    threads = [threading.Thread(target=worker, args=(v,)) for v in ("KA 01 A 1111", "KA 01 A 2222")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(statuses) == [201, 409], statuses
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    try:
        active = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE slot_id=3 AND booking_status IN ('HELD','CONFIRMED')"
        ).fetchone()[0]
    finally:
        conn.close()
    assert active == 1
