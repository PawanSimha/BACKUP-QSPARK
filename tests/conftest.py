"""Pytest configuration and fixtures for the 11-table schema."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from src.services.db import init_db, get_connection


def seed_base(db_path):
    """Seed a minimal dataset for tests: users, floors, vehicle types, slots, rules."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO users (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status) "
            "VALUES (NULL, 'Test Customer', 'cust@qspark.com', '9999900001', 'cust1', ?, 'CUSTOMER', 1000, 'ACTIVE')",
            (generate_password_hash("user123"),),
        )
        conn.execute(
            "INSERT INTO users (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status) "
            "VALUES ('ADM001', 'Test Admin', 'admin@qspark.com', '9999900002', 'admin1', ?, 'ADMIN', 1000, 'ACTIVE')",
            (generate_password_hash("admin123"),),
        )
        conn.execute(
            "INSERT INTO users (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status) "
            "VALUES ('SADM001', 'Test Super', 'super@qspark.com', '9999900003', 'superadmin', ?, 'SUPER_ADMIN', 10000, 'ACTIVE')",
            (generate_password_hash("super123"),),
        )
        conn.execute("INSERT INTO floors (floor_code, floor_status) VALUES ('B1', 'OPEN')")
        conn.execute("INSERT INTO vehicle_types (type_name, hourly_rate, overstay_rate) VALUES ('BIKE', 5.00, 10.00)")
        conn.execute("INSERT INTO vehicle_types (type_name, hourly_rate, overstay_rate) VALUES ('CAR', 10.00, 20.00)")
        # 3 bike slots
        for i in range(1, 4):
            conn.execute(
                "INSERT INTO parking_slots (floor_id, vehicle_type_id, slot_number, control_status) VALUES (1, 1, ?, 'ACTIVE')",
                (f"B1-{i:02d}",),
            )
        # 1 car slot
        conn.execute(
            "INSERT INTO parking_slots (floor_id, vehicle_type_id, slot_number, control_status) VALUES (1, 2, 'B1-41', 'ACTIVE')"
        )
        conn.execute(
            "INSERT INTO cancellation_rules (rule_code, rule_name, min_hours_before, max_hours_before, refund_percent, penalty_percent) "
            "VALUES ('MORE_24H','>24h',24,NULL,100,0)"
        )
        conn.execute(
            "INSERT INTO cancellation_rules (rule_code, rule_name, min_hours_before, max_hours_before, refund_percent, penalty_percent) "
            "VALUES ('BETWEEN_1_24H','1-24h',1,24,50,0)"
        )
        conn.execute(
            "INSERT INTO cancellation_rules (rule_code, rule_name, min_hours_before, max_hours_before, refund_percent, penalty_percent) "
            "VALUES ('LESS_1H','<1h',0,1,0,100)"
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def app():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # CSRF is covered explicitly in tests/test_security.py
    app.config["DATABASE_PATH"] = db_path
    yield app
    try:
        os.remove(db_path)
    except PermissionError:
        pass


@pytest.fixture
def seeded_app(app):
    seed_base(app.config["DATABASE_PATH"])
    yield app


@pytest.fixture
def client(seeded_app):
    return seeded_app.test_client()


@pytest.fixture
def raw_client(app):
    return app.test_client()