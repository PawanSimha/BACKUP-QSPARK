# QSPARK: project context briefing (`context.md`)

> **Single source of truth.** Read this file first when picking the project up. Update it whenever architecture, business rules or deployment state change.

## 1. Project identity
- **Name:** QSPARK, a smart parking slot booking and management system.
- **Owner:** Pawan Simha R (Conneqtion internship / FDE project).
- **Stack:** Python 3.14 + FastAPI backend, Oracle APEX / Oracle Database behind ORDS REST services, Bootstrap 5.3 + vanilla JS frontend.
- **Current state (2026-11-10):** works fully offline in **SQLite simulation mode**; all **8 live Oracle APEX ORDS endpoints were checked by hand** in Postman under module `qsparking.api.v2`. The FastAPI live-mode cutover is still open (see §6).

## 2. Business context and CEO mandates
QSPARK removes garage congestion, double-booking and manual fare collection. It is a closed loop: money enters only through the internal Metro Card (`wallet_balance`), never through a bank or payment gateway.

Non-negotiable rules:
1. Python/FastAPI backend; Oracle APEX (19c/21c/23ai) database reached only through ORDS.
2. Two roles: `ADMIN` (facility, heatmaps, overrides, audit) and `USER` (search, book, pay, cancel, exit).
3. **Zero external gateways.** No Razorpay/Stripe/UPI, no Twilio/SendGrid. Payments are wallet debits.
4. **Basic auth only.** Username or email plus a SHA-256 hashed password (`hmac.compare_digest` verification).
5. The app must run live at `http://127.0.0.1:8000/` with a visual basement grid and demo simulators.
6. No hardcoded secrets; all configuration lives in `.env` and loads through `python-dotenv`.
7. **Minimum 8 tables.** The schema ships `QSPARK_AUDIT_TRACK` as the eighth: a manual admin register where an administrator records which table or column was changed and why. Nothing writes to it automatically; the UI form is the only entry path.
8. Every table carries `reserved_col_1` / `reserved_col_2` spare columns (`VARCHAR2(255)`, nullable, unused). `QSPARK_AUDIT_TRACK` has only `reserved_col_1`.

## 3. Facility topology
4 basements, 240 bays in total.

| Floor | Bikes (₹5/hr) | Cars (₹10/hr) | Total | Numbering |
| :--- | :---: | :---: | :---: | :--- |
| B1 | 40 | 20 | 60 | `B1-B01`–`B1-B40`, `B1-C01`–`B1-C20` |
| B2 | 40 | 20 | 60 | `B2-B01`–`B2-B40`, `B2-C01`–`B2-C20` |
| B3 | 40 | 20 | 60 | `B3-B01`–`B3-B40`, `B3-C01`–`B3-C20` |
| B4 | 40 | 20 | 60 | `B4-B01`–`B4-B40`, `B4-C01`–`B4-C20` |
| **Total** | **160** | **80** | **240** | |

Seeded state: 10 bays RESERVED (`B1-B01`–`B1-B05`, `B1-C01`–`B1-C05`), 230 AVAILABLE.

## 4. Pricing and overstay engine
- Upfront fare: `hours × hourly rate` (bike ₹5.00/hr, car ₹10.00/hr), duration 1–8 hours.
- **Grace period:** 10 minutes (0.166 h) after `scheduled_end`, at zero penalty.
- Past the grace period: `penalty = late_hours × penalty_rate`, where **bike = ₹10.00/hr** and **car = ₹20.00/hr**.
- Settlement debits the penalty from the wallet and writes `OVERSTAY_DEBIT`. The base fare was already paid at booking.
- Worked example: 1.5 h late on a **bike** costs ₹15.00 (verified in the API contract); the same delay on a car costs ₹30.00.

## 5. Seed data
Master dataset: `Latest QSPARK.xlsx`, 8 tabs (7 seeded transactional tables in FK order, users → floors → vehicle types → slots → bookings → wallet → audit, plus the manual-entry `QSPARK_AUDIT_TRACK` register).

- **50 accounts**, all with `@qspark.com` emails.
- 3 ADMINs at ₹1,000.00: Karan Tulsani, Lalaji Gajera, Pawan Simha R (password `admin123`).
- 47 USERs at ₹500.00 (password `user123`), starting with Harshitha M N, Abhijna and Manprit. The full roster is in `prd.md`.
- 4 floors, 2 vehicle types, 240 slots, 50 bookings (10 CONFIRMED / 40 COMPLETED), 50 wallet rows, 50 audit rows.

## 6. Technical reality
- **Backend:** `src/main.py` (FastAPI plus routers), `src/api/{auth,slots,bookings,analytics}.py`.
- **Business logic:** `src/core/security.py` (SHA-256, HMAC tokens), `src/core/pricing_engine.py` (tariffs and grace period).
- **Data layer:** `src/services/ords_client.py`, a dual-mode broker exposed as the singleton `ords`.
  - `ORDS_SIMULATION_MODE=true` uses the local SQLite `src/services/parking_local.db`. It is created automatically with all 8 `QSPARK_` tables (including `reserved_col_1/2` and the empty `QSPARK_AUDIT_TRACK` register) and seeded on first run from the 7 data tabs of the Excel workbook.
  - `ORDS_SIMULATION_MODE=false` uses live Oracle APEX ORDS through `requests.Session`.
- **Frontend:** `src/templates/index.html`, `src/static/css/app.css` and `src/static/js/app.js` (Bootstrap 5.3, FontAwesome 6, Chart.js 4 from CDNs).
- **Database assets:** the authoritative schema is the **live Oracle APEX deployment** (8 tables). The repo copy `database/schema.sql` still contains 7 tables and 10 indexes, and `database/ords_setup.sql` still defines module `parking.api.v2` with 6 handlers. Neither has been regenerated to match the live module.
- **Tests:** `tests/test_core.py` (6 unit) plus `tests/test_api.py` (9 integration), 15 passing.

### 6.1 Live Oracle APEX ORDS (verified 2026-11-10)
- **Module:** `qsparking.api.v2`
- **Base URL:** `https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/`
- **All 9 endpoints were checked by hand in Postman against the live Oracle tables:**
  1. `GET slots/` returns live bay inventory for B1–B4.
  2. `PUT slots/:id/status` is the admin override. It validates the domain (`AVAILABLE`, `RESERVED`, `OCCUPIED`, `MAINTENANCE`) and writes `QSPARK_AUDIT_LOGS`.
  3. `POST bookings/` locks the slot, debits the wallet and writes the booking, ledger and audit rows atomically.
  4. `PUT bookings/:id/checkout` applies the 10-minute grace period, charges ₹10/hr for bikes and ₹20/hr for cars, and frees the bay.
  5. `PUT bookings/:id/cancel` works on `CONFIRMED` bookings only, refunds in full, writes `CANCEL_REFUND` and frees the bay.
  6. `GET analytics/kpi` returns occupancy, per-floor heatmaps and revenue.
  7. `GET audit/logs` returns paginated `QSPARK_AUDIT_LOGS` joined with users and slots, ordered `log_id DESC`.
  8. `POST admin/audit-track` inserts one manual `QSPARK_AUDIT_TRACK` row and returns HTTP 201.
  9. `GET bookings/` returns booking history with optional `?user_id=`, joined with slot, floor, vehicle type and user name.
- **Body handling:** JSON bodies are read from `:body_text` and parsed with `APEX_JSON.PARSE(:body_text)`; handlers return explicit HTTP codes through `:status_code`.
- **Known live-data issue:** the APEX Excel import stored `USER_ID` as decimals `1.001`–`1.050` instead of integers `1001`–`1050`. Booking creation was verified with user `1.004` (Harshitha). The broker now scales outbound IDs ≥ 1000 by `/1000.0` in live mode (`_live_user_id()`), so FastAPI's integer IDs resolve to the live decimals. Normalise the Oracle data before removing that workaround.
- **Wired in code (2026-11-10):** `.env` and `.env.example` point at `/qsparking/api/v2/`; `OrdsClient` defaults to the same URL; `list_audit_logs(limit=50, offset=0)` calls `GET audit/logs`; `insert_audit_track()` calls `POST admin/audit-track`; `POST /api/admin/audit-track` returns 201; the Admin Audit Compliance Log Register form in `src/templates/index.html` posts to that route and shows the returned `track_id`; `list_bookings()` calls `GET bookings/` and normalizes decimal `user_id` values, falling back to SQLite on network failure. The integration suite has 16 passing tests.
- **What is still open for the live cutover:**
  1. Normalize the live Oracle `USER_ID` values back to integers `1001`–`1050`.
  2. Auth (`POST /api/auth/login`) and `GET /api/auth/me` deliberately fall back to the local SQLite replica in live mode. Publish matching ORDS handlers when they exist.
  3. Run the full FastAPI suite with `ORDS_SIMULATION_MODE=false` and verify the live workflow end to end.

## 7. Run and verify
```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload
```
Open `http://127.0.0.1:8000/`, API docs at `http://127.0.0.1:8000/docs`, tests with `.\.venv\Scripts\python.exe -m pytest -q`.

## 8. Maintenance instruction
When architecture, business rules, seed data, endpoints or deployment state change:
1. Update **this file** in the same change.
2. Append a timestamped entry to `markdown/agent_tracker.md`.
3. Tick or add the matching item in `markdown/todo.md`.
