# Agent Activity Log

> Placeholder: Dedicated AI agent activity log recording every action, file created, and milestone completed.

---

## Setup Entry 001 — Documentation Scaffold Initialized

- **Date:** 2026-11-08
- **Phase:** Project initialization (documentation & agent-guidance only)
- **Action:** Created the `markdown/` folder in the project root.
- **Files created:**
  - `markdown/agents.md` — master rules, coding conventions, agent behavior
  - `markdown/prd.md` — product requirements document
  - `markdown/architecture.md` — Python + ORDS + local mock fallback
  - `markdown/database_and_ords.md` — 7 QSPARK_ tables & 5 ORDS endpoints
  - `markdown/frontend_and_flows.md` — UI specs & booking/overstay flows
  - `markdown/roadmap.md` — phased execution plan
  - `markdown/todo.md` — granular task checklist
  - `markdown/agent_tracker.md` — this activity log
- **Placeholder state:** Each document contains only a `# Title` header and a one-line placeholder description.
- **Respect boundary:** `README.md` left untouched until project completion. `MY_TRACK.md` (private manual tracker) never read, edited, or overwritten.
- **Milestone:** M0 — Documentation structure ready. No application code generated.
- **Next step:** Awaiting exact project context from the user before filling in any document or writing code.

---

## Setup Entry 002 — Python Environment & Project Skeleton

- **Date:** 2026-11-08
- **Phase:** Project initialization (environment only, no business logic)
- **Interpreter found:** Python 3.14.10 at `%LOCALAPPDATA%\Programs\Python\Python314\python.exe` (not on shell PATH; the `python` command resolved to the Microsoft Store stub).
- **Virtual environment:** Created `.venv` (isolated from global Python) and installed `requirements.txt` into it.
- **Files created:**
  - `.gitignore` — blocks venvs, secrets/wallets, Python caches, local DBs, `mytrack.md`/`MY_TRACK.md`, IDE/OS files
  - `.env.example` — safe-to-commit template with `APP_ENV`, `ORDS_SIMULATION_MODE`, `ORDS_BASE_URL`, `ORDS_TIMEOUT`, `SECRET_KEY`
  - `.env` — local copy of the template (git-ignored)
  - `requirements.txt` — fastapi, uvicorn, requests, pydantic, python-dotenv, openpyxl, pytest, httpx
  - `src/__init__.py`, `src/api/__init__.py`, `src/core/__init__.py`, `src/services/__init__.py`, `tests/__init__.py`
- **Folders created:** `src/`, `src/api/`, `src/core/`, `src/services/`, `src/static/`, `src/templates/`, `database/`, `tests/`
- **Respect boundary:** `README.md` untouched. `MY_TRACK.md` never read, edited, or overwritten.
- **Milestone:** M1 — Development environment and skeleton ready. No application code written.
- **Next step:** Awaiting instruction before adding any routes, models, or SQL.

---

## Setup Entry 003 — Operating Guidelines Written

- **Date:** 2026-11-08
- **Phase:** Documentation (agent-guidance)
- **Action:** Replaced the placeholder content in `markdown/agents.md` with the complete QSPARK AI Agent Operating Guidelines, verbatim as instructed (no points summarized or omitted).
- **File updated:** `markdown/agents.md`
  - Section 1 — Project Identity (QSPARK, Oracle APEX + ORDS + Python/FastAPI + HTML/JS stack)
  - Section 2 — Strict File & Security Boundaries (never touch `mytrack.md`; leave `README.md` untouched until completion; `.venv`-only installs; no hardcoded secrets — load from `.env` via `python-dotenv`; no external payment/SMS/email gateways — SHA-256 passwords and internal Metro Card `wallet_balance`)
  - Section 3 — Architectural & Coding Rules (dual-mode data layer with `ORDS_SIMULATION_MODE=true` SQLite replica of the 7 `QSPARK_` tables in `src/services/ords_client.py`; decoupled semantic HTML5 + modular vanilla JS with Tailwind-ready styling; mandatory timestamped entries here in `markdown/agent_tracker.md`)
- **Respect boundary:** `README.md` untouched. `mytrack.md` never read, edited, or overwritten.
- **Milestone:** M0 — Agent operating guidelines established.
- **Next step:** Awaiting the next file instruction from the user. No application code written.

---

## Setup Entry 004 — Product Requirements Document Written

- **Date:** 2026-11-08
- **Phase:** Documentation (product requirements)
- **Action:** Replaced the placeholder content in `markdown/prd.md` with the complete QSPARK PRD, verbatim as supplied (no section summarized, shortened, or omitted).
- **File updated:** `markdown/prd.md`
  - Section 1 — Executive Summary & Project Purpose (FastAPI + Oracle APEX via ORDS, closed-loop Metro Card wallet, no third-party gateways)
  - Section 2 — CEO Mandates & Non-Negotiable Constraints (Python/FastAPI, Oracle APEX 19c/21c/23ai, ORDS bridge, `ADMIN`/`USER` roles, no external payment/messaging, username-or-email + SHA-256 auth, live on `http://localhost:8000`)
  - Section 3 — Facility Topology & Slot Capacity (4 basements, 160 bikes at ₹5/hr + 80 cars at ₹10/hr = 240 slots, `B1-B01`…`B4-C20` numbering)
  - Section 4 — 50 seed accounts (admins 1001–1003 with `admin123`, users 1004–1050 with `user123`, ₹500.00 starting wallet, `hashlib.sha256` registration flow)
  - Section 5 — Tariffs and 10-minute-grace overstay penalty algorithm (bike ₹10/hr, car ₹20/hr, `OVERSTAY_DEBIT` settlement)
  - Section 6 — Metro Card wallet model (`BOOKING_DEBIT`, `CANCEL_REFUND`, atomic debit + slot `RESERVED` + booking creation)
  - Section 7 — Functional modules (auth/session, B1–B4 visual grid, booking & digital pass with QR simulation, self-service drawer & exit simulator, admin command center with KPI cards, heatmap, Chart.js charts, maintenance overrides, audit trail)
- **Respect boundary:** `README.md` untouched. `mytrack.md` never read, edited, or overwritten.
- **Milestone:** M0 — Product requirements documented.
- **Next step:** Awaiting the next file instruction from the user. No application code written.

---

## Setup Entry 005 — System Architecture Document Written

- **Date:** 2026-11-08
- **Phase:** Documentation (system architecture)
- **Action:** Replaced the placeholder content in `markdown/architecture.md` with the complete Technical & System Architecture Document, verbatim as supplied, including the full ASCII topology diagram (no section summarized, shortened, or omitted).
- **File updated:** `markdown/architecture.md`
  - Section 1 — Architectural Pattern & High-Level Topology: 3-tier decoupled stack (HTML5/CSS/vanilla JS client → Python 3.14 FastAPI application → Oracle APEX/Oracle Database via ORDS), core business engines (SHA-256 auth, ₹5/₹10 tariff calculator, 10-min-grace overstay penalty engine, Metro Card wallet engine), dual-mode data access broker, ORDS `v2` endpoint list (`/slots/`, `/slots/:id/status`, `/bookings/`, `/bookings/:id/checkout`, `/bookings/:id/cancel`, `/analytics/kpi`), SQLite fallback emulator at `src/services/parking_local.db`, and the 7 `QSPARK_` tables.
- **Respect boundary:** `README.md` untouched. `mytrack.md` never read, edited, or overwritten.
- **Milestone:** M0 — System architecture documented.
- **Next step:** Awaiting the next file instruction from the user. No application code written.

---

## Setup Entry 006 — Database Schema & ORDS Contract Written

- **Date:** 2026-11-08
- **Phase:** Documentation (database & API contract)
- **Action:** Replaced the placeholder content in `markdown/database_and_ords.md` with the complete Database Schema & ORDS REST API Specification. All 7 tables, every column, PK/FK/unique/check constraint, and all 5 API contracts were preserved.
- **File updated:** `markdown/database_and_ords.md`
  - Section 1 — 7 `QSPARK_` tables in Oracle DDL: `QSPARK_USERS` (identity from 1001), `QSPARK_FLOORS` (B1–B4, 40 bike / 20 car / 60 total), `QSPARK_VEHICLE_TYPES` (₹5/₹10 hourly, overstay rates), `QSPARK_PARKING_SLOTS` (240 bays, 4 statuses), `QSPARK_BOOKINGS` (identity from 10001, lifecycle + overstay fields), `QSPARK_WALLET_TRANSACTIONS` (identity from 20001, `BOOKING_DEBIT`/`OVERSTAY_DEBIT`/`CANCEL_REFUND`), `QSPARK_AUDIT_LOGS` (identity from 1, 5 event types).
  - Section 2 — ORDS contract under `http://<apex-host>:<port>/ords/<workspace>/smartparking/v2/`: `GET /slots/?floor_id={id}`, `PUT /slots/:id/status`, `POST /bookings/` (201/409/402), `PUT /bookings/:id/checkout`, `PUT /bookings/:id/cancel`, `GET /analytics/kpi`.
- **Formatting repair:** The supplied API 3 block arrived markdown-mangled (`PUT/bookings/...`, truncated payload `1.53`, stray `json`/`0` lines around the response). Restored the intended fence and `{"simulated_late_hours": 1.5}` payload; all numeric response values kept exactly as supplied (`penalty_charged: 15.0`, `final_total_amount: 30.0`).
- **Respect boundary:** `README.md` untouched. `mytrack.md` never read, edited, or overwritten.
- **Milestone:** M0 — Database schema and API contracts documented.
- **Next step:** Awaiting the next file instruction from the user. No application code written.

---

## Setup Entry 007 — Architecture Completed & Frontend Specification Written

- **Date:** 2026-11-08
- **Phase:** Documentation (architecture completion + frontend UI flows)
- **Clarification applied:** Checkout API example in `database_and_ords.md` is a BIKE slot (`B1-B14`), so 1.5 late hours × ₹10/hr = ₹15.0 penalty is correct; car rate would give ₹30.0. Example left as written — no edit needed.
- **Files updated:**
  - `markdown/architecture.md` — appended the previously separate Sections 2–5 verbatim: **2. Double-Booking Guard** (non-`AVAILABLE` slot aborts with HTTP 409 `{"error": "Slot is no longer available"}`), **3. Atomic Wallet Debit & Reservation** (slot `RESERVED` + wallet debit + `QSPARK_BOOKINGS` insert + `QSPARK_WALLET_TRANSACTIONS` passbook row in one transaction with rollback), **4. Frontend Architecture & Extensibility** (Phase 1 functional baseline, Phase 2 Tailwind/Chart.js polish, session-storage state + unified balance-refresh listener), **5. Security & Network Specifications** (SHA-256 password verification, `/api/admin/*` role middleware, no external outbound calls).
  - `markdown/frontend_and_flows.md` — replaced placeholder with the complete UI & Workflow specification, verbatim as supplied: design tokens and bay color palette (Sections 1–2), login screen (Section 3), 240-slot basement grid + fare calculator (Section 4), Metro Card payment modal (Section 5), digital QR parking pass (Section 6), bookings drawer with cancel + overstay exit simulator (Section 7), admin command center with KPIs, heatmap thresholds, Chart.js charts, maintenance overrides and audit log (Section 8).
- **Respect boundary:** `README.md` untouched. `mytrack.md` never read, edited, or overwritten.
- **Milestone:** M0 — Architecture and frontend specifications complete.
- **Next step:** Awaiting the next file instruction from the user. No application code written.

---

## Setup Entry 008 — Roadmap & Task Checklist Written

- **Date:** 2026-11-08
- **Phase:** Documentation (implementation planning)
- **Files updated:**
  - `markdown/roadmap.md` — full 5-phase plan, all milestones verbatim: Phase 1 environment/DDL/seed verification (Weeks 1–2), Phase 2 core backend & dual-mode ORDS broker (Weeks 3–4), Phase 3 customer portal & 240-slot grid (Weeks 5–6), Phase 4 admin command center, heatmaps & overstay simulator (Weeks 7–8), Phase 5 Oracle APEX cutover & deployment (Weeks 9–10).
  - `markdown/todo.md` — full granular checklist verbatim. 11 documentation/setup items ticked `[x]`; all database, backend, frontend, admin, and testing items remain `[ ]`.
- **Note:** The checklist line `- [ ] Initialize markdown/todo.md and verify initial tracking` was kept exactly as supplied, even though this entry initializes the file. Will tick it on confirmation.
- **Respect boundary:** `README.md` untouched (its update is scheduled for Phase 5 completion). `mytrack.md` never read, edited, or overwritten.
- **Milestone:** M0 — Documentation and planning phase complete.
- **Next step:** Awaiting the next file instruction from the user. No application code written.

---

## Setup Entry 009 — Foundational Database & Core Business Logic

- **Date:** 2026-11-08
- **Phase:** Implementation — Phase 1/2 foundations
- **Files created:**
  - `database/schema.sql` — Oracle DDL for all 7 `QSPARK_` tables with identity PKs (users 1001, bookings 10001, wallet 20001, others 1), unique/check constraints matching the spec, all foreign keys (`ON DELETE CASCADE` where specified), plus 10 performance indexes on FK and hot filter columns (floor+status, user+status, booking/slot lookups, wallet and audit history).
  - `database/ords_setup.sql` — ORDS `parking.api.v2` module (base path `v2/`) with `ORDS.ENABLE_SCHEMA`, `DEFINE_MODULE`, `DEFINE_TEMPLATE`, `DEFINE_PARAMETER` and `DEFINE_HANDLER` for all 6 endpoints: `GET slots/` (optional `floor_id` query param), `PUT slots/:id/status`, `POST bookings/` (atomic `FOR UPDATE` slot lock → 409 on non-`AVAILABLE`, wallet lock → 402 when short, booking insert, `BOOKING_DEBIT` ledger, slot `RESERVED`, audit row, commit), `PUT bookings/:id/checkout` (10-minute grace, ₹10/₹20 per hour penalty, `OVERSTAY_DEBIT` only when penalty > 0, slot freed, `COMPLETED`), `PUT bookings/:id/cancel` (refund + `CANCEL_REFUND` + slot freed), `GET analytics/kpi` (status counts, occupancy %, revenue, per-floor heatmaps). Responses emitted with `APEX_JSON`; handlers commit explicitly and `ROLLBACK` on failure.
  - `src/core/security.py` — `hash_password()` SHA-256 hex digest; `verify_password()` via `hmac.compare_digest`.
  - `src/core/pricing_engine.py` — `TARIFFS` (BIKE ₹5/₹10, CAR ₹10/₹20), `GRACE_PERIOD_HOURS = 10/60`, `calculate_booking_fare()`, `calculate_overstay_penalty()` returning `(overstay_hours, penalty)`; unknown vehicle types raise `ValueError`.
  - `tests/test_core.py` — 6 tests covering hashing, fares, invalid vehicle type, grace boundary, bike/car penalties, 30-minute case.
- **Bug found and fixed during self-check:** grace period was compared after rounding, so exactly 10 minutes rounded to 0.17 h and charged ₹1.70. Comparison now happens on the unrounded delta; `pytest` reports `6 passed`.
- **Todo updates:** ticked `Initialize markdown/todo.md and verify initial tracking`, `schema.sql`, `ords_setup.sql`, `security.py`, `pricing_engine.py`.
- **Respect boundary:** `README.md` untouched. `mytrack.md` never read, edited, or overwritten.
- **Next step:** `src/services/ords_client.py` dual-mode broker, then FastAPI routers.

---

## Setup Entry 010 — Phase 2: Dual-Mode Broker, API Routers & Integration Tests

- **Date:** 2026-11-08
- **Phase:** Implementation — Phase 2 (backend engine + REST endpoints)
- **Files created:**
  - `src/services/ords_client.py` — `OrdsClient` reads `ORDS_SIMULATION_MODE`, `ORDS_BASE_URL`, `ORDS_TIMEOUT` (plus optional `QSPARK_DB_PATH`), lazy singleton `ords`. Simulation mode builds the 7-table SQLite replica at `src/services/parking_local.db`, seeds 50 users (1001–1003 ADMIN ₹1000 / `admin123`, 1004–1050 USER ₹500 / `user123`; 1004–1006 named from PRD), 4 floors, 2 vehicle types, 240 slots (`B1-B01`…`B4-C20`, first 5 B1 bikes RESERVED), all `BEGIN IMMEDIATE` transactions with rollback. Methods: `get_slots`, `update_slot_status`, `create_booking`, `checkout_booking`, `cancel_booking`, `get_analytics_kpi`, `authenticate_user`, plus `get_user`, `list_bookings`, `reset_database`. Live mode routes the six published ORDS endpoints through `requests.Session` and maps 402/404/409 to typed errors.
  - `src/api/auth.py` — `POST /api/auth/login` (returns signed token + profile), `GET /api/auth/me`; HMAC Bearer dependency.
  - `src/api/slots.py` — `GET /api/slots?floor_id=`, `PUT /api/slots/{id}/status` (403 unless `admin_user_id` is ADMIN).
  - `src/api/bookings.py` — `POST /api/bookings` (201), `GET /api/bookings?user_id=`, `PUT /{id}/checkout`, `PUT /{id}/cancel`.
  - `src/api/analytics.py` — `GET /api/analytics/kpi`.
  - `src/main.py` — app "QSPARK Smart Parking API", static mount, Jinja2 templates, routers, `GET /api/health`, `GET /api/status`, central `OrdsError` → HTTP status mapping (400/402/404/409/501).
  - `tests/conftest.py` — isolates tests on `tests/.test_parking_local.db` via `QSPARK_DB_PATH`.
  - `tests/test_api.py` — 6 integration tests: admin/user login (+ bad password), 240 slots + floor filter, booking wallet debit, insufficient-balance 402, overstay checkout (bike ₹15 fine), cancellation refund.
- **Supporting changes:** `src/core/security.py` gained `create_token` / `read_token` (HMAC-SHA256, stateless); `requirements.txt` gained `jinja2` (installed into `.venv`) for Jinja2Templates.
- **Perf fix:** seeding ran one autocommit per row and took ~12.5 s on Windows; wrapped the seed in a single transaction — now ~0.6 s (`reset_database` same).
- **Test result:** `pytest -q` → **12 passed in 6.79 s** (6 unit + 6 integration). Smoke check: `/api/health`, `/api/status` (`local_emulator`) and `/api/analytics/kpi` (240 slots, 235 available, 5 reserved, 4 heatmaps) all correct.
- **Known limitation:** live ORDS mode only supports the six published handlers; `authenticate_user`, `get_user` and `list_bookings` raise `UnsupportedInLiveMode` (HTTP 501) until auth/booking-list ORDS handlers exist. `qspark_apex_dataload.xlsx` is absent, so 44 of the 47 regular users are generated (`user1007@qspark.com` … `user1050@qspark.com`).
- **Todo updates:** ticked SQLite init test, all 9 backend core/endpoint items, and both testing items.
- **Respect boundary:** `README.md` untouched. `mytrack.md` never read, edited, or overwritten.
- **Next step:** Phase 3 — customer portal templates/grid, or await instruction.

