# QSPARK — Project Context Briefing (`context.md`)

> **Single source of truth.** Read this file first when picking up the project. Update it whenever architecture, business rules, or deployment state change.

## 1. Project Identity
- **Name:** QSPARK — Smart Parking Slot Booking & Management System.
- **Owner:** Pawan Simha R (Conneqtion internship / FDE project).
- **Stack:** Python 3.14 + FastAPI backend, Oracle APEX / Oracle Database behind ORDS REST services, Bootstrap 5.3 + vanilla JS frontend.
- **Current state (2026-11-09):** Fully working locally in **SQLite simulation mode**; live Oracle APEX cutover pending.

## 2. Business Context & CEO Mandates
QSPARK removes garage congestion, double-booking and manual fare collection. It is a closed-loop system: money enters only through the internal Metro Card (`wallet_balance`), never through a bank or gateway.

Non-negotiable rules:
1. Python/FastAPI backend; Oracle APEX (19c/21c/23ai) database reached only through ORDS.
2. Two roles: `ADMIN` (facility, heatmaps, overrides, audit) and `USER` (search, book, pay, cancel, exit).
3. **Zero external gateways** — no Razorpay/Stripe/UPI, no Twilio/SendGrid. Payments are wallet debits.
4. **Basic auth only** — username or email + SHA-256 hashed password (`hmac.compare_digest` verification).
5. Application must run live at `http://127.0.0.1:8000/` with a visual basement grid and demo simulators.
6. No hardcoded secrets — all configuration in `.env` through `python-dotenv`.

## 3. Facility Topology
4 basements, 240 bays total.

| Floor | Bikes (₹5/hr) | Cars (₹10/hr) | Total | Numbering |
| :--- | :---: | :---: | :---: | :--- |
| B1 | 40 | 20 | 60 | `B1-B01`–`B1-B40`, `B1-C01`–`B1-C20` |
| B2 | 40 | 20 | 60 | `B2-B01`–`B2-B40`, `B2-C01`–`B2-C20` |
| B3 | 40 | 20 | 60 | `B3-B01`–`B3-B40`, `B3-C01`–`B3-C20` |
| B4 | 40 | 20 | 60 | `B4-B01`–`B4-B40`, `B4-C01`–`B4-C20` |
| **Total** | **160** | **80** | **240** | |

Seeded state: 10 bays RESERVED (`B1-B01`–`B1-B05`, `B1-C01`–`B1-C05`), 230 AVAILABLE.

## 4. Pricing & Overstay Engine
- Upfront fare: `hours × hourly rate` (bike ₹5.00/hr, car ₹10.00/hr), duration 1–8 hours.
- **Grace period:** 10 minutes (0.166 h) after `scheduled_end` at zero penalty.
- Beyond grace: `penalty = late_hours × penalty_rate` where **bike = ₹10.00/hr**, **car = ₹20.00/hr**.
- Settlement debits the penalty from the wallet and writes `OVERSTAY_DEBIT`; base fare was already paid at booking.
- Worked example: 1.5 h late on a **bike** = ₹15.00 (verified in API contract); same delay on a car = ₹30.00.

## 5. Seed Directory
Master dataset: `qspark_apex_dataload.xlsx` (7 tabs, FK order: users → floors → vehicle types → slots → bookings → wallet → audit).

- **50 accounts** with `@qspark.com` emails.
- 3 ADMINs at ₹1,000.00 — Karan Tulsani, Lalaji Gajera, Pawan Simha R (password `admin123`).
- 47 USERs at ₹500.00 (password `user123`) — first: Harshitha M N, Abhijna, Manprit; full roster in `prd.md`.
- 4 floors, 2 vehicle types, 240 slots, 50 bookings (10 CONFIRMED / 40 COMPLETED), 50 wallet rows, 50 audit rows.

## 6. Technical Reality
- **Backend:** `src/main.py` (FastAPI + routers), `src/api/{auth,slots,bookings,analytics}.py`.
- **Business logic:** `src/core/security.py` (SHA-256, HMAC tokens), `src/core/pricing_engine.py` (tariffs + grace).
- **Data layer:** `src/services/ords_client.py` — dual-mode broker with singleton `ords`:
  - `ORDS_SIMULATION_MODE=true` → local SQLite `src/services/parking_local.db`, auto-created and seeded from the Excel workbook on first run.
  - `ORDS_SIMULATION_MODE=false` → live Oracle APEX ORDS via `requests.Session`.
- **Frontend:** `src/templates/index.html` + `src/static/css/app.css` + `src/static/js/app.js` (Bootstrap 5.3, FontAwesome 6, Chart.js 4 via CDN).
- **Database assets:** `database/schema.sql` (7 tables, 10 indexes), `database/ords_setup.sql` (module `parking.api.v2`, 6 handlers).
- **Tests:** `tests/test_core.py` (6 unit) + `tests/test_api.py` (6 integration) = 12 passing.
- **Known limitation:** live ORDS mode supports only the six published handlers; `authenticate_user`, `get_user`, `list_bookings` and `list_audit_logs` return HTTP 501 until matching ORDS handlers exist.

## 7. Run & Verify
```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload
```
Open `http://127.0.0.1:8000/` · API docs `http://127.0.0.1:8000/docs` · tests: `.\.venv\Scripts\python.exe -m pytest -q`.

## 8. Maintenance Instruction
Whenever architectural decisions, business rules, seed data, endpoints or deployment state change:
1. Update **this file** in the same change.
2. Append a timestamped entry to `markdown/agent_tracker.md`.
3. Tick or add the matching item in `markdown/todo.md`.
