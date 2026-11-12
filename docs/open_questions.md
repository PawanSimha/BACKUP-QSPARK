# QSPARK — Open Questions and Decision Register

This file prevents the AI from inventing business rules. **Confirmed** requires an explicit user answer. **In effect** means the code currently does this as a safe, reversible default — confirm or change it.

## Resolved technical questions

### Q1. CSRF protection scheme — RESOLVED (12 Nov 2026)
Implemented with Flask-WTF `CSRFProtect`. Every non-GET request requires a token, delivered as `<meta name="csrf-token">` and sent by `QS` as `X-CSRFToken` (or as the `csrf_token` form field for HTML posts). No route is exempt. Missing/invalid tokens return HTTP 400 with `csrf: true`; the attempt is logged. Tokens last for the session (`WTF_CSRF_TIME_LIMIT = None`). Verified by `tests/test_security.py`.

### Q2. Tailwind delivery for production — RESOLVED (12 Nov 2026)
The CDN script was removed. Tailwind v3.4.17 is compiled by the standalone `tools/tailwindcss.exe` into `src/static/css/tailwind.css`, which `base.html` links before `app.css`. Content paths: `src/templates/**/*.html`, `src/static/js/**/*.js`. Rebuild with:
`.\tools\tailwindcss.exe -c tailwind.config.js -i src\static\css\tailwind.input.css -o src\static\css\tailwind.css --minify`
No Node/npm, no bundler, no framework.

### Q7. Physical QR scanning — BLOCKED, not a business question
The camera path uses `getUserMedia` and the same `/api/qr/scan` backend as manual entry. No camera device is available in this environment, so real-device scanning is untested. Manual reference entry works and is validated server-side, but it is not cryptographic QR proof. Recorded in `docs/test_results.md`.

## Open questions

### Q3. Exact report definitions
Report 1 — **Occupancy per floor** (`GET /api/admin/reports/occupancy`, `…/occupancy-csv`, SUPER_ADMIN for CSV):
per floor, `total_slots` = all rows in `parking_slots`, `occupied_slots` = slots whose live status is `RESERVED` or `OCCUPIED` (held/confirmed booking or entry event), `occupancy_percent` = `round(100 × occupied / total, 2)` (0 when no slots). Optional `date_from`/`date_to` (`YYYY-MM-DD`) keep only floors that have at least one booking whose `booked_from` date falls in range; no default range means all floors. `booking_count` is not part of this report despite the endpoint docstring saying "heat-map": there are no hourly rows.

Report 2 — **Revenue per floor** (`GET /api/admin/reports/revenue`, `…/revenue-csv`): only `COMPLETED` bookings, grouped by floor. `booking_count` = completed bookings, `total_revenue` = sum of `revenue_collections.amount` (refund rows positive), `net_revenue` = sum with `REFUND_REVERSAL` subtracted, `grand_total` = sum of per-floor `total_revenue`. Date filter compares `DATE(bookings.booked_from)`. The CSV variant groups by floor **and** `collection_type` and is implicitly date-filtered the same way. `GET /api/admin/reports/revenue-summary` (SUPER_ADMIN) groups `revenue_collections` by `collection_type` using `DATE(created_at)`.

**Question:** Are these the two required reports as worded, or should report 1 use hourly heat-map rows and report 2 a vehicle-type breakdown?

**Safe default (in effect):** the definitions above, streamed from real rows; not changed in this release.

### Q4. Walk-in customer activation
`POST /api/admin/users` creates a `CUSTOMER` with `account_status = 'PENDING'`, no password hash and a generated username. `PENDING` accounts cannot log in and no activation flow exists.

**Question:** Should Admin set an initial password, issue a one-time activation link, or should walk-in customers stay staff-managed (no self-service login)?

**Safe default (in effect):** staff-managed; the customer books through Admin. No plaintext/default password is ever set.

### Q5. OFFLINE scope
Today OFFLINE blocks new customer holds and confirmations (`HTTP 503`) and shows a paused notice on the booking page. QR entry/exit, wallet adjustments, admin reads and all Super Admin controls still work so nobody is stranded inside.

**Question:** Should OFFLINE also block Admin operational writes (slot control, walk-in registration, wallet adjustments) as §11 of `technical_spec.md` suggests?

**Safe default (in effect):** only customer booking writes are blocked; egress and money settlement stay available.

### Q6. Overtime settlement confirmation
On exit the gate scan debits the overtime from the customer wallet in the same transaction and records EXIT; exit is refused (409 `EXIT_BLOCKED`) with hours, amount and balance when the wallet cannot cover it.

**Question:** Is an automatic debit at scan acceptable, or must the customer approve the amount on screen first?

**Safe default (in effect):** automatic debit, blocked on insufficient balance, amount shown to staff.

## In effect — previously open, now decided by the implementation

| Was | Current behavior | Source |
|---|---|---|
| Q1 Booking start time | Customer picks a date, a start time (05:00–23:00, 30-minute steps) and a duration (≤18 h); end time is derived server-side | `booking.html`, `POST /api/bookings/hold` |
| Q2 Pricing / booking window | Rates live in `vehicle_types` and are seeded from legacy values; Super Admin owns them. Admin sees them read-only | `admin_master.html`, `src/api/admin.py` |
| Q3 Layout and starting balance | Floors/slots are seed data, not hard-coded; a new walk-in customer starts at ₹1,000 and Super Admin can change floors and slots | `schema.sql`, `seed` |
| Q5 Admin wallet adjustment | Admin may adjust **customer** wallets only; any other account requires SUPER_ADMIN. Every adjustment is confirmed, signed, ledgered and audited | `src/api/admin.py`, `src/api/super_admin.py` |
| Q6 Refund vs collection | Refund credits the customer and debits the Super Admin in the same transaction, with a `REFUND_REVERSAL` revenue row; history is never rewritten | `src/api/bookings.py` |
| Q8 "Delete user" | Always logical (`account_status = 'DELETED'`); history and bookings survive | `src/api/admin.py`, `src/api/super_admin.py` |
| Q9 "Reserved" slot | Administrative `ADMIN_RESERVED` and live `RESERVED` (held/confirmed booking) are distinct; both read as unavailable to customers | `_LIVE_STATUS_SQL` in `src/api/slots.py` |

## Confirmed decisions

No question is marked confirmed without an explicit user answer. Record the answer and date here, then update `project_spec.md`, `technical_spec.md` and the code in the same change.
