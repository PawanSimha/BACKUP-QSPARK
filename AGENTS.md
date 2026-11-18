# QSPARK — OpenCode Project Instructions

## Purpose
Build and maintain QSPARK, a web-based smart parking slot booking and management system. These instructions apply to the whole repository.

## Read these documents first
Before planning or changing code, read:

1. `markdown/project_spec.md` — confirmed product scope and role workflows.
2. `markdown/technical_spec.md` — architecture, data rules, security and integration requirements.
3. `markdown/open_questions.md` — decisions that are not yet confirmed; do not silently invent answers.
4. `markdown/implementation_plan.md` — recommended order of work and acceptance checks.

After implementation begins, also keep these generated technical documents accurate:

- `schema.sql` — executable SQLite schema; authoritative for the actual database structure.
- `markdown/db.md` — human-readable explanation of the exact schema in `schema.sql`.
- `markdown/api.md` — actual routes, permissions, request and response contracts.
- `markdown/test_results.md` — test cases actually run and their real results.

## Source-of-truth precedence
When sources conflict, use this order:

1. The user's latest explicit requirements recorded in `markdown/project_spec.md`.
2. Confirmed technical decisions in `markdown/technical_spec.md`.
3. Decisions explicitly marked confirmed in `markdown/open_questions.md`.
4. The running code and database, after validating that they implement the requirements.
5. Older project Markdown files, which are historical references only.

Do not treat old `context.md`, `conversation.md`, `prd.md`, `plan.md`, `roadmap.md`, `todo.md`, `admin-flow.md`, `user-flow.md`, `architecture.md`, `design.md` or `agents.md` as active instructions after the documentation consolidation. They may contain superseded counts, roles, schema columns and permissions.

If the user's requirements conflict with the existing code, report the conflict and implement the confirmed requirement safely. Do not allow old code or old Markdown to silently override the current specification.

## Working rules

- Work only inside this project repository unless the user explicitly authorizes another location.
- Inspect the existing code and its dependencies before editing. Do not assume the current file layout matches an old architecture document.
- Preserve useful working functionality. Replace obsolete code only after identifying and migrating its callers, templates, JavaScript and tests.
- Before changing or replacing a database, create a timestamped backup. Never silently discard the only copy of user data.
- Never run destructive schema reset commands against a non-test database without explicit approval and a verified backup.
- Do not fabricate credentials, user records, payment history or test results.
- Never store plaintext passwords or expose password hashes through APIs or table viewers.
- Do not hardcode secrets. Use environment variables and `.env.example`; never overwrite the real `.env` file.
- Keep financial operations atomic and auditable. A wallet balance update, its ledger entries and the related revenue record must succeed or roll back together.
- Enforce role permissions on the server, not just by hiding frontend controls.
- Use parameterized SQL. Enable SQLite foreign-key enforcement on every connection.
- Use database transactions and concurrency controls for bookings and wallet changes.
- Prefer soft deletion/deactivation where records have financial, booking or audit history.
- Do not add tables, columns, endpoints, roles or features that are not supported by the confirmed specification or an approved decision.
- If a material behavior is unresolved, document it in `markdown/open_questions.md` and choose a safe, reversible implementation only when necessary to keep moving.
- Keep UI, API, database schema and documentation in sync.
- Update `markdown/db.md` from the real schema, not from memory. Update `markdown/api.md` from the actual registered routes. Never claim tests passed unless they were run.

## Security requirements (implemented)

- **CSRF is mandatory.** `Flask-WTF CSRFProtect` validates every `POST/PUT/PATCH/DELETE`. Do not add `@csrf.exempt`, do not relax it to make a test pass, and do not rely on `SameSite` or JSON content type as the defence.
  - Server-rendered forms must include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
  - Fetch calls must go through `QS`, which sends `X-CSRFToken` from `<meta name="csrf-token">`. A page that calls `fetch` directly is a bug.
  - The only place CSRF is disabled is the shared pytest fixture (`tests/conftest.py`); `tests/test_security.py` proves token enforcement with CSRF on.
- **Secrets** come from `.env` only. `APP_ENV=production` without `SECRET_KEY` raises at startup. Never log passwords, hashes, secrets or full request bodies.
- **Cookies**: `HttpOnly`, `SameSite=Lax`, `Secure` via `SESSION_COOKIE_SECURE=1` (HTTPS only). Session lifetime from `SESSION_TIMEOUT`.
- **Authorization** is enforced server-side on every route and endpoint; the sidebar is cosmetic.
- **Response headers** (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`) are set in `app.py`; keep them.
- **Upload/request size** is capped by `MAX_CONTENT_LENGTH` (default 1 MiB, 413 on exceed).

## Financial integrity rules (implemented)

- A money-moving request runs inside `transaction()` (`BEGIN IMMEDIATE` … `COMMIT`, rollback on any exception). Wallet debit, wallet credit, both ledger rows, the revenue row and the booking state change must be in the same transaction.
- Never `UPDATE users SET wallet_balance = <computed value>` from a read taken outside the transaction; read and write inside the same transaction.
- Booking confirmation must re-read slot status, floor status and overlapping bookings inside the transaction. Never trust the availability response the browser saw earlier.
- Ledger `transaction_reference` is `UNIQUE`: generated references need a uuid or microsecond component so concurrent writers cannot collide.
- Financial and management writes append an `audit_logs` row. Financial history is never deleted or rewritten; use `REFUND_REVERSAL` rows.
- Reconciliation rule: each collection row's two ledger legs equal `rc.amount` (directions reversed for refunds), and the net collection sum equals the Super Admin wallet's net ledger movement. `tests/test_financial.py` asserts this — extend it when adding a money flow.

## Production configuration

- Development: `python run.py` (`debug=True`, HTTP, no `Secure` cookie). Never use this server in production.
- Production entry point: `waitress-serve --listen=0.0.0.0:8000 --call app:create_app` behind an HTTPS reverse proxy, with `APP_ENV=production`, a real `SECRET_KEY`, `SESSION_COOKIE_SECURE=1` and an absolute `DATABASE_PATH`.
- Full procedure (dependencies, seed, CSS build, backup/restore, troubleshooting) is in `markdown/deployment.md`. Keep it accurate when config changes.

## Technology baseline
The intended Phase 1 stack is Python, Flask, SQLite, Jinja2, HTML, Tailwind CSS and vanilla JavaScript, with session-based authentication. Use the existing repository's working structure where reasonable. QR generation/scanning may use the project's existing compatible libraries. Do not introduce a real payment gateway; the wallet is an internal simulated balance.

The project is SQLite-only. The former Phase 2 Oracle migration material was removed from this repository; do not reintroduce it.

## Completion expectations
For each substantial task:

1. Summarize files changed.
2. Run focused tests, then the relevant full test suite.
3. Report the actual command and pass/fail result.
4. List unresolved issues and assumptions.
5. Update the relevant canonical documentation in the same change.

Do not mark an implementation complete when only the UI or documentation has been created; verify the backend and database behavior too.

## Frontend rules (implemented)

Stack in use: Jinja2 templates, compiled Tailwind CSS (standalone binary; no CDN, no Node), one hand-written stylesheet, vanilla JavaScript, session cookies + CSRF tokens. No React/Vue/Angular, no bundler, no npm (Node is not installed on this machine). Do not introduce a Node build step.

- **Layout**: every page extends `src/templates/base.html` and fills `title`, `breadcrumb`, `content`, optional `scripts`. `base.html` owns the sidebar, topbar, mobile nav, toast region and confirm `<dialog>`.
- **Design system**: use the tokens and component classes in `src/static/css/app.css` (`.card`, `.stat`, `.btn*`, `.input/.select/.label/.hint`, `.table`, `.badge*`, `.slot`, `.steps`, `.skeleton`). Tailwind utilities only for layout. No inline hex colours.
- **JavaScript**: load `core/api.js` then `core/ui.js` (globals `QS`, `QSUI`). All HTTP through `QS.*`; never `fetch` directly in a page. Escape every interpolated value with `QSUI.esc`. Use `setBusy`, `confirmDialog`, `toast`. Keep page scripts inside `{% block scripts %}`.
- **Server authority**: page routes render shells only; no KPI maths in Jinja. The client never computes financial results, availability or booking state — it displays server responses.
- **Roles**: sidebar blocks are cosmetic. Page routes re-check the role and return `error.html` with 403; APIs enforce `require_admin` / `require_role`. Add new pages to both the sidebar and the route guard.
- **States**: each data view handles loading (skeleton), empty, validation error, business error and network error. Do not leave an endpoint's response unused or a button unwired.
- **Routes**: use only registered routes (see `markdown/api.md`). Compatibility aliases (`/api/admin/master/*`, `/api/admin/qr/scan`, `/api/super-admin/reports/*.csv`) must keep working.

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest -q                       # full suite
.\.venv\Scripts\python.exe -m pytest tests/test_security.py -q    # CSRF, headers, prod secret guard
.\.venv\Scripts\python.exe -m pytest tests/test_financial.py -q   # atomicity, duplicates, reconciliation
.\.venv\Scripts\python.exe -m pytest tests/test_booking_safety.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_qr_flow.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_frontend.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_e2e.py -q      # Playwright, temp DB, port 5099
.\.venv\Scripts\python.exe -m pytest tests/test_a11y.py -q     # axe-core, every page, port 5096
.\.venv\Scripts\python.exe -m pytest tests/test_browsers.py -q # Chromium/Firefox/WebKit, port 5095
```

Playwright is the Python package (`python -m playwright install chromium firefox webkit`). Browser suites start a throwaway server on ports 5095–5099 against a temp database. Never run destructive browser tests against `database/parking_local.db`. WebKit is not Safari — do not claim Safari testing.

Rebuild Tailwind after changing templates or JS utility classes:
`.\tools\tailwindcss.exe -c tailwind.config.js -i src\static\css\tailwind.input.css -o src\static\css\tailwind.css --minify`

## Required skills

`beinghuman`, `modern-web-guidance`, `ui-ux-pro-max` are installed globally under `~/.config/opencode/skills/`. Load `modern-web-guidance` before writing browser-side HTML/CSS/JS and `ui-ux-pro-max` before visual or UX decisions.

See `markdown/frontend.md` for the page inventory, tokens, JS conventions and responsive/accessibility rules.
