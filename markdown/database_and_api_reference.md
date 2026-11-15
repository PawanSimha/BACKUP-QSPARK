# QSPARK — Comprehensive Database & API Reference

> **Purpose:** Single consolidated reference for the QSPARK Smart Parking system's database schema and REST API surface. Written so it can be used directly to build the equivalent Oracle schema and to understand how every endpoint consumes/produces data.
>
> **Sources of truth:** `schema.sql` (executable SQLite schema), the running database `database/parking_local.db`, and the registered Flask blueprints in `src/api/`. Where this document and `markdown/db.md` / `markdown/api.md` differ, the running code + `schema.sql` win (per `AGENTS.md` precedence).
>
> **Last refreshed:** 2026-11-15 (after analytics heat-map, charts, slot hover tooltip, and revenue-report fixes).

---

## Table of Contents

- [Part A — Database Schema](#part-a--database-schema)
  - [A.1 Overview & conventions](#a1-overview--conventions)
  - [A.2 Table index](#a2-table-index)
  - [A.3 Table definitions (columns, constraints, FKs)](#a3-table-definitions)
  - [A.4 Indexes](#a4-indexes)
  - [A.5 Triggers](#a5-triggers)
  - [A.6 Partial unique indexes](#a6-partial-unique-indexes)
  - [A.7 Seed data](#a7-seed-data)
  - [A.8 Business logic flows](#a8-business-logic-flows)
  - [A.9 Oracle migration notes](#a9-oracle-migration-notes)
- [Part B — REST API Reference](#part-b--rest-api-reference)
  - [B.1 Conventions](#b1-conventions)
  - [B.2 Endpoint catalog (by blueprint)](#b2-endpoint-catalog)
  - [B.3 Detailed endpoint contracts](#b3-detailed-endpoint-contracts)
- [Part C — Cross-reference: DB columns ↔ query params ↔ template fields](#part-c--cross-reference)

---

# Part A — Database Schema

## A.1 Overview & conventions

- **Engine:** SQLite (Phase 1). Phase 2 targets Oracle (APEX/ORDS) — see `markdown/technical_spec.md`.
- **Tables:** 11 core tables + 15 secondary indexes + 3 partial unique indexes + 4 triggers.
- **Metadata columns** on every table: `created_by`, `created_at`, `updated_by`, `updated_at`, `reserved1`, `reserved2`.
  - `created_by` / `updated_by` → `users.user_id`, `ON DELETE SET NULL`.
  - `created_at` / `updated_at` default `datetime('now')`.
  - `reserved1`, `reserved2` are nullable TEXT extension hooks (for Oracle/Phase 2 additions without schema changes).
- **Soft delete:** `users.account_status = 'DELETED'`; no physical delete when active bookings exist (`trg_protect_active_user_delete`).
- **Foreign keys:** enforced on every connection (`PRAGMA foreign_keys = ON`). Most FKs use `ON DELETE RESTRICT` for financial/booking history; `SET NULL` for audit/created-by links.
- **Money:** `NUMERIC`, never negative; balances updated inside `BEGIN IMMEDIATE` transactions.
- **Live slot status** is computed in SQL (`_LIVE_STATUS_SQL`), never stored: `AVAILABLE / RESERVED / OCCUPIED / MAINTENANCE / INACTIVE`.
- **Booking status lifecycle:** `HELD → CONFIRMED → COMPLETED` or `CANCELLED` / `EXPIRED`.

## A.2 Table index

| # | Table | Purpose |
|---|---|---|
| 1 | `users` | All identities (CUSTOMER / ADMIN / SUPER_ADMIN) in one table |
| 2 | `floors` | Parking floors (B1..B4) |
| 3 | `vehicle_types` | Vehicle categories + hourly/overstay rates |
| 4 | `parking_slots` | Individual slots (floor × vehicle type) |
| 5 | `bookings` | Parking bookings (user, slot, vehicle, time, status) |
| 6 | `cancellation_rules` | Configurable cancellation/refund policies |
| 7 | `wallet_transactions` | Immutable wallet ledger (debit/credit) |
| 8 | `booking_events` | QR/manual ENTRY/EXIT events |
| 9 | `audit_logs` | Admin/Super Admin action trail |
| 10 | `revenue_collections` | Money collected from customers → Super Admin wallet |
| 11 | `system_settings` | Global settings (system ONLINE/OFFLINE) |

## A.3 Table definitions

### 1. users
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| user_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| admin_id | TEXT | — | — | YES | (nullable for CUSTOMER) | — | non-null for ADMIN/SUPER_ADMIN |
| full_name | TEXT | — | — | — | YES | — | — |
| email | TEXT | — | — | YES | (nullable for on-site) | — | — |
| phone | TEXT | — | — | — | YES | — | — |
| gender | TEXT | — | — | — | — | — | MALE/FEMALE/OTHER/PREFER_NOT_TO_SAY |
| company_name | TEXT | — | — | — | — | — | — |
| username | TEXT | — | — | YES | — | — | username OR email required |
| password_hash | TEXT | — | — | — | — | — | ACTIVE requires hash |
| role | TEXT | — | — | — | YES | — | CUSTOMER/ADMIN/SUPER_ADMIN |
| wallet_balance | NUMERIC | — | — | — | YES | 1000 | >= 0 |
| account_status | TEXT | — | — | — | YES | PENDING | PENDING/ACTIVE/BLOCKED/DELETED |
| created_by | INTEGER | — | users.user_id (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users.user_id (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

**Table-level checks:** `(role='CUSTOMER' AND admin_id IS NULL) OR (role IN ('ADMIN','SUPER_ADMIN') AND admin_id IS NOT NULL)`; `username IS NOT NULL OR email IS NOT NULL`; `(account_status='ACTIVE' AND password_hash IS NOT NULL) OR account_status <> 'ACTIVE'`.

### 2. floors
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| floor_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| floor_code | TEXT | — | — | YES | YES | — | — |
| floor_status | TEXT | — | — | — | YES | OPEN | OPEN/CLOSED/MAINTENANCE/INACTIVE |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

### 3. vehicle_types
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| vehicle_type_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| type_name | TEXT | — | — | YES | YES | — | — |
| hourly_rate | NUMERIC | — | — | — | YES | — | >= 0 |
| overstay_rate | NUMERIC | — | — | — | YES | — | >= 0 |
| is_active | INTEGER | — | — | — | YES | 1 | 0 or 1 |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

### 4. parking_slots
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| slot_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| floor_id | INTEGER | — | floors (RESTRICT) | — | YES | — | — |
| vehicle_type_id | INTEGER | — | vehicle_types | — | YES | — | — |
| slot_number | TEXT | — | — | — | YES | — | UNIQUE(floor_id, slot_number) |
| control_status | TEXT | — | — | — | YES | ACTIVE | ACTIVE/ADMIN_RESERVED/MAINTENANCE/INACTIVE |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

### 5. bookings
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| booking_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| booking_reference | TEXT | — | — | YES | YES | — | — |
| user_id | INTEGER | — | users (RESTRICT) | — | YES | — | — |
| slot_id | INTEGER | — | parking_slots (RESTRICT) | — | YES | — | — |
| vehicle_format | TEXT | — | — | — | YES | — | std1/std2/std3/bhr |
| vehicle_number | TEXT | — | — | partial unique (HELD/CONFIRMED) | YES | — | — |
| booked_from | DATETIME | — | — | — | YES | — | — |
| booked_until | DATETIME | — | — | — | YES | — | > booked_from |
| hold_expires_at | TEXT | — | — | — | — | — | — |
| hourly_rate_applied | NUMERIC | — | — | — | YES | — | >= 0 |
| overstay_rate_applied | NUMERIC | — | — | — | YES | — | >= 0 |
| estimated_amount | NUMERIC | — | — | — | YES | — | >= 0 |
| booking_status | TEXT | — | — | — | YES | HELD | HELD/CONFIRMED/COMPLETED/CANCELLED/EXPIRED |
| applied_cancellation_rule_id | INTEGER | — | cancellation_rules (SET NULL) | — | — | — | — |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

**Status transitions (trigger-enforced):** HELD→{CONFIRMED,CANCELLED,EXPIRED}; CONFIRMED→{COMPLETED,CANCELLED}. All others rejected.

### 6. cancellation_rules
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| rule_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| rule_code | TEXT | — | — | YES | YES | — | — |
| rule_name | TEXT | — | — | — | YES | — | — |
| min_hours_before | NUMERIC | — | — | — | — | — | >= 0 (nullable) |
| max_hours_before | NUMERIC | — | — | — | — | — | > min_hours (nullable) |
| is_no_show | INTEGER | — | — | — | YES | 0 | 0 or 1 |
| refund_percent | NUMERIC | — | — | — | YES | — | 0-100 |
| penalty_percent | NUMERIC | — | — | — | YES | 0 | 0-100 |
| description | TEXT | — | — | — | — | — | — |
| is_active | INTEGER | — | — | — | YES | 1 | 0 or 1 |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

**Seed rules:** MORE_24H (>24h → 100% refund), BETWEEN_1_24H (1-24h → 50%), LESS_1H (<1h → 0% + penalty), NOSHOW (no-show → 0%).

### 7. wallet_transactions
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| transaction_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| transaction_reference | TEXT | — | — | YES | YES | — | (uuid/microsecond to avoid collision) |
| user_id | INTEGER | — | users (RESTRICT) | — | YES | — | — |
| booking_id | INTEGER | — | bookings (SET NULL) | — | — | — | — |
| transaction_type | TEXT | — | — | — | YES | — | BOOKING_DEBIT/OVERTIME_DEBIT/CANCELLATION_REFUND/ADMIN_ADJUSTMENT/SUPER_ADMIN_REVENUE_CREDIT/REVENUE_REFUND_REVERSAL |
| direction | TEXT | — | — | — | YES | — | DEBIT/CREDIT |
| amount | NUMERIC | — | — | — | YES | — | > 0 |
| balance_after | NUMERIC | — | — | — | YES | — | >= 0 |
| description | TEXT | — | — | — | — | — | — |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

### 8. booking_events
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| event_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| booking_id | INTEGER | — | bookings (RESTRICT) | — | YES | — | — |
| event_type | TEXT | — | — | — | YES | — | ENTRY/EXIT |
| scan_method | TEXT | — | — | — | YES | — | QR/MANUAL |
| event_note | TEXT | — | — | — | — | — | — |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

**Partial unique indexes:** one ENTRY per booking, one EXIT per booking.

### 9. audit_logs
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| audit_log_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| action_type | TEXT | — | — | — | YES | — | (CREATE_USER, UPDATE_USER, …) |
| entity_type | TEXT | — | — | — | YES | — | — |
| entity_id | INTEGER | — | — | — | — | — | nullable |
| old_values | TEXT | — | — | — | — | — | JSON/text; never passwords/hashes |
| new_values | TEXT | — | — | — | — | — | JSON/text; never passwords/hashes |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

### 10. revenue_collections
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| collection_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| source_user_id | INTEGER | — | users (RESTRICT) | — | YES | — | customer who generated charge |
| super_admin_user_id | INTEGER | — | users (RESTRICT, SUPER_ADMIN) | — | YES | — | — |
| booking_id | INTEGER | — | bookings (RESTRICT) | — | YES | — | — |
| customer_wallet_transaction_id | INTEGER | — | wallet_transactions (RESTRICT) | YES | YES | — | — |
| super_admin_wallet_transaction_id | INTEGER | — | wallet_transactions (RESTRICT) | YES | YES | — | — |
| collection_type | TEXT | — | — | — | YES | — | BOOKING_CHARGE/OVERTIME_CHARGE/REFUND_REVERSAL |
| amount | NUMERIC | — | — | — | YES | — | > 0 |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

### 11. system_settings
| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| setting_id | INTEGER | YES (AUTOINCREMENT) | — | — | — | — | — |
| setting_key | TEXT | — | — | YES | YES | — | — |
| setting_value | TEXT | — | — | — | YES | — | — |
| description | TEXT | — | — | — | — | — | — |
| created_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| created_at | TEXT | — | — | — | YES | datetime('now') | — |
| updated_by | INTEGER | — | users (SET NULL) | — | — | — | — |
| updated_at | TEXT | — | — | — | YES | datetime('now') | — |
| reserved1 | TEXT | — | — | — | — | — | nullable |
| reserved2 | TEXT | — | — | — | — | — | nullable |

**Seed:** `SYSTEM_STATUS = ONLINE`.

---

## A.4 Indexes
| Index Name | Table | Columns | Purpose |
|---|---|---|---|
| idx_users_role | users | role | Role-based queries |
| idx_users_status | users | account_status | Account status filtering |
| idx_floors_status | floors | floor_status | Floor status filtering |
| idx_vehicle_types_active | vehicle_types | is_active | Active vehicle type queries |
| idx_parking_slots_floor | parking_slots | floor_id | Slot lookup by floor |
| idx_parking_slots_vtype | parking_slots | vehicle_type_id | Slot lookup by vehicle type |
| idx_parking_slots_status | parking_slots | control_status | Status-based slot queries |
| idx_bookings_user_status | bookings | user_id, booking_status | User's bookings by status |
| idx_bookings_slot | bookings | slot_id | Slot's bookings |
| idx_bookings_status | bookings | booking_status | Status filtering |
| idx_bookings_reference | bookings | booking_reference | Reference lookup |
| idx_cancellation_rules_active | cancellation_rules | is_active | Active rules lookup |
| idx_wallet_transactions_user | wallet_transactions | user_id | User's transaction history |
| idx_wallet_transactions_booking | wallet_transactions | booking_id | Booking's transaction history |
| idx_booking_events_booking | booking_events | booking_id | Event lookup by booking |
| idx_audit_logs_entity | audit_logs | entity_type, entity_id | Audit entity lookup |
| idx_revenue_collections_booking | revenue_collections | booking_id | Revenue per booking |
| idx_system_settings_key | system_settings | setting_key | System setting lookup |

## A.5 Triggers
| Trigger Name | Table | Event | Purpose |
|---|---|---|---|
| trg_no_overlapping_bookings | bookings | BEFORE INSERT | Reject overlapping active (HELD/CONFIRMED) bookings for the same slot |
| trg_booking_status_transitions | bookings | BEFORE UPDATE OF booking_status | Reject illegal status transitions |
| trg_exit_requires_entry | booking_events | BEFORE INSERT (EXIT) | Reject EXIT before ENTRY exists |
| trg_protect_active_user_delete | users | BEFORE DELETE | Block physical delete of users with active bookings (force soft delete) |

## A.6 Partial unique indexes
| Index Name | Table | Definition |
|---|---|---|
| uq_active_vehicle_number | bookings | UNIQUE(vehicle_number) WHERE booking_status IN ('HELD','CONFIRMED') |
| uq_one_entry_per_booking | booking_events | UNIQUE(booking_id) WHERE event_type = 'ENTRY' |
| uq_one_exit_per_booking | booking_events | UNIQUE(booking_id) WHERE event_type = 'EXIT' |

## A.7 Seed data
- **users:** 1 SUPER_ADMIN (`pawan.simha`), 3 ADMINs (`aditya`, `vivek`, `abhishek.paul`), 46+ CUSTOMERs.
- **floors:** B1–B4 (4 floors), 64 slots each (40 bike + 24 car per floor) = 256 slots.
- **vehicle_types:** 2-Wheeler (Bike) and 4-Wheeler (Car) with hourly/overstay rates.
- **cancellation_rules:** MORE_24H, BETWEEN_1_24H, LESS_1H, NOSHOW.
- **system_settings:** `SYSTEM_STATUS = ONLINE`.
- **wallet:** initial balance ₹1,000 per user (configurable).

## A.8 Business logic flows

**Booking confirmation (atomic, inside `BEGIN IMMEDIATE`):**
1. Re-read slot status, floor status, overlapping bookings inside transaction.
2. Validate wallet balance >= estimated_amount.
3. DEBIT customer wallet; INSERT `wallet_transactions` (BOOKING_DEBIT, DEBIT).
4. CREDIT Super Admin wallet; INSERT `wallet_transactions` (SUPER_ADMIN_REVENUE_CREDIT, CREDIT).
5. INSERT `revenue_collections` (BOOKING_CHARGE) linking both transaction IDs.
6. UPDATE booking_status → CONFIRMED; generate QR (booking reference).
7. COMMIT; any failure → ROLLBACK.

**Cancellation (atomic):** lookup rule → compute refund/penalty → credit customer → debit Super Admin → INSERT REFUND_REVERSAL collection → UPDATE booking CANCELLED → slot becomes AVAILABLE.

**Overtime (atomic):** compute overstay → debit customer → credit Super Admin → INSERT OVERTIME_CHARGE collection → mark paid → permit EXIT.

**Entry/Exit:** QR/manual scan → INSERT booking_events (ENTRY/EXIT) with unique constraint; slot live status derived from events.

**Revenue reconciliation:** each collection's two ledger legs equal `rc.amount`; net collection sum = Super Admin wallet's net ledger movement.

## A.9 Oracle migration notes
- `INTEGER PRIMARY KEY AUTOINCREMENT` → `NUMBER GENERATED ALWAYS AS IDENTITY` (or sequence + trigger for older Oracle).
- `TEXT` → `VARCHAR2` (with size) or `CLOB` for long text (old_values/new_values).
- `NUMERIC` → `NUMBER(18,2)` for money; use `CHECK (col >= 0)`.
- `DATETIME`/`TEXT` timestamps → `TIMESTAMP` or `DATE`; replace `datetime('now')` with `SYSTIMESTAMP`.
- Partial unique indexes (`WHERE ...`) → Oracle filtered unique indexes or function-based unique indexes.
- Triggers (`trg_*`) → PL/SQL triggers; `RAISE(ABORT,...)` → `RAISE_APPLICATION_ERROR`.
- `ON DELETE SET NULL` / `RESTRICT` → Oracle `ON DELETE SET NULL` / `NO ACTION` (default).
- Soft delete via `account_status = 'DELETED'` is portable.
- `reserved1`/`reserved2` columns allow additive changes without DDL in Oracle (use as JSON/extension hooks).
- Concurrency: replace SQLite `BEGIN IMMEDIATE` with Oracle `SELECT ... FOR UPDATE` row locking; `transaction_reference` needs uuid/microsecond to avoid collisions.
- Sequences: ensure `transaction_reference` generation uses `SYS_GUID()` or timestamp+uuid.

---

# Part B — REST API Reference

## B.1 Conventions
- Base URL: `http://127.0.0.1:5000` (dev). All endpoints return JSON.
- Auth: session cookie (`POST /api/auth/login`). Roles from DB (`users.role`).
- CSRF: all POST/PUT/PATCH/DELETE require `X-CSRFToken` (or `csrf_token` form field). GET/HEAD/OPTIONS exempt. 400 on missing/invalid.
- Error shape: `{"error": "<msg>", "code": <http>}`.
- Roles: `CUSTOMER`, `ADMIN`, `SUPER_ADMIN`. "Admin+" = ADMIN or SUPER_ADMIN.
- `QS` (frontend) sends CSRF automatically; pages must use `QS.*`, never raw fetch.

## B.2 Endpoint catalog (by blueprint)

### Auth (`/api/auth`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | /api/auth/login | public | Session login (username or email + password) |
| POST | /api/auth/logout | any | End session |
| GET | /api/auth/me | any | Current user (wallet refreshed) |
| PATCH | /api/auth/me | any | Self-service profile edit |
| POST | /api/auth/session/end | any | End session (alias) |
| POST | /api/auth/setup-admin | public (bootstrap) | One-time Super Admin + default admins |

### Slots (`/api/slots`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | /api/slots/floors | public | Floors with live capacity counts |
| GET | /api/slots/vehicle-types | public | Active vehicle types + rates |
| GET | /api/slots/availability | public | Slots with live status (filterable) |
| GET | /api/slots/<slot_id> | any | Single slot detail |

### Bookings (`/api/bookings`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | /api/bookings/hold | customer+ | Create HELD booking |
| POST | /api/bookings/<ref>/confirm | customer+ | Confirm (wallet debit + revenue) |
| GET | /api/bookings/<ref> | customer+ | Booking detail |
| POST | /api/bookings/<ref>/cancel | customer+ | Cancel with refund |
| GET | /api/bookings/my | customer+ | My bookings (paged/filterable) |
| GET | /api/bookings/wallet/transactions/me | customer+ | My wallet ledger |

### QR (`/api/qr`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | /api/qr/generate | customer+ | Generate QR for booking |
| POST | /api/qr/scan | admin+ | Scan QR for entry/exit |

### Admin (`/api/admin`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | /api/admin/dashboard | admin+ | KPIs (slots by state, revenue, users) |
| GET | /api/admin/floors | admin+ | Floors with available/reserved/occupied/maintenance counts |
| GET | /api/admin/vehicle-types | admin+ | All vehicle types |
| GET | /api/admin/slots | admin+ | Slots with live status + occupant info |
| PATCH | /api/admin/slots/<id>/control-status | admin+ | Change slot control status |
| GET | /api/admin/users | admin+ | List customers |
| POST | /api/admin/users | admin+ | Create customer |
| GET | /api/admin/users/<id> | admin+ | Customer detail |
| PUT | /api/admin/users/<id> | admin+ | Update customer |
| DELETE | /api/admin/users/<id> | admin+ | Soft-delete customer |
| GET | /api/admin/users/<id>/wallet | admin+ | Wallet balance |
| POST | /api/admin/users/<id>/wallet-adjustments | admin+ | Credit/debit wallet (ledgered) |
| GET | /api/admin/bookings | admin+ | All bookings (filterable/paged) |
| GET | /api/admin/cancellation-rules | admin+ | List rules |
| POST | /api/admin/cancellation-rules | admin+ | Create rule |
| PUT | /api/admin/cancellation-rules/<id> | admin+ | Update rule |
| DELETE | /api/admin/cancellation-rules/<id> | admin+ | Deactivate rule |
| GET | /api/admin/master/* | admin+ | Backward-compat aliases (floors/vehicle-types/slots/users) |
| POST | /api/admin/qr/scan | admin+ | QR scan (alias) |
| GET | /api/admin/reports/occupancy | admin+ | Floor occupancy heat-map (date filterable) |
| GET | /api/admin/reports/occupancy-csv | super admin | CSV download |
| GET | /api/admin/reports/revenue | admin+ | Revenue per floor (date filterable) |
| GET | /api/admin/reports/revenue-csv | super admin | CSV download |
| GET | /api/admin/reports/revenue-summary | super admin | Revenue by collection type |

### Super Admin (`/api/super-admin`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET/POST | /api/super-admin/admins | super admin | List/create admins |
| GET/PUT/DELETE | /api/super-admin/admins/<id> | super admin | Admin CRUD |
| PATCH | /api/super-admin/admins/<id>/status | super admin | Block/unblock admin |
| GET/POST/PUT/DELETE | /api/super-admin/floors[/<id>] | super admin | Floor CRUD |
| POST | /api/super-admin/floors/<id>/slots | super admin | Add slots to floor |
| PUT/DELETE | /api/super-admin/slots/<id> | super admin | Slot update/delete |
| GET/POST | /api/super-admin/users/<id>/wallet[/-adjustments] | super admin | Wallet ops |
| POST | /api/super-admin/bookings/<ref>/cancel | super admin | Cancel any booking |
| GET | /api/super-admin/analytics/overview | super admin | KPIs + occupancy % |
| GET | /api/super-admin/analytics/overtime | super admin | Overtime by day |
| GET | /api/super-admin/analytics/floor-heatmap | super admin | Floor occupancy (date filterable) |
| GET | /api/super-admin/analytics/revenue | super admin | Revenue by floor/type/day |
| GET | /api/super-admin/db-tables/<table> | super admin | Whitelisted read-only table view |
| GET | /api/super-admin/reports/occupancy.csv | super admin | CSV (alias) |
| GET | /api/super-admin/reports/revenue.csv | super admin | CSV (alias) |

### System (`/api/system`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | /api/system/status | public | System ONLINE/OFFLINE |
| PATCH | /api/system/super-admin/system/status | super admin | Toggle system status |
| GET/PATCH | /api/system/super-admin/session | super admin | Session policy (timeout) |

### Page routes (server-rendered shells)
`/`, `/landing`, `/login`, `/dashboard`, `/booking`, `/confirm/<ref>`, `/bookings/my`, `/wallet`, `/profile`, `/admin/dashboard`, `/admin/bookings`, `/admin/customers`, `/admin/qr-scan`, `/admin/slots`, `/admin/analytics`, `/admin/master`, `/super-admin/dashboard`, `/super-admin/admins`, `/super-admin/analytics`, `/super-admin/infrastructure`, `/super-admin/data`, `/super-admin/system`.

## B.3 Detailed endpoint contracts (selected high-value)

### POST /api/auth/login
- Body: `{"username": "...", "password": "..."}` (or form data; email also accepted as username).
- 200: `{"user": {user_id, username, email, full_name, role, wallet_balance, phone}}` + session cookie.
- 400 missing fields; 401 invalid credentials; 429 (if rate-limited). CSRF required.
- Logic: lookup by username or email; verify bcrypt hash; check account_status ACTIVE; set session.

### POST /api/bookings/hold
- Body: `{vehicle_format, vehicle_number, vehicle_type_id, floor_id, slot_id?, booked_from, booked_until}`.
- Validates format (std1/std2/std3/bhr), duplicate active vehicle, slot availability, floor status, time window (05:00–23:00, ≤18h, 30-min increments).
- 201: `{booking_reference, booking_status: "HELD", hold_expires_at, estimated_amount, ...}`. Slot reserved for 30 min.

### POST /api/bookings/<ref>/confirm
- Atomic transaction (see A.8). Wallet debit + Super Admin credit + revenue collection + status CONFIRMED + QR.
- 200: `{booking_reference, booking_status: "CONFIRMED", qr_base64}`.
- 400 insufficient balance / slot no longer available; 409 conflict.

### POST /api/qr/scan
- Body: `{qr_payload or booking_reference, event_type: "ENTRY"|"EXIT", scan_method}`.
- ENTRY: validates booking CONFIRMED, no prior entry → INSERT booking_events(ENTRY); slot becomes OCCUPIED.
- EXIT: validates entry exists; checks overtime paid; INSERT booking_events(EXIT); status COMPLETED; slot becomes AVAILABLE.
- Returns `{booking_reference, event_type, timestamp, slot_status}`.

### GET /api/admin/slots?floor_id=
- Returns `{items: [{slot_id, slot_number, floor_id, vehicle_type_id, control_status, status, floor_code, vehicle_type, occupant}], total}`.
- `occupant` is null for free slots; otherwise `{booking_reference, full_name, username, vehicle_number, booked_from, booked_until, booking_status, entry_time}`.

### GET /api/admin/reports/revenue?date_from=&date_to=
- Returns `{floor_revenue: [{floor_code, booking_count, total_revenue, net_revenue}], grand_total, date_from, date_to}`.
- Driven by `revenue_collections` (date filter on `rc.created_at`); booking_count = distinct bookings with collections.

### GET /api/super-admin/analytics/revenue?date_from=&date_to=
- Returns `{by_floor: [{floor_code, amount}], by_vehicle_type: [{type_name, amount}], by_day: [{day, amount}]}`.

### GET /api/super-admin/analytics/floor-heatmap
- Returns `{floors: [{floor_code, floor_status, total_slots, occupied_slots, occupancy_percent}]}`.

### GET /api/super-admin/db-tables/<table_name>
- Whitelisted read-only table view (paginated). Never exposes passwords/hashes/secrets or arbitrary SQL. Allowed tables: users (sanitized), floors, vehicle_types, parking_slots, bookings, cancellation_rules, wallet_transactions, booking_events, audit_logs, revenue_collections, system_settings.

### PATCH /api/system/super-admin/system/status
- Body: `{"system_status": "ONLINE"|"OFFLINE"}`. OFFLINE blocks customer bookings and admin writes; Super Admin retains control access.

---

# Part C — Cross-reference (DB columns ↔ query params ↔ template fields)

## C.1 Slot status flow
| DB column | Computed status | API field | Template/JS field | Color |
|---|---|---|---|---|
| parking_slots.control_status | AVAILABLE | status | s.status | green |
| parking_slots.control_status | RESERVED | status | s.status | amber |
| parking_slots.control_status + booking_events | OCCUPIED | status | s.status | red |
| parking_slots.control_status | MAINTENANCE | status | s.status | grey |
| parking_slots.control_status | INACTIVE | status | s.status | grey |

## C.2 Booking → revenue linkage
| Table | Column | Linked to | Purpose |
|---|---|---|---|
| bookings | booking_id | revenue_collections.booking_id | Collection per booking |
| bookings | slot_id | parking_slots.slot_id | Slot occupancy |
| revenue_collections | customer_wallet_transaction_id | wallet_transactions.transaction_id | Customer debit leg |
| revenue_collections | super_admin_wallet_transaction_id | wallet_transactions.transaction_id | Super Admin credit leg |
| revenue_collections | source_user_id | users.user_id | Customer who generated charge |
| revenue_collections | super_admin_user_id | users.user_id | Receiving Super Admin |

## C.3 Template ↔ API ↔ DB map (key pages)
| Page | API calls | DB tables | Key fields displayed |
|---|---|---|---|
| /dashboard (customer) | /api/slots/floors, /api/bookings/my, /api/bookings/wallet/transactions/me | floors, parking_slots, bookings, wallet_transactions | available_slots, total_slots, booking_reference, balance_after |
| /admin/dashboard | /api/admin/dashboard, /api/admin/floors, /api/admin/bookings | parking_slots, floors, bookings, users, revenue_collections | available/reserved/occupied/maintenance counts, occupied_slots/total_slots |
| /admin/slots | /api/admin/floors, /api/admin/slots, /api/admin/vehicle-types | parking_slots, floors, vehicle_types, bookings, booking_events, users | slot_number, status, occupant (booking_reference, full_name, vehicle_number, entry_time) |
| /admin/analytics | /api/admin/reports/occupancy, /api/admin/reports/revenue, /api/admin/dashboard, /api/slots/floors, /api/slots/availability | floors, parking_slots, bookings, revenue_collections | occupancy_percent, net_revenue, slot heat map |
| /super-admin/analytics | /api/super-admin/analytics/*, /api/admin/dashboard, /api/slots/* | (same) | by_floor, by_vehicle_type, by_day, floors, donuts, line chart |
| /admin/analytics (heat map) | /api/slots/availability?floor_id= | parking_slots, bookings, booking_events | slot_number, status, vehicle_type |

## C.4 Vehicle plate formats (validation)
| Code | Pattern | Example |
|---|---|---|
| std1 | `^[A-Z]{2} [0-9]{2} [A-Z]{1} [0-9]{4}$` | KA 04 A 2256 |
| std2 | `^[A-Z]{2} [0-9]{2} [A-Z]{2} [0-9]{4}$` | DL 03 CA 1234 |
| std3 | `^[A-Z]{2} [0-9]{2} [A-Z]{3} [0-9]{4}$` | ML 04 ASD 5256 |
| bhr | `^[0-9]{2} BH [0-9]{4} [A-Z]{2}$` | 26 BH 9876 AB |

(Stored in `bookings.vehicle_format` and `bookings.vehicle_number`; partial unique index on `vehicle_number` for HELD/CONFIRMED.)

---

*End of reference. Keep in sync with `schema.sql` and registered routes; regenerate when schema or endpoints change.*