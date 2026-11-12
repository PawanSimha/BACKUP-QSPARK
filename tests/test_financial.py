"""Financial integrity, atomicity and concurrency tests."""

import os
import sys
import threading

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


def scalar(db, sql, params=()):
    conn = get_connection(db)
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()


def wallet(db, username):
    return scalar(db, "SELECT wallet_balance FROM users WHERE username = ?", (username,))


def assert_financial_invariants(db):
    """Ledger/revenue invariants that must hold after every financial flow."""
    conn = get_connection(db)
    try:
        negatives = conn.execute("SELECT COUNT(*) FROM users WHERE wallet_balance < 0").fetchone()[0]
        assert negatives == 0, "a wallet balance went negative"

        rows = conn.execute(
            """SELECT rc.amount, rc.collection_type, rc.booking_id,
                      c.direction AS cust_direction, c.amount AS cust_amount,
                      s.direction AS sa_direction, s.amount AS sa_amount,
                      c.transaction_id AS cust_id, s.transaction_id AS sa_id
               FROM revenue_collections rc
               JOIN wallet_transactions c ON c.transaction_id = rc.customer_wallet_transaction_id
               JOIN wallet_transactions s ON s.transaction_id = rc.super_admin_wallet_transaction_id"""
        ).fetchall()
        for r in rows:
            assert r["cust_amount"] == r["amount"] and r["sa_amount"] == r["amount"], "collection amount mismatch"
            if r["collection_type"] == "REFUND_REVERSAL":
                assert r["cust_direction"] == "CREDIT" and r["sa_direction"] == "DEBIT"
            else:
                assert r["cust_direction"] == "DEBIT" and r["sa_direction"] == "CREDIT"

        charge_count = conn.execute(
            "SELECT COUNT(*) FROM revenue_collections WHERE collection_type='BOOKING_CHARGE'"
        ).fetchone()[0]
        uncharged = conn.execute(
            """SELECT COUNT(*) FROM bookings b WHERE b.booking_status IN ('CONFIRMED','COMPLETED')
               AND NOT EXISTS (SELECT 1 FROM revenue_collections rc
                               WHERE rc.booking_id = b.booking_id AND rc.collection_type='BOOKING_CHARGE')"""
        ).fetchone()[0]
        assert uncharged == 0, "a confirmed booking has no revenue collection"
        assert charge_count >= 1

        charged = conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN collection_type='REFUND_REVERSAL' THEN -amount ELSE amount END), 0)
               FROM revenue_collections"""
        ).fetchone()[0]
        sa_wallet = conn.execute(
            "SELECT wallet_balance FROM users WHERE role='SUPER_ADMIN' LIMIT 1"
        ).fetchone()[0]
        sa_credits = conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN direction='CREDIT' THEN amount ELSE -amount END), 0)
               FROM wallet_transactions WHERE user_id = (SELECT user_id FROM users WHERE role='SUPER_ADMIN' LIMIT 1)"""
        ).fetchone()[0]
        # Collections and the Super Admin ledger movement must agree (adjustments aside).
        assert round(float(charged), 2) == round(float(sa_credits), 2), (
            f"revenue {charged} != super-admin ledger {sa_credits}"
        )
        assert isinstance(sa_wallet, (int, float))
    finally:
        conn.close()


def test_confirm_posts_balanced_entries(client, seeded_app):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    db = seeded_app.config["DATABASE_PATH"]
    sa_before = wallet(db, "superadmin")
    res = client.post(f"/api/bookings/{ref}/confirm")
    assert res.status_code == 200
    assert wallet(db, "cust1") == 990.0
    assert wallet(db, "superadmin") == round(sa_before + 10, 2)
    assert scalar(db, "SELECT COUNT(*) FROM wallet_transactions WHERE transaction_type='BOOKING_DEBIT'") == 1
    assert scalar(db, "SELECT COUNT(*) FROM revenue_collections WHERE collection_type='BOOKING_CHARGE'") == 1
    assert scalar(db, "SELECT booking_status FROM bookings WHERE booking_reference=?", (ref,)) == "CONFIRMED"
    assert_financial_invariants(db)


def test_confirm_rolls_back_when_revenue_posting_fails(client, seeded_app, monkeypatch):
    import src.api.bookings as bookings_api

    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    db = seeded_app.config["DATABASE_PATH"]
    before = wallet(db, "cust1")

    calls = {"n": 0}
    real = bookings_api._record_wallet

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:  # fail after the customer debit, while crediting the Super Admin
            raise RuntimeError("simulated database failure")
        return real(*args, **kwargs)

    monkeypatch.setattr(bookings_api, "_record_wallet", flaky)
    res = client.post(f"/api/bookings/{ref}/confirm")
    assert res.status_code == 500

    assert wallet(db, "cust1") == before, "customer debit was not rolled back"
    assert scalar(db, "SELECT COUNT(*) FROM wallet_transactions") == 0
    assert scalar(db, "SELECT COUNT(*) FROM revenue_collections") == 0
    assert scalar(db, "SELECT booking_status FROM bookings WHERE booking_reference=?", (ref,)) == "HELD"


def test_insufficient_balance_leaves_no_partial_state(client, seeded_app):
    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    conn.execute("UPDATE users SET wallet_balance = 1 WHERE username='cust1'")
    conn.commit()
    conn.close()
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]

    res = client.post(f"/api/bookings/{ref}/confirm")
    assert res.status_code == 402
    db = seeded_app.config["DATABASE_PATH"]
    assert wallet(db, "cust1") == 1.0
    assert scalar(db, "SELECT COUNT(*) FROM wallet_transactions") == 0
    assert scalar(db, "SELECT booking_status FROM bookings WHERE booking_reference=?", (ref,)) == "HELD"


def test_duplicate_confirm_charges_once(client, seeded_app):
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    assert client.post(f"/api/bookings/{ref}/confirm").status_code == 200
    assert client.post(f"/api/bookings/{ref}/confirm").status_code == 409

    db = seeded_app.config["DATABASE_PATH"]
    assert wallet(db, "cust1") == 990.0
    assert scalar(db, "SELECT COUNT(*) FROM wallet_transactions") == 2  # one debit + one credit
    assert_financial_invariants(db)


def test_overtime_is_charged_once_and_completes_booking(client, seeded_app):
    login(client, "cust1")
    ref = hold(client, from_iso="2026-12-20T09:00:00", until_iso="2026-12-20T09:30:00").get_json()["booking_reference"]
    assert client.post(f"/api/bookings/{ref}/confirm").status_code == 200

    login(client, "admin1")
    assert client.post("/api/qr/scan", json={"booking_reference": ref}).get_json()["action"] == "ENTRY"

    conn = get_connection(seeded_app.config["DATABASE_PATH"])
    conn.execute("UPDATE bookings SET booked_from=datetime('now','-5 hours'), booked_until=datetime('now','-3 hours') "
                 "WHERE booking_reference=?", (ref,))
    conn.commit()
    conn.close()

    res = client.post("/api/qr/scan", json={"booking_reference": ref})
    assert res.status_code == 200 and res.get_json()["action"] == "EXIT"
    overtime = res.get_json()["overstay_amount"]
    assert overtime > 0

    db = seeded_app.config["DATABASE_PATH"]
    before = scalar(db, "SELECT COUNT(*) FROM wallet_transactions")
    assert scalar(db, "SELECT COUNT(*) FROM revenue_collections WHERE collection_type='OVERTIME_CHARGE'") == 1
    assert scalar(db, "SELECT booking_status FROM bookings WHERE booking_reference=?", (ref,)) == "COMPLETED"
    assert scalar(db, "SELECT control_status FROM parking_slots WHERE slot_id = "
                      "(SELECT slot_id FROM bookings WHERE booking_reference=?)", (ref,)) == "ACTIVE"

    again = client.post("/api/qr/scan", json={"booking_reference": ref})
    assert again.status_code == 409
    assert scalar(db, "SELECT COUNT(*) FROM wallet_transactions") == before
    assert_financial_invariants(db)


def test_unaffordable_overtime_blocks_exit_without_charging(client, seeded_app):
    login(client, "cust1")
    ref = hold(client, from_iso="2026-12-20T09:00:00", until_iso="2026-12-20T09:30:00").get_json()["booking_reference"]
    assert client.post(f"/api/bookings/{ref}/confirm").status_code == 200
    login(client, "admin1")
    assert client.post("/api/qr/scan", json={"booking_reference": ref}).status_code == 200

    db = seeded_app.config["DATABASE_PATH"]
    conn = get_connection(db)
    conn.execute("UPDATE users SET wallet_balance=0 WHERE username='cust1'")
    conn.execute("UPDATE bookings SET booked_from=datetime('now','-5 hours'), "
                 "booked_until=datetime('now','-3 hours') WHERE booking_reference=?", (ref,))
    conn.commit()
    conn.close()
    tx_before = scalar(db, "SELECT COUNT(*) FROM wallet_transactions")

    res = client.post("/api/qr/scan", json={"booking_reference": ref})
    assert res.status_code == 409 and res.get_json()["action"] == "EXIT_BLOCKED"
    assert scalar(db, "SELECT COUNT(*) FROM wallet_transactions") == tx_before
    assert scalar(db, "SELECT booking_status FROM bookings WHERE booking_reference=?", (ref,)) == "CONFIRMED"


def test_concurrent_confirm_charges_once(app, seeded_app):
    client = seeded_app.test_client()
    login(client, "cust1")
    ref = hold(client).get_json()["booking_reference"]
    statuses = []

    def worker():
        with seeded_app.test_client() as c:
            login(c, "cust1")
            statuses.append(c.post(f"/api/bookings/{ref}/confirm").status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    db = seeded_app.config["DATABASE_PATH"]
    assert sorted(statuses) == [200, 409], statuses
    assert wallet(db, "cust1") == 990.0
    assert scalar(db, "SELECT COUNT(*) FROM revenue_collections") == 1
    assert_financial_invariants(db)


def test_concurrent_wallet_adjustments_do_not_lose_updates(app, seeded_app):
    db = seeded_app.config["DATABASE_PATH"]
    before = wallet(db, "cust1")
    amounts = [10, 20, 30]

    def worker(amount):
        with seeded_app.test_client() as c:
            login(c, "superadmin")
            r = c.post("/api/super-admin/users/1/wallet-adjustments",
                       json={"amount": amount, "description": f"concurrent {amount}"})
            assert r.status_code == 200, r.get_data(as_text=True)

    threads = [threading.Thread(target=worker, args=(a,)) for a in amounts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert wallet(db, "cust1") == round(before + sum(amounts), 2)
    assert scalar(db, "SELECT COUNT(*) FROM wallet_transactions "
                      "WHERE transaction_type='ADMIN_ADJUSTMENT'") == len(amounts)


def test_reconciliation_after_mixed_activity(client, seeded_app):
    login(client, "cust1")
    ref = hold(client, from_iso="2026-12-20T09:00:00", until_iso="2026-12-20T11:00:00").get_json()["booking_reference"]
    client.post(f"/api/bookings/{ref}/confirm")
    client.post(f"/api/bookings/{ref}/cancel")  # full refund (>24h before start)

    login(client, "superadmin")
    client.post("/api/super-admin/users/1/wallet-adjustments",
                json={"amount": 25, "description": "goodwill credit"})

    assert_financial_invariants(seeded_app.config["DATABASE_PATH"])
