# QSPARK: frontend UI and interaction flows (`frontend_and_flows.md`)

## 1. Design principles and baseline
- **Framework and styling:** semantic HTML5 with modular CSS classes, structured so Tailwind CSS and JavaScript (`fetch()` API) can be layered on.
- **Component palette:**
  - Backgrounds: dark slate navbar (`#0f172a`), clean canvas (`#f8fafc`), white card surfaces (`#ffffff`).
  - Bay status tokens:
    - `AVAILABLE`: emerald green (`#10b981`, light fill `#ecfdf5`)
    - `RESERVED`: amber/orange (`#f59e0b`, light fill `#fffbeb`)
    - `OCCUPIED`: crimson red (`#ef4444`, light fill `#fef2f2`)
    - `MAINTENANCE`: slate grey (`#64748b`, light fill `#f1f5f9`)
  - Accent: royal blue (`#2563eb`) for selected bays and primary actions.

## 2. Navbar and session state
- **Brand:** `QSPARK` with a lightning bolt badge.
- **Backend status pill:** shows `Oracle APEX ORDS (Live)` or `ORDS Local Emulator (Active)`.
- **User and wallet display:**
  - The authenticated user's full name and role badge (`ADMIN` or `USER`).
  - Live Metro Card balance: `💳 Wallet: ₹500.00`, refreshed after every booking, checkout or cancellation.
- **View toggle:**
  - Switch between **Customer booking portal** and **Admin command center** (admins only).
  - Logout clears session storage and returns to the login screen.

## 3. Screen 1: login
- **Inputs:** username or email address, plus password.
- **Client logic:**
  - Sends `POST /api/auth/login` with `{login_id, password}`.
  - The backend checks the SHA-256 hash against `QSPARK_USERS.password_hash`.
  - On success it caches `user_id`, `full_name`, `role` and `wallet_balance` in session storage and opens the portal.
- **Quick test buttons:** one click signs in as **Admin (Pawan Simha R)** or **User (Harshitha M N)**.

## 4. Screen 2: customer portal and the 240-slot grid
- **Floor tabs:** four tabs (`B1`, `B2`, `B3`, `B4`). Switching fetches that floor's 60 bays through `GET /api/slots?floor_id=X`.
- **Bay grid:** two sections per floor.
  - **Bike section (40 bays):** `B1-B01` to `B1-B40`, with a motorcycle icon.
  - **Car section (20 bays):** `B1-C01` to `B1-C20`, with a car icon.
  - Clicking an `AVAILABLE` bay outlines it in blue and loads its ID into the reservation panel.
- **Sticky reservation and fare panel (right column):**
  - Selected slot number and vehicle type.
  - Vehicle licence plate input (e.g. `KA-01-AB-1234`).
  - Duration slider or input from 1.0 to 8.0 hours.
  - Live fare card:
    - rate `₹5.00/hr` (bike) or `₹10.00/hr` (car),
    - formula $\text{Hours} \times \text{Rate} = \text{Base Amount}$,
    - current balance `₹500.00`,
    - balance after booking `₹500.00 - Fare`.
  - Action button: **Proceed to pay from wallet**.

## 5. Modal 1: Metro Card payment confirmation
- Opens from **Proceed to pay**.
- Passbook summary:
  - total fare: `₹15.00`
  - current Metro Card balance: `₹500.00`
  - balance after payment: `₹485.00`
- If the balance is short, the button is disabled and shows `Insufficient Metro Card Balance`.
- **Confirm & deduct** calls `POST /api/bookings`, which deducts the fare and marks the bay `RESERVED` in one transaction, then opens the digital pass.

## 6. Modal 2: digital QR parking pass
- Shows:
  - unique ticket code (e.g. `QSP-1108-4012`),
  - bay number (`B1-B14`) and floor (`B1`),
  - plate number and vehicle class,
  - validity window (`scheduled_start` to `scheduled_end`),
  - amount paid and remaining wallet balance,
  - a simulated QR code for the boom barrier reader,
  - a print or save button.

## 7. Screen 3: bookings drawer and overstay simulator
- **My bookings table:** active and past reservations with status badges.
- **Cancel button:**
  - Enabled only for `CONFIRMED` bookings before entry.
  - After a confirmation prompt it calls `PUT /api/bookings/:id/cancel`.
  - The fare goes back to `QSPARK_USERS.wallet_balance`, a `CANCEL_REFUND` row lands in `QSPARK_WALLET_TRANSACTIONS`, the bay returns to `AVAILABLE` and the navbar balance updates.
- **Exit & settle simulator (for live demos):**
  - **Simulate exit** opens a delay selector:
    - *On time:* inside the window or the 10-minute grace period, penalty ₹0.00.
    - *30 mins late:* past the grace period, 0.5 hr penalty.
    - *1.5 hours late:* 1.5 hr penalty (bike ₹15, car ₹30).
  - **Process exit** calls `PUT /api/bookings/:id/checkout`, which debits the fine, sets the booking to `COMPLETED` and frees the slot.

## 8. Screen 4: admin command center and analytics
- **KPI cards:**
  - total facility capacity: `240 Slots`
  - real-time occupancy: `%`
  - active parked vehicles: `Count`
  - gross revenue collected: `₹ Amount`
- **Floor utilisation heatmap:**
  - four progress bars (`B1`, `B2`, `B3`, `B4`) with occupancy counts and percentages.
  - Colour thresholds: green ($<35\%$), amber ($35\text{–}70\%$), red ($>70\%$).
- **Chart.js charts:**
  - doughnut of bay status distribution (`AVAILABLE`, `RESERVED`, `OCCUPIED`, `MAINTENANCE`),
  - bar chart comparing bike and car revenue.
- **Slot maintenance override table:**
  - Searchable list of all 240 bays with a dropdown to force `MAINTENANCE` (sensor calibration), `OCCUPIED` (walk-in vehicle) or `AVAILABLE`.
- **Master audit log view:**
  - Chronological table of `QSPARK_AUDIT_LOGS` with user IDs, slot IDs, old status, new status and timestamps.
- **Admin audit register (manual entry, `QSPARK_AUDIT_TRACK`):**
  - Form in the Admin Command Center: `admin_name` prefilled from the logged-in admin, a `modified_table` dropdown for the seven source tables, a free-text `modified_column` input, a `why_modified` textarea and **Log Compliance Record**.
  - `time_date` comes from the database default; it is never typed.
  - It writes exactly one row and touches no other table. This is the only write path; nothing is captured automatically.

## 9. File map and component layout (as built)
The UI is three files served by FastAPI (`GET /`); Bootstrap 5.3, FontAwesome 6 and Chart.js 4 load from CDNs.

| File | Responsibility | Key UI element IDs |
| :--- | :--- | :--- |
| `src/templates/index.html` | Page shell: navbar, login, portal, admin, 3 modals, bookings offcanvas, print area | `loginView`, `portalView`, `adminView`, `floorTabs`, `bikeSection`, `carSection`, `bookingCard`, `paymentModal`, `passModal`, `exitModal`, `bookingsDrawer`, `printArea` |
| `src/static/css/app.css` | Design tokens and bay colours (#10b981 / #f59e0b / #ef4444 / #64748b), sticky booking card, heat bars, print stylesheet | `.bay`, `.bay.available`, `.bay.reserved`, `.bay.occupied`, `.bay.maintenance`, `.bay.selected`, `.wallet-chip` |
| `src/static/js/app.js` | Session/token handling, slot rendering, fare calculator, wallet refresh, booking and QR pass, cancel, exit simulator, admin KPIs/charts/overrides/audit | `state`, `api()`, `renderSlots()`, `confirmPayment()`, `drawQr()`, `processExit()`, `showAdmin()` |

Layout behaviour:
- The navbar shows `mode_label` from the server (`ORDS Local Emulator (Active)` or `Oracle APEX ORDS (Live)`), the wallet chip, role badge and a role-gated admin button.
- The portal is an 8/4 Bootstrap grid: floor tabs and bike/car grids on the left, sticky fare card on the right.
- Admin uses four KPI cards, a 5/4/3 chart row, then a 6/6 row for slot overrides and the audit log.
- Auth state and token persist in `sessionStorage` (`qspark_token`); every debit or refund calls `/api/auth/me` to refresh the wallet chip.

## 10. Exit simulator maths (`scheduled_end + delay`)
The seeded bookings have windows in the past, so the simulator cannot just add the delay to "now". It computes the target exit explicitly:

```
target_exit     = scheduled_end + delay
simulated_late  = (scheduled_end - now) / 1 hour + delay   // may be negative
payload         = { "simulated_late_hours": simulated_late }
```

The backend then evaluates `exit = now + simulated_late_hours`, which equals `target_exit`.

| Selector | Delay | Bike penalty (₹10/hr) | Car penalty (₹20/hr) |
| :--- | :---: | :---: | :---: |
| On-Time Exit | 0 h | ₹0.00 (within grace) | ₹0.00 |
| 30 Mins Late | 0.5 h | ₹5.00 | ₹10.00 |
| 1.5 Hours Late | 1.5 h | ₹15.00 | ₹30.00 |

Lateness inside the 10-minute grace window is always ₹0.00. Penalties are debited as `OVERSTAY_DEBIT`; a booking whose wallet cannot cover the fine is rejected with HTTP 402.
