# QSPARK — Phased Implementation Roadmap (`roadmap.md`)

## Phase 1: Environment, Database DDL & Seed Verification (Weeks 1–2)
**Status:** ✅ **COMPLETED** — verified against `database/schema.sql`, `database/ords_setup.sql` and the 7-sheet Excel workbook.
- **Objective:** Finalize local and Oracle APEX database layers and verify seed data.
- **Milestones:**
  1. Commit `database/schema.sql` containing all 7 `QSPARK_` tables with complete PK, FK, unique, and check constraints.
  2. Commit `database/ords_setup.sql` containing Oracle APEX ORDS module definitions, templates, and PL/SQL handlers.
  3. Verify the 7-tab Excel workbook (`qspark_apex_dataload.xlsx`) with 50 pre-loaded users (3 Admins: Karan, Lalaji, Pawan; 47 Users), 4 floors (`B1–B4`), 240 slots, and initial ₹500/₹1000 Metro Card wallet balances.
  4. Ensure `.env.example`, `.env`, and `.gitignore` protect all local environment variables and database files.

## Phase 2: Core Backend Engine & Dual-Mode ORDS Broker (Weeks 3–4)
**Status:** ✅ **COMPLETED** — `security.py`, `pricing_engine.py`, `ords_client.py` and all FastAPI routers implemented; 12 tests green.
- **Objective:** Build backend pricing, wallet debit, overstay logic, and the dual-mode data layer.
- **Milestones:**
  1. Build `src/core/security.py` with SHA-256 password hashing and basic login credential validation.
  2. Build `src/core/pricing_engine.py` with fixed tariffs (₹5/hr Bike, ₹10/hr Car) and overstay penalty calculations (10-min grace period, ₹10/hr Bike, ₹20/hr Car).
  3. Build `src/services/ords_client.py` with the Dual-Mode Broker:
     - Local SQLite emulator (`ORDS_SIMULATION_MODE=true`) replicating the 7 tables and PL/SQL atomic procedures.
     - Live Oracle APEX ORDS HTTP client (`ORDS_SIMULATION_MODE=false`) for seamless production cutover.
  4. Implement FastAPI application routers in `src/api/` matching the 5 core REST APIs (`/api/auth`, `/api/slots`, `/api/bookings`, `/api/bookings/:id/checkout`, `/api/bookings/:id/cancel`, and `/api/analytics/kpi`).

## Phase 3: Customer Portal & Interactive 240-Slot Basement Grid (Weeks 5–6)
**Status:** ✅ **COMPLETED** — Bootstrap 5.3 portal, wallet checkout, QR pass and bookings drawer browser-verified on `http://127.0.0.1:8000/`.
- **Objective:** Deliver the customer-facing interface with real-time floor maps and the Metro Card payment flow.
- **Milestones:**
  1. Build the global navbar with live session indicators, user identity, and live Metro Card balance display (`💳 Wallet: ₹500.00`).
  2. Implement the interactive 4-basement floor selector (`B1`, `B2`, `B3`, `B4`) rendering 60 slots per floor (40 Bikes, 20 Cars) with real-time color-coded availability states.
  3. Implement the dynamic fare calculator and the **Pay from Wallet** checkout modal with automatic balance verification.
  4. Generate the printable **Digital QR Parking Pass** modal upon booking confirmation.
  5. Build the self-service **My Bookings** drawer with instant wallet refunds upon cancellation.

## Phase 4: Admin Command Center, Heatmaps & Overstay Simulator (Weeks 7–8)
**Status:** ✅ **COMPLETED** — KPI cards, B1–B4 heatmap, Chart.js doughnut/bar, slot overrides, audit log and exit simulator verified.
- **Objective:** Equip facility managers with real-time monitoring tools, slot overrides, and demo capabilities.
- **Milestones:**
  1. Build the Admin KPI summary cards (Total Capacity 240, Occupancy %, Active Parked Vehicles, Gross Revenue).
  2. Build the live floor utilization heatmap with progress bars for `B1`, `B2`, `B3`, and `B4`.
  3. Integrate Chart.js visualizations (bay status ratio doughnut chart and vehicle category revenue bar chart).
  4. Build the Slot Maintenance Override table allowing admins to toggle any bay between `AVAILABLE`, `OCCUPIED`, and `MAINTENANCE`.
  5. Implement the interactive **Exit & Settle Simulator** to demonstrate automated overstay penalty calculations during live presentations.
  6. Display the searchable master audit log from `QSPARK_AUDIT_LOGS`.

## Phase 5: Production Oracle APEX Cutover & Live Deployment (Weeks 9–10)
**Status:** 🔄 **ACTIVE** — final sign-off and documentation complete; only the physical Oracle APEX deployment/cutover remains.
- **Objective:** Connect to live Oracle APEX ORDS and finalize project deliverables.
- **Milestones:**
  1. Load `qspark_apex_dataload.xlsx` into Oracle APEX via the Data Load wizard.
  2. Publish the ORDS REST services in the APEX schema and configure `.env` (`ORDS_SIMULATION_MODE=false`).
  3. Execute automated end-to-end integration and concurrency tests.
  4. Update `README.md` with full setup instructions, API documentation links, and the live demonstration script.

---
