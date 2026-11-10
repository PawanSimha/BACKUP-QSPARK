# QSPARK: phased implementation roadmap (`roadmap.md`)

## Phase 1: Environment, database DDL and seed verification (weeks 1–2)
**Status:** ✅ **Completed.** The authoritative 8-table DDL is deployed in live APEX and verified against the 8-tab Excel workbook. The repo copy `database/schema.sql` still holds 7 tables and needs regenerating.
- **Objective:** finalize the local and Oracle APEX database layers and verify seed data.
- **Milestones:**
  1. Deploy the authoritative 8-table `QSPARK_` DDL in live Oracle APEX and regenerate `database/schema.sql` to match (pending).
  2. Commit `database/ords_setup.sql` with the Oracle APEX ORDS module definitions, templates and PL/SQL handlers.
  3. Verify the 8-tab Excel workbook (`qspark_apex_dataload.xlsx`): 50 pre-loaded users (3 admins Karan, Lalaji, Pawan and 47 users), 4 floors (`B1–B4`), 240 slots, initial Metro Card balances of ₹500/₹1000, and the eighth tab `QSPARK_AUDIT_TRACK` (manual admin register, header row only).
  4. Make sure `.env.example`, `.env` and `.gitignore` keep all local environment variables and database files out of the repo.

## Phase 2: Core backend engine and dual-mode ORDS broker (weeks 3–4)
**Status:** ✅ **Completed.** `security.py`, `pricing_engine.py`, `ords_client.py` and all FastAPI routers are in place; 16 tests pass.
- **Objective:** build backend pricing, wallet debit, overstay logic and the dual-mode data layer.
- **Milestones:**
  1. Build `src/core/security.py` with SHA-256 password hashing and basic login credential checks.
  2. Build `src/core/pricing_engine.py` with fixed tariffs (₹5/hr bike, ₹10/hr car) and overstay penalties (10-minute grace, ₹10/hr bike, ₹20/hr car).
  3. Build `src/services/ords_client.py` with the dual-mode broker:
     - Local SQLite emulator (`ORDS_SIMULATION_MODE=true`) covering all 8 tables (7 seeded transactional tables) and the PL/SQL atomic procedures.
     - Live Oracle APEX ORDS HTTP client (`ORDS_SIMULATION_MODE=false`) for the production cutover.
  4. Implement the FastAPI routers in `src/api/` for the 5 core REST APIs (`/api/auth`, `/api/slots`, `/api/bookings`, `/api/bookings/:id/checkout`, `/api/bookings/:id/cancel` and `/api/analytics/kpi`).

## Phase 3: Customer portal and the interactive 240-slot basement grid (weeks 5–6)
**Status:** ✅ **Completed.** The Bootstrap 5.3 portal, wallet checkout, QR pass and bookings drawer were verified in a browser on `http://127.0.0.1:8000/`.
- **Objective:** deliver the customer interface with real-time floor maps and the Metro Card payment flow.
- **Milestones:**
  1. Build the global navbar with live session indicators, user identity and live Metro Card balance (`💳 Wallet: ₹500.00`).
  2. Build the four-basement floor selector (`B1`, `B2`, `B3`, `B4`) showing 60 slots per floor (40 bikes, 20 cars) with live colour-coded availability.
  3. Build the dynamic fare calculator and the **Pay from Wallet** checkout modal with an automatic balance check.
  4. Generate the printable **Digital QR parking pass** modal once a booking is confirmed.
  5. Build the self-service **My bookings** drawer with instant wallet refunds on cancellation.

## Phase 4: Admin command center, heatmaps and overstay simulator (weeks 7–8)
**Status:** ✅ **Completed.** KPI cards, the B1–B4 heatmap, Chart.js doughnut and bar charts, slot overrides, the master audit log, the audit compliance register form and the exit simulator are all in place.
- **Objective:** give facility managers real-time monitoring, slot overrides and demo tools.
- **Milestones:**
  1. Build the admin KPI cards (total capacity 240, occupancy %, active parked vehicles, gross revenue).
  2. Build the live floor utilisation heatmap with progress bars for `B1`, `B2`, `B3` and `B4`.
  3. Add Chart.js charts: bay status ratio doughnut and vehicle category revenue bar.
  4. Build the slot maintenance override table so an admin can switch any bay between `AVAILABLE`, `OCCUPIED` and `MAINTENANCE`.
  5. Build the **Exit & settle simulator** to show automatic overstay penalties during presentations.
  6. Show the searchable master audit log from `QSPARK_AUDIT_LOGS`.
  7. [x] **Audit register wired (2026-11-10):** `POST admin/audit-track` is live, and the Admin Audit Compliance Log Register form posts to `/api/admin/audit-track` and shows the returned `track_id`.

## Phase 5: Production Oracle APEX cutover and live deployment (weeks 9–10)
**Status:** ✅ **Completed for the UI and frontend scope.** The Admin Audit Compliance Log Register form is wired end to end. The live-cutover items still open are `USER_ID` normalisation and the `ORDS_SIMULATION_MODE=false` end-to-end run.
- **Objective:** connect to live Oracle APEX ORDS and finish the project deliverables.
- **Milestones:**
  1. [x] Load all 8 tabs of `qspark_apex_dataload.xlsx` into Oracle APEX with the Data Load wizard.
  2. [x] Publish and verify the live ORDS module `qsparking.api.v2` with 9 endpoints (`GET slots/`, `PUT slots/:id/status`, `POST bookings/`, `GET bookings/?user_id=`, `PUT bookings/:id/checkout`, `PUT bookings/:id/cancel`, `GET analytics/kpi`, `GET audit/logs`, `POST admin/audit-track`).
  3. [x] Point `.env` and `src/services/ords_client.py` at the `/qsparking/api/v2/` base path and wire `list_audit_logs()` and `insert_audit_track()`.
  4. [ ] Normalize the live Oracle `USER_ID` decimals (`1.001`–`1.050`) back to integers (`1001`–`1050`) with APEX SQL Commands so wallet and booking foreign keys agree with FastAPI's integer IDs.
  5. [x] Publish matching ORDS handlers for `POST /api/auth/login`, `GET /api/auth/me` and `GET /api/bookings?user_id=`, or keep those routes on the local SQLite fallback (they stayed on the local replica).
  6. [ ] Run the automated end-to-end integration and concurrency tests with `ORDS_SIMULATION_MODE=false`.
  7. [ ] Update `README.md` with setup instructions, API documentation links and the live demo script, but only after full verification.

---
