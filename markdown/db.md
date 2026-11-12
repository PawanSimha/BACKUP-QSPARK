# QSPARK Smart Parking System - Database Design Documentation

## Overview

This document describes the complete database design for the QSPARK Smart Parking Slot Booking and Management System.
The schema consists of exactly 11 core tables with full integrity constraints, triggers, and relationships.

All 11 tables contain the six mandatory metadata columns at the end:
- `created_by` (FOREIGN KEY → users.user_id)
- `created_at` (default: current timestamp)
- `updated_by` (FOREIGN KEY → users.user_id)
- `updated_at` (default: current timestamp, updated on record change)
- `reserved1` (nullable TEXT)
- `reserved2` (nullable TEXT)

Foreign keys use `ON DELETE SET NULL` so historical records are not destroyed when an account is deactivated.
Normal user deletion is soft deletion (account_status = 'DELETED'), not physical deletion.

---

## Table Descriptions

### 1. users

**Purpose:** Store all customers, three initial admins and one Super Admin in the same table.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| user_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| admin_id | TEXT | NO | NO | YES | (nullable for CUSTOMER) | | |
| full_name | TEXT | NO | NO | | YES | | |
| email | TEXT | NO | NO | YES | (nullable for on-site reg) | | |
| phone | TEXT | NO | NO | | YES | | |
| gender | TEXT | NO | NO | | | CHECK (MALE/FEMALE/OTHER/PREFER_NOT_TO_SAY) | |
| company_name | TEXT | NO | NO | | | | |
| username | TEXT | NO | NO | YES | | | |
| password_hash | TEXT | NO | NO | | | (nullable for unactivated) | |
| role | TEXT | NO | NO | | YES | CHECK (CUSTOMER/ADMIN/SUPER_ADMIN) | |
| wallet_balance | NUMERIC | NO | NO | | YES | 1000 | >= 0 |
| account_status | TEXT | NO | NO | | YES | DEFAULT 'PENDING' | PENDING/ACTIVE/BLOCKED/DELETED |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Constraints:**
- `admin_id` must be NULL for CUSTOMER; must exist for ADMIN/SUPER_ADMIN
- Only one SUPER_ADMIN account allowed (enforced at application level)
- At least one login identifier (username or email) must exist
- ACTIVE account must have valid password hash
- Wallet balance cannot be negative

**Relationships:**
- users.user_id → bookings.user_id (RESTRICT)
- users.user_id → wallet_transactions.user_id (RESTRICT)
- users.user_id → audit_logs.created_by (SET NULL)
- users.user_id → audit_logs.updated_by (SET NULL)
- users.user_id → revenue_collections.source_user_id (RESTRICT)
- users.user_id → revenue_collections.super_admin_user_id (RESTRICT)

---

### 2. floors

**Purpose:** Store parking floor information.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| floor_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| floor_code | TEXT | NO | NO | YES | YES | | |
| floor_status | TEXT | NO | NO | | YES | DEFAULT 'OPEN' | OPEN/CLOSED/MAINTENANCE/INACTIVE |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Relationships:**
- floors.floor_id → parking_slots.floor_id (RESTRICT, no cascade)

---

### 3. vehicle_types

**Purpose:** Maintain vehicle categories and parking rates.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| vehicle_type_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| type_name | TEXT | NO | NO | YES | YES | | |
| hourly_rate | NUMERIC | NO | NO | | YES | >= 0 | |
| overstay_rate | NUMERIC | NO | NO | | YES | >= 0 | |
| is_active | INTEGER | NO | NO | | YES | DEFAULT 1 | 0 or 1 |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Relationships:**
- vehicle_types.vehicle_type_id → parking_slots.vehicle_type_id

---

### 4. parking_slots

**Purpose:** Store every individual parking spot.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| slot_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| floor_id | INTEGER | NO | YES → floors.floor_id | | YES | | ON DELETE RESTRICT |
| vehicle_type_id | INTEGER | NO | YES → vehicle_types.vehicle_type_id | | YES | | |
| slot_number | TEXT | NO | NO | | YES | | |
| control_status | TEXT | NO | NO | | YES | DEFAULT 'ACTIVE' | ACTIVE/ADMIN_RESERVED/MAINTENANCE/INACTIVE |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Unique Constraints:**
- UNIQUE(floor_id, slot_number)

**Calculated Display Status (from application logic, not stored manually):**
- AVAILABLE: no active booking, control_status = ACTIVE
- RESERVED: active HELD/CONFIRMED booking not yet entered, or ADMIN_RESERVED
- OCCUPIED: confirmed booking has ENTRY without EXIT
- MAINTENANCE: control_status = MAINTENANCE
- INACTIVE: unavailable for new bookings

**Relationships:**
- parking_slots.floor_id → floors.floor_id (RESTRICT)
- parking_slots.vehicle_type_id → vehicle_types.vehicle_type_id

---

### 5. bookings

**Purpose:** Store all parking booking records.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| booking_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| booking_reference | TEXT | NO | NO | YES | YES | | |
| user_id | INTEGER | NO | YES → users.user_id | | YES | | ON DELETE RESTRICT |
| slot_id | INTEGER | NO | YES → parking_slots.slot_id | | YES | | ON DELETE RESTRICT |
| vehicle_format | TEXT | NO | NO | | YES | ('std1'/'std2'/'std3'/'bhr') | |
| vehicle_number | TEXT | NO | NO | YES (partial, active statuses) | | | |
| booked_from | DATETIME | NO | NO | | YES | | |
| booked_until | DATETIME | NO | NO | | YES | > booked_from | |
| hold_expires_at | TEXT | NO | YES | | | | (30 min from hold) |
| hourly_rate_applied | NUMERIC | NO | NO | | YES | >= 0 | Stored at booking time |
| overstay_rate_applied | NUMERIC | NO | NO | | YES | >= 0 | Stored at booking time |
| estimated_amount | NUMERIC | NO | NO | | YES | >= 0 | Stored at booking time |
| booking_status | TEXT | NO | NO | | YES | DEFAULT 'HELD' | HELD/CONFIRMED/COMPLETED/CANCELLED/EXPIRED |
| applied_cancellation_rule_id | INTEGER | NO | YES → cancellation_rules.rule_id | | | | ON DELETE SET NULL |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Constraints:**
- booked_until > booked_from
- Rates and estimated_amount cannot be negative
- Partial unique index on vehicle_number for active statuses HELD and CONFIRMED

**Status Transitions (application-enforced):**
- HELD → CONFIRMED
- HELD → CANCELLED
- HELD → EXPIRED (after 30 minutes without confirmation)
- CONFIRMED → COMPLETED
- CONFIRMED → CANCELLED
- All other transitions rejected

**Relationships:**
- bookings.user_id → users.user_id (RESTRICT)
- bookings.slot_id → parking_slots.slot_id (RESTRICT)
- bookings.applied_cancellation_rule_id → cancellation_rules.rule_id (SET NULL)

---

### 6. cancellation_rules

**Purpose:** Store configurable cancellation and refund conditions.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| rule_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| rule_code | TEXT | NO | NO | YES | YES | | |
| rule_name | TEXT | NO | NO | | YES | | |
| min_hours_before | NUMERIC | NO | NO | | YES | >= 0 (nullable) | |
| max_hours_before | NUMERIC | NO | NO | | YES | > min_hours (nullable) | |
| is_no_show | INTEGER | NO | NO | | YES | DEFAULT 0 | 0 or 1 |
| refund_percent | NUMERIC | NO | NO | | YES | 0-100 | |
| penalty_percent | NUMERIC | NO | NO | | YES | DEFAULT 0 | 0-100 |
| description | TEXT | NO | NO | | | | |
| is_active | INTEGER | NO | NO | | YES | DEFAULT 1 | 0 or 1 |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Seed Data:**
- MORE_24H: >24h before start → 100% refund
- BETWEEN_1_24H: 1-24h before → 50% refund
- LESS_1H: <1h before → 0% refund + penalty
- NOSHOW: no-show/cancel after start → 0% refund

**Relationships:**
- cancellation_rules.rule_id → bookings.applied_cancellation_rule_id (SET NULL)

---

### 7. wallet_transactions

**Purpose:** Maintain the complete transaction history for every customer, admin and Super Admin wallet.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| transaction_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| transaction_reference | TEXT | NO | NO | YES | YES | | |
| user_id | INTEGER | NO | YES → users.user_id | | YES | | ON DELETE RESTRICT |
| booking_id | INTEGER | NO | YES → bookings.booking_id | | | | ON DELETE SET NULL |
| transaction_type | TEXT | NO | NO | | YES | ('BOOKING_DEBIT'/'OVERTIME_DEBIT'/'CANCELLATION_REFUND'/'ADMIN_ADJUSTMENT'/'SUPER_ADMIN_REVENUE_CREDIT'/'REVENUE_REFUND_REVERSAL') | |
| direction | TEXT | NO | NO | | YES | ('DEBIT'/'CREDIT') | |
| amount | NUMERIC | NO | NO | | YES | > 0 | |
| balance_after | NUMERIC | NO | NO | | YES | >= 0 | |
| description | TEXT | NO | NO | | | | |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Relationships:**
- wallet_transactions.user_id → users.user_id (RESTRICT)
- wallet_transactions.booking_id → bookings.booking_id (SET NULL)

---

### 8. booking_events

**Purpose:** Store QR-based and manual vehicle entry and exit events.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| event_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| booking_id | INTEGER | NO | YES → bookings.booking_id | | YES | | ON DELETE RESTRICT |
| event_type | TEXT | NO | NO | | YES | ('ENTRY'/'EXIT') | |
| scan_method | TEXT | NO | NO | | YES | ('QR'/'MANUAL') | |
| event_note | TEXT | NO | NO | | | | |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Unique Partial Indexes:**
- One ENTRY event per booking (UNIQUE WHERE event_type = 'ENTRY')
- One EXIT event per booking (UNIQUE WHERE event_type = 'EXIT')

**Constraints:**
- Every event must reference a valid booking
- One ENTRY per booking
- One EXIT per booking
- EXIT not allowed before ENTRY
- EXIT blocked if outstanding overtime payment

**Relationships:**
- booking_events.booking_id → bookings.booking_id (RESTRICT)
- booking_events.created_by → users.user_id (SET NULL)

---

### 9. audit_logs

**Purpose:** Record actions performed by Admins and the Super Admin.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| audit_log_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| action_type | TEXT | NO | NO | | YES | | |
| entity_type | TEXT | NO | NO | | YES | | |
| entity_id | INTEGER | NO | YES (nullable) | | | | |
| old_values | TEXT | NO | NO | | | | |
| new_values | TEXT | NO | NO | | | | |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Action Types:**
- CREATE_USER, UPDATE_USER, DELETE_USER
- CREATE_ADMIN, UPDATE_ADMIN, DELETE_ADMIN
- BLOCK_ADMIN, UNBLOCK_ADMIN
- WALLET_ADJUSTMENT
- SLOT_RESERVED, SLOT_MAINTENANCE
- BOOKING_CANCELLED
- FLOOR_CREATED, FLOOR_UPDATED, FLOOR_DEACTIVATED
- SLOT_CREATED, SLOT_UPDATED
- SYSTEM_OFFLINE, SYSTEM_ONLINE

**Constraints:**
- No physical deletion of historical audit records
- created_by identifies the person performing the action

**Relationships:**
- audit_logs.created_by → users.user_id (SET NULL)
- audit_logs.updated_by → users.user_id (SET NULL)

---

### 10. revenue_collections

**Purpose:** Maintain a permanent record of money collected from customer wallet deductions and credited to the Super Admin wallet.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| collection_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| source_user_id | INTEGER | NO | YES → users.user_id | | YES | | ON DELETE RESTRICT |
| super_admin_user_id | INTEGER | NO | YES → users.user_id | | YES | SUPER_ADMIN only | |
| booking_id | INTEGER | NO | YES → bookings.booking_id | | YES | | ON DELETE RESTRICT |
| customer_wallet_transaction_id | INTEGER | NO | YES → wallet_transactions.transaction_id | | YES | UNIQUE | |
| super_admin_wallet_transaction_id | INTEGER | NO | YES → wallet_transactions.transaction_id | | YES | UNIQUE | |
| collection_type | TEXT | NO | NO | | YES | ('BOOKING_CHARGE'/'OVERTIME_CHARGE'/'REFUND_REVERSAL') | |
| amount | NUMERIC | NO | NO | | YES | > 0 | |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Business Logic:**
- One collection record per customer transaction
- source_user_id = user whose booking generated the charge
- super_admin_user_id = the SUPER_ADMIN account
- customer_wallet_transaction_id links to the BOOKING_DEBIT transaction
- super_admin_wallet_transaction_id links to the SUPER_ADMIN_REVENUE_CREDIT transaction

**Relationships:**
- revenue_collections.source_user_id → users.user_id (RESTRICT)
- revenue_collections.super_admin_user_id → users.user_id (RESTRICT, SUPER_ADMIN)
- revenue_collections.booking_id → bookings.booking_id (RESTRICT)
- revenue_collections.customer_wallet_transaction_id → wallet_transactions.transaction_id (RESTRICT)
- revenue_collections.super_admin_wallet_transaction_id → wallet_transactions.transaction_id (RESTRICT)

---

### 11. system_settings

**Purpose:** Store global system settings managed by the Super Admin.

| Column | Type | PK | FK | Unique | Not Null | Default | Check |
|---|---|---|---|---|---|---|---|
| setting_id | INTEGER | YES | NO | AUTOINCREMENT | | | |
| setting_key | TEXT | NO | NO | YES | YES | | |
| setting_value | TEXT | NO | NO | | YES | | |
| description | TEXT | NO | NO | | | | |
| created_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| created_at | TEXT | NO | NO | | YES | datetime('now') | |
| updated_by | INTEGER | NO | YES → users.user_id | | | | ON DELETE SET NULL |
| updated_at | TEXT | NO | NO | | YES | datetime('now') ON UPDATE datetime('now') | |
| reserved1 | TEXT | NO | NO | | | | nullable |
| reserved2 | TEXT | NO | NO | | | | nullable |

**Seed Data:**
- SYSTEM_STATUS = ONLINE

**Super Admin Controls:**
- Can switch system between ONLINE and OFFLINE
- When OFFLINE: customers cannot create/confirm bookings, admins cannot perform write actions
- Super Admin retains access to system control interface

**Relationships:**
- system_settings.created_by → users.user_id (SET NULL)
- system_settings.updated_by → users.user_id (SET NULL)

---

## Complete Table Relationship List

```
users (1)-------(M) bookings
  |               |
  |               +-------(1) wallet_transactions
  |                               |
  +-------(1) revenue_collections (as source_user)
  +-------(1) revenue_collections (as super_admin_user)
  +-------(1) audit_logs (as created_by)
  +-------(1) audit_logs (as updated_by)
  +-------(1) system_settings (as created_by)
  +-------(1) system_settings (as updated_by)

floors (1)-------(M) parking_slots
  |               |
  +-------(1) admin dashboard counts (calculated)

vehicle_types (1)-------(M) parking_slots

parking_slots (1)-------(M) bookings
  |               |
  |               +-------(1) wallet_transactions (via booking_id)
  +-------(1) revenue_collections (via booking_id)
  +-------(1) booking_events (via booking_id)

bookings (1)-------(M) wallet_transactions (via booking_id)
  |               |
  +-------(1) booking_events (one-to-many)

cancellation_rules (1)-------(M) bookings (applied_cancellation_rule_id)

booking_events (1)-------(M) audit_logs (via created_by)

users (1)-------(M) audit_logs (via created_by/updated_by)

users (1)-------(1) system_settings (via created_by/updated_by)

revenue_collections (1)-------(1) wallet_transactions (customer)
revenue_collections (1)-------(1) wallet_transactions (Super Admin)
```

---

## Indexes

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

---

## Database Triggers

| Trigger Name | Table | Purpose |
|---|---|---|
| trg_no_overlapping_bookings | bookings | Reject overlapping active (HELD/CONFIRMED) bookings for the same slot (BEFORE INSERT) |
| trg_booking_status_transitions | bookings | Reject illegal booking_status transitions (BEFORE UPDATE) |
| trg_exit_requires_entry | booking_events | Reject EXIT event before ENTRY exists |
| trg_protect_active_user_delete | users | Block physical deletion of users with active bookings (forces soft delete) |

## Partial Unique Indexes (integrity)

| Index Name | Table | Definition |
|---|---|---|
| uq_active_vehicle_number | bookings | UNIQUE(vehicle_number) WHERE booking_status IN ('HELD','CONFIRMED') |
| uq_one_entry_per_booking | booking_events | UNIQUE(booking_id) WHERE event_type='ENTRY' |
| uq_one_exit_per_booking | booking_events | UNIQUE(booking_id) WHERE event_type='EXIT' |

Note: Live slot display status (AVAILABLE/RESERVED/OCCUPIED) is computed in application
queries from bookings + booking_events; it is NOT stored as a mutable control_status value.
`parking_slots.control_status` only stores ACTIVE / ADMIN_RESERVED / MAINTENANCE / INACTIVE.

---

## Booking State Transitions

```
HELD
  ├──→ CONFIRMED (after wallet payment)
  ├──→ CANCELLED (with refund per cancellation_rule)
  └──→ EXPIRED (after 30 minutes unconfirmed)

CONFIRMED
  ├──→ COMPLETED (after EXIT scan)
  └──→ CANCELLED (with refund per cancellation_rule)

All other transitions are REJECTED by application logic.
```

---

## Wallet Transaction Logic

**On Booking Confirmation (atomic transaction):**
1. Validate user's wallet balance >= estimated_amount
2. DEBIT estimated_amount from customer wallet
3. INSERT wallet_transactions (BOOKING_DEBIT, DEBIT, amount, balance_after)
4. CREDIT estimated_amount to Super Admin wallet
5. INSERT wallet_transactions (SUPER_ADMIN_REVENUE_CREDIT, CREDIT, amount, balance_after)
6. INSERT revenue_collections (BOOKING_CHARGE, source_user, super_admin, booking_id, customer_txid, super_admin_txid, amount)
7. UPDATE booking_status → CONFIRMED
8. Generate QR code

**On Cancellation (atomic transaction):**
1. Lookup cancellation_rule for the booking
2. Calculate refund_percent and penalty_percent
3. CREDIT refund_amount to customer wallet (minus penalty)
4. INSERT wallet_transactions (CANCELLATION_REFUND, CREDIT, refund_amount, balance_after)
5. DEBIT refund_amount from Super Admin wallet
6. INSERT wallet_transactions (ADMIN_ADJUSTMENT or similar, DEBIT, refund_amount, balance_after)
7. INSERT revenue_collections (REFUND_REVERSAL, source_user, super_admin, booking_id, customer_txid, super_admin_txid, refund_amount)
8. UPDATE booking_status → CANCELLED
9. Update slot status to AVAILABLE

**On Overtime (atomic transaction):**
1. Calculate overstay based on stored rate and actual exit time
2. Verify customer wallet balance >= overstay_amount
3. DEBIT overstay_amount from customer wallet
4. INSERT wallet_transactions (OVERTIME_DEBIT, DEBIT, overstay_amount, balance_after)
5. CREDIT overstay_amount to Super Admin wallet
6. INSERT wallet_transactions (SUPER_ADMIN_REVENUE_CREDIT, CREDIT, overstay_amount, balance_after)
7. INSERT revenue_collections (OVERTIME_CHARGE, source_user, super_admin, booking_id, customer_txid, super_admin_txid, overstay_amount)
8. UPDATE booking: actual_exit_time, overstay_hours, overstay_amount, overstay_paid=1, status=COMPLETED
9. Permit exit only after successful settlement

---

## Soft-Delete Rules

- User deletion: Set account_status = 'DELETED', do NOT physically delete
- All historical records (bookings, wallet_transactions, revenue_collections, audit_logs) are preserved
- ON DELETE SET NULL on foreign keys ensures historical records remain intact
- Admin/Super Admin accounts cannot be physically deleted if they have associated historical records
- Floor/slot reduction blocked if it would delete active bookings or occupied allocations

---

## ER Diagram (Mermaid format)

```mermaid
erDiagram
    USERS ||--o| BOOKINGS : creates
    USERS ||--o| WALLET_TRANSACTIONS : debits/credits
    USERS ||--o| REVENUE_COLLECTIONS : source user
    USERS ||--o| REVENUE_COLLECTIONS : receiving Super Admin
    USERS ||--o| AUDIT_LOGS : creates/updates
    USERS ||--o| SYSTEM_SETTINGS : creates/updates
    USERS ||--o| AUDIT_LOGS : modified by
    
    FLOORS ||--o| PARKING_SLOTS : has
    VEHICLE_TYPES ||--o| PARKING_SLOTS : category
    PARKING_SLOTS ||--o| BOOKINGS : accommodates
    PARKING_SLOTS ||--o| WALLET_TRANSACTIONS : via booking
    PARKING_SLOTS ||--o| REVENUE_COLLECTIONS : via booking
    PARKING_SLOTS ||--o| BOOKING_EVENTS : via booking
    
    BOOKINGS ||--o| WALLET_TRANSACTIONS : generates
    BOOKINGS ||--o| BOOKING_EVENTS : produces events
    BOOKINGS ||--o| CANCELLATION_RULES : applies rule
    BOOKINGS ||--o| REVENUE_COLLECTIONS : generates charge
    
    CANCELLATION_RULES ||--o| BOOKINGS : defines refund rules
    
    WALLET_TRANSACTIONS ||--o| REVENUE_COLLECTIONS : customer txn
    WALLET_TRANSACTIONS ||--o| REVENUE_COLLECTIONS : Super Admin txn
    
    SYSTEM_SETTINGS ||--o| USERS : created by/modified by
```