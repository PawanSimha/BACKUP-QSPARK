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

---

## Setup Entry 011 — Excel-Driven Seeding & Complete Frontend

- **Date:** 2026-11-09
- **Phase:** Implementation — Phase 3 & 4 (master dataset + UI)
- **Dataset inspected:** `qspark_apex_dataload.xlsx` has exactly 7 sheets. Counts: 50 users (3 ADMIN ₹1000, 47 USER ₹500; admins hash = `admin123`, users = `user123`), 4 floors, 2 vehicle types, 240 slots (10 RESERVED: `B1-B01`–`B1-B05` and `B1-C01`–`B1-C05`; 230 AVAILABLE), 50 bookings (10 CONFIRMED on slots 1–5/41–45, 40 COMPLETED), 50 `BOOKING_DEBIT` wallet rows, 50 audit rows.
- **Seeding rewritten:** `src/services/ords_client.py` now loads all 7 tables directly from the workbook with `openpyxl` (`SEED_SHEETS` order respects FKs), path `DEFAULT_DATA_FILE` (project root) overridable via `QSPARK_DATA_FILE`; removed the generated placeholder users and programmatic slot loops. `_cell()` normalises datetime cells. Missing workbook now raises a clear `FileNotFoundError`.
- **Tests updated:** seeded reservations shifted car slots, so the insufficient-funds and cancellation tests now use slots 46–52; `pytest -q` → **12 passed**.
- **Frontend created:**
  - `src/templates/index.html` — Bootstrap 5.3 + FontAwesome 6 + Chart.js CDNs; navbar with mode pill, wallet chip, role badge, portal/admin/bookings/logout; login card with quick-login for Pawan/Harshitha; B1–B4 tabs; bike/car bay grids; sticky fare card; payment, digital pass (QR canvas + print), exit simulator modals; bookings offcanvas; admin KPIs, heatmap, charts, override table, audit log.
  - `src/static/css/app.css` — status colour tokens (#10b981/#f59e0b/#ef4444/#64748b), sticky card, heat bars, print-only pass stylesheet.
  - `src/static/js/app.js` — session storage token, wallet refresh on every debit/refund, live fare math, atomic booking + pass generation, cancel with refund, exit simulator, admin rendering (`Chart.js` doughnut/bar), overrides and audit.
  - `src/main.py` — `GET /` renders `index.html` with live mode label; `src/api/analytics.py` — added `GET /api/analytics/audit`; `src/services/ords_client.py` — added `list_audit_logs()`.
- **Demo bug fixed:** seeded CONFIRMED bookings have windows in the past, so "On-Time Exit" would have charged ~48 h of overstay. Simulator now targets `scheduled_end + delay` (negative offset allowed), verified in-browser: past booking exits with ₹0 penalty, 1.5 h late charges exactly ₹15 on a bike.
- **Browser verification (real uvicorn on :8000):** admin quick-login → 60 bays/50 available/₹1000; booking `B1-B06` → pass `QSP-1109-0051`, QR painted, wallet ₹995, bay RESERVED; 1.5 h late checkout → ₹15 penalty, wallet ₹980, COMPLETED; user quick-login → book `B1-B07` (₹495) then cancel → wallet back to ₹500, bay AVAILABLE; admin center → 240 slots, 4 heat bars, both charts, 240 override rows, 51 audit rows. No console errors.
- **Cleanup:** removed temporary inspection scripts and reset `src/services/parking_local.db` so the next run reseeds fresh from Excel. Stopped the demo server.
- **How to run:** `.\\.venv\\Scripts\\python.exe -m uvicorn src.main:app --reload` then open `http://127.0.0.1:8000/`.
- **Todo updates:** ticked Excel verification, all 9 frontend items, all 6 admin items, and zero-config local run.
- **Respect boundary:** `README.md` untouched. `mytrack.md` never read, edited, or overwritten.
- **Next step:** final polish / Oracle APEX live cutover, or await instruction.



---

## Setup Entry 012 - Phase 5 Final Delivery, Documentation Audit & Sign-off

- **Date:** 2026-11-09
- **Phase:** Phase 5 - Final delivery and documentation sign-off
- **Context file created:** `markdown/context.md` - project identity, CEO mandates, facility topology, pricing/overstay engine, 50-account seed directory, technical reality (dual-mode broker), run commands and the living-document maintenance rule.
- **Documentation audited and synced:**
  - `agents.md` - new Section 4 "Living Documentation & Context Sync": context.md is the single source of truth, tracker is the audit trail, todo reflects reality, code wins, sign off only when all are consistent.
  - `architecture.md` - Section 6 FastAPI internal endpoint to ORDS handler mapping (all 10 routes, local-only routes marked); Section 7 dual-mode broker and Excel auto-seeder internals (`SEED_SHEETS` FK order, single-transaction seeding, live-mode 501 limitation).
  - `database_and_ords.md` - added the 10 indexes matching `database/schema.sql`; recorded the BIKE Rs.10/hr vs CAR Rs.20/hr overstay math on the checkout contract.
  - `frontend_and_flows.md` - Section 9 implemented file map (`index.html`, `app.css`, `app.js`) with key element IDs and layout behaviour; Section 10 `scheduled_end + delay` exit-simulator math with the selectors (on-time / 30 min / 1.5 h) and penalty table.
  - `prd.md` - replaced the abbreviated user list with the verified full 50-row roster (3 ADMIN Rs.1,000 / 47 USER Rs.500) loaded from `qspark_apex_dataload.xlsx`.
  - `roadmap.md` - Phases 1-4 marked COMPLETED with verified outcomes; Phase 5 marked ACTIVE (only physical APEX cutover remains).
  - `todo.md` - ticked README finalization and context creation; only "Test live Oracle APEX ORDS connectivity" remains open.
- **Root files:**
  - `requirements.txt` - clean deduplicated list (fastapi, uvicorn, jinja2, openpyxl, python-dotenv, requests, pydantic, pytest, httpx).
  - `.gitignore` - added lowercase `mytrack.md` alongside `MY_TRACK.md`; tidied the IDE section comment.
  - `README.md` - rewritten as UTF-8 (was UTF-16LE developer note) with overview, mandates met, facility/pricing table, architecture + directory tree, quickstart, credentials table, API table, 4-step APEX cutover checklist, 5-minute CEO demo script and documentation index.
- **Test result:** `pytest -q` -> **12 passed, 1 warning in 10.19 s** (6 unit + 6 integration). Warning is the upstream Starlette/httpx deprecation notice, not a project issue.
- **Cleanup:** removed temporary inspection artifacts (`probe_readme.py`, `readme_probe.txt`, `dump_users.py`, `users_table.md`).
- **Respect boundary:** `mytrack.md` was never read, edited, or overwritten.
- **Next step:** physical Oracle APEX deployment - run `database/schema.sql`, load the 7 Excel sheets, publish `database/ords_setup.sql`, set `ORDS_SIMULATION_MODE=false`.

---

## Setup Entry 013 - 8-Table Schema, Reserved Columns & Manual Admin Audit Register

- **Date:** 2026-11-09 22:40
- **Phase:** Database schema revision (documentation sync)
- **Schema change:** the Oracle DDL in `no_entry/APEX SQL Doc/QSPARK - DDL Cmds.txt` now defines **8** tables:
  1. `QSPARK_USERS`
  2. `QSPARK_FLOORS`
  3. `QSPARK_VEHICLE_TYPES`
  4. `QSPARK_PARKING_SLOTS`
  5. `QSPARK_BOOKINGS`
  6. `QSPARK_WALLET_TRANSACTIONS`
  7. `QSPARK_AUDIT_LOGS` (system-generated state events)
  8. `QSPARK_AUDIT_TRACK` (manual admin register: `track_id`, `admin_name`, `time_date`, `modified_table`, `modified_column`, `why_modified`, `reserved_col_1`)
- **Reserved columns:** every table carries `reserved_col_1` and `reserved_col_2` (`VARCHAR2(255)`, nullable, unused); `QSPARK_AUDIT_TRACK` has only `reserved_col_1`.
- **Manual audit rule:** `QSPARK_AUDIT_TRACK` is written only by an admin from the UI. No triggers, no backend hooks, no automatic capture.
- **Excel:** `qspark_apex_dataload.xlsx` rebuilt to 8 tabs matching the schema; seven tabs keep their data and gain the two reserved columns, `QSPARK_AUDIT_TRACK` is header-only.
- **Docs updated:**
  - `database_and_ords.md` - heading now 8 tables, reserved columns added to all seven DDL blocks, new Table 8 + relationship/ERD summary + planned `POST /admin/audit-track` contract.
  - `architecture.md` - database layer diagram, seeding notes and sheet order now reflect 8 tables / 8 tabs (audit track not mirrored in SQLite).
  - `context.md` - CEO rule 7 (minimum 8 tables) and rule 8 (reserved columns), seed directory and database-assets counts.
  - `prd.md` - Admin Command Center gains the manual Admin Audit Register feature.
  - `frontend_and_flows.md` - new Admin Audit Register form spec (table/column dropdowns + reason).
  - `roadmap.md` - Phase 1/2 counts and Phase 5 load step updated; audit-register form marked planned.
  - `todo.md` - added schema/Excel items, left the UI form open.
  - `agents.md` - SQLite replica wording no longer pins "7".
- **Respect boundary:** `README.md` and `MY_TRACK.md` untouched.
- **Next step:** build the Admin Audit Register form and add its ORDS handler; regenerate `database/schema.sql` for the 8-table schema.

---

## Setup Entry 014 - SQLite Replica Aligned With the 8-Table Schema

- **Date:** 2026-11-09
- **Phase:** Database parity fix (local emulator)
- **Finding:** `src/services/parking_local.db` did not exist yet (created on first run). The replica schema in `src/services/ords_client.py` defined only the 7 transactional tables, without `reserved_col_1/2` and without `QSPARK_AUDIT_TRACK`, so it did not match `no_entry/APEX SQL Doc/QSPARK - DDL Cmds.txt` or the 8-tab workbook.
- **Fix:** `_SCHEMA_SQL` now creates all 8 tables with the exact workbook columns, including `reserved_col_1/2` on the seven transactional tables and `reserved_col_1` only on `QSPARK_AUDIT_TRACK`; `reset_database()` now drops the audit-track table too. The seven data tabs still seed from Excel; the audit-track tab stays empty (manual admin register).
- **Verification:** recreated `src/services/parking_local.db` and compared every table's SQLite columns against the Excel headers — all 8 MATCH. Row counts: 50 users, 4 floors, 2 vehicle types, 240 slots, 50 bookings, 50 wallet rows, 50 audit rows, 0 audit-track rows.
- **Tests:** `pytest -q` -> **12 passed, 1 warning in 3.42 s**.
- **Docs synced:** `context.md` (simulation mode description), `architecture.md` (broker/seeder section), `todo.md` (new ticked parity item).
- **Respect boundary:** `README.md` and `MY_TRACK.md` untouched.
- **Next step:** same as before — build the Admin Audit Register form + ORDS handler; regenerate `database/schema.sql` for 8 tables.

---

## Setup Entry 015 — Live Oracle APEX ORDS Endpoints Manually Configured & Verified

- **Date:** 2026-11-10
- **Phase:** Phase 5 — live Oracle APEX ORDS verification
- **Live module:** `qsparking.api.v2`
- **Base URL:** `https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/`
- **Endpoints manually created and verified in Postman against live Oracle tables:**
  1. `GET slots/` — real-time bay inventory across B1–B4.
  2. `PUT slots/:id/status` — admin override; `AVAILABLE`/`RESERVED`/`OCCUPIED`/`MAINTENANCE` validated; modified slot 1 and reverted it; wrote `QSPARK_AUDIT_LOGS`.
  3. `POST bookings/` — atomic slot lock (`FOR UPDATE`), wallet lock, fare debit ₹500.00 → ₹490.00 on user `1.004` (Harshitha), slot 6 (`B1-B06`) set `RESERVED`, booking `10001` (`QSP-1110-2086`) created with ledger and audit rows.
  4. `PUT bookings/:id/checkout` — booking `10001` with `{"simulated_late_hours": 1.5}`; 10-minute grace applied, bike penalty 1.5 × ₹10 = ₹15.00, wallet ₹490.00 → ₹475.00, booking `COMPLETED`, bay freed, `OVERSTAY_DEBIT` recorded.
  5. `PUT bookings/:id/cancel` — freshly created booking `10021` (slot 6, ₹5.00 base); `CONFIRMED` check passed, wallet ₹470.00 → ₹475.00, slot freed, booking `CANCELLED`, `CANCEL_REFUND` recorded.
  6. `GET analytics/kpi` — 240 total slots (230 available, 10 reserved, 0 occupied, 0 maintenance), 4.17% occupancy, revenue ₹1,105.00, floor heatmaps B1 16.67% / B2–B4 0%.
  7. `GET audit/logs` — paginated join of `QSPARK_AUDIT_LOGS` with users and slots, ordered `log_id DESC`; standard ORDS pagination (`limit` default 50, `offset` default 0, `items`/`hasMore`/`limit`/`offset`/`count`).
  8. `POST admin/audit-track` — inserts one manual `QSPARK_AUDIT_TRACK` row from `admin_name`, `modified_table`, `modified_column`, `why_modified`; returns HTTP 201 with `track_id`, `admin_name`, `modified_table`, `status: "SAVED"`.
- **Input-handling resolution:** `PUT slots/:id/status` initially received an empty `:body_text`; fixed by configuring raw JSON in Postman and parsing with `APEX_JSON.PARSE(:body_text)`. All JSON handlers now use that convention and set explicit HTTP status via `:status_code`.
- **Discovery — `USER_ID` decimals:** the APEX Excel import stored `USER_ID` as `1.001`–`1.050` instead of `1001`–`1050`; booking creation was verified with user `1.004`. FastAPI, the Excel workbook and the frontend still use integer IDs, so live data needs normalization (or mapping) before the FastAPI cutover.
- **Docs synced:** `context.md` (§1 state, §6.1 live ORDS, known limitation/remaining cutover), `database_and_ords.md` (live base path, 8 endpoint contracts, `APEX_JSON.PARSE(:body_text)` + `:status_code` conventions), `architecture.md` (live module paths, mapping table, live-mode status), `roadmap.md` (Phase 4 audit-track backend done; Phase 5 honest remaining work), `todo.md` (live ORDS items ticked; normalization, broker wiring and FastAPI live test added).
- **Remaining live cutover:** (a) normalize live Oracle `USER_ID` decimals to integers `1001`–`1050`; (b) point `.env` / `ords_client.py` at `/qsparking/api/v2/` and wire `list_audit_logs()` + `insert_audit_track()`; (c) add ORDS handlers for login/get_user/list_bookings or keep those routes on SQLite fallback; then run FastAPI with `ORDS_SIMULATION_MODE=false`.
- **Respect boundary:** `README.md`, `MY_TRACK.md`, and `no_entry/` untouched.
- **Next step:** update `.env` and `src/services/ords_client.py` for live client consumption, then fix the `USER_ID` data.

## Setup Entry 016 — Live ORDS Broker Wiring, Audit-Track Route & Test

- **Date:** 2026-11-10 12:38
- **Phase:** Phase 5 — live client wiring
- **Code:**
  - `src/services/ords_client.py` — added `DEFAULT_LIVE_BASE_URL`; `ORDS_BASE_URL` falls back to `/qsparking/api/v2/`; live `list_audit_logs(limit=50, offset=0)` calls `GET audit/logs` and returns `items`; added `insert_audit_track()` (live `POST admin/audit-track`, simulation insert into `QSPARK_AUDIT_TRACK`); `create_booking` and `update_slot_status` scale outbound IDs ≥ 1000 via `_live_user_id()`; simulation `list_audit_logs` now supports `LIMIT ? OFFSET ?`.
  - `src/api/admin.py` — new `POST /api/admin/audit-track` accepting `admin_name`, `modified_table`, `modified_column`, `why_modified`; returns HTTP 201.
  - `src/main.py` — registers `admin.router`.
  - `.env` / `.env.example` — `ORDS_BASE_URL` now points at the live module.
  - `src/services/ords_client.py` — `DEFAULT_DATA_FILE` updated to the current workbook `Latest QSPARK.xlsx` (old filename was deleted, which broke seeding).
- **Tests:** added `test_audit_track_inserts_without_audit_log` (201, incrementing `track_id`, no new `QSPARK_AUDIT_LOGS` row). `pytest -q` → **13 passed**.
- **Docs synced:** `context.md` (wired-in-code status, 13 tests, revised remaining cutover), `architecture.md` (audit/admin mapping rows, live-mode status, data-file name), `todo.md` (base-path/broker item and admin route ticked), `roadmap.md` (Phase 5 milestone 3 ticked, status refreshed).
- **Remaining:** normalize live `USER_ID` decimals, publish auth/get_user/list_bookings ORDS handlers (or keep SQLite fallback), then run the suite with `ORDS_SIMULATION_MODE=false`.
- **Respect boundary:** `README.md`, `MY_TRACK.md`, and `no_entry/` untouched.
- **Next step:** decide auth/list fallback strategy and run live-mode end-to-end verification.

## Setup Entry 017 — Live Auth Fallback & Root Health Alias

- **Date:** 2026-11-10 12:51
- **Phase:** Phase 5 — live-mode compatibility fixes
- **Code:**
  - `src/services/ords_client.py` — added `_ensure_db()`; `authenticate_user()`, `get_user()` and `list_bookings()` no longer call `_require_simulation()`. In live mode they use the local SQLite replica (50 seeded accounts) instead of raising 501; slots, bookings writes, KPI and audit remain live ORDS.
  - `src/main.py` — added `GET /health` alias returning `{"status": "ok", "mode": "live"|"simulation"}` alongside `GET /api/health`.
- **Tests:** added `test_root_health_alias` and `test_live_auth_falls_back_to_local_replica` (live-mode client authenticates, reads profile and bookings from a temp replica). `pytest -q` → **15 passed**.
- **Docs synced:** `context.md` (fallback status, 15 tests), `architecture.md` (live-mode behaviour), `todo.md` and `roadmap.md` (auth/list fallback item ticked).
- **Remaining:** normalize live `USER_ID` decimals and run the full workflow with `ORDS_SIMULATION_MODE=false`.
- **Respect boundary:** `README.md`, `MY_TRACK.md`, and `no_entry/` untouched.

## Setup Entry 018 — Documentation Rewritten in the beinghuman Style

- **Date:** 2026-11-10 13:09
- **Phase:** Documentation (style pass only, no spec changes)
- **Scope:** every spec file in `markdown/`: `agents.md`, `prd.md`, `architecture.md`, `database_and_ords.md`, `frontend_and_flows.md`, `roadmap.md`, `todo.md`, `context.md`.
- **What changed:** prose now follows the global `beinghuman` skill. Removed AI vocabulary (robust, leverage, seamless, comprehensive, visionary phrasing), significance overlays, tailing -ing clauses, canned openers and closers, and title-case headings. Em dashes kept only where they separate real clauses.
- **What did not change:** every fact, number, price, ID range, status, checklist state, table row, SQL block, JSON payload and ASCII diagram. Fenced code blocks were compared against the previous file contents and match.
- **Tracker note:** entries 001 to 017 are historical records and keep their original wording; only this entry uses the new style.
- **Respect boundary:** `README.md` and `MY_TRACK.md` untouched.
- **Next step:** nothing pending from this pass. Live `USER_ID` normalisation and the FastAPI live-mode test stay open in `todo.md`.

## Setup Entry 019 — Live Bookings Query Handler Connected

- **Date:** 2026-11-10 13:15
- **Phase:** Phase 5, live bookings-list wiring
- **Endpoint:** `GET https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/bookings/` with optional `?user_id=`, verified in APEX module `qsparking.api.v2`.
- **Code:** `src/services/ords_client.py` now has `_sqlite_list_bookings()`. In live mode `list_bookings()` calls `GET bookings/` with `user_id` when supplied, reads `items`, normalises decimal returned IDs (`1.004` becomes `1004`), and falls back to the local replica when the request fails.
- **Tests:** added a decimal-normalisation test and a network-failure fallback assertion. `pytest -q` gives **16 passed**.
- **Docs synced:** `context.md` (9 live endpoints, 16 tests), `database_and_ords.md` (`GET /bookings/?user_id=` contract), `architecture.md` (mapping and live-mode status), `todo.md` (bookings-list item ticked), `roadmap.md` (9-endpoint milestone).
- **Note:** entry 018 was already used by the documentation style pass, so this is 019.
- **Remaining:** normalise live `USER_ID` decimals and run the full workflow with `ORDS_SIMULATION_MODE=false`.
- **Respect boundary:** `README.md`, `MY_TRACK.md`, and `no_entry/` untouched.

## Setup Entry 020 — Admin Audit Register Form Wired

- **Date:** 2026-11-10 13:28
- **Phase:** Phase 4/5, final frontend item
- **UI:** `src/templates/index.html` now has an **Audit Compliance Log Register** card in the Admin Command Center. Fields: `admin_name` (prefilled from the logged-in admin), `modified_table` dropdown for the seven source tables, `modified_column` text input and `why_modified` textarea, with a **Log Compliance Record** button.
- **Script:** `src/static/js/app.js` prefills `admin_name` in `showAdmin()`, posts the form to `/api/admin/audit-track`, shows a success toast with the returned `track_id`, and clears the justification field. Errors use the existing danger toast.
- **Docs synced:** `context.md` (form wired), `frontend_and_flows.md` (actual field behaviour), `todo.md` (UI milestone ticked), `roadmap.md` (Phase 4 completed; Phase 5 UI scope completed, live-cutover items still open).
- **Tests:** `pytest -q` gives **16 passed**.
- **Remaining:** normalise live `USER_ID` decimals and run the workflow with `ORDS_SIMULATION_MODE=false`.
- **Respect boundary:** `README.md`, `MY_TRACK.md`, and `no_entry/` untouched.

