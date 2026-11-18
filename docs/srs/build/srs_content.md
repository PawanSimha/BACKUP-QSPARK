# 1. Introduction

## 1.1 Purpose

This document specifies the requirements of QSPARK, a web-based smart parking slot booking and management system. It records what the implemented system does, how it is structured, which data it persists and which constraints apply. It is intended to support maintenance, testing, audit, handover and academic assessment of the existing product.

The specification was produced by reverse-engineering the running implementation, the executable database schema and the verified project documentation. It does not propose new features except where a gap is explicitly labelled TBD or Planned.

## 1.2 Document Conventions

Requirement identifiers use the form `FR-<MODULE>-<nnn>` for functional requirements and `NFR-<CLASS>-<nnn>` for non-functional requirements. Identifiers are stable and are referenced again in the traceability matrix in Section 11.

Priorities use three values: **Must** (required for the product to operate), **Should** (required for a complete operational deployment) and **May** (optional or cosmetic).

Status values distinguish **AS-IS** (implemented and observable in code), **TO-BE** (approved future work), and **TBD** (unconfirmed, recorded in Appendix C). The keyword "shall" denotes a binding requirement; "may" denotes a permitted option.

Headings use Word's native heading styles. Body text is Times New Roman 12 pt, justified, 1.5 line spacing. Tables use 10 pt. Figure and table captions use 10 pt italic. Bold text marks identifiers, field names and UI labels; italics mark notes and document titles.

## 1.3 Intended Audience and Reading Suggestions

| Audience | Suggested reading |
|---|---|
| Project stakeholders and academic reviewers | Sections 1, 2, 3, 6 and 12 |
| Software developers and architects | Sections 2, 3, 7, 8 and 9 |
| QA and test engineers | Sections 3, 6, 8, 9 and 11 |
| Database administrators | Sections 7 and 8 |
| Operations and deployment staff | Sections 10 and 5 |
| Project managers | Sections 1, 2, 11 and Appendix C |

## 1.4 Product Scope

QSPARK allows a registered customer to reserve a parking slot in advance, pay from an internal wallet, receive a QR-coded booking reference and use that reference at the gate. Staff scan or key the reference to register vehicle entry and exit. Administrators manage customers, slots, bookings, refund rules and day-to-day operations. A Super Admin manages administrators, infrastructure, revenue, system-wide online/offline state and read-only database inspection.

The system solves three operational problems: advance slot allocation with overlap prevention, cashless internal settlement with an auditable ledger, and gate-level entry/exit tracking tied to the reservation.

In scope: role-based web application, booking lifecycle, wallet and revenue settlement, cancellation and refund rules, QR entry/exit, overtime settlement, floor and slot management, analytics and CSV reports, system state control, audit logging and a whitelisted read-only data browser.

Out of scope: real payment gateway integration, native mobile applications, SMS or email notification providers, external identity providers, hardware gate controllers, multi-tenant operation and any deployment beyond a single Flask process.

## 1.5 References

| Reference | Use in this document |
|---|---|
| ISO/IEC/IEEE 29148:2018 — Requirements engineering | Structure and quality of requirement statements |
| IEEE 830-1998 — Recommended practice for SRS | Section organisation (adapted) |
| RFC 6265 — HTTP State Management Mechanism | Session cookie behaviour |
| OWASP Application Security Verification Standard 4.0 | Security requirement categories (referenced, not certified) |
| WCAG 2.2 Level AA | Accessibility expectations |
| Flask 3.x, Werkzeug 3.x, Flask-WTF 1.x documentation | Framework behaviour |
| SQLite 3 documentation | Constraints, triggers, transaction behaviour |
| Tailwind CSS 3.4 documentation | Styling build |
| Project files: `schema.sql`, `docs/project_spec.md`, `docs/technical_spec.md`, `docs/api.md`, `docs/db.md`, `docs/test_results.md`, `docs/open_questions.md` | Primary project evidence |
| Repository source under `app.py` and `src/` | Authoritative implementation evidence |

No claim of formal certification or standards compliance is made. The references informed the document's structure only.

# 2. Overall Description

## 2.1 Product Perspective

QSPARK is a self-contained, server-rendered web application. A single Python process serves HTML shells and JSON APIs; a single SQLite file holds all business data. There is no separate frontend build server, message broker, cache or payment provider. The browser renders pages from Jinja2 templates, then loads data from the JSON APIs with vanilla JavaScript.

The system is not an extension of another product. Its only external runtime dependency is the browser's media stack for the optional camera scanner and the operating system's file system for the database and logs. The delivered system is SQLite-only.

## 2.2 Product Functions

| Module | Summary |
|---|---|
| Authentication and session | Login by username or email, session issuance, idle and absolute expiry, logout |
| Profile self-service | Read and update own name, phone, gender and company |
| Availability discovery | Public floor, vehicle-type and live slot-state queries |
| Booking lifecycle | Hold, confirm, expire, cancel, complete; overlap and duplicate-vehicle prevention |
| Wallet and revenue | Atomic customer debit, Super Admin credit, paired ledger entries and a collection record |
| Cancellation and refund | Rule-driven refund and penalty calculation with revenue reversal |
| QR entry and exit | QR generation for confirmed bookings, entry/exit events, overtime settlement |
| Admin customer management | Walk-in registration, search, update, logical deletion, wallet adjustment |
| Admin parking operations | Slot control states, booking oversight, gate scanning, read-only rates |
| Super Admin management | Admin CRUD, block/unblock, wallet adjustment for any account |
| Super Admin infrastructure | Floor and slot creation, status change, safe deactivation |
| Analytics and reports | Occupancy, revenue, overtime, heat maps, CSV export |
| System control | ONLINE/OFFLINE switch, session-timeout policy |
| Audit and data inspection | Audit log writes, whitelisted read-only table browser |

## 2.3 User Classes and Characteristics

| Role | Responsibilities and permissions | Access restrictions | Assumed proficiency |
|---|---|---|---|
| CUSTOMER | Books parking, pays from wallet, views own bookings and ledger, edits own profile, presents QR | Cannot access admin or Super Admin pages; cannot cancel another user's booking | Basic browser use |
| ADMIN | Registers and maintains customers, adjusts customer wallets, controls slot states, views bookings, scans QR, views analytics and read-only rates | Cannot manage other admins; cannot change system state; cannot cancel an occupied booking | Operational staff, moderate proficiency |
| SUPER_ADMIN | Full administrative authority: admins, any wallet, floors, slots, cancellations, analytics, reports, system state, database views | No restrictions inside the application | Technical administrator |
| Anonymous visitor | Login page, health endpoint, public availability queries | No session, no booking | Basic browser use |

All three roles share one account table and one login mechanism. Admin and Super Admin accounts also have a customer-facing booking interface. Initial counts (three Admins, one Super Admin) are seed defaults, not hard limits.

## 2.4 Operating Environment

| Layer | Verified environment |
|---|---|
| Server language | Python 3.14.10 (project states Python 3.11 or newer as the minimum) |
| Web framework | Flask 3.1.3 application factory, Waitress 3.0.2 for production |
| Database | SQLite 3 single file, created from `schema.sql` |
| Templates | Jinja2, server-rendered HTML5 |
| Styling | Tailwind CSS 3.4.17 compiled by a standalone binary, plus `app.css` |
| Client script | Vanilla JavaScript, `QS` and `QSUI` globals, no framework |
| QR | `qrcode[pil]` 8.2 server-side, `BarcodeDetector` browser API for decoding |
| Server OS | Windows 10/11 or Linux with Python 3.11+ |
| Client | Current Chromium, Firefox or WebKit-based browser; camera optional |
| Hosting | One application process behind a TLS-terminating reverse proxy |

## 2.5 Design and Implementation Constraints

- **Single-writer database.** SQLite serialises writes; the design assumes one application process. Horizontal scaling is not supported.
- **Session authentication only.** No bearer tokens, OAuth or external identity provider; every state-changing request also requires a CSRF token.
- **Server authority.** Financial results, availability and booking state are computed server-side; the browser only displays the response.
- **Append-only financial history.** Corrections use reversal entries, never in-place edits.
- **No Node toolchain.** Tailwind is pre-compiled; the runtime image needs no Node or npm.
- **Camera decoding depends on `BarcodeDetector`.** Where the API is absent, operators must use manual reference entry.
- **One currency and one locale.** Amounts are INR rounded to two decimals; timestamps are stored as SQLite datetime text.
- **No background scheduler.** Hold expiry is applied lazily at confirmation time rather than by a timer.

## 2.6 Assumptions and Dependencies

- The server clock is authoritative for booking, expiry and overtime calculations.
- The database file is on a writable local volume and is backed up independently.
- Exactly one Super Admin account exists; several flows select `LIMIT 1` when locating the revenue wallet.
- The operator has physical access control at the gate; QR scanning is advisory software evidence, not cryptographic proof of presence.
- Camera scanning requires HTTPS or `localhost`.
- Seeded floor, slot and rate values are configuration defaults, not invariants.

## 2.7 System Architecture Overview

The implementation is a four-layer monolith. The presentation layer renders Jinja2 shells; the route layer exposes page routes and JSON blueprints; the domain layer contains security guards, pricing and booking/wallet logic inside the API modules; the data layer wraps SQLite connections and transactions. `app.py` owns configuration, security headers, session validation and error handlers.

Eight blueprints are registered: `auth` (`/api/auth`), `slots` (`/api/slots`), `bookings` (`/api/bookings`), `qr` (`/api/qr`), `admin` (`/api/admin`), `reports` (`/api/admin/reports`), `super_admin` (`/api/super-admin`) and `system` (`/api/system`). Page routes live directly on the application object.

[[FIGURE:Technical Architecture Diagram.png|QSPARK technical architecture as documented in the project repository]]

[[DIAGRAM:DIA-001|System context: actors, QSPARK process and the SQLite data store]]

# 3. System Features and Functional Requirements

## 3.1 Authentication and Session Management

### 3.1.1 Description

Authenticates a user by username or email against an ACTIVE account, verifies a PBKDF2-SHA256 hash and stores identity in a signed Flask session. All protected APIs resolve the role from the server-side session and re-read the account on every page request.

### 3.1.2 Actors

Anonymous visitor, CUSTOMER, ADMIN, SUPER_ADMIN.

### 3.1.3 Preconditions

The account exists, is ACTIVE and has a password hash. The request carries a valid CSRF token for state-changing calls.

### 3.1.4 Stimulus and Response Sequence

1. The visitor requests `/login` and receives the sign-in form with a CSRF token in the page meta tag.
2. The visitor submits credentials to `POST /api/auth/login`.
3. The system matches username or email case-insensitively, rejects non-ACTIVE accounts, verifies the password hash and clears any previous session.
4. The system stores user identity, role, wallet balance and session timestamps, and returns the user object.
5. On each subsequent page request the system checks the absolute session age and the configured idle timeout, then re-reads the account and clears the session if it is missing or inactive.

### 3.1.5 Functional Requirements

- **FR-AUTH-001 (Must):** The system shall authenticate a user with a username or email and a password, matching the identifier case-insensitively.
- **FR-AUTH-002 (Must):** The system shall reject authentication for accounts whose status is not ACTIVE.
- **FR-AUTH-003 (Must):** The system shall store passwords only as salted PBKDF2-SHA256 hashes and shall never return the hash in any API response.
- **FR-AUTH-004 (Must):** The system shall issue a signed session cookie marked HttpOnly and SameSite=Lax, adding Secure when configured for HTTPS.
- **FR-AUTH-005 (Must):** The system shall clear the session after 20 minutes of absolute age and after the configured idle period, evaluated server-side.
- **FR-AUTH-006 (Must):** The system shall require a valid CSRF token on every POST, PUT, PATCH and DELETE request.
- **FR-AUTH-007 (Must):** The system shall clear the session on logout and redirect HTML form posts to `/login`.
- **FR-AUTH-008 (Must):** The system shall redirect unauthenticated page requests to `/login?error=login_required`.
- **FR-AUTH-009 (Must):** The system shall return HTTP 401 for unauthenticated API requests and HTTP 403 for authenticated requests with an insufficient role.
- **FR-AUTH-010 (Should):** The system shall provide a one-time bootstrap endpoint that creates the Super Admin and default admins only when no privileged account exists.

### 3.1.6 Business Rules

- Login accepts either `username` or `email`; at least one must be non-null for an account to exist.
- An ACTIVE account must have a password hash (database CHECK constraint).
- Failed logins are logged with the attempted username and remote address, never the password.
- Sessions are non-permanent; `SESSION_TIMEOUT` sets the Flask lifetime, while application-level checks enforce the 20-minute absolute limit and the configurable idle limit.
- Idle timeout is selectable only from 5, 10, 15 or 20 minutes by the Super Admin.

### 3.1.7 Alternate and Exception Flows

- Missing credentials: HTTP 400.
- Unknown user, inactive account or wrong password: HTTP 401 with a generic message.
- Missing or invalid CSRF token: HTTP 400 with `csrf: true`.
- Expired or inactive session: the session is cleared and the next request behaves as unauthenticated.
- Production start without `SECRET_KEY`: the application raises at startup.

### 3.1.8 Acceptance Criteria

1. Valid credentials return 200 and a session cookie. Invalid credentials return 401 and set no session.
2. A BLOCKED or DELETED account cannot log in.
3. A request without `X-CSRFToken` to any POST returns 400.
4. A session older than 20 minutes is rejected on the next request.
5. No response body contains `password_hash`.

## 3.2 Profile and Account Self-Service

### 3.2.1 Description

Allows an authenticated user to read their own account and to change a limited set of profile fields.

### 3.2.2 Actors

CUSTOMER, ADMIN, SUPER_ADMIN.

### 3.2.3 Preconditions

An active session.

### 3.2.4 Stimulus and Response Sequence

1. The user opens `/profile`; the page fetches `GET /api/auth/me`.
2. The user edits name, mobile, gender or company and submits `PATCH /api/auth/me`.
3. The system validates the supplied fields and updates only the permitted columns.

### 3.2.5 Functional Requirements

- **FR-PROF-001 (Must):** The system shall return the authenticated user's current record, including the refreshed wallet balance.
- **FR-PROF-002 (Must):** The system shall allow the user to update full name, phone, gender and company name only.
- **FR-PROF-003 (Must):** The system shall reject attempts to change role, wallet balance or account status through the profile endpoint.
- **FR-PROF-004 (Must):** The system shall require a 10-digit phone number when a phone is supplied.

### 3.2.6 Business Rules

- Gender is restricted to MALE, FEMALE, OTHER or PREFER_NOT_TO_SAY.
- An empty update body returns HTTP 400.
- Email and username are not self-editable through this endpoint.

### 3.2.7 Alternate and Exception Flows

- Invalid phone length or gender value: HTTP 400, no write.
- No fields supplied: HTTP 400.
- Write failure: HTTP 500.

### 3.2.8 Acceptance Criteria

1. A profile update persists and is visible on reload.
2. A payload containing `role` leaves the stored role unchanged.

## 3.3 Parking Availability and Slot Discovery

### 3.3.1 Description

Exposes floors, vehicle categories and live slot states to the booking wizard and the admin views. Live state is derived rather than stored.

### 3.3.2 Actors

Anonymous visitor, CUSTOMER, ADMIN, SUPER_ADMIN.

### 3.3.3 Preconditions

Floors, vehicle types and slots exist.

### 3.3.4 Stimulus and Response Sequence

1. The booking page requests `GET /api/slots/floors` and `GET /api/slots/vehicle-types`.
2. The user selects a floor; the page requests `GET /api/slots/availability` with optional filters.
3. The system computes each slot's live status from floor status, control status, active bookings and entry/exit events, and returns it with the applicable rates.

### 3.3.5 Functional Requirements

- **FR-SLOT-001 (Must):** The system shall list open floors with total and currently available slot counts.
- **FR-SLOT-002 (Must):** The system shall list active vehicle types with hourly and overstay rates.
- **FR-SLOT-003 (Must):** The system shall return a live status of AVAILABLE, RESERVED, OCCUPIED, MAINTENANCE or INACTIVE for each slot.
- **FR-SLOT-004 (Must):** The system shall exclude inactive floors from public floor listings.
- **FR-SLOT-005 (Must):** The system shall treat a slot with an open ENTRY event and no EXIT as OCCUPIED.
- **FR-SLOT-006 (Must):** The system shall expose floor and vehicle-type filters without permitting write access.
- **FR-SLOT-007 (Should):** The system shall include a colour hint per live status for UI rendering.

### 3.3.6 Business Rules

- Stored `control_status` values are ACTIVE, ADMIN_RESERVED, MAINTENANCE and INACTIVE.
- A non-OPEN floor makes its slots unavailable regardless of slot state.
- HELD and CONFIRMED bookings make a slot RESERVED for their interval.
- Availability responses are advisory; the authoritative recheck happens inside the confirmation transaction.

### 3.3.7 Alternate and Exception Flows

- Unknown `floor_id` or `vehicle_type_id` filter: empty result set.
- Unknown slot id: HTTP 404.
- Database failure: HTTP 500.

### 3.3.8 Acceptance Criteria

1. A slot under maintenance never appears AVAILABLE.
2. A slot with an entry event and no exit appears OCCUPIED.
3. Filtering by floor returns only that floor's slots.

## 3.4 Booking Lifecycle

### 3.4.1 Description

Creates a short-lived hold, confirms it with wallet payment, and supports expiry, cancellation and completion. Overlap, duplicate-vehicle and account-state checks run inside a `BEGIN IMMEDIATE` transaction.

### 3.4.2 Actors

CUSTOMER, ADMIN, SUPER_ADMIN (the latter two may book for a registered customer).

### 3.4.3 Preconditions

An active session, an OPEN floor, an ACTIVE slot, a valid plate format and sufficient wallet balance at confirmation.

### 3.4.4 Stimulus and Response Sequence

1. The wizard collects vehicle type, plate format and number, floor, slot, date, start time and duration.
2. The client submits `POST /api/bookings/hold` with slot, vehicle data and start/end timestamps.
3. The system validates the plate, the 05:00–23:00 window, the duration cap, the floor and slot state, slot overlap and conflicting vehicle bookings, then inserts a HELD booking with `hold_expires_at = now + 30 minutes`.
4. The user reviews the summary and confirms through `POST /api/bookings/{ref}/confirm`.
5. The system expires stale holds, revalidates slot, floor and overlap, checks the wallet, then debits the customer, credits the Super Admin, writes both ledger rows and a collection record, and sets the booking to CONFIRMED in one transaction.

### 3.4.5 Functional Requirements

- **FR-BOOK-001 (Must):** The system shall create a HELD booking with a unique reference and a 30-minute hold expiry.
- **FR-BOOK-002 (Must):** The system shall reject a slot that is not ACTIVE or a floor that is not OPEN.
- **FR-BOOK-003 (Must):** The system shall reject overlapping HELD or CONFIRMED bookings for the same slot.
- **FR-BOOK-004 (Must):** The system shall reject a vehicle number that already has a HELD or CONFIRMED booking.
- **FR-BOOK-005 (Must):** The system shall validate the plate against the four accepted Indian formats.
- **FR-BOOK-006 (Must):** The system shall permit bookings only where the start hour is at least 05:00 and the end hour is at most 23:00.
- **FR-BOOK-007 (Must):** The system shall reject durations of zero, negative or more than 18 hours.
- **FR-BOOK-008 (Must):** The system shall compute the estimated amount as duration hours multiplied by the slot's hourly rate, rounded to two decimals.
- **FR-BOOK-009 (Must):** The system shall confirm only bookings in HELD state and revalidate allocation inside the transaction.
- **FR-BOOK-010 (Must):** The system shall reject confirmation when the wallet balance is below the estimated amount, using HTTP 402.
- **FR-BOOK-011 (Must):** The system shall allow ADMIN and SUPER_ADMIN to create a booking for another registered, ACTIVE customer by supplying `user_id`.
- **FR-BOOK-012 (Must):** The system shall allow a user to read their own bookings, and Admin or Super Admin to read any booking.
- **FR-BOOK-013 (Must):** The system shall return booking events with a booking detail response.
- **FR-BOOK-014 (Should):** The system shall expose whether a booking currently has an open entry for list views.

### 3.4.6 Business Rules

- Hold expiry is swept when a confirmation is attempted; there is no background scheduler.
- Rates and the estimated amount are copied onto the booking at hold time and are not recalculated later.
- The booking reference format is `QSP-YYYYMMDD-HHMMSS-XXXXXXXX`.
- Admins and Super Admins are exempt from the ONLINE/OFFLINE booking block.
- A HELD booking has no payment; cancellation of a HELD booking therefore refunds zero.
- The vehicle number is stored uppercase; the plate regex requires the conventional space separators.

### 3.4.7 Alternate and Exception Flows

- Invalid plate, formats, timestamps or missing fields: HTTP 400.
- Slot not found: HTTP 404.
- Slot unavailable, floor closed, overlap, duplicate vehicle: HTTP 409.
- Inactive account: HTTP 403.
- Insufficient funds at confirmation: HTTP 402, booking remains HELD.
- Hold expired or already confirmed: HTTP 409.
- System OFFLINE and the caller is a customer: HTTP 503.

### 3.4.8 Acceptance Criteria

1. Two concurrent holds for one slot produce one 201 and one 409.
2. Confirmation debits exactly once, even under duplicate submission.
3. A booking cannot be confirmed after its hold expiry.
4. A confirmed booking reappears as RESERVED in availability for its interval.

## 3.5 Wallet and Revenue Settlement

### 3.5.1 Description

Maintains each account's current balance and an append-only ledger. Booking charges move money from the customer to the Super Admin and create a linked collection record.

### 3.5.2 Actors

CUSTOMER (payer), ADMIN (customer wallet adjustments), SUPER_ADMIN (any wallet adjustment and revenue recipient).

### 3.5.3 Preconditions

The booking is confirmable and the payer's wallet covers the amount.

### 3.5.4 Stimulus and Response Sequence

1. Confirmation reads the customer balance and the Super Admin account inside the transaction.
2. The system reduces the customer balance, increases the Super Admin balance, writes a DEBIT and a CREDIT ledger row with unique references and `balance_after` values.
3. The system inserts a `revenue_collections` row linking both ledger legs to the booking.

### 3.5.5 Functional Requirements

- **FR-WALL-001 (Must):** The system shall update `users.wallet_balance` and write a matching `wallet_transactions` row in the same transaction.
- **FR-WALL-002 (Must):** The system shall prevent a negative wallet balance.
- **FR-WALL-003 (Must):** The system shall record every movement with a unique `transaction_reference`.
- **FR-WALL-004 (Must):** The system shall create one `revenue_collections` row per booking or overtime charge, linked to both ledger legs.
- **FR-WALL-005 (Must):** The system shall credit the Super Admin wallet by the same amount debited from the customer.
- **FR-WALL-006 (Must):** The system shall allow ADMIN to adjust CUSTOMER wallets only, and SUPER_ADMIN to adjust any account.
- **FR-WALL-007 (Must):** The system shall record the previous balance, the signed adjustment and the new balance for every manual adjustment.
- **FR-WALL-008 (Must):** The system shall return the wallet balance and ledger history for the current user and, for staff, for a target user.
- **FR-WALL-009 (Must):** The system shall roll back the entire money movement if any leg fails.
- **FR-WALL-010 (Should):** The system shall reject an adjustment that would make the balance negative.

### 3.5.6 Business Rules

- Ledger types are BOOKING_DEBIT, OVERTIME_DEBIT, CANCELLATION_REFUND, ADMIN_ADJUSTMENT, SUPER_ADMIN_REVENUE_CREDIT and REVENUE_REFUND_REVERSAL.
- `amount` is always positive; `direction` carries the sign.
- Adjustment amounts must be non-zero and may be negative to represent a debit.
- Revenue is recognised at confirmation, not at vehicle exit.
- Internal wallet balances are simulated; no external payment instrument is involved.

### 3.5.7 Alternate and Exception Flows

- Insufficient funds: HTTP 402 for booking; HTTP 400 for an adjustment producing a negative balance.
- Missing Super Admin account at confirmation: HTTP 500 and full rollback.
- Concurrent adjustments: `BEGIN IMMEDIATE` serialises writers, so no update is lost.

### 3.5.8 Acceptance Criteria

1. After a confirmation, the sum of customer debits equals the sum of Super Admin credits and collection amounts.
2. A forced failure after the customer debit leaves no ledger rows and no balance change.
3. A duplicate confirmation produces no second charge.

## 3.6 Cancellation and Refund

### 3.6.1 Description

Cancels a HELD or CONFIRMED booking before entry using active cancellation rules, credits the calculated refund and reverses the corresponding revenue from the Super Admin wallet.

### 3.6.2 Actors

CUSTOMER (owner), SUPER_ADMIN (any booking), staff acting through the Super Admin endpoint.

### 3.6.3 Preconditions

The booking belongs to the caller, is HELD or CONFIRMED and has no open entry event.

### 3.6.4 Stimulus and Response Sequence

1. The user opens My Bookings and selects cancel on an eligible booking.
2. The client submits `POST /api/bookings/{ref}/cancel`.
3. The system computes hours before start, selects the first matching active rule, and derives refund and penalty amounts from the paid amount.
4. The system credits the net amount to the customer, debits it from the Super Admin, writes a REFUND_REVERSAL collection row, sets the booking CANCELLED and appends an audit entry.

### 3.6.5 Functional Requirements

- **FR-CANC-001 (Must):** The system shall permit cancellation only by the booking owner through the customer endpoint.
- **FR-CANC-002 (Must):** The system shall permit cancellation only for HELD or CONFIRMED bookings.
- **FR-CANC-003 (Must):** The system shall refuse cancellation when an ENTRY event exists without a matching EXIT.
- **FR-CANC-004 (Must):** The system shall select the cancellation rule whose notice window contains the hours remaining before the booking start.
- **FR-CANC-005 (Must):** The system shall compute refund as paid amount times the rule's refund percentage and penalty as paid amount times the penalty percentage.
- **FR-CANC-006 (Must):** The system shall move the net amount between the customer and Super Admin wallets atomically and record a REFUND_REVERSAL collection.
- **FR-CANC-007 (Must):** The system shall store the applied rule id on the booking and append an audit record.
- **FR-CANC-008 (Must):** The system shall allow SUPER_ADMIN to cancel another user's eligible booking.

### 3.6.6 Business Rules

- Rules are ordered by descending `min_hours_before`; lower bounds are inclusive and upper bounds exclusive.
- No matching rule yields zero refund and zero penalty.
- HELD bookings have paid amount zero, so refund and penalty are zero.
- A negative net credit is written as a customer DEBIT and a Super Admin CREDIT.
- Financial history is never rewritten; the reversal is a new collection row.

### 3.6.7 Alternate and Exception Flows

- Unknown reference: HTTP 404.
- Not the owner: HTTP 403.
- Vehicle inside: HTTP 409.
- Completed, cancelled or expired booking: HTTP 409.

### 3.6.8 Acceptance Criteria

1. A cancellation inside a 100 percent refund window restores the full paid amount.
2. The Super Admin balance decreases by the same net amount.
3. A booking with an open entry cannot be cancelled.

## 3.7 QR Entry, Exit and Overtime

### 3.7.1 Description

Generates a QR image for a confirmed booking and processes gate scans as ENTRY or EXIT events. Exit settles overtime from the customer wallet before completing the booking.

### 3.7.2 Actors

CUSTOMER (present QR), ADMIN and SUPER_ADMIN (scan), booking owner (self-scan via API).

### 3.7.3 Preconditions

The booking is CONFIRMED; for exit, an ENTRY event must exist.

### 3.7.4 Stimulus and Response Sequence

1. The user opens the booking QR; the page calls `POST /api/qr/generate`.
2. At the gate, the operator opens `/admin/qr-scan`; the camera decodes a QR where `BarcodeDetector` exists, otherwise the operator types the reference.
3. The page submits `POST /api/qr/scan`.
4. With no ENTRY event, the system inserts ENTRY and returns the booking, vehicle, slot and timestamp.
5. With an ENTRY and no EXIT, the system computes overtime per started 30-minute unit, debits the wallet and credits the Super Admin when overtime is due, inserts EXIT, sets the slot ACTIVE and the booking COMPLETED.

### 3.7.5 Functional Requirements

- **FR-QR-001 (Must):** The system shall return a PNG QR image encoding the booking reference for a CONFIRMED booking.
- **FR-QR-002 (Must):** The system shall authorise QR generation for the booking owner, Admin or Super Admin.
- **FR-QR-003 (Must):** The system shall record the first scan as ENTRY and the second as EXIT, each at most once per booking.
- **FR-QR-004 (Must):** The system shall record the scan method as QR or MANUAL.
- **FR-QR-005 (Must):** The system shall reject ENTRY for a booking that is not CONFIRMED.
- **FR-QR-006 (Must):** The system shall compute overtime from the planned end time to the actual exit time, rounded up to the next 30-minute unit.
- **FR-QR-007 (Must):** The system shall settle overtime atomically with the Super Admin credit and an OVERTIME_CHARGE collection.
- **FR-QR-008 (Must):** The system shall block exit with HTTP 409 and no charge when the customer cannot cover the overtime.
- **FR-QR-009 (Must):** The system shall reject a third scan with HTTP 409.
- **FR-QR-010 (Must):** The system shall set the booking COMPLETED and release the slot after a successful exit.

### 3.7.6 Business Rules

- Overtime is charged only for time after `booked_until`; early exit is not refunded.
- Overtime rate is read from the vehicle type at scan time, not from the rate captured on the booking.
- The exit response reports overstay hours and amount even when they are zero.
- QR encoding contains only the booking reference; it is not a signed token.

### 3.7.7 Alternate and Exception Flows

- Unknown reference: HTTP 404.
- Unauthenticated scan: HTTP 401.
- A customer scanning someone else's booking: HTTP 403.
- Duplicate entry or exit: HTTP 409.
- Insufficient balance for overtime: HTTP 409 `EXIT_BLOCKED`, no wallet movement.
- Generation for a non-confirmed booking: HTTP 409.

### 3.7.8 Acceptance Criteria

1. First scan creates exactly one ENTRY row.
2. Exit after the planned end charges the expected number of 30-minute units.
3. A blocked exit leaves the wallet, ledger and events unchanged.
4. The slot becomes available after exit.

## 3.8 Admin Customer Management

### 3.8.1 Description

Registers walk-in customers, maintains their details, performs logical deletion and adjusts customer wallets.

### 3.8.2 Actors

ADMIN, SUPER_ADMIN.

### 3.8.3 Preconditions

An authenticated staff session.

### 3.8.4 Stimulus and Response Sequence

1. Staff open `/admin/customers` and search or register a customer.
2. The page calls `GET /api/admin/users` or `POST /api/admin/users`.
3. Updates use `PUT /api/admin/users/{id}`; deletion uses `DELETE`; wallet changes use `POST /api/admin/users/{id}/wallet-adjustments`.

### 3.8.5 Functional Requirements

- **FR-ACUST-001 (Must):** The system shall register a walk-in customer with full name, phone, optional gender, company, email and username.
- **FR-ACUST-002 (Must):** The system shall create walk-in customers with status PENDING and no password.
- **FR-ACUST-003 (Must):** The system shall reject duplicate phone, email or username values according to existing uniqueness rules.
- **FR-ACUST-004 (Must):** The system shall list and search customers without exposing password hashes.
- **FR-ACUST-005 (Must):** The system shall allow staff to update customer profile fields and status.
- **FR-ACUST-006 (Must):** The system shall perform logical deletion by setting status DELETED.
- **FR-ACUST-007 (Must):** The system shall prevent an ADMIN from modifying another ADMIN or the SUPER_ADMIN through these endpoints.
- **FR-ACUST-008 (Must):** The system shall record an audit entry for creation, update, deletion, wallet adjustment and slot-state change.
- **FR-ACUST-009 (Should):** The system shall charge a new customer the configured default wallet balance.

### 3.8.6 Business Rules

- PENDING accounts cannot log in; no activation flow exists (Appendix C, Q4).
- A customer's booking and financial history survive logical deletion.
- Admin wallet adjustments apply only to CUSTOMER accounts.

### 3.8.7 Alternate and Exception Flows

- Missing required fields: HTTP 400.
- Duplicate identity: HTTP 409.
- Target is an admin: HTTP 403.
- Unknown user: HTTP 404.

### 3.8.8 Acceptance Criteria

1. A walk-in customer appears in the list immediately after creation.
2. Deletion changes status only; the row remains.
3. An Admin cannot edit another Admin through the customer endpoint.

## 3.9 Admin Parking Operations

### 3.9.1 Description

Gives staff a live operational view of floors and slots, booking oversight, read-only rates and slot control actions.

### 3.9.2 Actors

ADMIN, SUPER_ADMIN.

### 3.9.3 Preconditions

An authenticated staff session.

### 3.9.4 Stimulus and Response Sequence

1. The dashboard requests `GET /api/admin/dashboard` for KPI totals and `GET /api/admin/floors` for live floor state.
2. The slot page requests `GET /api/admin/slots?floor_id=` and renders each slot with its occupant.
3. Staff may set an eligible slot to ACTIVE, ADMIN_RESERVED or MAINTENANCE through `PATCH /api/admin/slots/{id}/control-status`.

### 3.9.5 Functional Requirements

- **FR-AOPS-001 (Must):** The system shall return slot totals by live state and total revenue for the dashboard.
- **FR-AOPS-002 (Must):** The system shall list floors with total, available and occupied slot counts.
- **FR-AOPS-003 (Must):** The system shall return occupant details for reserved and occupied slots.
- **FR-AOPS-004 (Must):** The system shall allow staff to change slot control status among ACTIVE, ADMIN_RESERVED and MAINTENANCE.
- **FR-AOPS-005 (Must):** The system shall reject a control-status change for a slot with an active booking or occupant.
- **FR-AOPS-006 (Must):** The system shall list all bookings with date, status, floor, vehicle-type and customer filters.
- **FR-AOPS-007 (Must):** The system shall expose vehicle rates read-only to Admin.
- **FR-AOPS-008 (Should):** The system shall show a slot tooltip with customer, vehicle, reference, entry time and expected exit.

### 3.9.6 Business Rules

- Admin cannot close or deactivate a floor; that is a Super Admin action.
- Releasing an occupied slot is refused; exit through the gate is the only release path.
- Cancellation rules are editable by Admin in the current build; the rate table is read-only to Admin.

### 3.9.7 Alternate and Exception Flows

- Occupied or booked slot: HTTP 409.
- Unknown slot: HTTP 404.
- Invalid status value: HTTP 400.

### 3.9.8 Acceptance Criteria

1. KPI totals equal the sum of the per-floor counts.
2. A Maintenance slot immediately stops appearing as AVAILABLE.
3. An occupied slot cannot be set to Maintenance.

## 3.10 Super Admin Administration and Infrastructure

### 3.10.1 Description

Manages administrator accounts, any wallet, floors and slots, and booking cancellations across users.

### 3.10.2 Actors

SUPER_ADMIN.

### 3.10.3 Preconditions

An authenticated Super Admin session.

### 3.10.4 Stimulus and Response Sequence

1. The Super Admin opens `/super-admin/admins` and creates or edits an administrator.
2. The system generates a unique `admin_id`, hashes the supplied password and sets the role.
3. The Super Admin opens `/super-admin/infrastructure` to add a floor, change floor status, add a slot, change slot state or remove a slot.
4. Destructive changes are refused when an active booking or occupant would be orphaned.

### 3.10.5 Functional Requirements

- **FR-SADM-001 (Must):** The system shall create ADMIN accounts with a unique admin identifier and hashed password.
- **FR-SADM-002 (Must):** The system shall list, read, update and logically delete administrator accounts.
- **FR-SADM-003 (Must):** The system shall allow blocking and unblocking an administrator.
- **FR-SADM-004 (Must):** The system shall allow the Super Admin to adjust the wallet of any account.
- **FR-SADM-005 (Must):** The system shall allow creation of a floor with a unique code.
- **FR-SADM-006 (Must):** The system shall allow a floor status change to OPEN, CLOSED, MAINTENANCE or INACTIVE.
- **FR-SADM-007 (Must):** The system shall refuse floor deactivation when active bookings or occupants exist.
- **FR-SADM-008 (Must):** The system shall allow adding a slot with a unique number per floor and a vehicle type.
- **FR-SADM-009 (Must):** The system shall allow updating a slot number or control status, refusing changes that orphan active bookings.
- **FR-SADM-010 (Must):** The system shall deactivate rather than physically delete slots and floors with history.
- **FR-SADM-011 (Must):** The system shall allow the Super Admin to cancel any eligible booking.
- **FR-SADM-012 (Should):** The system shall record every administrative change in the audit log.

### 3.10.6 Business Rules

- Admin identifiers satisfy the schema constraint that ADMIN and SUPER_ADMIN accounts have a non-null `admin_id`.
- A Super Admin cannot be deleted through the admin-management endpoints.
- Slot numbers are unique per floor, not globally.

### 3.10.7 Alternate and Exception Flows

- Duplicate floor code or slot number: HTTP 409.
- Active bookings present: HTTP 409.
- Unknown floor, slot or admin: HTTP 404.
- Invalid status: HTTP 400.

### 3.10.8 Acceptance Criteria

1. A blocked admin cannot log in and an unblocked admin can.
2. A floor with an active booking cannot be deactivated.
3. Removing a free slot succeeds; removing an occupied slot fails.

## 3.11 Analytics and Reporting

### 3.11.1 Description

Provides occupancy and revenue views for Admin, deeper analytics for Super Admin, and CSV exports.

### 3.11.2 Actors

ADMIN, SUPER_ADMIN.

### 3.11.3 Preconditions

Persisted bookings, collections and slots.

### 3.11.4 Stimulus and Response Sequence

1. The analytics page requests occupancy, revenue, heat-map and chart data.
2. The system aggregates live slot state for occupancy and `revenue_collections` for revenue.
3. CSV endpoints stream a file attachment with the same filters.

### 3.11.5 Functional Requirements

- **FR-REP-001 (Must):** The system shall report per-floor total and occupied slots with an occupancy percentage rounded to two decimals.
- **FR-REP-002 (Must):** The system shall report per-floor total revenue, net revenue and distinct booking count.
- **FR-REP-003 (Must):** The system shall filter reports by an optional inclusive date range.
- **FR-REP-004 (Must):** The system shall derive revenue from `revenue_collections`, not from booking status.
- **FR-REP-005 (Must):** The system shall subtract REFUND_REVERSAL collections from net revenue.
- **FR-REP-006 (Must):** The system shall provide occupancy and revenue CSV downloads.
- **FR-REP-007 (Must):** The system shall provide Super Admin revenue summary by collection type.
- **FR-REP-008 (Must):** The system shall provide Super Admin overtime analytics and revenue grouped by floor, vehicle type and day.
- **FR-REP-009 (Should):** The system shall provide per-floor heat maps and donut/line chart data.
- **FR-REP-010 (Should):** The system shall restrict CSV downloads to SUPER_ADMIN.

### 3.11.6 Business Rules

- Occupancy counts RESERVED and OCCUPIED as occupied and uses all slot rows as the denominator.
- The occupancy date filter keeps floors that have at least one booking starting in range; it does not change the live counts.
- Revenue date filters compare `DATE(revenue_collections.created_at)`.
- `grand_total` sums per-floor gross revenue.

### 3.11.7 Alternate and Exception Flows

- No data: zero-valued rows, not an error.
- Invalid date strings: empty result set.
- Non-Super Admin requesting a CSV: HTTP 403.

### 3.11.8 Acceptance Criteria

1. Revenue rows reconcile with `revenue_collections` for the same range.
2. A REFUND_REVERSAL reduces net revenue and leaves gross revenue unchanged.
3. CSV content matches the JSON equivalent.

## 3.12 System Control, Audit and Data Inspection

### 3.12.1 Description

Controls the global ONLINE/OFFLINE state, the idle-session policy and read-only access to whitelisted tables.

### 3.12.2 Actors

SUPER_ADMIN; all roles observe the system state.

### 3.12.3 Preconditions

A Super Admin session for writes.

### 3.12.4 Stimulus and Response Sequence

1. The system page reads `GET /api/system/status` and the session policy.
2. The Super Admin switches the system OFFLINE or ONLINE through `PATCH /api/system/super-admin/system/status` after a confirmation dialog.
3. The system stores the value in `system_settings` and appends an audit entry.

### 3.12.5 Functional Requirements

- **FR-SYS-001 (Must):** The system shall store the global state in `system_settings` under `SYSTEM_STATUS`.
- **FR-SYS-002 (Must):** The system shall return the current state publicly.
- **FR-SYS-003 (Must):** The system shall block customer holds and confirmations while OFFLINE and return HTTP 503.
- **FR-SYS-004 (Must):** The system shall keep Super Admin access to restore ONLINE.
- **FR-SYS-005 (Must):** The system shall allow the Super Admin to set the idle timeout to 5, 10, 15 or 20 minutes.
- **FR-SYS-006 (Must):** The system shall append an audit row for each system-state and timeout change.
- **FR-SYS-007 (Must):** The system shall expose read-only, paginated table views for an explicit whitelist only.
- **FR-SYS-008 (Must):** The system shall exclude `password_hash` from the user table view.
- **FR-SYS-009 (Must):** The system shall refuse any table not on the whitelist with HTTP 403.
- **FR-SYS-010 (Must):** The system shall return HTTP 404 for unknown tables.

### 3.12.6 Business Rules

- The whitelist is the eleven application tables.
- Pagination defaults to 25 rows per page and is bounded.
- OFFLINE does not block QR entry/exit, wallet adjustment or Super Admin operations, so occupants are never stranded.
- The absolute session limit remains 20 minutes regardless of the idle setting.

### 3.12.7 Alternate and Exception Flows

- Invalid state value: HTTP 400.
- Invalid timeout value: HTTP 400.
- Non-whitelisted table: HTTP 403.

### 3.12.8 Acceptance Criteria

1. Setting OFFLINE causes a customer hold to return 503 while a Super Admin hold still succeeds.
2. The users view never contains a hash.
3. Every state change appears in `audit_logs`.

# 4. External Interface Requirements

## 4.1 User Interface Requirements

The interface is a responsive server-rendered web application. Every page extends `base.html`, which owns the sidebar, top bar, mobile navigation, toast region and confirmation dialog. Page-specific data is loaded by inline scripts through the `QS` HTTP helper, and all interpolated values pass through `QSUI.esc`.

[[DIAGRAM:DIA-012|UI navigation map across customer, admin and super-admin pages]]

Verified pages: `/login`, `/dashboard`, `/booking`, `/bookings/my`, `/wallet`, `/profile`, `/confirm/{ref}`, `/admin/dashboard`, `/admin/bookings`, `/admin/customers`, `/admin/slots`, `/admin/analytics`, `/admin/master`, `/admin/qr-scan`, `/super-admin/dashboard`, `/super-admin/admins`, `/super-admin/infrastructure`, `/super-admin/analytics`, `/super-admin/data`, `/super-admin/system`, and `error.html` for 400/403/404/413/500.

The booking wizard is a five-step flow: vehicle type, plate format and number, floor and slot grid, schedule and duration, review and confirm. Data tables use server-side filtering with pagination, skeleton loading states, empty states and inline error messages. Slot states use a consistent colour system. Destructive actions use a confirmation dialog and surface a toast on completion.

Accessibility expectations: semantic landmarks, visible focus, form labels, keyboard-operable dialogs, `tabindex="0"` on scrollable table regions, and a contrast-compliant muted colour. Current evidence is an axe-core run recorded in `docs/test_results.md`; the test artifacts are not present in the repository, so this remains Unverified.

## 4.2 Hardware Interface Requirements

No dedicated hardware interface is implemented. The only optional physical interaction is the client device camera through `navigator.mediaDevices.getUserMedia` for QR scanning. No barcode scanner, printer, gate controller, sensor or embedded device integration exists. Printed QR display depends on the browser print function, which the application does not control.

## 4.3 Software Interface Requirements

| Interface | Direction | Protocol/Format | Purpose |
|---|---|---|---|
| SQLite database file | Internal | File system + SQL | All persistent business data |
| Browser runtime | Inbound | HTTP/HTTPS | Pages and JSON APIs |
| `qrcode` and Pillow | Internal | Python library | QR PNG generation |
| `BarcodeDetector` | Browser API | JavaScript API | Optional QR decoding |
| Flask-WTF CSRF | Internal | Python library + header/meta tag | Request forgery protection |
| Waitress | Internal | WSGI | Production HTTP serving |
| Reverse proxy | External | HTTP | TLS termination and forwarding |
| CSV consumer | Outbound | `text/csv` | Report downloads |

There is no payment gateway, SMS gateway, email provider, message broker or third-party authentication service.

## 4.4 Communication Interface Requirements

- HTTP/1.1 over TLS in production; the application itself listens on plain HTTP behind the proxy.
- JSON request and response bodies with `application/json`; HTML form posts for login and logout.
- Session cookie authentication, plus `X-CSRFToken` on state-changing requests.
- Error bodies use `{"error": "...", "code": <status>}`.
- CSV responses use `Content-Disposition: attachment` with `text/csv`.
- Recommended response headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Permissions-Policy: camera=(self), geolocation=(), microphone=()`.
- Request bodies are capped at 1 MiB by default (HTTP 413 above the limit).
- No WebSocket, server-sent events or long polling is used.

# 5. Non-Functional Requirements

## 5.1 Performance Requirements

- **NFR-PERF-001 (Should):** The system shall return cached-free JSON responses for dashboard and listing endpoints within 2 seconds at the seeded data volume (64 slots per floor, four floors), measured on the deployment host. Target TBD; no benchmark artifact exists.
- **NFR-PERF-002 (Should):** The system shall render an authenticated page shell without waiting for data queries, because data loads asynchronously.
- **NFR-PERF-003 (Should):** The system shall keep client payloads paginated, with 25 rows per page in the data browser.
- **NFR-PERF-004 (May):** The system shall support concurrent gate scans without duplicate postings, relying on write serialisation. Throughput target TBD.

No load, soak or capacity test has been executed; no figures are asserted beyond these design intents.

## 5.2 Security Requirements

- **NFR-SEC-001 (Must):** The system shall enforce authentication and role authorisation on the server for every protected route and API.
- **NFR-SEC-002 (Must):** The system shall validate a CSRF token on every state-changing request.
- **NFR-SEC-003 (Must):** The system shall hash passwords with a salted adaptive algorithm (PBKDF2-SHA256) and never expose hashes.
- **NFR-SEC-004 (Must):** The system shall parameterise all SQL statements.
- **NFR-SEC-005 (Must):** The system shall set HttpOnly and SameSite=Lax on the session cookie and Secure when HTTPS is configured.
- **NFR-SEC-006 (Must):** The system shall refuse production startup when `SECRET_KEY` is absent.
- **NFR-SEC-007 (Must):** The system shall apply the documented security response headers.
- **NFR-SEC-008 (Must):** The system shall cap request bodies and return HTTP 413 above the limit.
- **NFR-SEC-009 (Must):** The system shall exclude password hashes and secret configuration from logs and API payloads.
- **NFR-SEC-010 (Must):** The system shall record security-relevant actions in `audit_logs`.
- **NFR-SEC-011 (Must):** The system shall restrict database inspection to a whitelist and paginate results.
- **NFR-SEC-012 (Should):** The system shall enforce HTTPS in production through a reverse proxy with `SESSION_COOKIE_SECURE=1`.

Verified gaps: QR content is an unsigned reference; manual reference entry is not cryptographic proof; the seeded prototype password rule in `src/core/security.py` is predictable and should not be treated as a production credential policy; one seed script contains a hard-coded development password and must not be used in production.

## 5.3 Reliability and Availability

- **NFR-REL-001 (Must):** The system shall keep every money movement atomic and roll back the whole unit on failure.
- **NFR-REL-002 (Must):** The system shall enable SQLite foreign-key enforcement on every connection.
- **NFR-REL-003 (Must):** The system shall never physically delete users, bookings, ledger rows, events or collections that carry history.
- **NFR-REL-004 (Must):** The system shall allow a consistent hot backup of the SQLite file.
- **NFR-REL-005 (Should):** The system shall recover from a restart without manual data repair because all state is persisted.
- **NFR-REL-006 (Should):** The system shall expose `GET /health` returning `{"status":"ok","service":"QSPARK"}`.
- **NFR-REL-007 (May):** Availability target TBD; no measured uptime or SLA exists.
- **NFR-REL-008 (Should):** Backups shall be verified with `PRAGMA integrity_check` before being trusted.

Single-process deployment is a known single point of failure. No failover or replication exists.

## 5.4 Usability Requirements

- **NFR-USE-001 (Must):** The system shall present one consistent design system across all roles.
- **NFR-USE-002 (Must):** The system shall show explicit loading, empty, validation-error and network-error states for every data view.
- **NFR-USE-003 (Must):** The system shall confirm destructive actions before executing them.
- **NFR-USE-004 (Must):** The system shall label every form control and preserve keyboard operability.
- **NFR-USE-005 (Should):** The system shall support viewports from 320 px upward without horizontal overflow on primary pages.
- **NFR-USE-006 (Should):** The system shall meet WCAG 2.2 AA contrast and structure expectations; current evidence is a documented axe-core run with zero violations, Unverified in this repository.
- **NFR-USE-007 (Should):** The system shall display amounts in INR with two decimals.

## 5.5 Maintainability Requirements

- **NFR-MAINT-001 (Must):** The system shall keep business logic in API/domain modules and SQL in the data layer, not in templates.
- **NFR-MAINT-002 (Must):** The system shall keep one authoritative schema file and regenerate the data dictionary from it.
- **NFR-MAINT-003 (Should):** The system shall use the shared `QS` and `QSUI` helpers rather than ad-hoc `fetch` and DOM code.
- **NFR-MAINT-004 (Should):** The system shall write structured application logs to stdout and avoid logging secrets or request bodies.
- **NFR-MAINT-005 (Should):** The system shall keep the Tailwind stylesheet reproducible from source with a documented command.
- **NFR-MAINT-006 (May):** Automated test coverage target TBD; the referenced suite is absent from the repository.

## 5.6 Scalability Requirements

- **NFR-SCALE-001 (Should):** The data model shall support additional floors, slots, vehicles and bookings without schema change.
- **NFR-SCALE-002 (Should):** List endpoints shall paginate or bound result sets.
- **NFR-SCALE-003 (May):** Horizontal scaling is not supported while SQLite and in-process sessions are used; a future database migration is Required before multi-instance deployment.
- **NFR-SCALE-004 (May):** Growth targets for users, bookings per day and concurrent operators are TBD.

## 5.7 Compatibility Requirements

- **NFR-COMP-001 (Must):** The system shall run on Windows 10/11 and Linux with Python 3.11 or newer.
- **NFR-COMP-002 (Should):** The system shall support current Chromium, Firefox and WebKit browsers; Playwright runs are recorded historically but the artifacts are absent.
- **NFR-COMP-003 (Should):** The system shall serve a layout usable at 320 px and 1440 px widths.
- **NFR-COMP-004 (Must):** The system shall not require Node, npm or a browser build step.
- **NFR-COMP-005 (Should):** Automatic QR decoding shall be available only where `BarcodeDetector` exists; manual entry shall remain available everywhere.
- **NFR-COMP-006 (May):** Safari, iOS and Android have not been tested; WebKit is not Safari.

## 5.8 Data Integrity Requirements

- **NFR-DATA-001 (Must):** The system shall enforce primary, foreign, unique and check constraints in the database.
- **NFR-DATA-002 (Must):** The system shall prevent overlapping active bookings for a slot with a trigger and a service check.
- **NFR-DATA-003 (Must):** The system shall prevent more than one active booking per vehicle number with a partial unique index.
- **NFR-DATA-004 (Must):** The system shall enforce the booking status transition rules with a trigger.
- **NFR-DATA-005 (Must):** The system shall allow at most one ENTRY and one EXIT event per booking.
- **NFR-DATA-006 (Must):** The system shall reject EXIT before ENTRY at database level.
- **NFR-DATA-007 (Must):** The system shall reject physical deletion of a user with active bookings.
- **NFR-DATA-008 (Must):** The system shall keep `transaction_reference` unique across all ledger rows.
- **NFR-DATA-009 (Must):** The system shall enforce `booked_until > booked_from`.
- **NFR-DATA-010 (Must):** The system shall enforce that ACTIVE accounts have a password hash and that admin roles have an `admin_id`.

# 6. System Workflows and Business Logic

## 6.1 Customer Booking and Gate Workflow

1. The customer signs in and opens the booking wizard.
2. The wizard loads floors, vehicle types and live slot states.
3. The customer selects vehicle type, plate format and number, floor and slot.
4. The customer selects a date, a start time between 05:00 and 23:00 and a duration of at most 18 hours.
5. The system creates a HELD booking and returns the reference and amount. Decision: if the slot or vehicle conflicts, the request fails with 409 and the customer reselects.
6. The customer confirms. Decision: if the wallet is insufficient, the booking stays HELD and the customer tops up or abandons it.
7. On success the system debits the wallet, credits the Super Admin, records the collection and returns the QR.
8. At entry the operator scans the reference; the system records ENTRY.
9. At exit the operator scans again. Decision: if overtime is due and unaffordable, exit is blocked until the wallet is funded.
10. On successful exit the booking becomes COMPLETED and the slot returns to general availability.

[[FIGURE:User Process Flow Diagrm.png|Customer process flow supplied with the project; the verified flow is shown in the next figure]]

[[DIAGRAM:DIA-004|Customer booking to gate exit activity flow]]

## 6.2 Administrative Cancellation and Wallet Adjustment Workflow

1. The operator identifies a booking or customer.
2. For cancellation, the operator confirms the booking has no open entry.
3. The system applies the matching rule, moves the net amount between wallets, writes a reversal collection and audits the action.
4. For a wallet adjustment, the operator enters a non-zero signed amount and a reason.
5. The system validates the target role, prevents a negative result, updates the balance, writes an ADMIN_ADJUSTMENT ledger row and audits the change.

[[DIAGRAM:DIA-005|Administrative operations activity flow]]

## 6.3 Super Admin Infrastructure Change Workflow

1. The Super Admin opens the infrastructure page.
2. To add capacity, the Super Admin creates a floor or adds a slot with a vehicle type.
3. To reduce capacity, the Super Admin closes a floor or deactivates a slot.
4. The system checks for active bookings and occupants.
5. Decision: if any exist, the change is refused with 409 and the operator must wait for exit or reassignment.
6. On success the change is persisted and audited.

[[DIAGRAM:DIA-006|Super admin infrastructure and system-control activity flow]]

# 7. Data Requirements and Database Design

## 7.1 Data Model Overview

The database is a normalised SQLite file generated from `schema.sql`. It contains eleven application tables. Every table ends with the mandatory columns `created_by`, `created_at`, `updated_by`, `updated_at`, `reserved1` and `reserved2`. Actor columns reference `users(user_id)` with `ON DELETE SET NULL`; business references use `RESTRICT` where history must survive.

Identity is unified: one `users` row represents a customer, an admin or the super admin. Parking capacity is modelled as floors containing slots, each slot bound to a vehicle type that carries the rates. Bookings connect a user to a slot for a time interval. Money is modelled twice: `wallet_transactions` is the immutable ledger, `users.wallet_balance` is the fast current value, and `revenue_collections` pairs the two ledger legs of a charge. Gate activity is modelled as `booking_events`. Administrative actions are captured in `audit_logs`, and global switches in `system_settings`.

[[FIGURE:Entity Relationship Diagram.png|Entity-relationship diagram provided with the project]]

## 7.2 Database Table Inventory

[[TABLE:Database table inventory and principal relationships]]

[[TABLE_INVENTORY]]

## 7.3 Entity-Relationship Diagram

The ERD below must show aggregate cardinality: one floor to many slots, one vehicle type to many slots, one user to many bookings, one slot to many bookings over time, one booking to zero or many events (at most one of each type), one booking to one or more collections, and one user to many ledger rows. The machine-readable specification is diagram `DIA-009`.

[[DIAGRAM:DIA-009|Complete entity-relationship diagram with keys and cardinality]]

## 7.4 Data Dictionary

The dictionary is generated directly from `schema.sql`, so column names, types, nullability, defaults and constraints reflect the authoritative schema.

[[SCHEMA_DICTIONARY]]

## 7.5 Data Validation and Integrity

Database-level controls:

- CHECK constraints restrict role, account status, gender, floor status, slot control status, booking status, vehicle format, ledger type and direction, event type, scan method, collection type and percentage ranges.
- Partial unique indexes enforce one active booking per vehicle number and one ENTRY and one EXIT per booking.
- A BEFORE INSERT trigger rejects overlapping HELD or CONFIRMED bookings for a slot.
- A BEFORE UPDATE trigger rejects illegal booking status transitions.
- A BEFORE INSERT trigger rejects EXIT before ENTRY.
- A BEFORE DELETE trigger rejects physical deletion of a user with active bookings.
- Foreign keys use RESTRICT where history must be preserved and SET NULL for actor references.

Application-level controls: plate format and normalisation, booking window and duration, slot and floor eligibility, wallet sufficiency, role authorisation, ownership checks, state checks before every transition, and a full revalidation of allocation inside the confirmation transaction.

## 7.6 Data Lifecycle and Retention

- Accounts are logically deleted by setting `account_status = DELETED`; rows remain for history.
- Floors and slots are closed or deactivated, not deleted when referenced.
- Bookings progress to COMPLETED, CANCELLED or EXPIRED and are retained.
- Wallet transactions are append-only; corrections use reversal entries.
- Booking events are never updated; a booking has at most one ENTRY and one EXIT.
- Audit logs are append-only.
- Revenue collections are retained; refunds add REFUND_REVERSAL rows.
- No automated archival or pruning is implemented. Retention duration is TBD and must be set by policy.

# 8. System State and Transaction Management

## 8.1 Booking States

| State | Meaning | Permitted transitions |
|---|---|---|
| HELD | Slot reserved temporarily, unpaid | CONFIRMED, CANCELLED, EXPIRED |
| CONFIRMED | Paid reservation with QR | COMPLETED, CANCELLED |
| COMPLETED | Vehicle exited | None |
| CANCELLED | Reservation cancelled | None |
| EXPIRED | Hold lapsed before payment | None |

A CANCELLED or COMPLETED booking cannot be reopened. Any other transition is rejected by `trg_booking_status_transitions`.

[[DIAGRAM:DIA-010|Booking state machine and permitted transitions]]

## 8.2 Slot and Event States

Stored control states are ACTIVE, ADMIN_RESERVED, MAINTENANCE and INACTIVE. Live display states are derived: INACTIVE when the floor or slot is inactive; MAINTENANCE when the slot is under maintenance; OCCUPIED when an ENTRY exists without an EXIT; RESERVED when a HELD or CONFIRMED booking covers the current interval; otherwise AVAILABLE.

Events are append-only. ENTRY requires a CONFIRMED booking. EXIT requires an existing ENTRY. Exit completes the booking and sets the slot control status to ACTIVE.

## 8.3 Transaction Boundaries

All money-moving operations run inside `BEGIN IMMEDIATE`. The unit includes the balance update, both ledger legs, the collection row, the booking state change and, where applicable, the audit row. Any exception rolls back the whole unit.

| Operation | Unit of work | Isolation |
|---|---|---|
| Hold | Slot/vehicle checks plus booking insert | BEGIN IMMEDIATE |
| Confirm | Revalidation, debit, credit, ledger, collection, status | BEGIN IMMEDIATE |
| Cancel | Rule selection, refund legs, reversal collection, status, audit | BEGIN IMMEDIATE |
| Exit | Overtime settlement, EXIT event, slot release, completion | BEGIN IMMEDIATE |
| Wallet adjustment | Balance update, ledger row, audit | BEGIN IMMEDIATE |
| System change | Setting update plus audit | BEGIN IMMEDIATE |

## 8.4 Audit History

`audit_logs` records action type, entity type, entity id, old and new values, actor and timestamp. Verified writes cover booking cancellation, customer creation, update and deletion, wallet adjustment, slot status change, cancellation-rule maintenance, administrator changes, session-timeout change and system online/offline. Audit rows are never updated or deleted by the application.

# 9. API and Integration Specification

## 9.1 API Conventions

All API endpoints return JSON except the CSV reports. Authentication is a session cookie. Role checks are server-side. Errors use `{"error": "<message>", "code": <http_status>}`. State-changing requests require `X-CSRFToken` or a `csrf_token` form field.

Status codes used: 200, 201, 400 (validation or CSRF), 401, 402 (insufficient funds), 403, 404, 409 (conflict or state violation), 413, 500 and 503 (system offline).

## 9.2 API Inventory

[[TABLE:API inventory grouped by blueprint]]

| API ID | Method | Endpoint | Purpose | Auth | Roles |
|---|---|---|---|---|---|
| API-001 | POST | /api/auth/login | Authenticate and create session | No | Public |
| API-002 | GET | /api/auth/me | Current user | Yes | Any |
| API-003 | PATCH | /api/auth/me | Update own profile | Yes | Any |
| API-004 | POST | /api/auth/session/end | End session | Yes | Any |
| API-005 | POST | /api/auth/logout | Logout | Yes | Any |
| API-006 | POST | /api/auth/setup-admin | One-time bootstrap | No | Public, env-guarded |
| API-101 | GET | /api/slots/floors | List open floors | No | Public |
| API-102 | GET | /api/slots/vehicle-types | List active vehicle types | No | Public |
| API-103 | GET | /api/slots/availability | Live slot availability | No | Public |
| API-104 | GET | /api/slots/{slot_id} | Single slot state | No | Public |
| API-201 | POST | /api/bookings/hold | Create HELD booking | Yes | Any authenticated |
| API-202 | POST | /api/bookings/{ref}/confirm | Pay and confirm | Yes | Owner or Admin+ |
| API-203 | GET | /api/bookings/{ref} | Booking detail and events | Yes | Owner or Admin+ |
| API-204 | GET | /api/bookings/my | Own bookings | Yes | Any authenticated |
| API-205 | POST | /api/bookings/{ref}/cancel | Cancel own booking | Yes | Owner |
| API-206 | GET | /api/bookings/wallet/transactions/me | Own wallet ledger | Yes | Any authenticated |
| API-301 | POST | /api/qr/generate | QR PNG for confirmed booking | Yes | Owner or Admin+ |
| API-302 | POST | /api/qr/scan | Record entry or exit | Yes | Admin+ or owner |
| API-401 | GET | /api/admin/dashboard | Operational KPIs | Yes | Admin+ |
| API-402 | GET | /api/admin/bookings | Filtered booking list | Yes | Admin+ |
| API-403 | GET | /api/admin/users | Customer list | Yes | Admin+ |
| API-404 | POST | /api/admin/users | Register walk-in customer | Yes | Admin+ |
| API-405 | GET | /api/admin/users/{id} | Customer detail | Yes | Admin+ |
| API-406 | PUT | /api/admin/users/{id} | Update customer | Yes | Admin+ |
| API-407 | DELETE | /api/admin/users/{id} | Logical delete | Yes | Admin+ |
| API-408 | POST | /api/admin/users/{id}/wallet-adjustments | Adjust wallet | Yes | Admin+ |
| API-409 | GET | /api/admin/users/{id}/wallet | Wallet and ledger | Yes | Admin+ |
| API-410 | PATCH | /api/admin/slots/{id}/control-status | Change slot state | Yes | Admin+ |
| API-411 | GET | /api/admin/cancellation-rules | List rules | Yes | Admin+ |
| API-412 | POST | /api/admin/cancellation-rules | Create rule | Yes | Admin+ |
| API-413 | PUT | /api/admin/cancellation-rules/{id} | Update rule | Yes | Admin+ |
| API-414 | DELETE | /api/admin/cancellation-rules/{id} | Deactivate rule | Yes | Admin+ |
| API-415 | GET | /api/admin/floors | Live floor state | Yes | Admin+ |
| API-416 | GET | /api/admin/vehicle-types | Rates | Yes | Admin+ |
| API-417 | GET | /api/admin/slots | Slots and occupants | Yes | Admin+ |
| API-418 | GET | /api/admin/master/floors | Compatibility alias | Yes | Admin+ |
| API-419 | GET | /api/admin/master/vehicle-types | Compatibility alias | Yes | Admin+ |
| API-420 | GET | /api/admin/master/slots | Compatibility alias | Yes | Admin+ |
| API-421 | GET | /api/admin/master/users | Compatibility alias | Yes | Admin+ |
| API-422 | GET | /api/admin/master/cancellation-rules | Compatibility alias | Yes | Admin+ |
| API-423 | PUT | /api/admin/master/floors/{id} | Compatibility alias | Yes | Admin+ |
| API-424 | PUT | /api/admin/master/slots/{id}/status | Compatibility alias | Yes | Admin+ |
| API-425 | POST | /api/admin/qr/scan | Compatibility alias for scan | Yes | Admin+ |
| API-501 | GET | /api/admin/reports/occupancy | Occupancy per floor | Yes | Admin+ |
| API-502 | GET | /api/admin/reports/revenue | Revenue per floor | Yes | Admin+ |
| API-503 | GET | /api/admin/reports/revenue-summary | Revenue by type | Yes | Super Admin |
| API-504 | GET | /api/admin/reports/occupancy-csv | Occupancy CSV | Yes | Super Admin |
| API-505 | GET | /api/admin/reports/revenue-csv | Revenue CSV | Yes | Super Admin |
| API-601 | POST | /api/super-admin/admins | Create admin | Yes | Super Admin |
| API-602 | GET | /api/super-admin/admins | List admins | Yes | Super Admin |
| API-603 | GET | /api/super-admin/admins/{id} | Admin detail | Yes | Super Admin |
| API-604 | PUT | /api/super-admin/admins/{id} | Update admin | Yes | Super Admin |
| API-605 | DELETE | /api/super-admin/admins/{id} | Soft-delete admin | Yes | Super Admin |
| API-606 | PATCH | /api/super-admin/admins/{id}/status | Block or unblock | Yes | Super Admin |
| API-607 | POST | /api/super-admin/users/{id}/wallet-adjustments | Adjust any wallet | Yes | Super Admin |
| API-608 | GET | /api/super-admin/users/{id}/wallet | Any wallet and ledger | Yes | Super Admin |
| API-609 | POST | /api/super-admin/floors | Create floor | Yes | Super Admin |
| API-610 | PUT | /api/super-admin/floors/{id} | Change floor status | Yes | Super Admin |
| API-611 | DELETE | /api/super-admin/floors/{id} | Deactivate floor | Yes | Super Admin |
| API-612 | POST | /api/super-admin/floors/{id}/slots | Add slot | Yes | Super Admin |
| API-613 | PUT | /api/super-admin/slots/{id} | Update slot | Yes | Super Admin |
| API-614 | DELETE | /api/super-admin/slots/{id} | Deactivate slot | Yes | Super Admin |
| API-615 | POST | /api/super-admin/bookings/{ref}/cancel | Cancel any eligible booking | Yes | Super Admin |
| API-616 | GET | /api/super-admin/db-tables/{table} | Read-only table view | Yes | Super Admin |
| API-617 | GET | /api/super-admin/analytics/overview | KPI overview | Yes | Super Admin |
| API-618 | GET | /api/super-admin/analytics/overtime | Overtime analytics | Yes | Super Admin |
| API-619 | GET | /api/super-admin/analytics/floor-heatmap | Floor heat map | Yes | Super Admin |
| API-620 | GET | /api/super-admin/analytics/revenue | Revenue analytics | Yes | Super Admin |
| API-621 | GET | /api/super-admin/reports/occupancy.csv | Compatibility CSV | Yes | Super Admin |
| API-622 | GET | /api/super-admin/reports/revenue.csv | Compatibility CSV | Yes | Super Admin |
| API-701 | GET | /api/system/status | Public system state | No | Public |
| API-702 | GET | /api/system/super-admin/session | Session policy | Yes | Super Admin |
| API-703 | PATCH | /api/system/super-admin/session | Set idle timeout | Yes | Super Admin |
| API-704 | PATCH | /api/system/super-admin/system/status | Set ONLINE/OFFLINE | Yes | Super Admin |

## 9.3 Representative Contracts

**Login.** Request `{"username": "<username or email>", "password": "<password>"}`. Response 200: `{"user": {user_id, username, email, full_name, role, wallet_balance, phone}}`. Errors: 400 missing fields, 401 invalid credentials.

**Hold.** Request `{"slot_id": 12, "vehicle_number": "KA 04 A 2256", "vehicle_format": "std1", "booked_from": "2026-11-20 10:00", "booked_until": "2026-11-20 12:00"}` plus optional `user_id` for staff. Response 201 includes the reference, slot number, vehicle type, duration, hourly rate, estimated amount, HELD status and hold expiry. Errors: 400, 401, 403, 404, 409, 503.

**Confirm.** Request has no body fields. Response 200: `{booking_reference, booking_status: "CONFIRMED", amount_debited, new_wallet_balance, qr_generated: true}`. Errors: 402 insufficient funds, 409 not HELD or expired, 503 offline.

**Scan.** Request `{"booking_reference": "QSP-...", "scan_method": "QR"}`. Response ENTRY: `{action: "ENTRY", user_name, vehicle_number, slot_number, entry_time}`. Response EXIT: `{action: "EXIT", exit_time, overstay_hours, overstay_amount}`. Blocked exit: 409 `{action: "EXIT_BLOCKED", overstay_hours, overstay_amount, wallet_balance}`.

**Cancel.** Response 200: `{booking_status: "CANCELLED", refund_amount, penalty_amount, net_credit, new_wallet_balance}`. Errors: 403, 404, 409.

**Wallet adjustment.** Request `{"amount": -100, "description": "..."}`. Response 200: `{user_id, previous_balance, new_balance, adjustment}`. Errors: 400 negative result, 403 forbidden target, 404.

**System status.** Request `{"system_status": "OFFLINE"}`. Response 200: `{"system_status": "OFFLINE"}`. Errors: 400 invalid value, 403 wrong role.

## 9.4 Integration Notes

No external service is integrated. Compatibility aliases under `/api/admin/master/*`, `/api/admin/qr/scan` and `/api/super-admin/reports/*.csv` are kept so older clients continue to work.

# 10. Deployment and Operational Requirements

## 10.1 Deployment Architecture

One Python process serves the application on an internal port. A TLS-terminating reverse proxy publishes it over HTTPS and forwards the host and scheme. The SQLite database is a file on a writable local volume. Static assets are served by Flask from `src/static`. Logs go to stdout and are captured by the process manager.

[[DIAGRAM:DIA-011|Deployment architecture for the single-process Phase 1 deployment]]

## 10.2 Server Configuration

| Item | Requirement |
|---|---|
| Python | 3.11 or newer; verified on 3.14.10 |
| Process | `waitress-serve --listen=0.0.0.0:8000 --call app:create_app` |
| Development | `python run.py` on port 5000 with debug enabled; never production |
| OS | Windows 10/11 or Linux |
| Disk | Approximately 150 MB for the environment plus the database file |
| Network | One HTTP port behind TLS; application port bound to localhost or a private network |

## 10.3 Environment Variables

Names only; values are secrets and must not be committed.

[[CODE]]
APP_ENV
SECRET_KEY
DATABASE_PATH
SESSION_TIMEOUT
MAX_CONTENT_LENGTH
SESSION_COOKIE_SECURE
QSPARK_ADMIN_PASSWORD
QSPARK_ADMIN2_PASSWORD
QSPARK_ADMIN3_PASSWORD
QSPARK_SUPER_ADMIN_PASSWORD
[[/CODE]]

`APP_ENV=production` without `SECRET_KEY` raises at startup. `DATABASE_PATH` must be an absolute writable path; its parent directory is created automatically. `SESSION_COOKIE_SECURE=1` requires HTTPS.

## 10.4 Application Startup

Startup loads `.env`, validates the secret, configures session and CSRF behaviour, creates and initialises the database directory, registers blueprints, runs `init_db()` which executes `schema.sql`, and seeds the mandatory `SYSTEM_STATUS` setting. If an incompatible legacy database is detected, the initialiser preserves it under a timestamped legacy name rather than deleting it.

## 10.5 Database Initialisation and Seeding

`schema.sql` is executed on every start with `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`, so repeated starts are safe. Seed data covers four floors, 64 slots per floor, two vehicle types, cancellation rules and one Super Admin plus three Admins. Seeding is skipped when users already exist.

## 10.6 Backup and Recovery

A hot backup is taken with SQLite's backup API or `.backup`. Backups must be timestamped, never overwritten, verified with `PRAGMA integrity_check` and a row count, and copied off the host. Suggested retention is seven daily, four weekly and twelve monthly copies. Financial history is never pruned from the live database. A full restore drill has not been recorded.

## 10.7 Monitoring and Logging

The application logs to stdout with standard Python logging. `GET /health` provides a liveness probe. No metrics endpoint, tracing, alerting or log aggregation is implemented. Operational monitoring must be provided by the process manager and proxy.

## 10.8 Operational Dependencies

Python runtime and pinned requirements, a writable disk, a reverse proxy with TLS, a process supervisor, a backup destination and an operator with access to the Super Admin account. The camera scanner additionally requires a browser supporting `getUserMedia` and, for decoding, `BarcodeDetector`.

# 11. Requirement Traceability and Verification

Status values: **Implemented** means observable in current source. **Partially** means the behaviour exists with a known limitation. **Unverified** means documentation or reports assert it but no runnable test artifact exists in the repository. **Planned** means future phase only.

The `tests/` directory referenced by project documentation is absent from this repository. `test_results.txt` records `ERROR: file or directory not found: tests/`. Consequently, no requirement is marked verified by an executable test suite; historical pytest results in `docs/test_results.md` are treated as claims.

[[TABLE:Requirement traceability matrix]]

| Requirement ID | Requirement | Module | Evidence | Test reference | Status |
|---|---|---|---|---|---|
| FR-AUTH-001 | Authenticate by username or email | Auth | src/core/security.py authenticate_user | tests/ absent | Implemented |
| FR-AUTH-002 | Reject non-ACTIVE accounts | Auth | security.py account_status filter | tests/ absent | Implemented |
| FR-AUTH-003 | Hash passwords, never expose | Auth | security.py hash_password; admin.py projections | tests/ absent | Implemented |
| FR-AUTH-004 | Hardened session cookie | Auth | app.py cookie configuration | tests/ absent | Implemented |
| FR-AUTH-005 | Absolute and idle expiry | Auth | app.py _current_user | tests/ absent | Implemented |
| FR-AUTH-006 | CSRF on every write | Auth | app.py CSRFProtect | tests/ absent | Implemented |
| FR-AUTH-009 | 401/403 role responses | Auth | security.py decorators | tests/ absent | Implemented |
| FR-PROF-002 | Self-service profile fields | Profile | auth.py PATCH /me | tests/ absent | Implemented |
| FR-SLOT-003 | Live slot status | Availability | slots.py _LIVE_STATUS_SQL | tests/ absent | Implemented |
| FR-SLOT-005 | Occupied after entry | Availability | slots.py event join | tests/ absent | Implemented |
| FR-BOOK-001 | HELD with 30-minute expiry | Booking | bookings.py hold | tests/ absent | Implemented |
| FR-BOOK-003 | Reject slot overlap | Booking | schema trigger and service check | tests/ absent | Implemented |
| FR-BOOK-004 | Reject duplicate active vehicle | Booking | partial unique index | tests/ absent | Implemented |
| FR-BOOK-006 | 05:00–23:00 window | Booking | bookings.py hold | tests/ absent | Implemented |
| FR-BOOK-007 | 18-hour maximum | Booking | bookings.py hold | tests/ absent | Implemented |
| FR-BOOK-009 | Revalidate at confirm | Booking | bookings.py confirm | tests/ absent | Implemented |
| FR-BOOK-010 | Insufficient funds 402 | Booking | bookings.py confirm | tests/ absent | Implemented |
| FR-WALL-001 | Atomic balance plus ledger | Wallet | bookings.py transaction block | tests/ absent | Implemented |
| FR-WALL-005 | Super Admin equal credit | Wallet | bookings.py confirm | tests/ absent | Implemented |
| FR-WALL-006 | Role-scoped adjustments | Wallet | admin.py and super_admin.py | tests/ absent | Implemented |
| FR-WALL-009 | Roll back on failure | Wallet | services/db.py transaction | tests/ absent | Implemented |
| FR-CANC-003 | Refuse cancel after entry | Cancellation | bookings.py _has_open_entry | tests/ absent | Implemented |
| FR-CANC-004 | Rule matching by notice window | Cancellation | bookings.py _calc_refund_percent | tests/ absent | Implemented |
| FR-CANC-006 | Reversal legs and collection | Cancellation | bookings.py cancel | tests/ absent | Implemented |
| FR-QR-001 | QR for confirmed booking | QR | qr.py generate | tests/ absent | Implemented |
| FR-QR-003 | One entry and one exit | QR | partial unique indexes | tests/ absent | Implemented |
| FR-QR-006 | Overtime per 30-minute unit | QR | qr.py _overstay | tests/ absent | Implemented |
| FR-QR-008 | Block unaffordable exit | QR | qr.py EXIT_BLOCKED | tests/ absent | Implemented |
| FR-ACUST-002 | Walk-in as PENDING | Admin | admin.py create user | tests/ absent | Implemented |
| FR-ACUST-006 | Logical deletion | Admin | admin.py DELETE | tests/ absent | Implemented |
| FR-AOPS-005 | Reject control change when booked | Admin | admin.py slot status | tests/ absent | Implemented |
| FR-SADM-001 | Admin creation with admin_id | Super Admin | super_admin.py create | tests/ absent | Implemented |
| FR-SADM-007 | Refuse unsafe floor deactivation | Super Admin | super_admin.py delete floor | tests/ absent | Implemented |
| FR-REP-004 | Revenue from collections | Reporting | reports.py revenue | tests/ absent | Implemented |
| FR-REP-005 | Net of refund reversals | Reporting | reports.py CASE expression | tests/ absent | Implemented |
| FR-SYS-003 | OFFLINE blocks customer writes | System | bookings.py _system_online | tests/ absent | Implemented |
| FR-SYS-008 | Hash excluded from data browser | System | super_admin.py projection | tests/ absent | Implemented |
| NFR-SEC-002 | CSRF enforcement | Security | app.py | tests/ absent | Implemented |
| NFR-SEC-006 | Production secret guard | Security | app.py create_app | tests/ absent | Implemented |
| NFR-DATA-002 | Overlap trigger | Data | schema.sql | tests/ absent | Implemented |
| NFR-DATA-004 | Transition trigger | Data | schema.sql | tests/ absent | Implemented |
| NFR-DATA-006 | EXIT requires ENTRY | Data | schema.sql | tests/ absent | Implemented |
| NFR-USE-006 | WCAG AA evidence | Usability | docs/test_results.md claim | artifacts absent | Unverified |
| NFR-COMP-002 | Cross-browser support | Compatibility | docs/test_results.md claim | artifacts absent | Unverified |
| NFR-PERF-001 | Response within 2 s | Performance | no benchmark | none | Unverified |
| NFR-SCALE-003 | Multi-instance support | Scalability | single SQLite file | none | Planned |

Requirements without a corresponding executable test include every row above, plus the API contracts in Section 9, the CSV exports, the audit-log coverage and the read-only data browser.

# 12. Appendices

## Appendix A: Glossary and Acronyms

| Term | Definition |
|---|---|
| ADMIN | Operational staff role |
| ADMIN_RESERVED | Slot control state withholding a slot from customers |
| Audit log | Append-only record of administrative and security actions |
| Booking | A reservation of one slot by one user for one interval |
| Booking reference | Unique identifier encoded in the QR |
| CSRF | Cross-Site Request Forgery |
| Collection | A revenue record pairing a customer charge with the Super Admin credit |
| CUSTOMER | End-user role that books parking |
| ENTRY/EXIT | Gate events recorded against a booking |
| HELD | Unpaid temporary reservation with a 30-minute expiry |
| INR | Indian Rupee, the only currency used |
| Overstay | Time beyond the booked end, charged per started 30-minute unit |
| PBKDF2-SHA256 | Password hashing algorithm used by Werkzeug |
| SRS | Software Requirements Specification |
| SUPER_ADMIN | Highest-privilege role |
| TBD | To be determined; recorded in Appendix C |
| Wallet | Internal prepaid balance held per account |

## Appendix B: Diagram Reference Index

| ID | Title | Section | Purpose |
|---|---|---|---|
| DIA-001 | System context | 2.7 | Actors and external boundaries |
| DIA-009 | Entity-relationship diagram | 7.3 | Data model with keys and cardinality |
| DIA-004 | Customer booking to exit | 6.1 | Primary customer workflow |
| DIA-005 | Administrative operations | 6.2 | Cancellation and wallet adjustment |
| DIA-006 | Super Admin operations | 6.3 | Infrastructure and system control |
| DIA-010 | Booking state machine | 8.1 | Permitted transitions |
| DIA-011 | Deployment architecture | 10.1 | Process, proxy and database |
| DIA-012 | UI navigation | 4.1 | Page map by role |

Additional machine-readable specifications for architecture, use case, data-flow and admin workflow diagrams are provided in `SRS_Diagram_Prompts.json`.

## Appendix C: Open Issues and TBD Items

| ID | Issue | Current behaviour | Needed decision |
|---|---|---|---|
| TBD-01 | Report definitions | Occupancy per floor and revenue per floor, with CSV variants | Confirm these are the two required reports |
| TBD-02 | Walk-in customer activation | PENDING accounts with no password; staff book for them | Choose password issue, activation link or staff-managed only |
| TBD-03 | OFFLINE scope | Blocks customer holds and confirmations only | Decide whether admin writes must also be blocked |
| TBD-04 | Overtime settlement consent | Automatic debit at exit, blocked if unaffordable | Confirm automatic debit is acceptable |
| TBD-05 | Browser QR decoding | `BarcodeDetector` only; manual fallback | Decide whether to bundle a JS decoder |
| TBD-06 | Overtime granularity | Code rounds up to 30-minute units; product notes say per started hour | Confirm the billing granularity |
| TBD-07 | Retention policy | No archival or pruning implemented | Set legal and operational retention |
| TBD-08 | Performance and availability targets | No benchmarks or SLA | Set measurable targets |
| TBD-09 | Author, organisation and document approval | Placeholders on the title page | Supply for the final issue |
| TBD-10 | Physical camera testing | No device available | Validate on real gate hardware |

## Appendix D: Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 18 Nov 2026 | TBD | Initial reverse-engineered draft |
| 1.0 | 18 Nov 2026 | TBD | Complete SRS with data dictionary, API inventory and traceability |
