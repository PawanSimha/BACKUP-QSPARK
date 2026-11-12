# QSPARK — Implementation Plan

Single implementation checklist. Do not maintain competing plan/roadmap/todo documents.

Legend: `[x]` implemented and verified by the command in `markdown/test_results.md`; `[~]` implemented with a documented gap; `[ ]` not started.

## Phase 0 — Repository and documentation audit

- [x] Inspect repository, application, database, routes, templates, JavaScript, tests.
- [x] Compare implementation to `project_spec.md` / `technical_spec.md`.
- [x] Identify obsolete endpoints, duplicated logic, unused pages (`admin_reports.html` removed; canonical `markdown/api.md`).
- [x] Back up SQLite database before schema work (schema unchanged during frontend phase).
- [x] Record migration risks and unresolved decisions (`open_questions.md`).

## Phase 1 — Database and data-access foundation

- [x] 11-table model in one authoritative `schema.sql`.
- [x] PK/FK/UNIQUE/CHECK/NOT NULL/defaults/indexes.
- [x] Six metadata/reserved fields at the end of every table.
- [x] Foreign keys enabled on every connection (`PRAGMA foreign_keys=ON`).
- [x] Safe initialization + repeatable seeding; env-driven seed passwords.
- [x] Floor/slot and vehicle-type seed data.
- [x] Secure bootstrap for Super Admin and three Admins (generated passwords printed once).
- [x] Schema tests; `markdown/db.md` generated from the executable schema.

## Phase 2 — Authentication and permissions

- [x] Login/logout/current-user endpoints and pages; `PATCH /api/auth/me` for self-service contact edits.
- [x] Werkzeug password hashing; session auth; fresh user reload per request.
- [x] CUSTOMER / ADMIN / SUPER_ADMIN authorization on APIs and page routes.
- [x] ACTIVE / BLOCKED / DELETED account handling.
- [x] Admin and Super Admin can use the normal customer booking experience (admin-on-behalf booking supported).
- [~] CSRF: not implemented as a token scheme. SameSite=Lax session cookie + same-origin JSON only. Tracked in `open_questions.md`.

## Phase 3 — Floors, slots and availability

- [x] Floor and slot queries plus configuration APIs.
- [x] Live slot state derived from control state, bookings and events (`_LIVE_STATUS_SQL`).
- [x] Availability filtered by floor and vehicle type.
- [x] Admin maintenance/reservation with active-booking safeguards.
- [x] Super Admin floor/slot create, update, deactivate.
- [x] Delete/deactivate refuses while active bookings or an occupied vehicle exist.

## Phase 4 — Customer booking and wallet/revenue

- [x] Vehicle format/number validation on client and server.
- [x] Hold, confirm, cancel, hold expiry (30 min).
- [x] Non-overlapping slot bookings and one active booking per vehicle under `BEGIN IMMEDIATE`.
- [x] Rates captured at booking time; estimates from configured rates.
- [x] Wallet ledger with balance snapshots.
- [x] Super Admin revenue credit + `revenue_collections` written in the same transaction.
- [x] Cancellation/refund per confirmed rules.
- [x] Repeated confirm/cancel cannot double-charge.

## Phase 5 — QR, entry, exit and overtime

- [x] QR generated for confirmed bookings (`/api/qr/generate`).
- [x] Camera scanning (`BarcodeDetector`) with manual-reference fallback.
- [x] ENTRY and EXIT recorded as separate `booking_events`.
- [x] Event sequence and booking state validated.
- [x] Overtime calculated and settled atomically; exit blocked when the wallet cannot cover it.

## Phase 6 — Admin operations

- [x] Admin dashboard and floor monitoring.
- [x] Walk-in registration (name, mobile, gender, company, optional email).
- [x] Customer view/update/logical deactivation.
- [x] Slot Maintenance/Reserved/Active controls.
- [x] All-bookings view with filters.
- [x] Operational QR scanning page.
- [x] Occupancy and revenue analytics.
- [x] Restrictions enforced server-side.

## Phase 7 — Super Admin operations

- [x] Super Admin dashboard.
- [x] Admin create/update/block/unblock/logical deactivation.
- [x] User and wallet administration with explicit credit/debit and confirmation.
- [x] Booking cancellation with financial reversal (never for an entered, unexited vehicle).
- [x] Floor/slot configuration with impact confirmation.
- [x] Read-only paginated whitelisted table views with `password_hash` masked.
- [x] Overtime, floor heatmap, revenue charts from real data.
- [x] Two CSV report downloads (occupancy, revenue) streaming real rows.
- [x] ONLINE/OFFLINE control with Super Admin recovery access retained; state enforced by the API.
- [x] Every privileged change audited.

## Phase 8 — UI integration and quality verification

- [x] All pages connected to real endpoints; design system applied to every role.
- [x] Dead links and obsolete calls removed (orphan `admin_reports.html` deleted).
- [x] Role navigation and shared booking interface verified.
- [x] Automated tests: backend, frontend contract, Playwright E2E.
- [x] Security review: authorization, input validation, password exposure, table whitelist, XSS escaping.
- [x] Documentation updated: `AGENTS.md`, `project_spec.md`, `technical_spec.md`, `api.md`, `db.md`, `test_results.md`, `frontend.md`, `open_questions.md`.

## Phase 8b — Release readiness, security hardening and QA (12 Nov 2026)

- [x] CSRF protection (Flask-WTF) for every state-changing route, HTML forms and fetch; no exemptions. Tests in `tests/test_security.py`.
- [x] Compiled Tailwind CSS replaces the CDN; reproducible standalone build documented.
- [x] Financial integrity audit with atomicity, duplicate and concurrency tests (`tests/test_financial.py`).
- [x] Booking allocation safety and confirm-time revalidation (`tests/test_booking_safety.py`).
- [x] QR entry/exit state-machine tests (`tests/test_qr_flow.py`).
- [x] axe-core accessibility audit across all authenticated pages, zero violations (`tests/test_a11y.py`).
- [x] Cross-engine Playwright checks: Chromium, Firefox, WebKit (`tests/test_browsers.py`).
- [x] Session/security hardening: HttpOnly, SameSite, optional Secure, security headers, `MAX_CONTENT_LENGTH`, production secret guard, failed-login and 500 logging.
- [x] Deployment, backup and restore guide (`markdown/deployment.md`); `requirements.txt` and `.env.example` updated.
- [x] **Password rotation for exposed privileged accounts** (`admin1` ADMIN and `superadmin` SUPER_ADMIN): old credentials rejected, new credentials verified; customer accounts unaffected; audit events recorded; schema unchanged.
- [x] QR scanner camera lifecycle: preview independent of QR-decoder availability, `BarcodeDetector` feature-detected, per-error camera messages, tracks stopped on exit (`src/templates/qr_scan.html`).
- [x] Frontend DOM wiring guard: `tests/test_frontend_wiring.py` fails if an inline script references an element the page never renders (26 tests).
- [ ] Physical QR scanning on a real camera device — blocked, no hardware available.
- [ ] Bundled JS QR decoder for browsers without `BarcodeDetector` (Firefox) — not started; manual reference entry is the current fallback (`markdown/test_results.md`).
- [ ] Safari/real mobile browser verification — not performed (WebKit only).
- [ ] Report business definitions confirmed by owner (`open_questions.md` Q3).
- [ ] Walk-in activation model approved (`open_questions.md` Q4).

## Phase 9 — Future Phase 2 (Oracle APEX/ORDS) — not started

- [ ] Plan schema migration.
- [ ] Define ORDS APIs and auth model.
- [ ] Data-access abstraction for SQLite/ORDS.
- [ ] Migration parity tests.

Do not start Phase 9 during Phase 1 unless explicitly requested.
