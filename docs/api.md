# QSPARK API Documentation

All endpoints return JSON. Session-cookie authentication (`POST /api/auth/login`).
Roles are read from the database (`users.role`) — never from the client.
Error shape: `{"error": "<message>", "code": <http_status>}`.

Roles: `CUSTOMER`, `ADMIN`, `SUPER_ADMIN`. "Admin+" means ADMIN or SUPER_ADMIN.

## CSRF (all state-changing routes)

Every `POST`, `PUT`, `PATCH` and `DELETE` requires a valid CSRF token; `GET`/`HEAD`/`OPTIONS` do not.

- Send it as `X-CSRFToken: <token>`, or as a `csrf_token` form field for HTML `<form>` posts.
- Get it from the `csrf-token` meta tag on any rendered page (`<meta name="csrf-token" content="…">`). `QS` in `src/static/js/core/api.js` reads it automatically.
- Tokens are bound to the session and do not expire on their own; the session cookie lifetime (`SESSION_TIMEOUT`, default 3600 s) does.
- Rejection: HTTP 400, `{"error": "Your form session expired or the security token is missing. Reload the page and try again.", "code": 400, "csrf": true}`. No endpoint is exempt.
- When the pytest suite (not in the current tree) runs, the shared fixture sets `WTF_CSRF_ENABLED = False`; `tests/test_security.py` exercises tokens with CSRF enabled.

---

## Authentication

### POST /api/auth/login
- Roles: public
- Body: `{"username": "cust1", "password": "..."}` (also accepts form data)
- 200: `{"user": {user_id, username, email, full_name, role, wallet_balance, phone}}` (session cookie set; there is no bearer token)
- 400 missing fields, 401 invalid credentials
- Requires a CSRF token (all POSTs do). Failed attempts are logged with the username and remote address, never the password.

### POST /api/auth/logout
- Roles: any authenticated
- HTML form post: 302 → `/login`; JSON request: 200 `{"message": "Logged out"}`
- 400 without a CSRF token, 401 if not logged in

### GET /api/auth/me
- Roles: any authenticated
- 200: current user object (wallet refreshed from DB); 401 otherwise

### POST /api/auth/setup-admin
- Roles: public (one-time bootstrap; guarded by env vars)
- Creates Super Admin + default admins if none exist
- 201 created, 409 already exists, 500 missing env config

---

## Shared customer booking APIs
Available to CUSTOMER, ADMIN and SUPER_ADMIN.

### GET /api/slots/floors
- Roles: public
- 200: `{"items": [{floor_id, floor_code, floor_status, total_slots, available_slots}]}` (live state; inactive floors omitted)

### GET /api/slots/vehicle-types
- Roles: public
- 200: `{"items": [{vehicle_type_id, type_name, hourly_rate, overstay_rate, is_active}]}` (active only)

### GET /api/slots/availability
- Roles: public
- Query: `floor_id` (optional), `vehicle_type_id` (optional)
- 200: `{"items": [{slot_id, slot_number, floor_id, vehicle_type_id, control_status, status, floor_code, floor_status, vehicle_type, hourly_rate, overstay_rate, color}], floor_id, vehicle_type_id, total}`
- `status` is live: AVAILABLE | RESERVED | OCCUPIED | MAINTENANCE | INACTIVE. `control_status` is the stored state.

### GET /api/slots/{slot_id}
- Roles: public
- 200: slot object with live `status`; 404 not found

### POST /api/bookings/hold
- Roles: any authenticated (CUSTOMER/ADMIN/SUPER_ADMIN)
- Body: `{slot_id, vehicle_number, vehicle_format (std1|std2|std3|bhr, default std1), booked_from, booked_until, user_id?}`
- `user_id` is honoured only for ADMIN/SUPER_ADMIN (booking on behalf of a registered customer).
- 201: `{booking_reference, user_id, slot_id, slot_number, vehicle_type, vehicle_number, booked_from, booked_until, duration_hours, hourly_rate, estimated_amount, booking_status:"HELD", hold_expires_at, message}`
- Errors: 400 invalid/validation, 401, 403 inactive, 404 slot, 409 slot unavailable/overlap/duplicate vehicle, 503 system offline

### POST /api/bookings/{booking_reference}/confirm
- Roles: booking owner (any role)
- 200: `{booking_reference, booking_status:"CONFIRMED", amount_debited, new_wallet_balance, qr_generated:true, message}`
- Errors: 401, 403 not owner, 404, 402 insufficient wallet, 409 not HELD/expired, 503 offline

### GET /api/bookings/{booking_reference}
- Roles: owner or Admin+
- 200: booking + `events[]`; 403 not owner, 404

### GET /api/bookings/my
- Roles: any authenticated
- 200: `{"items": [booking...]}` for the current user only; each row includes `has_entered` (open ENTRY event without EXIT)

### PATCH /api/auth/me
- Roles: any authenticated
- Body: any of `{full_name, phone (10 digits), gender, company_name}`; role, wallet and status are not writable here
- 200: updated user object; 400 invalid/no fields; 500 on write failure

### POST /api/bookings/{booking_reference}/cancel
- Roles: booking owner
- 200: `{booking_reference, booking_status:"CANCELLED", refund_amount, penalty_amount, net_credit, new_wallet_balance, message}`
- Errors: 401, 403, 404, 409 not cancellable / vehicle entered

### GET /api/bookings/wallet/transactions/me
- Roles: any authenticated
- 200: `{wallet_balance, transactions:[...]}`

---

## Admin APIs (ADMIN + SUPER_ADMIN)

### GET /api/admin/floors
- 200: `{"items": [{floor_id, floor_code, floor_status, total_slots, available_slots, occupied_slots}]}` (live state)

### GET /api/admin/vehicle-types
- 200: `{"items": [{vehicle_type_id, type_name, hourly_rate, overstay_rate, is_active}]}`

### GET /api/admin/slots?floor_id=
- 200: `{"items": [{slot_id, slot_number, floor_id, vehicle_type_id, control_status, status, floor_code, vehicle_type, occupant}], total}` where `occupant` is null for free slots, else `{booking_reference, full_name, username, vehicle_number, booked_from, booked_until, booking_status, entry_time}`
- Compatibility aliases (same handlers, kept working):
  - `GET /api/admin/master/floors`
  - `GET /api/admin/master/vehicle-types`
  - `GET /api/admin/master/slots`
  - `GET /api/admin/master/users`
  - `GET /api/admin/master/cancellation-rules`
  - `PUT /api/admin/master/floors/{floor_id}` — body `{floor_status}`; same as `PUT /api/super-admin/floors/{floor_id}`
  - `PUT /api/admin/master/slots/{slot_id}/status` — body `{control_status}`; same as `PATCH /api/admin/slots/{slot_id}/control-status`

### GET /api/admin/dashboard
- 200: `{total_slots, available_slots, reserved_slots, occupied_slots, maintenance_slots, total_revenue, active_users}`

### GET /api/admin/bookings
- Query: `date_from, date_to, status, floor, vehicle_type, user_search`
- 200: `{"items":[...], "total": n}`

### POST /api/admin/users
- Registers a walk-in customer. Body: `{full_name, phone, gender?, company_name?, email?, username?}`
- 201: `{user_id, username, message}`; 400, 409 duplicate

### GET /api/admin/users
- 200: `{"items":[...]}` (no password_hash)

### GET /api/admin/users/{user_id}
- 200 user object; 404

### PUT /api/admin/users/{user_id}
- Admin can update CUSTOMER accounts only. Body: any of full_name, phone, email, gender, company_name, username, account_status
- 200; 403 if target is admin (unless SUPER_ADMIN), 404

### DELETE /api/admin/users/{user_id}
- Soft delete (account_status = DELETED)
- 200; 403 target admin, 404

### POST /api/admin/users/{user_id}/wallet-adjustments
- Body: `{amount (non-zero), description?}`
- 200: `{user_id, previous_balance, new_balance, adjustment}`
- 400 negative result, 403 non-customer target (unless SUPER_ADMIN), 404

### GET /api/admin/users/{user_id}/wallet
- 200: `{user_id, wallet_balance, transactions:[...]}`

### PATCH /api/admin/slots/{slot_id}/control-status
- Body: `{control_status: ACTIVE|ADMIN_RESERVED|MAINTENANCE}`
- 200: `{slot_id, control_status}`
- 409 if slot booked/occupied; 404

### GET /api/admin/cancellation-rules
- 200: `{"items":[...]}`

### POST /api/admin/cancellation-rules
- Body: `{rule_code, rule_name, min_hours_before?, max_hours_before?, is_no_show?, refund_percent, penalty_percent, description?, is_active?}`
- 201: `{rule_id, message}`

### PUT /api/admin/cancellation-rules/{rule_id}
- 200; 404

### DELETE /api/admin/cancellation-rules/{rule_id}
- Deactivates (is_active=0); 200; 404

### POST /api/admin/qr/scan
- Alias of `POST /api/qr/scan` (see below)

### GET /api/admin/reports/occupancy
- Query: `date_from, date_to` (`YYYY-MM-DD`, optional)
- Per floor: `total_slots` = all slots on the floor, `occupied_slots` = slots currently `RESERVED` or `OCCUPIED`; `occupancy_percent = round(100 × occupied / total, 2)`.
- Date filter keeps floors having at least one booking whose `booked_from` date is in range; unfiltered = all floors. No hourly rows exist despite the `floor_heatmaps` key.
- 200: `{floor_heatmaps:[{floor_code, floor_status, total_slots, occupied_slots, occupancy_percent}], date_from, date_to}`

### GET /api/admin/reports/revenue
- Query: `date_from, date_to`
- Only `COMPLETED` bookings, grouped by floor. `total_revenue` = sum of `revenue_collections.amount`; `net_revenue` = same with `REFUND_REVERSAL` subtracted; `grand_total` = sum of per-floor `total_revenue`. Date filter uses `DATE(bookings.booked_from)`.
- 200: `{floor_revenue:[{floor_code, booking_count, total_revenue, net_revenue}], grand_total, date_from, date_to}`

### GET /api/admin/reports/revenue-summary
- Roles: SUPER_ADMIN
- Groups `revenue_collections` by `collection_type`; date filter uses `DATE(created_at)`
- 200: `{revenue_summary:[{collection_type, count, total_amount}]}`

### GET /api/admin/reports/occupancy-csv
### GET /api/admin/reports/revenue-csv
- Roles: SUPER_ADMIN
- 200: `text/csv` attachment (occupancy: floor totals; revenue: grouped by floor and `collection_type`, completed bookings only)

---

## QR scanning

### POST /api/qr/generate
- Roles: booking owner or Admin+
- Body: `{booking_reference}`
- 200: `{booking_reference, qr_base64, qr_data}`; 409 not confirmed, 403, 404

### POST /api/qr/scan
- Roles: Admin+ or booking owner
- Body: `{booking_reference, scan_method?: QR|MANUAL}`
- 200 ENTRY: `{action:"ENTRY", ...}`
- 200 EXIT: `{action:"EXIT", overstay_hours, overstay_amount, ...}` (overtime settled atomically)
- 409 `{action:"EXIT_BLOCKED", ...}` when overtime unaffordable; 409 duplicate/already exited; 403; 404

---

## Super Admin APIs (SUPER_ADMIN only)

### Admins
- POST `/api/super-admin/admins` — body `{full_name, phone, username, password, email?, gender?, company_name?}` → 201 `{user_id, admin_id, message}`
- GET `/api/super-admin/admins` → `{items:[{user_id, admin_id, full_name, phone, email, gender, company_name, username, account_status, wallet_balance, created_at}]}`
- GET `/api/super-admin/admins/{user_id}` → admin object; 404
- PUT `/api/super-admin/admins/{user_id}` — update admin fields; 200
- DELETE `/api/super-admin/admins/{user_id}` — soft delete; 200
- PATCH `/api/super-admin/admins/{user_id}/status` — body `{account_status: ACTIVE|BLOCKED}`; 200

### Wallets
- POST `/api/super-admin/users/{user_id}/wallet-adjustments` — body `{amount, description?}`; 200
- GET `/api/super-admin/users/{user_id}/wallet` — 200

### Floors
- POST `/api/super-admin/floors` — body `{floor_code}`; 201 `{floor_id, floor_code}`
- PUT `/api/super-admin/floors/{floor_id}` — body `{floor_status}`; 200
- DELETE `/api/super-admin/floors/{floor_id}` — safe deactivation; 409 if active bookings

### Slots
- POST `/api/super-admin/floors/{floor_id}/slots` — body `{slot_number, vehicle_type_id}`; 201
- PUT `/api/super-admin/slots/{slot_id}` — body `{slot_number?, control_status?}`; 409 if active booking for maintenance/reserved
- DELETE `/api/super-admin/slots/{slot_id}` — deactivate; 409 if active booking

### Bookings
- POST `/api/super-admin/bookings/{booking_reference}/cancel` — refund + revenue reversal; 409 if entered/not cancellable

### Live DB tables (read-only, whitelisted)
- GET `/api/super-admin/db-tables/{table_name}?page=1&per_page=25`
- Allowed: users, floors, vehicle_types, parking_slots, bookings, cancellation_rules, wallet_transactions, booking_events, audit_logs, revenue_collections, system_settings
- `users` view excludes password_hash
- 403 if table not whitelisted

### Analytics
- GET `/api/super-admin/analytics/overview` → `{total_customers, total_bookings, completed_bookings, net_revenue, total_slots, occupied_slots, occupancy_percent}`
- GET `/api/super-admin/analytics/overtime` → `{overtime:[{day, count, amount}]}`
- GET `/api/super-admin/analytics/floor-heatmap` → `{floors:[{floor_code, floor_status, total_slots, occupied_slots, occupancy_percent}]}`
- GET `/api/super-admin/analytics/revenue?date_from&date_to` → `{by_floor, by_vehicle_type, by_day}`

### Reports (CSV)
- GET `/api/super-admin/reports/occupancy.csv`
- GET `/api/super-admin/reports/revenue.csv`
- 200 text/csv

---

## System control

### GET /api/system/status
- Roles: public
- 200: `{system_status: "ONLINE"|"OFFLINE"}`

### PATCH /api/system/super-admin/system/status
- Roles: SUPER_ADMIN only
- Body: `{system_status: ONLINE|OFFLINE}`
- 200: `{system_status}`; 400 invalid

When OFFLINE: customers cannot hold/confirm bookings (503); Super Admin retains access to restore ONLINE.

---

## HTML page routes (Jinja2 shells)

Every page route below requires a signed-in session. Unknown roles receive `error.html` with HTTP 403. Page routes render markup only; data is fetched from the JSON APIs above by `src/static/js`.

| Route | Template | Roles |
|---|---|---|
| `/landing` | `landing.html` | public |
| `/login` | `login.html` | public |
| `/dashboard` | `dashboard.html` | any authenticated |
| `/booking` | `booking.html` | any authenticated |
| `/bookings/my` | `my_bookings.html` | any authenticated |
| `/wallet` | `wallet.html` | any authenticated |
| `/profile` | `profile.html` | any authenticated |
| `/confirm/<booking_reference>` | `confirm.html` | booking owner view; Admin+ allowed by API |
| `/admin/dashboard` | `admin_dashboard.html` | ADMIN, SUPER_ADMIN |
| `/admin/bookings` (alias `/admin/bookings/page`) | `admin_bookings.html` | ADMIN, SUPER_ADMIN |
| `/admin/customers` | `admin_customers.html` | ADMIN, SUPER_ADMIN |
| `/admin/slots` | `admin_slots.html` | ADMIN, SUPER_ADMIN |
| `/admin/analytics` | `admin_analytics.html` | ADMIN, SUPER_ADMIN |
| `/admin/master` | `admin_master.html` | ADMIN, SUPER_ADMIN |
| `/admin/qr-scan` | `qr_scan.html` | ADMIN, SUPER_ADMIN |
| `/super-admin/dashboard` | `super_admin_dashboard.html` | SUPER_ADMIN |
| `/super-admin/admins` | `super_admin_admins.html` | SUPER_ADMIN |
| `/super-admin/infrastructure` | `super_admin_infrastructure.html` | SUPER_ADMIN |
| `/super-admin/analytics` | `super_admin_analytics.html` | SUPER_ADMIN |
| `/super-admin/data` | `super_admin_data.html` | SUPER_ADMIN |
| `/super-admin/system` | `super_admin_system.html` | SUPER_ADMIN |

`GET /health` and `GET /` (redirect to `/landing` when signed out, `/dashboard` when signed in) are also public. HTML 404/500/400 render `error.html`; API paths receive JSON errors.

## HTTP status codes used
- 200 OK, 201 Created, 400 Bad Request (validation or CSRF), 401 Unauthenticated, 402 Payment Required,
- 403 Forbidden, 404 Not Found, 409 Conflict, 413 Payload Too Large, 500 Server Error, 503 Service Unavailable