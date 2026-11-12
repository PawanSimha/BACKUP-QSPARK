"""QSPARK Smart Parking System - Seed Data for 11 Core Tables.

Provides safe seed data using secure setup. No passwords are hardcoded;
initial credentials are configured via environment variables.
"""

import os
import secrets
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from src.services.db import get_connection, init_db

load_dotenv()

DB_PATH = os.getenv("DATABASE_PATH", "database/parking_local.db")

# Passwords are never hardcoded: read from env, else generate once and print.
generated_passwords = {}


def _password(env_key):
    value = os.getenv(env_key)
    if value:
        return value
    value = secrets.token_urlsafe(12)
    generated_passwords[env_key] = value
    return value


def seed():
    """Seed master data into the SQLite database.

    Creates the 11 core tables if not exists, then inserts:
    - 4 floors (B1-B4)
    - 2 vehicle types (BIKE, CAR)
    - 64 slots per floor (40 bike + 24 car = 256 total)
    - 4 cancellation rules
    - 3 Admin accounts (from env vars or defaults)
    - 1 Super Admin account (from env vars or defaults)
    """
    # Ensure schema exists
    init_db(DB_PATH)

    conn = get_connection(DB_PATH)
    try:
        # Check if already seeded
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            print("Database already seeded. Skipping.")
            return

        # === Insert floors ===
        floors_data = [
            ("B1", "OPEN"),
            ("B2", "OPEN"),
            ("B3", "OPEN"),
            ("B4", "OPEN"),
        ]
        floor_ids = []
        for floor_code, floor_status in floors_data:
            conn.execute(
                "INSERT INTO floors (floor_code, floor_status) VALUES (?, ?)",
                (floor_code, floor_status),
            )
            floor_ids.append(conn.execute(
                "SELECT last_insert_rowid()").fetchone()[0])

        # === Insert vehicle types ===
        vehicle_types_data = [
            ("BIKE", 5.00, 10.00),
            ("CAR", 10.00, 20.00),
        ]
        vt_ids = []
        for type_name, hourly_rate, overstay_rate in vehicle_types_data:
            conn.execute(
                "INSERT INTO vehicle_types (type_name, hourly_rate, overstay_rate) VALUES (?, ?, ?)",
                (type_name, hourly_rate, overstay_rate),
            )
            vt_ids.append(conn.execute(
                "SELECT last_insert_rowid()").fetchone()[0])

        # === Insert cancellation rules ===
        cancellation_rules_data = [
            ("MORE_24H", "More than 24 hours before start", 24, 100.00, 0.00),
            ("BETWEEN_1_24H", "Between 1 and 24 hours", 1, 50.00, 0.00),
            ("LESS_1H", "Less than 1 hour", 0, 0.00, 100.00),
            ("NOSHOW", "No-show / cancel after start", 0, 0.00, 100.00),
        ]
        for rule_code, rule_name, min_hours, refund, penalty in cancellation_rules_data:
            conn.execute(
                "INSERT INTO cancellation_rules (rule_code, rule_name, min_hours_before, max_hours_before, refund_percent, penalty_percent) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (rule_code, rule_name, min_hours, None, refund, penalty),
            )

        # === Insert admin accounts ===
        # Read from environment variables, fall back to defaults
        admin_usernames = os.getenv("QSPARK_ADMIN_USERS", "admin1,admin2,admin3").split(",")
        admin_emails = os.getenv("QSPARK_ADMIN_EMAILS", "admin1@qspark.com,admin2@qspark.com,admin3@qspark.com").split(",")
        admin_names = os.getenv("QSPARK_ADMIN_NAMES", "Admin One,Admin Two,Admin Three").split(",")

        admins_created = []
        for i, username in enumerate(admin_usernames):
            email = admin_emails[i] if i < len(admin_emails) else f"{username}@qspark.com"
            full_name = admin_names[i] if i < len(admin_names) else f"Admin {username}"

            # Password from env; generated once if absent
            plain_pwd = _password(f"QSPARK_{username.upper()}_PASSWORD")
            pwd_hash = generate_password_hash(plain_pwd)

            conn.execute(
                "INSERT INTO users (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"ADM{i+1:03d}",
                    full_name,
                    email,
                    f"99999000{ i + 1 }",
                    username,
                    pwd_hash,
                    "ADMIN",
                    1000.00,
                    "ACTIVE",
                ),
            )
            admins_created.append(conn.execute(
                "SELECT last_insert_rowid()").fetchone()[0])

        # === Insert Super Admin account ===
        super_admin_username = os.getenv("QSPARK_SUPER_ADMIN_USERNAME", "superadmin")
        super_admin_email = os.getenv("QSPARK_SUPER_ADMIN_EMAIL", "superadmin@qspark.com")
        super_admin_name = os.getenv("QSPARK_SUPER_ADMIN_NAME", "Super Admin")

        super_admin_plain_pwd = _password("QSPARK_SUPER_ADMIN_PASSWORD")
        super_admin_pwd_hash = generate_password_hash(super_admin_plain_pwd)

        conn.execute(
            "INSERT INTO users (admin_id, full_name, email, phone, username, password_hash, role, wallet_balance, account_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "SADM001",
                super_admin_name,
                super_admin_email,
                "9999900000",
                super_admin_username,
                super_admin_pwd_hash,
                "SUPER_ADMIN",
                10000.00,
                "ACTIVE",
            ),
        )
        super_admin_id = conn.execute(
            "SELECT last_insert_rowid()").fetchone()[0]

        # === Insert parking slots: 64 per floor (40 bikes + 24 cars) ===
        for floor_idx, floor_id in enumerate(floor_ids, start=1):
            # Bike slots: slots 01-40
            for i in range(1, 41):
                slot_number = f"B{floor_idx:01d}-{i:02d}"
                # Determine vehicle type: BIKE for first 40 slots per floor
                vehicle_type_id = vt_ids[0]  # BIKE
                conn.execute(
                    "INSERT INTO parking_slots (floor_id, vehicle_type_id, slot_number, control_status) "
                    "VALUES (?, ?, ?, 'ACTIVE')",
                    (floor_id, vehicle_type_id, slot_number),
                )
            # Car slots: slots 41-64
            for i in range(41, 65):
                slot_number = f"B{floor_idx:01d}-{i:02d}"
                vehicle_type_id = vt_ids[1]  # CAR
                conn.execute(
                    "INSERT INTO parking_slots (floor_id, vehicle_type_id, slot_number, control_status) "
                    "VALUES (?, ?, ?, 'ACTIVE')",
                    (floor_id, vehicle_type_id, slot_number),
                )

        conn.execute("COMMIT")
        print("Seeding complete:")
        print(f"  Floors: {len(floors_data)} ({', '.join(f[0] for f in floors_data)})")
        print(f"  Vehicle types: {len(vehicle_types_data)} ({vehicle_types_data[0][0]}, {vehicle_types_data[1][0]})")
        print(f"  Admins: {len(admins_created)}")
        print(f"  Super Admin: 1 (username: {super_admin_username})")
        print(f"  Cancellation rules: {len(cancellation_rules_data)}")
        print(f"  Parking slots: {4 * 64} (64 per floor x {len(floors_data)} floors)")
        print(f"  Total users: {len(admin_usernames) + 1}")
        if generated_passwords:
            print("\nGENERATED CREDENTIALS (store them now; not recoverable):")
            for key, value in generated_passwords.items():
                print(f"  {key}={value}")

    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed()