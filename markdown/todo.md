# QSPARK: granular task checklist (`todo.md`)

## Environment and documentation setup
- [x] Create project skeleton (`src/`, `database/`, `markdown/`, `tests/`)
- [x] Create the isolated Python virtual environment (`.venv`)
- [x] Configure `.gitignore` (ignore `.venv`, `.env`, `*.db`, `mytrack.md`)
- [x] Create `.env.example` and initialise `.env`
- [x] Create `requirements.txt` with the required dependencies
- [x] Create the master agent operating guidelines (`markdown/agents.md`)
- [x] Create the product requirements document (`markdown/prd.md`)
- [x] Create the technical and architecture spec (`markdown/architecture.md`)
- [x] Create the database and ORDS REST API contract (`markdown/database_and_ords.md`)
- [x] Create the frontend UI and workflow guidelines (`markdown/frontend_and_flows.md`)
- [x] Create the phased implementation roadmap (`markdown/roadmap.md`)
- [x] Set up `markdown/todo.md` and confirm tracking works

## Database and ORDS assets
- [x] Create `database/schema.sql` with all 7 `QSPARK_` tables, constraints and indexes
- [x] Add the 8th table `QSPARK_AUDIT_TRACK` (manual admin register) to the Oracle DDL
- [x] Add `reserved_col_1` / `reserved_col_2` placeholder columns to every table
- [x] Update `qspark_apex_dataload.xlsx` to 8 tabs matching the current schema
- [x] Create `database/ords_setup.sql` with the ORDS REST module, templates and PL/SQL handlers
- [x] Verify `qspark_apex_dataload.xlsx` (50 users, 4 floors, 240 slots, seed bookings and wallet rows)
- [x] Test local SQLite schema initialisation in `src/services/`
- [x] Align the local SQLite replica with the 8-table Oracle schema (reserved columns plus an empty `QSPARK_AUDIT_TRACK`)
- [x] Create and verify live ORDS `GET audit/logs` (standard pagination: `limit` default 50, `offset` default 0)
- [x] Create and verify live ORDS `POST admin/audit-track` (manual register, HTTP 201 Created)
- [x] Create and verify live ORDS `GET bookings/?user_id=` (optional filter, `items` response)
- [ ] Normalize live Oracle `USER_ID` decimals (`1.001`–`1.050`) to integers (`1001`–`1050`) in APEX SQL Commands
- [x] Point `.env` and `src/services/ords_client.py` at `/qsparking/api/v2/` and wire `list_audit_logs()` and `insert_audit_track()`
- [x] Publish ORDS handlers for login/get_user/list_bookings, or keep those routes on the SQLite fallback (they stayed on the local replica)

## Backend core and business logic
- [x] Implement `src/core/security.py` (SHA-256 password hashing and verification)
- [x] Implement `src/core/pricing_engine.py` (₹5 bike / ₹10 car tariffs and overstay penalty maths)
- [x] Implement `src/services/ords_client.py` with the dual-mode data access broker
- [x] Create the local emulator fallback database engine (`src/services/parking_local.db`)
- [x] Implement the FastAPI main app and lifespan events in `src/main.py`
- [x] Build the `/api/auth` endpoints (login, current user, wallet balance)
- [x] Build the `/api/slots` endpoints (query by floor, admin status override)
- [x] Build the `/api/bookings` endpoints (atomic booking creation with wallet debit)
- [x] Build the `/api/bookings/:id/checkout` endpoint (overstay calculation and exit settlement)
- [x] Build the `/api/bookings/:id/cancel` endpoint (cancellation and wallet refund)
- [x] Build the `/api/analytics/kpi` endpoint (occupancy counts, floor heatmaps, revenue)
- [x] Build the `/api/admin/audit-track` endpoint (201 Created; live `POST admin/audit-track` or SQLite `QSPARK_AUDIT_TRACK`)
- [x] Add a `GET /health` alias returning status and the active mode

## Frontend and user workflows
- [x] Build the base layout template with a responsive navbar and live wallet balance chip
- [x] Build the login view with quick-login buttons for Admin (Pawan) and User (Harshitha)
- [x] Build the four basement floor tabs (`B1`, `B2`, `B3`, `B4`)
- [x] Render a 60-slot grid per floor (40 bike slots, 20 car slots) with live colour states
- [x] Implement the sticky booking calculator panel (hours $\times$ rate, remaining wallet balance)
- [x] Implement the Metro Card checkout modal with a balance check
- [x] Implement the digital QR parking pass modal with print/save support
- [x] Build the My bookings drawer with status badges and instant cancellation refunds
- [x] Build the Exit & settle simulator modal for live overstay penalty demos

## Admin dashboard and analytics
- [x] Build the admin KPI cards (total slots, occupancy %, active parked, revenue)
- [x] Build the floor utilisation heatmap with progress bars for `B1–B4`
- [x] Add the Chart.js doughnut chart (slot status distribution)
- [x] Add the Chart.js bar chart (bike vs car revenue)
- [x] Build the slot maintenance override table with direct status dropdowns
- [x] Build the master audit log view reading from `QSPARK_AUDIT_LOGS`
- [x] Build the manual Admin audit register **UI form**: the ORDS `POST admin/audit-track` route is verified live, and the form writes `QSPARK_AUDIT_TRACK` with table/column inputs plus a reason

## Testing, verification and delivery
- [x] Write unit tests for the pricing engine and overstay penalty edge cases
- [x] Write integration tests for atomic wallet debits and cancellation refunds
- [x] Test the zero-config local run (`python -m uvicorn src.main:app --reload`)
- [x] Verify all 8 live Oracle APEX ORDS endpoints by hand in Postman (`qsparking.api.v2`)
- [ ] Test FastAPI live mode end to end with `ORDS_SIMULATION_MODE=false`
- [x] Finish `README.md` with the setup guide, live demo script and API documentation
- [x] Create the `markdown/context.md` single-source-of-truth briefing and sync all documentation
