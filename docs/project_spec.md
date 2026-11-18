# QSPARK — Product and Functional Specification

**Status:** Consolidated working specification based on the user's latest requirements and the project material reviewed on 11 November 2026. Unconfirmed legacy values are identified as provisional.

## 1. Product purpose

QSPARK is a web-based smart parking slot booking and management system. Customers book parking in advance using an internal digital wallet, receive a QR code, and present it at the parking gate. Staff scan the QR code to register vehicle entry and exit. Admins manage day-to-day parking operations. A Super Admin has system-wide authority.

## 2. Roles and account model

Use one account model with three roles. Do not create separate customer, admin and super-admin identity tables.

| Role | Initial number | Summary |
|---|---:|---|
| `CUSTOMER` | Not fixed | Books parking, pays from wallet, uses booking QR and views own bookings. |
| `ADMIN` | 3 | Performs daily operations, registers/manages customers, monitors floors and scans QR codes. Admin can also use the customer booking interface. |
| `SUPER_ADMIN` | 1 | Highest privilege. Manages admins, users, wallets, floors, slots, system state, live views, reports and analytics. Super Admin can also use the customer booking interface. |

The initial count is a setup default, not a hard-coded limit. The Super Admin can create, update, temporarily block/unblock and logically deactivate Admin accounts.

### Account details

The account/profile information required by current workflows includes:

- Internal user ID.
- Admin ID for Admin and Super Admin accounts.
- Full name.
- Mobile number.
- Email where supplied/required for login.
- Gender.
- Company name / workplace.
- Login identifier and securely hashed password, where login is enabled.
- Role and account status.
- Current wallet balance.

Do not create sample real-person identities or passwords. The process for giving login credentials to a walk-in user is still open; see `open_questions.md`.

## 3. Customer workflow

1. Customer opens the website and logs in with credentials.
2. The booking screen retrieves the customer's name and mobile number from their account and displays them as read-only values.
3. Customer selects vehicle type: Bike or Car.
4. Customer selects a vehicle registration/plate-number format and enters the vehicle number.
5. System validates the vehicle number format and checks that the vehicle does not have another conflicting active booking.
6. Customer chooses a floor.
7. System displays that floor's slots and their live availability.
8. Customer selects an available compatible slot.
9. Customer selects the parking time/duration. The exact start-date/time interaction is unresolved and must be confirmed before final UX behavior is locked.
10. System calculates the estimated charge using the applicable vehicle rate and displays booking details.
11. Customer submits the booking request and reviews the summary.
12. Customer confirms the booking.
13. System checks wallet balance and deducts the charge from the customer's internal wallet.
14. System creates the transaction/revenue records, confirms the booking and generates a QR code associated with the unique booking reference.
15. Customer can view the booking details and QR code in the website.
16. At the parking facility, the gate/admin scanner scans the QR code on entry and records the entry event/time.
17. On departure, the QR code is scanned again and the exit event/time is recorded. Any applicable overtime rule is processed before exit is accepted.

The wallet is an internal stored balance (similar to a prepaid metro card). A real card/UPI/payment gateway is not part of the confirmed scope.

## 4. Admin workflow and permissions

There are three initial Admin accounts. An Admin logs in to an operational dashboard and can also access the same customer booking interface available to Customers.

### Customer registration and management

- Register a walk-in/on-the-spot customer.
- Collect the customer's full name, mobile number, gender and company/workplace.
- View and update customer details.
- Delete/deactivate a customer account. Use logical deletion where records exist; preserve booking and financial history.

### Parking operations

- View all floors and their slots.
- Mark an eligible slot as Maintenance.
- Mark an eligible slot as Reserved by Admin.
- Do not allow an Admin to cancel or remove a booked or occupied parking allocation.
- View slot occupancy and the related customer/booking details, including who occupies a slot, entry time and elapsed duration.
- Scan QR codes for vehicle entry and exit. A manual booking-reference fallback may be provided if the camera is unavailable.

### Admin analytics

- View floor-wise occupancy and heatmap analytics.
- View relevant parking/booking activity and usage details.

### Admin restrictions

- Admin cannot create, update, block or delete another Admin or the Super Admin.
- Admin cannot cancel another customer's booked/occupied slot.
- Admin cannot change system-wide ONLINE/OFFLINE state.
- Admin may adjust a **customer** wallet only (credit or debit, confirmed and ledgered); adjusting an Admin or Super Admin wallet requires the Super Admin. See `open_questions.md`.

## 5. Super Admin workflow and permissions

The Super Admin is the highest-privilege account and has a separate management dashboard. It can also book parking through the customer interface.

### Users and administrators

- Create, view, update and logically deactivate users.
- Create, view, update and logically deactivate Admins.
- Temporarily block and unblock Admin accounts.
- View Admin ID, internal user ID, name, mobile number, email and account status.
- Adjust the wallet balance of any Customer or Admin, recording every adjustment.

### Parking configuration and bookings

- Reserve an eligible spot.
- Update spot details/status.
- Cancel another user's eligible future reservation.
- Do not use cancellation to remove a vehicle that has already entered and is still occupying a slot.
- Add, update, close/deactivate or remove floors safely.
- Increase/decrease the number of slots on a floor.
- Prevent changes that would orphan active bookings or occupied vehicles.

### Monitoring, analytics and reports

- View all floors, slots, bookings, occupants and live operational details.
- View read-only live database table data through an explicitly whitelisted/paginated interface. Never expose passwords, hashes, secrets or arbitrary SQL execution.
- View overtime analytics.
- View floor-wise heatmaps.
- View bar charts, line graphs and donut charts.
- View collected revenue and revenue by floor.
- Provide two report-download actions. The exact report definitions/formats must be confirmed in `open_questions.md` before the UI contract is finalized.

### System control

- Switch the system ONLINE/OFFLINE.
- While OFFLINE, block normal Customer bookings and normal Admin operational writes.
- Retain Super Admin access to the control interface so the Super Admin can restore ONLINE status.

## 6. Revenue and wallet collection requirement

When a Customer's wallet is debited for a parking booking, the corresponding amount must be credited to the Super Admin's collection wallet/balance. The system must create a durable collection record linked to the source user, booking and corresponding wallet movements. The same requirement applies to overtime charges.

Do not update a balance without inserting the matching transaction record. Do not create a collection record without the linked wallet transactions. The customer debit, Super Admin credit and revenue record must be committed atomically.

Revenue reporting must be derivable by date range, floor and vehicle type through the related booking/slot/floor records. Do not duplicate customer name, phone or floor details in the collection table if they can be retrieved through foreign keys.

Refund treatment against the Super Admin's collected balance requires confirmation; see `open_questions.md`. Do not silently assume a financial policy.

## 7. Parking and booking rules

- A booking belongs to one user, one parking slot and one vehicle registration value.
- A slot cannot have overlapping active bookings.
- A vehicle number cannot have conflicting active bookings.
- A booking is not allowed on a Maintenance, Admin-Reserved, inactive or closed slot/floor.
- The slot's displayed live state must be derived from administrative control status and active bookings/entry-exit events rather than being independently edited into contradictory values.
- QR identifies a booking using a unique booking reference; QR is generated after successful confirmation.
- Entry and exit scans must be recorded as distinct events.
- Do not mark a slot available until the vehicle's exit is recorded.

The earlier project files specify the following behavior, but confirm exact values before treating them as immutable production policy:

- Booking status lifecycle: `HELD` → `CONFIRMED` → `COMPLETED`, `CANCELLED` or `EXPIRED`.
- A `HELD` booking expires after 30 minutes if not confirmed.
- Overtime is calculated per started hour and exit is blocked until required overtime is paid.
- Earlier sample rates: Bike ₹5/hour, Car ₹10/hour; overtime Bike ₹10/hour, Car ₹20/hour.
- Earlier sample booking window: 05:00–23:00, 30-minute increments, maximum 18 hours.
- Earlier sample initial layout: B1–B4, 64 slots per floor (40 Bike and 24 Car spaces).
- Earlier sample initial wallet balance: ₹1,000.

These legacy values must be configurable where applicable. Do not hard-code them as unchangeable limits because the Super Admin can change floor/slot counts and rates. See `open_questions.md` for confirmations needed.

## 8. Vehicle registration formats

Earlier project files contain these four plate formats. Retain them as the current proposed validation choices unless the user later changes them:

| Code | Pattern | Example |
|---|---|---|
| `std1` | `^[A-Z]{2} [0-9]{2} [A-Z]{1} [0-9]{4}$` | `KA 04 A 2256` |
| `std2` | `^[A-Z]{2} [0-9]{2} [A-Z]{2} [0-9]{4}$` | `DL 03 CA 1234` |
| `std3` | `^[A-Z]{2} [0-9]{2} [A-Z]{3} [0-9]{4}$` | `ML 04 ASD 5256` |
| `bhr` | `^[0-9]{2} BH [0-9]{4} [A-Z]{2}$` | `26 BH 9876 AB` |

Validate both client-side for usability and server-side for correctness. Normalize registration numbers consistently before duplicate checks.

## 9. Out of scope unless separately approved

- Real payment gateway integration.
- Native mobile application.
- SMS/email notification providers.
- Unrequested external integrations.
- Public access to unrestricted database queries.

## 10. Implemented frontend and workflow status (12 Nov 2026)

All three roles use the same Flask application and one design system. Every page is a Jinja2 shell that reads real JSON APIs; there are no hardcoded KPIs.

**Public landing (planned, not implemented)** - the stylesheet layer exists in `src/static/css/app.css`, but there is no `/landing` route and no `landing.html` template. `GET /` redirects signed-out visitors to `/login`.

**Customer** — login; dashboard (wallet, live available slots per floor, active bookings, recent ledger); 5-step booking wizard (vehicle type → registration → floor/slot grid with live states → schedule with server-side 05:00–23:00 / ≤18 h rules → review) with hold + confirm, wallet debit and QR display; My bookings with status filter, search, paging, detail dialog, QR and rule-checked cancellation; wallet ledger with credit/debit breakdown; profile self-service edit of name, mobile, gender and company.

**Admin** — operations dashboard (slot counts by live state, revenue, floor occupancy, recent bookings, vehicles inside); walk-in registration (name, mobile, gender, company, optional email) with duplicate handling; customer search/update/deactivate and wallet adjustments (explicit credit/debit with confirmation); floor/slot control (maintenance, admin reservation, release) blocked for occupied slots; all-bookings table with date/status/floor/customer filters; QR gate page (camera `BarcodeDetector` when available, manual reference fallback, entry then exit, overtime block explained); analytics for occupancy and floor revenue; configuration page for read-only rates and cancellation-rule CRUD.

**Super Admin** — overview with customer/booking/revenue/occupancy KPIs, system status, floor occupancy, daily revenue, overtime activity; admin management (create, edit, block, unblock, deactivate) and wallet adjustments with ledger; customers via the shared customer page; infrastructure (add floor, change floor status, deactivate, add slot, change slot state, remove slot) with impact confirmations; revenue/occupancy analytics with date filters and both CSV downloads; approved read-only database views with pagination and `password_hash` masked; system online/offline control with consequences, confirmation, backend enforcement and audit trail.

Booking and overtime money movement stays atomic and server-side: debit customer → credit Super Admin → write `revenue_collections`, all in one transaction. The UI never deducts, credits or overwrites a balance. Admins and Super Admins can also book on behalf of a registered customer.

Known gaps are tracked in `open_questions.md` and `docs/test_results.md`: the CSRF token scheme is resolved (Q1), physical camera QR capture is not testable in this environment (Q7), automatic QR decoding needs the native `BarcodeDetector` API so manual reference entry is the fallback in other browsers (Q8), and no Safari/real-mobile run has been performed.

## 11. Completion criteria

The product is not complete until the Customer, Admin and Super Admin workflows work end-to-end against the same authoritative database, role permissions are enforced server-side, wallet/revenue records reconcile, QR entry/exit works, analytics are based on persisted data, and tests verify the main success and failure cases.

---

## 11. Implemented updates (Nov 2026)

- **Slot hover tooltip** (admin + super admin `/admin/slots`): hovering an occupied/reserved slot shows customer, vehicle, booking reference, entry time, expected exit; disappears on mouse leave; follows cursor.
- **Floor status breakdown** (admin dashboard): 4-segment stacked bar (available/reserved/occupied/maintenance) per floor with legend, reconciling with KPI cards.
- **Analytics heat maps** (admin + super admin analytics): per-floor slot heat map with 4 floor selector buttons; clicking switches the heat map.
- **Analytics charts** (donut + line): slot status mix donut, revenue-by-vehicle-type donut, revenue-by-floor donut, daily collections line chart.
- **Revenue report fix**: `/api/admin/reports/revenue` now driven by `revenue_collections` (date filter on `rc.created_at`), fixing blank Net revenue column; `booking_count` = distinct bookings with collections.
