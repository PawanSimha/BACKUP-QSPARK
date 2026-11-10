# QSPARK: AI agent operating guidelines (`agents.md`)

## 1. Project identity
- **Project name:** QSPARK (Smart Parking Slot Booking & Management System)
- **Stack:** Oracle APEX for the database, ORDS for the REST APIs created inside APEX, Python (FastAPI) for the backend and business logic, and plain HTML/JS for the frontend. The frontend is built in modules so Tailwind CSS and richer JS components can be added later.

## 2. File and security boundaries
1. **Never touch personal files.** Never read, modify or overwrite `mytrack.md` in the root folder. It belongs to the developer.
2. **Leave `README.md` alone.** Do not edit it until the whole project is finished and verified.
3. **Keep the environment isolated.** Run Python commands and package installs inside the local `.venv`. Never install packages globally on the company laptop.
4. **No hardcoded secrets.** Never put Oracle APEX URLs, workspace credentials or keys in `.py` or `.html` files. Load them from `.env` with `python-dotenv`.
5. **No external gateways.** No real payment gateways (Razorpay/Stripe/UPI) and no external SMS or email services. Login uses a username or email plus a SHA-256 hashed password, and payments come out of the internal Metro Card (`wallet_balance` column).

## 3. Architecture and coding rules
1. **Dual-mode data layer (live ORDS plus local fallback).**
   - In production, Python talks to Oracle APEX only through ORDS REST APIs (`requests` / `httpx`).
   - Oracle APEX schema permissions may be pending or offline during development, so `src/services/ords_client.py` must support `ORDS_SIMULATION_MODE=true`, which runs a local SQLite copy of the `QSPARK_` tables. The app and frontend then build, run and test at any time.
2. **Frontend stays decoupled.**
   - Start with semantic HTML5 and modular vanilla JavaScript (`fetch()` calls to FastAPI endpoints) and get the core flows working end to end first: booking, wallet deduction, cancellation, overstay exit and the admin heatmap.
   - Keep templates and CSS classes structured so Tailwind CSS and interactive JS can be layered on without touching backend routes.
3. **Progress tracking is mandatory.**
   - Each time you finish a task, create or edit a file, or tick an item in `markdown/todo.md`, append a timestamped entry to `markdown/agent_tracker.md` saying what was done and what comes next.

## 4. Living documentation and context sync
1. **`markdown/context.md` is the single source of truth.** Update it whenever architecture, business rules, seed data, endpoints or deployment state change, in the same change as the code or config.
2. **`markdown/agent_tracker.md` is the audit trail.** Append a timestamped entry for every task, file edit, todo tick, test run or deployment step, including what was done and what comes next.
3. **`markdown/todo.md` reflects reality.** Tick finished items right away and add new work as you find it. Never leave a completed task unticked.
4. **Code wins.** When docs and the working codebase disagree, fix the docs first, then the code. Never leave both stale.
5. **Sync at every sign-off.** Before reporting a phase complete, check that `context.md`, `agent_tracker.md`, `todo.md` and the affected spec files match the code and tests.
