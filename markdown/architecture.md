# QSPARK — System Architecture Document (`architecture.md`)

## 1. Architectural Pattern & High-Level Topology
QSPARK is structured as a decoupled, asynchronous 3-tier enterprise web system:
1. **Client / Presentation Layer:** A responsive web application built with semantic HTML5, modular CSS (prepared for Tailwind CSS integration), and native JavaScript (Fetch API).
2. **Application & Business Logic Layer:** A high-throughput Python 3.14 backend powered by the FastAPI framework, handling authentication, request validation, pricing math, and state orchestration.
3. **Database & API Gateway Layer:** Oracle APEX running on Oracle Database (19c/21c/23ai), exposing relational tables and PL/SQL transactional procedures via Oracle REST Data Services (ORDS).


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
|  Base: /ords/smartparking/v2/      |  |  |  File: src/services/parking_local.db      |
|  - GET  /slots/                    |  |  |  Mirrors all 7 QSPARK_ Tables, Identity    |
|  - PUT  /slots/:id/status          |  |  |  Columns, and PL/SQL atomic procedures    |
|  - POST /bookings/                 |  |  |  (Allows 100% full-stack development while |
|  - PUT  /bookings/:id/checkout     |  |  |  Oracle APEX schema permissions are pending|
|  - PUT  /bookings/:id/cancel       |  |  +--------------------------------------------+
|  - GET  /analytics/kpi             |
+-----------------+------------------+
| SQL & PL/SQL Kernel
v
+-----------------------------------------------------------------------------------+
|                     DATABASE LAYER (Oracle APEX / Oracle Database)                |
|  7 Normalized Tables with PKs, FKs, Check Constraints & Triggers:                 |
|  - QSPARK_USERS (50 Users, Roles, Metro Card Wallet Balance)                      |
|  - QSPARK_FLOORS (B1, B2, B3, B4 Capacity Controls)                               |
|  - QSPARK_VEHICLE_TYPES (BIKE ₹5/hr, CAR ₹10/hr, Overstay Penalty Rates)           |
|  - QSPARK_PARKING_SLOTS (240 Physical Bays: 160 Bikes, 80 Cars)                   |
|  - QSPARK_BOOKINGS (Reservation Lifecycles & Timestamps)                          |
|  - QSPARK_WALLET_TRANSACTIONS (Metro Card Passbook / Debit-Refund Ledger)          |
|  - QSPARK_AUDIT_LOGS (Immutable System State Event History)                       |
+-----------------------------------------------------------------------------------+

## 2. Double-Booking Guard
If `v_slot_status != 'AVAILABLE'`, the transaction immediately aborts and returns an HTTP 409 Conflict payload: `{"error": "Slot is no longer available"}`.

## 3. Atomic Wallet Debit & Reservation
The slot status update to `RESERVED`, the debit from `QSPARK_USERS.wallet_balance`, the row creation in `QSPARK_BOOKINGS`, and the passbook entry in `QSPARK_WALLET_TRANSACTIONS` occur within a single atomic database transaction. If any step fails, an automatic rollback is executed.

## 4. Frontend Architecture & Extensibility
The client tier is structured into modular layers to allow clean incremental visual enhancements:
- **Phase 1 (Functional Baseline):** Semantic HTML5 templates styled with utility CSS, standard responsive flex/grid layouts, and vanilla JavaScript `fetch()` calls. Every button, booking modal, QR code pass, exit simulator, and admin heatmap functions end-to-end.
- **Phase 2 (Visual Polish):** Upgraded seamlessly with Tailwind CSS utility classes and interactive charting libraries (Chart.js / Recharts) without altering any backend endpoints or request payloads.
- **State Management:** Session storage caches the authenticated user ID, role, and current wallet balance. A unified event listener triggers balance refreshes across the navbar whenever a booking, cancellation, or checkout occurs.

## 5. Security & Network Specifications
- **Password Security:** Client submits plain passwords over HTTPS; backend computes `hashlib.sha256(password.encode()).hexdigest()` and verifies against `QSPARK_USERS.password_hash`. Plaintext passwords are never written to disk or logged.
- **Role Enforcement Middleware:** FastAPI dependencies inspect user roles before granting access to `/api/admin/*` routes.
- **No External Outbound Calls:** Zero network requests are made to external payment processors, SMS providers, or third-party cloud services.
