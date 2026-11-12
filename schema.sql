/* QSPARK Smart Parking System - Complete Database Schema (single source of truth)
 * 11 core tables + indexes + integrity triggers.
 * init_db() executes this file verbatim.
 */

PRAGMA foreign_keys = ON;

/* ============================ 1. users ============================ */
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id TEXT UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT NOT NULL,
    gender TEXT CHECK (gender IN ('MALE', 'FEMALE', 'OTHER', 'PREFER_NOT_TO_SAY')),
    company_name TEXT,
    username TEXT UNIQUE,
    password_hash TEXT,
    role TEXT NOT NULL CHECK (role IN ('CUSTOMER', 'ADMIN', 'SUPER_ADMIN')),
    wallet_balance NUMERIC NOT NULL DEFAULT 1000,
    account_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (account_status IN ('PENDING', 'ACTIVE', 'BLOCKED', 'DELETED')),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL,
    CHECK ((role = 'CUSTOMER' AND admin_id IS NULL) OR (role IN ('ADMIN','SUPER_ADMIN') AND admin_id IS NOT NULL)),
    CHECK (username IS NOT NULL OR email IS NOT NULL),
    CHECK ((account_status = 'ACTIVE' AND password_hash IS NOT NULL) OR account_status <> 'ACTIVE')
);

/* ============================ 2. floors ============================ */
CREATE TABLE IF NOT EXISTS floors (
    floor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    floor_code TEXT UNIQUE NOT NULL,
    floor_status TEXT NOT NULL DEFAULT 'OPEN' CHECK (floor_status IN ('OPEN', 'CLOSED', 'MAINTENANCE', 'INACTIVE')),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);

/* ============================ 3. vehicle_types ============================ */
CREATE TABLE IF NOT EXISTS vehicle_types (
    vehicle_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT UNIQUE NOT NULL,
    hourly_rate NUMERIC NOT NULL CHECK (hourly_rate >= 0),
    overstay_rate NUMERIC NOT NULL CHECK (overstay_rate >= 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);

/* ============================ 4. parking_slots ============================ */
CREATE TABLE IF NOT EXISTS parking_slots (
    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    floor_id INTEGER NOT NULL,
    vehicle_type_id INTEGER NOT NULL,
    slot_number TEXT NOT NULL,
    control_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (control_status IN ('ACTIVE', 'ADMIN_RESERVED', 'MAINTENANCE', 'INACTIVE')),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (floor_id) REFERENCES floors(floor_id) ON DELETE RESTRICT,
    FOREIGN KEY (vehicle_type_id) REFERENCES vehicle_types(vehicle_type_id),
    UNIQUE (floor_id, slot_number)
);

/* ============================ 5. bookings ============================ */
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_reference TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    slot_id INTEGER NOT NULL,
    vehicle_format TEXT NOT NULL CHECK (vehicle_format IN ('std1','std2','std3','bhr')),
    vehicle_number TEXT NOT NULL,
    booked_from DATETIME NOT NULL,
    booked_until DATETIME NOT NULL,
    hold_expires_at TEXT,
    hourly_rate_applied NUMERIC NOT NULL CHECK (hourly_rate_applied >= 0),
    overstay_rate_applied NUMERIC NOT NULL CHECK (overstay_rate_applied >= 0),
    estimated_amount NUMERIC NOT NULL CHECK (estimated_amount >= 0),
    booking_status TEXT NOT NULL DEFAULT 'HELD' CHECK (booking_status IN ('HELD','CONFIRMED','COMPLETED','CANCELLED','EXPIRED')),
    applied_cancellation_rule_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (slot_id) REFERENCES parking_slots(slot_id) ON DELETE RESTRICT,
    FOREIGN KEY (applied_cancellation_rule_id) REFERENCES cancellation_rules(rule_id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL,
    CHECK (booked_until > booked_from)
);

/* ============================ 6. cancellation_rules ============================ */
CREATE TABLE IF NOT EXISTS cancellation_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_code TEXT UNIQUE NOT NULL,
    rule_name TEXT NOT NULL,
    min_hours_before NUMERIC,
    max_hours_before NUMERIC,
    is_no_show INTEGER NOT NULL DEFAULT 0 CHECK (is_no_show IN (0,1)),
    refund_percent NUMERIC NOT NULL CHECK (refund_percent >= 0 AND refund_percent <= 100),
    penalty_percent NUMERIC NOT NULL DEFAULT 0 CHECK (penalty_percent >= 0 AND penalty_percent <= 100),
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL,
    CHECK (min_hours_before IS NULL OR min_hours_before >= 0),
    CHECK (max_hours_before IS NULL OR min_hours_before IS NULL OR max_hours_before > min_hours_before)
);

/* ============================ 7. wallet_transactions ============================ */
CREATE TABLE IF NOT EXISTS wallet_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_reference TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    booking_id INTEGER,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BOOKING_DEBIT','OVERTIME_DEBIT','CANCELLATION_REFUND','ADMIN_ADJUSTMENT','SUPER_ADMIN_REVENUE_CREDIT','REVENUE_REFUND_REVERSAL')),
    direction TEXT NOT NULL CHECK (direction IN ('DEBIT','CREDIT')),
    amount NUMERIC NOT NULL CHECK (amount > 0),
    balance_after NUMERIC NOT NULL CHECK (balance_after >= 0),
    description TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);

/* ============================ 8. booking_events ============================ */
CREATE TABLE IF NOT EXISTS booking_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('ENTRY','EXIT')),
    scan_method TEXT NOT NULL CHECK (scan_method IN ('QR','MANUAL')),
    event_note TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);

/* ============================ 9. audit_logs ============================ */
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    old_values TEXT,
    new_values TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);

/* ============================ 10. revenue_collections ============================ */
CREATE TABLE IF NOT EXISTS revenue_collections (
    collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_user_id INTEGER NOT NULL,
    super_admin_user_id INTEGER NOT NULL,
    booking_id INTEGER NOT NULL,
    customer_wallet_transaction_id INTEGER NOT NULL UNIQUE,
    super_admin_wallet_transaction_id INTEGER NOT NULL UNIQUE,
    collection_type TEXT NOT NULL CHECK (collection_type IN ('BOOKING_CHARGE','OVERTIME_CHARGE','REFUND_REVERSAL')),
    amount NUMERIC NOT NULL CHECK (amount > 0),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (source_user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (super_admin_user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_wallet_transaction_id) REFERENCES wallet_transactions(transaction_id) ON DELETE RESTRICT,
    FOREIGN KEY (super_admin_wallet_transaction_id) REFERENCES wallet_transactions(transaction_id) ON DELETE RESTRICT
);

/* ============================ 11. system_settings ============================ */
CREATE TABLE IF NOT EXISTS system_settings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    reserved1 TEXT,
    reserved2 TEXT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);

/* ============================ INDEXES ============================ */
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(account_status);
CREATE INDEX IF NOT EXISTS idx_floors_status ON floors(floor_status);
CREATE INDEX IF NOT EXISTS idx_vehicle_types_active ON vehicle_types(is_active);
CREATE INDEX IF NOT EXISTS idx_parking_slots_floor ON parking_slots(floor_id);
CREATE INDEX IF NOT EXISTS idx_parking_slots_vtype ON parking_slots(vehicle_type_id);
CREATE INDEX IF NOT EXISTS idx_parking_slots_status ON parking_slots(control_status);
CREATE INDEX IF NOT EXISTS idx_bookings_user_status ON bookings(user_id, booking_status);
CREATE INDEX IF NOT EXISTS idx_bookings_slot ON bookings(slot_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(booking_status);
CREATE INDEX IF NOT EXISTS idx_bookings_reference ON bookings(booking_reference);
CREATE INDEX IF NOT EXISTS idx_cancellation_rules_active ON cancellation_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user ON wallet_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_booking ON wallet_transactions(booking_id);
CREATE INDEX IF NOT EXISTS idx_booking_events_booking ON booking_events(booking_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_revenue_collections_booking ON revenue_collections(booking_id);
CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(setting_key);

/* Partial unique indexes enforcing integrity */
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_vehicle_number
    ON bookings(vehicle_number) WHERE booking_status IN ('HELD','CONFIRMED');
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_entry_per_booking
    ON booking_events(booking_id) WHERE event_type = 'ENTRY';
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_exit_per_booking
    ON booking_events(booking_id) WHERE event_type = 'EXIT';

/* ============================ TRIGGERS ============================ */

/* Reject overlapping active bookings for the same slot (interval overlap). */
CREATE TRIGGER IF NOT EXISTS trg_no_overlapping_bookings
BEFORE INSERT ON bookings
WHEN NEW.booking_status IN ('HELD','CONFIRMED')
BEGIN
    SELECT RAISE(ABORT, 'overlapping active booking for slot')
    WHERE EXISTS (
        SELECT 1 FROM bookings b
        WHERE b.slot_id = NEW.slot_id
          AND b.booking_status IN ('HELD','CONFIRMED')
          AND b.booked_from < NEW.booked_until
          AND b.booked_until > NEW.booked_from
    );
END;

/* Enforce booking status transitions. */
CREATE TRIGGER IF NOT EXISTS trg_booking_status_transitions
BEFORE UPDATE OF booking_status ON bookings
WHEN NEW.booking_status <> OLD.booking_status
BEGIN
    SELECT RAISE(ABORT, 'illegal booking status transition')
    WHERE NOT (
        (OLD.booking_status = 'HELD' AND NEW.booking_status IN ('CONFIRMED','CANCELLED','EXPIRED')) OR
        (OLD.booking_status = 'CONFIRMED' AND NEW.booking_status IN ('COMPLETED','CANCELLED'))
    );
END;

/* Prevent ENTRY event before CONFIRMED, EXIT before ENTRY. */
CREATE TRIGGER IF NOT EXISTS trg_exit_requires_entry
BEFORE INSERT ON booking_events
WHEN NEW.event_type = 'EXIT'
BEGIN
    SELECT RAISE(ABORT, 'EXIT before ENTRY not allowed')
    WHERE NOT EXISTS (SELECT 1 FROM booking_events WHERE booking_id = NEW.booking_id AND event_type = 'ENTRY');
END;

/* Protect users with active bookings from physical deletion (soft delete only). */
CREATE TRIGGER IF NOT EXISTS trg_protect_active_user_delete
BEFORE DELETE ON users
WHEN EXISTS (
    SELECT 1 FROM bookings WHERE user_id = OLD.user_id
      AND booking_status IN ('HELD','CONFIRMED')
)
BEGIN
    SELECT RAISE(ABORT, 'cannot physically delete user with active bookings; soft delete instead');
END;

/* Seed the mandatory system setting. */
INSERT OR IGNORE INTO system_settings (setting_key, setting_value, description)
VALUES ('SYSTEM_STATUS', 'ONLINE', 'Global system online/offline switch');
