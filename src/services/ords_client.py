"""QSPARK dual-mode data broker.

ORDS_SIMULATION_MODE=true  -> local SQLite replica (zero-block development)
ORDS_SIMULATION_MODE=false -> live Oracle APEX ORDS REST endpoints
"""

from __future__ import annotations

import openpyxl
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from src.core.pricing_engine import calculate_booking_fare, calculate_overstay_penalty
from src.core.security import verify_password

DEFAULT_DB_PATH = Path(__file__).with_name("parking_local.db")
DEFAULT_DATA_FILE = Path(__file__).resolve().parents[2] / "Latest QSPARK.xlsx"
DEFAULT_LIVE_BASE_URL = (
    "https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com"
    "/ords/nov_2026_batch/qsparking/api/v2"
)

SLOT_STATUSES = ("AVAILABLE", "RESERVED", "OCCUPIED", "MAINTENANCE")

# Sheet order matters: parent tables before children.
SEED_SHEETS = (
    ("QSPARK_USERS", "QSPARK_USERS"),
    ("QSPARK_FLOORS", "QSPARK_FLOORS"),
    ("QSPARK_VEHICLE_TYPES", "QSPARK_VEHICLE_TYPES"),
    ("QSPARK_PARKING_SLOTS", "QSPARK_PARKING_SLOTS"),
    ("QSPARK_BOOKINGS", "QSPARK_BOOKINGS"),
    ("QSPARK_WALLET_TRANSACTIONS", "QSPARK_WALLET_TRANSACTIONS"),
    ("QSPARK_AUDIT_LOGS", "QSPARK_AUDIT_LOGS"),
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS QSPARK_USERS (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'USER' CHECK (role IN ('ADMIN', 'USER')),
    wallet_balance REAL NOT NULL DEFAULT 500.00 CHECK (wallet_balance >= 0),
    is_active TEXT NOT NULL DEFAULT 'Y' CHECK (is_active IN ('Y', 'N')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reserved_col_1 TEXT,
    reserved_col_2 TEXT
);

CREATE TABLE IF NOT EXISTS QSPARK_FLOORS (
    floor_id INTEGER PRIMARY KEY,
    floor_code TEXT NOT NULL UNIQUE CHECK (floor_code IN ('B1', 'B2', 'B3', 'B4')),
    floor_name TEXT NOT NULL,
    bike_capacity INTEGER NOT NULL DEFAULT 40 CHECK (bike_capacity = 40),
    car_capacity INTEGER NOT NULL DEFAULT 20 CHECK (car_capacity = 20),
    total_capacity INTEGER NOT NULL DEFAULT 60 CHECK (total_capacity = 60),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'MAINTENANCE')),
    reserved_col_1 TEXT,
    reserved_col_2 TEXT
);

CREATE TABLE IF NOT EXISTS QSPARK_VEHICLE_TYPES (
    vehicle_type_id INTEGER PRIMARY KEY,
    type_code TEXT NOT NULL UNIQUE CHECK (type_code IN ('BIKE', 'CAR')),
    display_name TEXT NOT NULL,
    hourly_rate REAL NOT NULL CHECK (hourly_rate IN (5.00, 10.00)),
    overstay_penalty_hour REAL NOT NULL DEFAULT 10.00 CHECK (overstay_penalty_hour >= 0),
    total_slots_per_floor INTEGER NOT NULL CHECK (total_slots_per_floor IN (40, 20)),
    reserved_col_1 TEXT,
    reserved_col_2 TEXT
);

CREATE TABLE IF NOT EXISTS QSPARK_PARKING_SLOTS (
    slot_id INTEGER PRIMARY KEY,
    floor_id INTEGER NOT NULL REFERENCES QSPARK_FLOORS(floor_id) ON DELETE CASCADE,
    vehicle_type_id INTEGER NOT NULL REFERENCES QSPARK_VEHICLE_TYPES(vehicle_type_id),
    slot_number TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'AVAILABLE'
        CHECK (status IN ('AVAILABLE', 'RESERVED', 'OCCUPIED', 'MAINTENANCE')),
    last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reserved_col_1 TEXT,
    reserved_col_2 TEXT,
    UNIQUE (floor_id, slot_number)
);

CREATE TABLE IF NOT EXISTS QSPARK_BOOKINGS (
    booking_id INTEGER PRIMARY KEY,
    booking_code TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES QSPARK_USERS(user_id),
    slot_id INTEGER NOT NULL REFERENCES QSPARK_PARKING_SLOTS(slot_id),
    vehicle_type_id INTEGER NOT NULL REFERENCES QSPARK_VEHICLE_TYPES(vehicle_type_id),
    vehicle_number TEXT NOT NULL,
    scheduled_start TEXT NOT NULL,
    scheduled_end TEXT NOT NULL,
    actual_entry_time TEXT,
    actual_exit_time TEXT,
    duration_hours REAL NOT NULL CHECK (duration_hours >= 1.0),
    hourly_rate_applied REAL NOT NULL CHECK (hourly_rate_applied IN (5.00, 10.00)),
    base_amount REAL NOT NULL CHECK (base_amount >= 5.00),
    overstay_hours REAL NOT NULL DEFAULT 0.00 CHECK (overstay_hours >= 0),
    overstay_penalty REAL NOT NULL DEFAULT 0.00 CHECK (overstay_penalty >= 0),
    total_amount REAL NOT NULL CHECK (total_amount >= 0),
    status TEXT NOT NULL DEFAULT 'CONFIRMED'
        CHECK (status IN ('CONFIRMED', 'CHECKED_IN', 'COMPLETED', 'CANCELLED', 'OVERSTAY')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reserved_col_1 TEXT,
    reserved_col_2 TEXT
);

CREATE TABLE IF NOT EXISTS QSPARK_WALLET_TRANSACTIONS (
    txn_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES QSPARK_USERS(user_id),
    booking_id INTEGER NOT NULL REFERENCES QSPARK_BOOKINGS(booking_id) ON DELETE CASCADE,
    txn_type TEXT NOT NULL CHECK (txn_type IN ('BOOKING_DEBIT', 'OVERSTAY_DEBIT', 'CANCEL_REFUND')),
    previous_balance REAL NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    new_balance REAL NOT NULL CHECK (new_balance >= 0),
    status TEXT NOT NULL DEFAULT 'COMPLETED' CHECK (status IN ('COMPLETED', 'REVERSED')),
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reserved_col_1 TEXT,
    reserved_col_2 TEXT
);

CREATE TABLE IF NOT EXISTS QSPARK_AUDIT_LOGS (
    log_id INTEGER PRIMARY KEY,
    changed_by_user_id INTEGER REFERENCES QSPARK_USERS(user_id),
    slot_id INTEGER REFERENCES QSPARK_PARKING_SLOTS(slot_id) ON DELETE CASCADE,
    booking_id INTEGER REFERENCES QSPARK_BOOKINGS(booking_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    old_state TEXT,
    new_state TEXT,
    log_details TEXT,
    logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reserved_col_1 TEXT,
    reserved_col_2 TEXT
);

CREATE TABLE IF NOT EXISTS QSPARK_AUDIT_TRACK (
    track_id INTEGER PRIMARY KEY,
    admin_name TEXT NOT NULL,
    time_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_table TEXT NOT NULL,
    modified_column TEXT,
    why_modified TEXT,
    reserved_col_1 TEXT
);
"""


class OrdsError(Exception):
    """Base error for broker operations mapped to HTTP responses."""


class NotFound(OrdsError):
    pass


class InvalidRequest(OrdsError):
    pass


class InvalidState(OrdsError):
    pass


class InsufficientFunds(OrdsError):
    pass


class UnsupportedInLiveMode(OrdsError):
    pass


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def _cell(value):
    """Normalise Excel cell values for SQLite (datetimes -> ISO text)."""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    return value


class OrdsClient:
    def __init__(
        self,
        simulation_mode: bool | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        if simulation_mode is None:
            simulation_mode = os.getenv("ORDS_SIMULATION_MODE", "true").strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )

        self.simulation_mode = simulation_mode
        self.base_url = (
            base_url or os.getenv("ORDS_BASE_URL") or DEFAULT_LIVE_BASE_URL
        ).rstrip("/")
        self.timeout = float(timeout if timeout is not None else os.getenv("ORDS_TIMEOUT", "5"))
        self.db_path = Path(db_path or os.getenv("QSPARK_DB_PATH") or DEFAULT_DB_PATH)
        self._session = None

        if self.simulation_mode:
            self._init_db()

    # ------------------------------------------------------------------ utils
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _tx(self):
        conn = self._connect()
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def _rows(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = self._connect()
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    @staticmethod
    def _next_id(conn: sqlite3.Connection, table: str, column: str, minimum: int) -> int:
        row = conn.execute(
            f"SELECT COALESCE(MAX({column}), ?) + 1 FROM {table}", (minimum,)
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _public_user(row: dict) -> dict:
        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "wallet_balance": round(row["wallet_balance"], 2),
        }

    @staticmethod
    def _live_user_id(user_id: int) -> float | int:
        # shortcut: live Excel import stores IDs as 1.001–1.050; drop after normalization
        return user_id / 1000.0 if user_id >= 1000 else user_id

    # ------------------------------------------------------------------ setup
    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA_SQL)
            if conn.execute("SELECT COUNT(*) FROM QSPARK_USERS").fetchone()[0] == 0:
                # One transaction: per-row autocommit makes seeding take ~12s on Windows.
                conn.execute("BEGIN")
                try:
                    self._seed(conn)
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        finally:
            conn.close()

    def _ensure_db(self) -> None:
        """Live mode has no auth/list ORDS handlers, so keep the local replica ready."""
        self._init_db()

    def reset_database(self) -> None:
        """Drop and recreate the local replica (tests / demo resets)."""
        if not self.simulation_mode:
            raise UnsupportedInLiveMode("Cannot reset a live Oracle schema")
        conn = self._connect()
        try:
            for table in (
                "QSPARK_AUDIT_TRACK",
                "QSPARK_AUDIT_LOGS",
                "QSPARK_WALLET_TRANSACTIONS",
                "QSPARK_BOOKINGS",
                "QSPARK_PARKING_SLOTS",
                "QSPARK_VEHICLE_TYPES",
                "QSPARK_FLOORS",
                "QSPARK_USERS",
            ):
                conn.execute(f"DROP TABLE IF EXISTS {table}")
        finally:
            conn.close()
        self._init_db()

    def _seed(self, conn: sqlite3.Connection) -> None:
        """Load all 7 tables from the master Excel workbook (exact dataset)."""
        data_file = Path(os.getenv("QSPARK_DATA_FILE", DEFAULT_DATA_FILE))
        if not data_file.exists():
            raise FileNotFoundError(f"Master dataset not found: {data_file}")

        workbook = openpyxl.load_workbook(data_file, data_only=True, read_only=True)
        try:
            for sheet_name, table in SEED_SHEETS:
                rows = workbook[sheet_name].iter_rows(values_only=True)
                headers = [str(header).strip().upper() for header in next(rows)]
                columns = ", ".join(headers)
                placeholders = ", ".join("?" for _ in headers)
                values = [
                    tuple(_cell(v) for v in row[: len(headers)])
                    for row in rows
                    if row and any(v is not None for v in row)
                ]
                conn.executemany(
                    f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values
                )
        finally:
            workbook.close()

    # --------------------------------------------------------------- read side
    def get_user(self, user_id: int) -> dict | None:
        self._ensure_db()
        rows = self._rows("SELECT * FROM QSPARK_USERS WHERE user_id = ?", (user_id,))
        return self._public_user(rows[0]) if rows else None

    def get_slots(self, floor_id: int | None = None) -> list[dict]:
        if not self.simulation_mode:
            params = {"floor_id": floor_id} if floor_id is not None else None
            return self._request("GET", "slots/", params=params)["items"]

        sql = """SELECT s.slot_id, f.floor_code, s.floor_id, s.slot_number,
                        vt.type_code AS vehicle_type, vt.hourly_rate, s.status
                   FROM QSPARK_PARKING_SLOTS s
                   JOIN QSPARK_FLOORS f ON f.floor_id = s.floor_id
                   JOIN QSPARK_VEHICLE_TYPES vt ON vt.vehicle_type_id = s.vehicle_type_id"""
        params: tuple = ()
        if floor_id is not None:
            sql += " WHERE s.floor_id = ?"
            params = (floor_id,)
        return self._rows(sql + " ORDER BY s.slot_number", params)

    def _sqlite_list_bookings(self, user_id: int | None = None) -> list[dict]:
        self._ensure_db()
        sql = """SELECT b.*, s.slot_number, f.floor_code, vt.type_code AS vehicle_type,
                        u.full_name
                   FROM QSPARK_BOOKINGS b
                   JOIN QSPARK_PARKING_SLOTS s ON s.slot_id = b.slot_id
                   JOIN QSPARK_FLOORS f ON f.floor_id = s.floor_id
                   JOIN QSPARK_VEHICLE_TYPES vt ON vt.vehicle_type_id = b.vehicle_type_id
                   JOIN QSPARK_USERS u ON u.user_id = b.user_id"""
        params: tuple = ()
        if user_id is not None:
            sql += " WHERE b.user_id = ?"
            params = (user_id,)
        return self._rows(sql + " ORDER BY b.booking_id DESC", params)

    def list_bookings(self, user_id: int | None = None) -> list[dict]:
        if not self.simulation_mode:
            params = {"user_id": user_id} if user_id is not None else None
            try:
                payload = self._request("GET", "bookings/", params=params)
            except Exception:
                return self._sqlite_list_bookings(user_id)
            items = payload.get("items", [])
            for item in items:
                raw = item.get("user_id")
                if isinstance(raw, (int, float)) and raw < 100:
                    item["user_id"] = int(round(raw * 1000))
            return items
        return self._sqlite_list_bookings(user_id)

    def list_audit_logs(self, limit: int = 50, offset: int = 0) -> list[dict]:
        if not self.simulation_mode:
            payload = self._request(
                "GET", "audit/logs", params={"limit": limit, "offset": offset}
            )
            return payload.get("items", [])

        return self._rows(
            """SELECT a.log_id, a.event_type, a.old_state, a.new_state, a.log_details,
                      a.logged_at, a.changed_by_user_id, u.full_name,
                      a.slot_id, s.slot_number, a.booking_id
                 FROM QSPARK_AUDIT_LOGS a
                 LEFT JOIN QSPARK_USERS u ON u.user_id = a.changed_by_user_id
                 LEFT JOIN QSPARK_PARKING_SLOTS s ON s.slot_id = a.slot_id
                ORDER BY a.log_id DESC
                LIMIT ? OFFSET ?""",
            (limit, offset),
        )

    def insert_audit_track(
        self,
        admin_name: str,
        modified_table: str,
        modified_column: str | None = None,
        why_modified: str | None = None,
    ) -> dict:
        payload = {
            "admin_name": admin_name,
            "modified_table": modified_table,
            "modified_column": modified_column,
            "why_modified": why_modified,
        }
        if not self.simulation_mode:
            return self._request("POST", "admin/audit-track", json=payload)

        with self._tx() as conn:
            track_id = self._next_id(conn, "QSPARK_AUDIT_TRACK", "track_id", 0)
            conn.execute(
                """INSERT INTO QSPARK_AUDIT_TRACK
                   (track_id, admin_name, modified_table, modified_column, why_modified)
                   VALUES (?, ?, ?, ?, ?)""",
                (track_id, admin_name, modified_table, modified_column, why_modified),
            )
        return {
            "track_id": track_id,
            "admin_name": admin_name,
            "modified_table": modified_table,
            "status": "SAVED",
        }

    def authenticate_user(self, login_id: str, plain_password: str) -> dict | None:
        self._ensure_db()
        rows = self._rows(
            """SELECT * FROM QSPARK_USERS
               WHERE (LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?))
                 AND is_active = 'Y'""",
            (login_id, login_id),
        )
        if not rows or not verify_password(plain_password, rows[0]["password_hash"]):
            return None
        return self._public_user(rows[0])

    # -------------------------------------------------------------- write side
    def update_slot_status(self, slot_id: int, status: str, admin_user_id: int) -> bool:
        if status not in SLOT_STATUSES:
            raise InvalidRequest(f"Invalid slot status: {status}")
        if not self.simulation_mode:
            self._request(
                "PUT",
                f"slots/{slot_id}/status",
                json={"status": status, "admin_user_id": self._live_user_id(admin_user_id)},
            )
            return True

        with self._tx() as conn:
            row = conn.execute(
                "SELECT status FROM QSPARK_PARKING_SLOTS WHERE slot_id = ?", (slot_id,)
            ).fetchone()
            if row is None:
                raise NotFound(f"Slot {slot_id} not found")

            conn.execute(
                "UPDATE QSPARK_PARKING_SLOTS SET status = ?, last_updated = ? WHERE slot_id = ?",
                (status, _now(), slot_id),
            )
            conn.execute(
                """INSERT INTO QSPARK_AUDIT_LOGS
                   (log_id, changed_by_user_id, slot_id, event_type, old_state, new_state,
                    log_details, logged_at)
                   VALUES (?, ?, ?, 'SLOT_STATUS_CHANGE', ?, ?, 'Admin status override', ?)""",
                (
                    self._next_id(conn, "QSPARK_AUDIT_LOGS", "log_id", 0),
                    admin_user_id,
                    slot_id,
                    row["status"],
                    status,
                    _now(),
                ),
            )
        return True

    def create_booking(
        self, user_id: int, slot_id: int, vehicle_number: str, duration_hours: float
    ) -> dict:
        if not 1 <= float(duration_hours) <= 8:
            raise InvalidRequest("duration_hours must be between 1 and 8")

        if not self.simulation_mode:
            return self._request(
                "POST",
                "bookings/",
                json={
                    "user_id": self._live_user_id(user_id),
                    "slot_id": slot_id,
                    "vehicle_number": vehicle_number,
                    "duration_hours": duration_hours,
                },
            )

        with self._tx() as conn:
            slot = conn.execute(
                """SELECT s.status, s.slot_number, vt.type_code, vt.hourly_rate
                   FROM QSPARK_PARKING_SLOTS s
                   JOIN QSPARK_VEHICLE_TYPES vt ON vt.vehicle_type_id = s.vehicle_type_id
                   WHERE s.slot_id = ?""",
                (slot_id,),
            ).fetchone()
            if slot is None:
                raise NotFound(f"Slot {slot_id} not found")
            if slot["status"] != "AVAILABLE":
                raise InvalidState("Slot is no longer available")

            user = conn.execute(
                "SELECT wallet_balance FROM QSPARK_USERS WHERE user_id = ?", (user_id,)
            ).fetchone()
            if user is None:
                raise NotFound(f"User {user_id} not found")

            fare = calculate_booking_fare(slot["type_code"], duration_hours)
            base_amount = fare["base_amount"]
            wallet = float(user["wallet_balance"])
            if wallet < base_amount:
                raise InsufficientFunds("Insufficient Metro Card wallet balance")

            now = datetime.now().replace(microsecond=0)
            start = now.isoformat(sep=" ")
            end = (now + timedelta(hours=float(duration_hours))).isoformat(sep=" ")

            booking_id = self._next_id(conn, "QSPARK_BOOKINGS", "booking_id", 10000)
            booking_code = f"QSP-{now:%m%d}-{booking_id % 10000:04d}"
            new_balance = round(wallet - base_amount, 2)

            conn.execute(
                """INSERT INTO QSPARK_BOOKINGS
                   (booking_id, booking_code, user_id, slot_id, vehicle_type_id,
                    vehicle_number, scheduled_start, scheduled_end, duration_hours,
                    hourly_rate_applied, base_amount, total_amount, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?)""",
                (
                    booking_id,
                    booking_code,
                    user_id,
                    slot_id,
                    conn.execute(
                        "SELECT vehicle_type_id FROM QSPARK_PARKING_SLOTS WHERE slot_id = ?",
                        (slot_id,),
                    ).fetchone()[0],
                    vehicle_number,
                    start,
                    end,
                    float(duration_hours),
                    fare["hourly_rate"],
                    base_amount,
                    base_amount,
                    start,
                ),
            )
            conn.execute(
                "UPDATE QSPARK_USERS SET wallet_balance = ? WHERE user_id = ?",
                (new_balance, user_id),
            )
            conn.execute(
                """INSERT INTO QSPARK_WALLET_TRANSACTIONS
                   (txn_id, user_id, booking_id, txn_type, previous_balance, amount,
                    new_balance, status, processed_at)
                   VALUES (?, ?, ?, 'BOOKING_DEBIT', ?, ?, ?, 'COMPLETED', ?)""",
                (
                    self._next_id(conn, "QSPARK_WALLET_TRANSACTIONS", "txn_id", 20000),
                    user_id,
                    booking_id,
                    wallet,
                    base_amount,
                    new_balance,
                    start,
                ),
            )
            conn.execute(
                "UPDATE QSPARK_PARKING_SLOTS SET status = 'RESERVED', last_updated = ? WHERE slot_id = ?",
                (start, slot_id),
            )
            conn.execute(
                """INSERT INTO QSPARK_AUDIT_LOGS
                   (log_id, changed_by_user_id, slot_id, booking_id, event_type,
                    old_state, new_state, log_details, logged_at)
                   VALUES (?, ?, ?, ?, 'BOOKING_CREATED', 'AVAILABLE', 'RESERVED', ?, ?)""",
                (
                    self._next_id(conn, "QSPARK_AUDIT_LOGS", "log_id", 0),
                    user_id,
                    slot_id,
                    booking_id,
                    f"Booking {booking_code} created",
                    start,
                ),
            )

        return {
            "booking_id": booking_id,
            "booking_code": booking_code,
            "slot_number": slot["slot_number"],
            "base_amount": base_amount,
            "previous_wallet_balance": wallet,
            "new_wallet_balance": new_balance,
            "status": "CONFIRMED",
        }

    def checkout_booking(self, booking_id: int, simulated_late_hours: float = 0.0) -> dict:
        if not self.simulation_mode:
            return self._request(
                "PUT",
                f"bookings/{booking_id}/checkout",
                json={"simulated_late_hours": simulated_late_hours},
            )

        with self._tx() as conn:
            booking = conn.execute(
                """SELECT b.user_id, b.slot_id, b.status, b.scheduled_end, b.base_amount,
                          vt.type_code
                   FROM QSPARK_BOOKINGS b
                   JOIN QSPARK_VEHICLE_TYPES vt ON vt.vehicle_type_id = b.vehicle_type_id
                   WHERE b.booking_id = ?""",
                (booking_id,),
            ).fetchone()
            if booking is None:
                raise NotFound(f"Booking {booking_id} not found")
            if booking["status"] not in ("CONFIRMED", "CHECKED_IN", "OVERSTAY"):
                raise InvalidState("Booking is not open for checkout")

            exit_time = datetime.now().replace(microsecond=0) + timedelta(
                hours=float(simulated_late_hours)
            )
            scheduled_end = datetime.fromisoformat(booking["scheduled_end"])
            overstay_hours, penalty = calculate_overstay_penalty(
                booking["type_code"], scheduled_end, exit_time
            )

            wallet = float(
                conn.execute(
                    "SELECT wallet_balance FROM QSPARK_USERS WHERE user_id = ?",
                    (booking["user_id"],),
                ).fetchone()[0]
            )
            if wallet < penalty:
                raise InsufficientFunds(
                    "Insufficient Metro Card wallet balance for overstay penalty"
                )

            new_balance = round(wallet - penalty, 2)
            final_total = round(float(booking["base_amount"]) + penalty, 2)
            exit_text = exit_time.isoformat(sep=" ")

            if penalty > 0:
                conn.execute(
                    "UPDATE QSPARK_USERS SET wallet_balance = ? WHERE user_id = ?",
                    (new_balance, booking["user_id"]),
                )
                conn.execute(
                    """INSERT INTO QSPARK_WALLET_TRANSACTIONS
                       (txn_id, user_id, booking_id, txn_type, previous_balance, amount,
                        new_balance, status, processed_at)
                       VALUES (?, ?, ?, 'OVERSTAY_DEBIT', ?, ?, ?, 'COMPLETED', ?)""",
                    (
                        self._next_id(conn, "QSPARK_WALLET_TRANSACTIONS", "txn_id", 20000),
                        booking["user_id"],
                        booking_id,
                        wallet,
                        penalty,
                        new_balance,
                        exit_text,
                    ),
                )

            conn.execute(
                """UPDATE QSPARK_BOOKINGS
                   SET actual_exit_time = ?, overstay_hours = ?, overstay_penalty = ?,
                       total_amount = ?, status = 'COMPLETED'
                   WHERE booking_id = ?""",
                (exit_text, overstay_hours, penalty, final_total, booking_id),
            )
            conn.execute(
                "UPDATE QSPARK_PARKING_SLOTS SET status = 'AVAILABLE', last_updated = ? WHERE slot_id = ?",
                (exit_text, booking["slot_id"]),
            )
            conn.execute(
                """INSERT INTO QSPARK_AUDIT_LOGS
                   (log_id, changed_by_user_id, slot_id, booking_id, event_type,
                    old_state, new_state, log_details, logged_at)
                   VALUES (?, ?, ?, ?, 'CHECKOUT_COMPLETED', 'RESERVED', 'AVAILABLE', ?, ?)""",
                (
                    self._next_id(conn, "QSPARK_AUDIT_LOGS", "log_id", 0),
                    booking["user_id"],
                    booking["slot_id"],
                    booking_id,
                    f"Exit settled, penalty {penalty}",
                    exit_text,
                ),
            )

        return {
            "booking_id": booking_id,
            "overstay_hours": overstay_hours,
            "penalty_charged": penalty,
            "final_total_amount": final_total,
            "new_wallet_balance": new_balance,
            "status": "COMPLETED",
        }

    def cancel_booking(self, booking_id: int) -> dict:
        if not self.simulation_mode:
            return self._request("PUT", f"bookings/{booking_id}/cancel")

        with self._tx() as conn:
            booking = conn.execute(
                "SELECT user_id, slot_id, status, base_amount FROM QSPARK_BOOKINGS WHERE booking_id = ?",
                (booking_id,),
            ).fetchone()
            if booking is None:
                raise NotFound(f"Booking {booking_id} not found")
            if booking["status"] != "CONFIRMED":
                raise InvalidState("Only confirmed bookings can be cancelled")

            wallet = float(
                conn.execute(
                    "SELECT wallet_balance FROM QSPARK_USERS WHERE user_id = ?",
                    (booking["user_id"],),
                ).fetchone()[0]
            )
            refund = float(booking["base_amount"])
            new_balance = round(wallet + refund, 2)
            now = _now()

            conn.execute(
                "UPDATE QSPARK_USERS SET wallet_balance = ? WHERE user_id = ?",
                (new_balance, booking["user_id"]),
            )
            conn.execute(
                """INSERT INTO QSPARK_WALLET_TRANSACTIONS
                   (txn_id, user_id, booking_id, txn_type, previous_balance, amount,
                    new_balance, status, processed_at)
                   VALUES (?, ?, ?, 'CANCEL_REFUND', ?, ?, ?, 'COMPLETED', ?)""",
                (
                    self._next_id(conn, "QSPARK_WALLET_TRANSACTIONS", "txn_id", 20000),
                    booking["user_id"],
                    booking_id,
                    wallet,
                    refund,
                    new_balance,
                    now,
                ),
            )
            conn.execute(
                "UPDATE QSPARK_BOOKINGS SET status = 'CANCELLED' WHERE booking_id = ?",
                (booking_id,),
            )
            conn.execute(
                "UPDATE QSPARK_PARKING_SLOTS SET status = 'AVAILABLE', last_updated = ? WHERE slot_id = ?",
                (now, booking["slot_id"]),
            )
            conn.execute(
                """INSERT INTO QSPARK_AUDIT_LOGS
                   (log_id, changed_by_user_id, slot_id, booking_id, event_type,
                    old_state, new_state, log_details, logged_at)
                   VALUES (?, ?, ?, ?, 'BOOKING_CANCELLED', 'CONFIRMED', 'CANCELLED', ?, ?)""",
                (
                    self._next_id(conn, "QSPARK_AUDIT_LOGS", "log_id", 0),
                    booking["user_id"],
                    booking["slot_id"],
                    booking_id,
                    f"Refund {refund}",
                    now,
                ),
            )

        return {
            "booking_id": booking_id,
            "refunded_amount": refund,
            "restored_wallet_balance": new_balance,
            "slot_status": "AVAILABLE",
            "status": "CANCELLED",
        }

    def get_analytics_kpi(self) -> dict:
        if not self.simulation_mode:
            return self._request("GET", "analytics/kpi")

        totals = self._rows(
            """SELECT COUNT(*) AS total,
                      COUNT(CASE WHEN status = 'AVAILABLE' THEN 1 END) AS available,
                      COUNT(CASE WHEN status = 'RESERVED' THEN 1 END) AS reserved,
                      COUNT(CASE WHEN status = 'OCCUPIED' THEN 1 END) AS occupied,
                      COUNT(CASE WHEN status = 'MAINTENANCE' THEN 1 END) AS maintenance
               FROM QSPARK_PARKING_SLOTS"""
        )[0]
        revenue = self._rows(
            "SELECT COALESCE(SUM(total_amount), 0) AS revenue FROM QSPARK_BOOKINGS WHERE status != 'CANCELLED'"
        )[0]["revenue"]

        heatmaps = self._rows(
            """SELECT f.floor_code,
                      COUNT(s.slot_id) AS total,
                      COUNT(CASE WHEN s.status != 'AVAILABLE' THEN 1 END) AS occupied
               FROM QSPARK_FLOORS f
               LEFT JOIN QSPARK_PARKING_SLOTS s ON s.floor_id = f.floor_id
               GROUP BY f.floor_code
               ORDER BY f.floor_code"""
        )
        for floor in heatmaps:
            floor["total"] = int(floor["total"])
            floor["occupied"] = int(floor["occupied"])
            floor["occupancy_percent"] = (
                round(100 * floor["occupied"] / floor["total"], 2) if floor["total"] else 0.0
            )

        total = int(totals["total"])
        return {
            "total_slots": total,
            "available_slots": int(totals["available"]),
            "reserved_slots": int(totals["reserved"]),
            "occupied_slots": int(totals["occupied"]),
            "maintenance_slots": int(totals["maintenance"]),
            "occupancy_rate_percent": (
                round(100 * (total - int(totals["available"])) / total, 2) if total else 0.0
            ),
            "total_revenue_collected": round(float(revenue), 2),
            "floor_heatmaps": heatmaps,
        }

    # --------------------------------------------------------------- live mode
    def _require_simulation(self, operation: str) -> None:
        if not self.simulation_mode:
            raise UnsupportedInLiveMode(
                f"{operation} has no ORDS handler; run with ORDS_SIMULATION_MODE=true"
            )

    def _request(self, method: str, path: str, **kwargs):
        if self._session is None:
            import requests

            self._session = requests.Session()

        response = self._session.request(
            method, f"{self.base_url}/{path}", timeout=self.timeout, **kwargs
        )
        payload = {}
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = {}

        if response.status_code == 402:
            raise InsufficientFunds(payload.get("error", "Insufficient wallet balance"))
        if response.status_code == 404:
            raise NotFound(payload.get("error", "Resource not found"))
        if response.status_code == 409:
            raise InvalidState(payload.get("error", "Request conflicts with current state"))
        if response.status_code >= 400:
            raise OrdsError(payload.get("error", f"ORDS request failed ({response.status_code})"))
        return payload


ords = OrdsClient()
