# SRS Analysis Report — QSPARK

**Analysis date:** 18 November 2026
**Scope:** `BACKUP-QSPARK/` (the only project directory present)
**Method:** Direct inspection of source, schema and project documentation; no application code was modified.

## 1. Resources Inspected

| Resource | What was taken from it |
|---|---|
| `schema.sql` | Authoritative table, column, constraint, index and trigger definitions |
| `app.py`, `run.py` | Application factory, configuration, session validation, page routes, error handlers |
| `src/api/auth.py`, `slots.py`, `bookings.py`, `qr.py`, `admin.py`, `reports.py`, `super_admin.py`, `system.py` | Endpoint inventory, request/response behaviour, role guards, business rules |
| `src/core/security.py`, `pricing.py` | Hashing, authentication, role decorators, fare and overtime formulas |
| `src/services/db.py` | Connection handling, foreign-key enforcement, transaction helper |
| `src/templates/*.html` (22 files) | Page inventory, role-specific UI, form behaviour |
| `src/static/js/**`, `src/static/css/app.css` | Client conventions, design tokens, request wrapper |
| `requirements.txt` | Runtime and test dependencies |
| `docs/project_spec.md`, `technical_spec.md`, `api.md`, `db.md`, `open_questions.md`, `deployment.md`, `frontend.md`, `test_results.md` | Stated requirements, decisions, known gaps and historical test claims |
| `AI TESTING/00_*` through `07_*` | Architecture evaluation and QA reports |
| `docs/*.png`, `docs/*.excalidraw` | Existing architecture, ERD and process-flow diagrams |
| `seed_init.py`, `seed_direct.py` | Seeding behaviour |
| `test_login.py` | Available test artefact |
| `database/parking_local.db` | Presence and configured data volume (schema not modified) |

Not inspected line by line: every line of every template and JavaScript file and the binary backups. These do not affect the requirement statements made.

## 2. Architecture Identified

- **Pattern:** layered monolith. Jinja2 presentation, page routes on the Flask app, eight API blueprints, core helpers, a thin SQLite data-access module.
- **Process model:** one Python process; SQLite is the only persistent store; no cache, queue, scheduler or external service.
- **Identity:** a single `users` table with `CUSTOMER`, `ADMIN` and `SUPER_ADMIN` roles.
- **Data:** eleven tables, 18 secondary indexes, 3 partial unique indexes, 4 triggers, 1 seeded setting.
- **Money:** `users.wallet_balance` for fast checks, `wallet_transactions` as the immutable ledger, `revenue_collections` pairing the two legs of each charge, all inside `BEGIN IMMEDIATE`.
- **Gate flow:** `booking_events` with at most one ENTRY and one EXIT per booking.
- **Frontend:** compiled Tailwind, one hand-written stylesheet, vanilla JS with `QS` and `QSUI`, no framework or bundler.
- **Storage:** SQLite only; nothing in the running app reaches an external database.

## 3. Implemented Features

Authentication and session control; profile self-service; public floor, vehicle-type and live availability queries; booking hold, confirm, cancel and complete; atomic wallet and revenue settlement; cancellation rules and refund reversal; QR generation and gate entry/exit with overtime settlement; admin customer management, wallet adjustment, slot control, booking filters, analytics and read-only rates; Super Admin admin management, infrastructure control, cross-user cancellation, analytics, CSV exports, system online/offline, session policy and whitelisted table browsing; audit logging; security headers, CSRF, request-size limit and health endpoint.

## 4. Partial, Planned and Absent

| Item | Classification | Note |
|---|---|---|
| Automated test suite | Absent | `tests/` does not exist; `test_results.txt` records the failure to find it |
| Landing page | Absent | `docs/api.md` and `project_spec.md` claim `/landing`; no route or template exists |
| Walk-in customer login | Partial | Accounts are created PENDING with no password; no activation flow |
| QR decoding across browsers | Partial | Depends on `BarcodeDetector`; manual entry is the fallback |
| Physical camera scanning | Unverified | No device available |
| Bundled JS QR decoder | Planned | Recommended follow-up, not implemented |
| Report definitions | Unconfirmed | Implemented shapes differ from earlier wording; recorded as TBD |
| Retention, performance targets, uptime SLA | Absent | No policy or measurement exists |
| Notifications, payment gateway, mobile app | Out of scope | No implementation |

## 5. Conflicts Discovered

1. **Test evidence.** `AGENTS.md`, `docs/api.md` and `docs/test_results.md` describe 109+ pytest tests, Playwright suites and axe runs. The `tests/` directory is absent and `test_results.txt` shows the suite could not be found. All test-based claims are therefore marked Unverified.
2. **Landing page.** Documentation describes `GET /landing` and `landing.html`. The code has neither; `/` redirects to `/login` or `/dashboard`.
3. **Revenue report.** `docs/api.md` still says revenue is filtered to COMPLETED bookings and dates on `bookings.booked_from`. `reports.py` reads `revenue_collections` and filters on `rc.created_at`. The code is authoritative.
4. **Overtime granularity.** `docs/project_spec.md` says overtime is charged per started hour. `pricing.py` and `qr.py` round up to 30-minute units. Recorded as TBD-06.
5. **Admin cancellation.** The product notes imply Admin can cancel; the customer endpoint allows only the owner, and cross-user cancellation is a Super Admin endpoint. Documented as implemented.
6. **Seeding command.** `docs/deployment.md` instructs `python seed.py`. No `seed.py` exists; `seed_init.py` and `seed_direct.py` are present.
7. **Environment file.** `.env.example` is referenced in documentation but was not among the visible root files.
8. **Session timeout wording.** `SESSION_TIMEOUT` sets the Flask cookie lifetime, while application code enforces a 20-minute absolute limit and a configurable idle limit. The document describes the effective behaviour, not the variable name alone.
9. **Hard-coded seed credential.** `seed_init.py` sets a Super Admin password in source. The value is not reproduced in the SRS. It must not be used in any deployed environment and should be rotated or removed.
10. **Predictable password rule.** `src/core/security.py` contains a prototype rule that derives a password from the first name and phone suffix. It is documented as a prototype, not a security control.

## 6. Unverified Assumptions

- Exactly one Super Admin exists; several queries use `LIMIT 1`.
- The seeded four-floor, 64-slot layout matches the deployed data.
- The server clock is accurate and timezone-consistent with operator expectations.
- The reverse proxy enforces HTTPS and forwards the correct scheme.
- Backups are taken and verified by operations staff.
- Historical test results reflect a build that included the now-missing `tests/` directory.

## 7. Documentation Limitations

- No executable tests exist to validate the requirement statements; every test reference is a claim.
- The ERD image in `docs/` predates some current columns and was not used as the authoritative source; the data dictionary is generated from `schema.sql` instead.
- Existing process-flow images were not regenerated; the JSON file provides exact specifications.
- Performance, availability and scalability figures are absent and are marked TBD rather than invented.
- No formal standards certification is claimed; ISO/IEC/IEEE 29148 informed structure only.
- PDF export was not produced because no local converter is installed.

## 8. Security Observations for Follow-up

- QR payload is an unsigned booking reference; scanning is evidence of knowledge, not proof of presence.
- Manual reference entry bypasses the camera but reaches the same server-side endpoint.
- The prototype password-generation helper and the hard-coded seed password are development artifacts and must not reach production.
- The read-only data browser is whitelisted and masks `password_hash`; it remains a privileged surface and should stay SUPER_ADMIN-only.
- No rate limiting is implemented on login or scan endpoints.
- Audit coverage is good for financial and administrative writes but does not cover every read or login attempt beyond logging.
