# QSPARK — Granular Task Checklist (`todo.md`)

## Environment & Documentation Setup
- [x] Create project skeleton (`src/`, `database/`, `markdown/`, `tests/`)
- [x] Create isolated Python virtual environment (`.venv`)
- [x] Configure `.gitignore` (ignoring `.venv`, `.env`, `*.db`, `mytrack.md`)
- [x] Create `.env.example` and initialize `.env`
- [x] Create `requirements.txt` with required dependencies
- [x] Create master agent operating guidelines (`markdown/agents.md`)
- [x] Create Product Requirements Document (`markdown/prd.md`)
- [x] Create Technical & Architecture specification (`markdown/architecture.md`)
- [x] Create Database & ORDS REST API contract (`markdown/database_and_ords.md`)
- [x] Create Frontend UI & Workflow guidelines (`markdown/frontend_and_flows.md`)
- [x] Create Phased Implementation Roadmap (`markdown/roadmap.md`)
- [x] Initialize `markdown/todo.md` and verify initial tracking

## Database & ORDS Asset Creation
- [x] Create `database/schema.sql` with all 7 `QSPARK_` tables, constraints, and indexes
- [x] Create `database/ords_setup.sql` with ORDS REST module, templates, and PL/SQL handlers
- [ ] Verify `qspark_apex_dataload.xlsx` (50 users, 4 floors, 240 slots, seed bookings & wallet rows)
- [x] Test local SQLite schema initialization in `src/services/`

## Backend Core & Business Logic
- [x] Implement `src/core/security.py` (SHA-256 password hashing & verification)
- [x] Implement `src/core/pricing_engine.py` (₹5 Bike / ₹10 Car tariffs & overstay penalty math)
- [x] Implement `src/services/ords_client.py` with Dual-Mode Data Access Broker
- [x] Create local emulator fallback database engine (`src/services/parking_local.db`)
- [x] Implement FastAPI main app and lifespan events in `src/main.py`
- [x] Build `/api/auth` endpoints (Login, Current User, Wallet Balance)
- [x] Build `/api/slots` endpoints (Query by floor, Admin status override)
- [x] Build `/api/bookings` endpoints (Atomic booking creation with wallet debit)
- [x] Build `/api/bookings/:id/checkout` endpoint (Overstay calculation & exit settlement)
- [x] Build `/api/bookings/:id/cancel` endpoint (Cancellation & wallet refund)
- [x] Build `/api/analytics/kpi` endpoint (Occupancy counts, floor heatmaps, revenue)

## Frontend Development & User Workflows
- [ ] Build base layout template with responsive navigation bar and live wallet balance chip
- [ ] Build login view with quick-login buttons for Admin (Pawan) and User (Harshitha)
- [ ] Build 4-level basement floor selector tabs (`B1`, `B2`, `B3`, `B4`)
- [ ] Render 60-slot visual grid per floor (40 Bike slots, 20 Car slots) with live color states
- [ ] Implement sticky booking calculator panel (Hours $\times$ Rate, Remaining Wallet Balance)
- [ ] Implement Metro Card checkout modal with balance verification
- [ ] Implement Digital QR Parking Pass modal with print/save support
- [ ] Build My Bookings drawer with status badges and instant cancellation refunds
- [ ] Build Exit & Settle Simulator modal for live overstay penalty demonstrations

## Admin Dashboard & Analytics
- [ ] Build Admin KPI metric cards (Total Slots, Occupancy %, Active Parked, Revenue)
- [ ] Build Floor Utilization Heatmap with progress bars for `B1–B4`
- [ ] Integrate Chart.js doughnut chart (Slot status distribution)
- [ ] Integrate Chart.js bar chart (Bike vs. Car revenue comparison)
- [ ] Build Slot Maintenance Override table with direct status dropdowns
- [ ] Build Master Audit Log view reading from `QSPARK_AUDIT_LOGS`

## Testing, Verification & Final Delivery
- [x] Write unit tests for pricing engine and overstay penalty edge cases
- [x] Write integration tests for atomic wallet debits and cancellation refunds
- [ ] Test zero-config local run (`python -m uvicorn src.main:app --reload`)
- [ ] Test live Oracle APEX ORDS connectivity (`ORDS_SIMULATION_MODE=false`)
- [ ] Finalize `README.md` with setup guide, live demo script, and API documentation
