# QSPARK: system architecture (`architecture.md`)

## 1. Pattern and high-level topology
QSPARK is a decoupled, asynchronous three-tier web system:

1. **Client / presentation layer:** a responsive web app built with semantic HTML5, modular CSS prepared for Tailwind CSS, and native JavaScript (Fetch API).
2. **Application and business logic layer:** a Python 3.14 backend on FastAPI, handling authentication, request validation, pricing maths and state orchestration.
3. **Database and API gateway layer:** Oracle APEX on Oracle Database (19c/21c/23ai), which exposes relational tables and PL/SQL transactional procedures through Oracle REST Data Services (ORDS).


+-----------------------------------------------------------------------------------+
|                              CLIENT / PRESENTATION LAYER                          |
|   +---------------------------------------+   +-------------------------------+   |
|   |         Customer Booking Portal       |   |     Admin Command Center      |   |
|   | (B1-B4 Slot Grid, Wallet Pay, Pass)   |   | (Heatmap, Overrides, Audits)  |   |
|   +-------------------+-------------------+   +---------------+---------------+   |
+-----------------------|---------------------------------------|-------------------+
| JSON over HTTPS (Fetch API)           |
v                                       v
+-----------------------------------------------------------------------------------+
|                        APPLICATION LAYER (Python 3.14 / FastAPI)                  |
|   +---------------------------------------------------------------------------+   |
|   |  FastAPI App & Routers (/api/auth, /api/slots, /api/bookings, /api/kpi)   |   |
|   +---------------------------------------------------------------------------+   |
|   |  Core Business Engines:                                                   |   |
|   |  - SHA-256 Basic Authentication & Role Verification                       |   |
|   |  - Fixed Tariff Calculator (₹5 Bike / ₹10 Car)                            |   |
|   |  - Overstay Penalty Engine (10-min Grace, ₹10/hr Bike, ₹20/hr Car)        |   |
|   |  - Closed-Loop Metro Card Wallet Engine (Balance Verification & Debits)   |   |
|   +---------------------------------------------------------------------------+   |
|   |  Data Access Broker (Dual-Mode Interface):                                |   |
|   |  - Live ORDS HTTP Connector (Production Mode via Requests/HTTPX)          |   |
|   |  - In-Memory / SQLite Emulator (Local Fallback Mode: Zero-Block Dev)      |   |
|   +---------------------------------------------------------------------------+   |
+---------------------------------------|-------------------------------------------+
|
+-------------------------------+-------------------------------+
| If ORDS_SIMULATION_MODE=false |                               | If ORDS_SIMULATION_MODE=true
v (REST / JSON over HTTPS)      |                               v (Local Python SQLite Engine)
+------------------------------------+  |  +--------------------------------------------+
|         ORDS RESTFUL GATEWAY       |  |  |      LOCAL HIGH-FIDELITY EMULATOR          |
|  Base: .../qsparking/api/v2/       |  |  |  File: src/services/parking_local.db      |
|  - GET  /slots/                    |  |  |  Mirrors all 8 QSPARK_ Tables, Identity    |
|  - PUT  /slots/:id/status          |  |  |  Columns, and PL/SQL atomic procedures    |
|  - POST /bookings/                 |  |  |  (Allows 100% full-stack development while |
|  - PUT  /bookings/:id/checkout     |  |  |  Oracle APEX schema permissions are pending|
|  - PUT  /bookings/:id/cancel       |  |  +--------------------------------------------+
|  - GET  /analytics/kpi             |
|  - GET  /audit/logs                |
|  - POST /admin/audit-track         |
+-----------------+------------------+
| SQL & PL/SQL Kernel
v
+-----------------------------------------------------------------------------------+
|                     DATABASE LAYER (Oracle APEX / Oracle Database)                |
|  8 Normalized Tables with PKs, FKs, Check Constraints & Triggers:                 |
|  - QSPARK_USERS (50 Users, Roles, Metro Card Wallet Balance)                      |
|  - QSPARK_FLOORS (B1, B2, B3, B4 Capacity Controls)                               |
|  - QSPARK_VEHICLE_TYPES (BIKE ₹5/hr, CAR ₹10/hr, Overstay Penalty Rates)           |
|  - QSPARK_PARKING_SLOTS (240 Physical Bays: 160 Bikes, 80 Cars)                   |
|  - QSPARK_BOOKINGS (Reservation Lifecycles & Timestamps)                          |
|  - QSPARK_WALLET_TRANSACTIONS (Metro Card Passbook / Debit-Refund Ledger)          |
|  - QSPARK_AUDIT_LOGS (Immutable System State Event History)                       |
|  - QSPARK_AUDIT_TRACK (Manual Admin Change Register & Reasons)                    |
+-----------------------------------------------------------------------------------+

## 2. Double-booking guard
If `v_slot_status != 'AVAILABLE'`, the transaction aborts at once and returns an HTTP 409 Conflict payload: `{"error": "Slot is no longer available"}`.

## 3. Atomic wallet debit and reservation
The slot status update to `RESERVED`, the debit from `QSPARK_USERS.wallet_balance`, the new `QSPARK_BOOKINGS` row and the passbook entry in `QSPARK_WALLET_TRANSACTIONS` all happen in one database transaction. If any step fails, the whole thing rolls back.

## 4. Frontend architecture and extensibility
The client tier is split into layers so it can be improved in steps:
- **Phase 1 (functional baseline):** semantic HTML5 templates styled with utility CSS, standard responsive flex/grid layouts and vanilla JavaScript `fetch()` calls. Every button, booking modal, QR pass, exit simulator and admin heatmap works end to end.
- **Phase 2 (visual polish):** add Tailwind CSS utility classes and charting libraries (Chart.js / Recharts) without touching backend endpoints or request payloads.
- **State management:** session storage caches the authenticated user ID, role and current wallet balance. One event listener refreshes the balance in the navbar after every booking, cancellation or checkout.

## 5. Security and network
- **Passwords:** the client sends plain passwords over HTTPS; the backend computes `hashlib.sha256(password.encode()).hexdigest()` and compares it with `QSPARK_USERS.password_hash`. Plaintext passwords are never written to disk or logged.
- **Role enforcement:** FastAPI dependencies check user roles before allowing `/api/admin/*` routes.
- **No outbound calls:** the app makes zero network requests to payment processors, SMS providers or third-party cloud services.

## 6. FastAPI internal API to ORDS mapping (as built)
The browser only talks to FastAPI. The broker decides whether each call stays local or becomes an ORDS HTTP request. Live module: `qsparking.api.v2`; base URL `/ords/nov_2026_batch/qsparking/api/v2/`.

| Internal endpoint (`src/api/`) | Broker method | ORDS handler (live module) |
| :--- | :--- | :--- |
| `POST /api/auth/login` | `authenticate_user()` | *local only, no ORDS handler* |
| `GET /api/auth/me` | `get_user()` | *local only, no ORDS handler* |
| `GET /api/slots?floor_id=` | `get_slots()` | `GET slots/` |
| `PUT /api/slots/{slot_id}/status` | `update_slot_status()` | `PUT slots/:id/status` |
| `POST /api/bookings` | `create_booking()` | `POST bookings/` |
| `GET /api/bookings?user_id=` | `list_bookings()` | `GET bookings/` (optional `?user_id=`, SQLite fallback on network error) |
| `PUT /api/bookings/{id}/checkout` | `checkout_booking()` | `PUT bookings/:id/checkout` |
| `PUT /api/bookings/{id}/cancel` | `cancel_booking()` | `PUT bookings/:id/cancel` |
| `GET /api/analytics/kpi` | `get_analytics_kpi()` | `GET analytics/kpi` |
| `GET /api/analytics/audit` | `list_audit_logs()` | `GET audit/logs` (`limit`/`offset` pagination) |
| `POST /api/admin/audit-track` | `insert_audit_track()` | `POST admin/audit-track` (HTTP 201) |

Supporting endpoints: `GET /api/health` (liveness), `GET /api/status` (mode label), `GET /` (Jinja2 `index.html`). Broker exceptions are typed and mapped in one place in `src/main.py`: 400 invalid input, 402 insufficient funds, 404 not found, 409 state conflict (slot taken or not cancellable), 501 unsupported in live mode.

> **Live-data caveat (verified 2026-11-10):** the APEX Excel import stored `USER_ID` as decimals `1.001`–`1.050` instead of integers `1001`–`1050`. In live mode the broker temporarily scales outbound IDs ≥ 1000 (`user_id / 1000.0`) through `_live_user_id()`. Live data still needs normalising before cutover.

## 7. Dual-mode broker and Excel auto-seeder (verified)
- `src/services/ords_client.py` exposes the singleton `ords`. Configuration: `ORDS_SIMULATION_MODE`, `ORDS_BASE_URL`, `ORDS_TIMEOUT`, plus optional `QSPARK_DB_PATH` and `QSPARK_DATA_FILE`.
- **Simulation mode:** creates `src/services/parking_local.db`, applies the SQLite replica schema for all eight `QSPARK_` tables (including `reserved_col_1/2`), and on an empty database seeds the seven transactional tables straight from `Latest QSPARK.xlsx` with `openpyxl`. Sheet order is `QSPARK_USERS → QSPARK_FLOORS → QSPARK_VEHICLE_TYPES → QSPARK_PARKING_SLOTS → QSPARK_BOOKINGS → QSPARK_WALLET_TRANSACTIONS → QSPARK_AUDIT_LOGS` so foreign keys hold. The eighth tab `QSPARK_AUDIT_TRACK` is a manual admin register, so locally the table is created empty and never seeded. Seeding runs in one transaction (about 0.6 s); `reset_database()` drops and re-seeds for demos and tests.
- **Live mode:** the same methods issue `requests.Session` calls to the published ORDS paths. All nine endpoints are verified live and the broker now defaults to `/qsparking/api/v2/` (or `ORDS_BASE_URL`). `list_bookings()` calls `GET bookings/` (optional `user_id`), normalizes decimal `user_id` values and falls back to SQLite on network failure. `list_audit_logs()` and `insert_audit_track()` are wired, and `POST /api/admin/audit-track` returns 201. Outbound admin and user IDs ≥ 1000 are divided by 1000 until `USER_ID` is normalized. Auth and `get_user` have no ORDS handler, so they fall back to the local replica (`_ensure_db()`). `GET /health` aliases `GET /api/health` with the active mode.
- Write methods (`create_booking`, `checkout_booking`, `cancel_booking`, `update_slot_status`) use `BEGIN IMMEDIATE` transactions with rollback in simulation, mirroring the PL/SQL handlers.
