# QSPARK — Entity Relationship Diagram (ERD)

## Tables Overview

11 normalized tables with PK, UK, FK, CHECK constraints, indexes, and reserved columns.

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│    floors       │      │  vehicle_types   │      │  users          │
├─────────────────┤      ├──────────────────┤      ├─────────────────┤
│ floor_id (PK)   │      │ vehicle_type_id  │      │ user_id (PK)    │
│ floor_code (UK) │────┤ type_code (UK)   │      │ username (UK)   │
│ bike_capacity   │      │ display_name     │      │ email (UK)      │
│ car_capacity    │      │ hourly_rate      │      │ password_hash   │
│ status          │      │ overstay_rate    │      │ full_name       │
│ reserved1-3     │      │ total_slots_per_ │      │ role            │
│                 │      │ floor            │      │ wallet_balance  │
└─────────────────┘      │ reserved1-3      │      │ phone           │
                         └──────────────────┘      │ is_active       │
                                                   │ reserved1-3     │
                                                   └─────────────────┘
                                                            │
                              ┌─────────────────────────────┼─────────────────────────────┐
                              │                             │                             │
                              ▼                             ▼                             ▼
                         ┌───────────┐               ┌──────────────┐             ┌──────────────┐
                         │ park_slots│               │ bookings     │             │ wallet_trans │
                         ├───────────┤               ├──────────────┤             ├──────────────┤
                         │ slot_id   │               │ booking_id   │             │ txn_id (PK)  │
                         │ floor_id  │─┐             │ booking_ref  │────────────│ user_id (FK) │
                         │ vtype_id  │─┤             │ user_id (FK) │            │ booking_id   │
                         │ slot_num  │─┘             │ slot_id (FK) │            │ txn_type     │
                         │ status    │               │ vtype_id (FK)│            │ amount       │
                         │ reserved1-│               │ vehicle_num  │            │ prev_balance │
                         │   3       │               │ booked_from  │            │ new_balance  │
                         └───────────┘               │ booked_until │            │ created_at   │
                                                     │ actual_entry │            │ reserved1-3  │
                                                     │ actual_exit  │            └──────────────┘
                                                     │ status       │
                                                     │ estimated_am │
                                                     │ actual_amount│
                                                     │ overstay_hou │
                                                     │ overstay_amt │
                                                     │ overstay_paid│
                                                     │ qr_generated │
                                                     │ reserved1-3  │
                                                     └──────────────┘
                                                            │
                              ┌─────────────────────────────┼─────────────────────────────┐
                              │                             │                             │
                              ▼                             ▼                             ▼
                         ┌───────────┐               ┌──────────────┐             ┌──────────────┐
                         │book_events│               │ payments     │             │ audit_logs   │
                         ├───────────┤               ├──────────────┤             ├──────────────┤
                         │ event_id  │               │ payment_id   │             │ log_id (PK)  │
                         │ booking_id│───────────────│ booking_id   │────────────│ changed_by_uid│
                         │ event_type│               │ payment_ref  │             │ changed_at   │
                         │ event_ts  │               │ amount       │             │ table_name   │
                         │ scanned_by│               │ status       │             │ record_id    │
                         │ reserved1-│               │ payment_date │             │ action       │
                         │   3       │               │ reserved1-3  │             │ old_values   │
                         └───────────┘               └──────────────┘             │ new_values   │
                                                                                 │ reserved1-3  │
                                                                                 └──────────────┘
                                                                                 │
                                                                                 ▼
                                                                           ┌──────────────┐
                                                                           │ error_logs   │
                                                                           ├──────────────┤
                                                                           │ error_id (PK)│
                                                                           │ error_code   │
                                                                           │ error_message│
                                                                           │ endpoint     │
                                                                           │ request_data │
                                                                           │ occurred_at  │
                                                                           │ reserved1-3  │
                                                                           └──────────────┘
```

## Relationships

| Child Table | FK Column | Parent Table | Parent Column | On Delete |
|-------------|-----------|--------------|---------------|-----------|
| parking_slots | floor_id | floors | floor_id | CASCADE |
| parking_slots | vehicle_type_id | vehicle_types | vehicle_type_id | — |
| bookings | user_id | users | user_id | — |
| bookings | slot_id | parking_slots | slot_id | — |
| bookings | vehicle_type_id | vehicle_types | vehicle_type_id | — |
| payments | booking_id | bookings | booking_id | — |
| wallet_transactions | user_id | users | user_id | — |
| wallet_transactions | booking_id | bookings | booking_id | — |
| booking_events | booking_id | bookings | booking_id | — |
| booking_events | scanned_by_user_id | users | user_id | — |
| audit_logs | changed_by_user_id | users | user_id | — |
| error_logs | — | — | — | — |

## Constraints Summary

- **PK:** Every table has an auto-incrementing primary key
- **UK:** floor_code, type_code, slot_number, username, email, booking_reference, payment_reference
- **FK:** All relationships enforced with foreign keys
- **CHECK:** status values, role values, refund/penalty percentages, slot capacities, hourly rates
- **Indexes:** On FK columns, search columns (slot_number, booking_reference, username, floor_code), status columns
- **Reserved Columns:** reserved1, reserved2, reserved3 on all 11 tables
- **WHO Audit:** Only in audit_logs (changed_by_user_id, changed_at)
