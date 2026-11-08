# QSPARK — Frontend UI & User Interaction Flows (`frontend_and_flows.md`)

## 1. UI Design Principles & Baseline Architecture
- **Framework & Styling:** Clean, semantic HTML5 with modular CSS classes structured for seamless Tailwind CSS styling and interactive JavaScript (`fetch()` API).
- **Component Palette:**
  - Backgrounds: Dark slate navbar (`#0f172a`), clean canvas (`#f8fafc`), white card surfaces (`#ffffff`).
  - Bay Status Tokens:
    - `AVAILABLE`: Emerald Green (`#10b981`, light fill `#ecfdf5`)
    - `RESERVED`: Amber/Orange (`#f59e0b`, light fill `#fffbeb`)
    - `OCCUPIED`: Crimson Red (`#ef4444`, light fill `#fef2f2`)
    - `MAINTENANCE`: Slate Gray (`#64748b`, light fill `#f1f5f9`)
  - Accent Color: Royal Blue (`#2563eb`) for selected bays and primary actions.

## 2. Global Navigation Bar & Session State
- **Brand Logo:** `QSPARK` with lightning bolt badge.
- **Backend Status Indicator:** Live pill badge showing `Oracle APEX ORDS (Live)` or `ORDS Local Emulator (Active)`.
- **User Profile & Metro Card Wallet Display:**
  - Displays authenticated user full name and role badge (`ADMIN` or `USER`).
  - Displays live Metro Card Smart Balance: `💳 Wallet: ₹500.00` (auto-refreshes after booking, checkout, or cancellation).
- **Role Switcher / View Toggle:**
  - Allows switching between **Customer Booking Portal** and **Admin Command Center** (restricted to Admin users).
  - Logout button that clears session storage and returns to the login screen.

## 3. Screen 1: Basic Authentication (Login Screen)
- **Input Fields:** Username or Email address + Password.
- **Client Logic:**
  - Dispatches `POST /api/auth/login` with `{login_id, password}`.
  - Backend verifies SHA-256 hash against `QSPARK_USERS.password_hash`.
  - On success, caches `user_id`, `full_name`, `role`, and `wallet_balance` in browser session storage and redirects to the portal.
- **Quick Test Buttons (for Live Demo):** One-click buttons to sign in as **Admin (Pawan Simha R)** or **User (Harshitha M N)**.

## 4. Screen 2: Customer Portal & 240-Slot Basement Grid
- **Basement Level Tabs:** 4 interactive tabs (`B1`, `B2`, `B3`, `B4`). Switching tabs immediately fetches that floor's 60 bays via `GET /api/slots?floor_id=X`.
- **Bay Visual Grid:**
  - Arranged in 2 clear sections per floor:
    - **Bike Section (40 bays):** `B1-B01` to `B1-B40` (with motorcycle icon).
    - **Car Section (20 bays):** `B1-C01` to `B1-C20` (with automobile icon).
  - Clicking any `AVAILABLE` bay outlines it in blue and loads its ID into the reservation panel.
- **Live Reservation & Fare Calculator Panel (Sticky Right Column):**
  - Displays selected slot number and vehicle type.
  - Vehicle License Plate input field (e.g., `KA-01-AB-1234`).
  - Duration Slider / Input: 1.0 to 8.0 hours.
  - Real-time Fare Math Card:
    - Rate: `₹5.00/hr` (Bike) or `₹10.00/hr` (Car)
    - Formula: $\text{Hours} \times \text{Rate} = \text{Base Amount}$
    - Current Wallet Balance: `₹500.00`
    - Remaining Balance After Booking: `₹500.00 - Fare`
  - Action Button: **Proceed to Pay from Wallet**.

## 5. Modal 1: Metro Card Payment Confirmation
- Opens upon clicking **Proceed to Pay**.
- Displays passbook summary:
  - Total Fare Deductible: `₹15.00`
  - Current Metro Card Balance: `₹500.00`
  - Balance After Payment: `₹485.00`
- If balance is insufficient, the button is disabled with warning: `Insufficient Metro Card Balance`.
- Clicking **Confirm & Deduct** triggers `POST /api/bookings` $\rightarrow$ atomically executes wallet deduction, marks bay `RESERVED`, and opens the Digital Pass modal.

## 6. Modal 2: Digital QR Parking Pass
- Displays confirmation details:
  - Unique Ticket Code (e.g., `QSP-1108-4012`)
  - Bay Number (`B1-B14`) and Floor (`B1`)
  - Vehicle Plate Number & Vehicle Classification
  - Validity Window (`scheduled_start` to `scheduled_end`)
  - Amount Paid & Remaining Wallet Balance
  - Scannable QR Code simulation for boom barrier optical readers.
  - Print / Save Pass button.

## 7. Screen 3: Self-Service Bookings Drawer & Overstay Simulator
- **My Bookings Table:** Lists active and historical reservations with status badges.
- **Cancel Button:**
  - Only active for `CONFIRMED` bookings before entry.
  - Confirmation prompt $\rightarrow$ calls `PUT /api/bookings/:id/cancel`.
  - Instantly refunds fare to `QSPARK_USERS.wallet_balance`, creates `CANCEL_REFUND` in `QSPARK_WALLET_TRANSACTIONS`, reverts bay to `AVAILABLE`, and updates the navbar balance.
- **Exit & Settle Simulator (for Live CEO / Evaluator Demos):**
  - Clicking **Simulate Exit** opens a dialog with a departure delay selector:
    - *On-Time Exit:* Within window or 10-minute grace period $\rightarrow$ Penalty = ₹0.00.
    - *30 Mins Late:* Breaches grace period $\rightarrow$ 0.5 hr penalty deducted.
    - *1.5 Hours Late:* 1.5 hr penalty deducted (Bike: ₹15, Car: ₹30).
  - Clicking **Process Exit** calls `PUT /api/bookings/:id/checkout` $\rightarrow$ debits fine from wallet, sets booking to `COMPLETED`, and frees the slot.

## 8. Screen 4: Admin Command Center & Analytics
- **Executive KPI Cards:**
  - Total Facility Capacity: `240 Slots`
  - Real-Time Occupancy: `%`
  - Active Parked Vehicles: `Count`
  - Total Gross Revenue Collected: `₹ Amount`
- **Floor-Wise Utilization Heatmap:**
  - 4 progress bars (`B1`, `B2`, `B3`, `B4`) showing occupancy counts and percentages.
  - Dynamic color thresholds: Green ($<35\%$), Amber ($35\text{–}70\%$), Red ($>70\%$).
- **Live Chart.js Visualizations:**
  - Doughnut chart: Bay status distribution (`AVAILABLE`, `RESERVED`, `OCCUPIED`, `MAINTENANCE`).
  - Bar chart: Bike vs. Car revenue comparison.
- **Slot Maintenance Override Table:**
  - Searchable table of all 240 bays with a dropdown to force state to `MAINTENANCE` (sensor calibration), `OCCUPIED` (walk-in vehicle), or `AVAILABLE`.
- **Master Audit Log View:**
  - Chronological table of `QSPARK_AUDIT_LOGS` recording user IDs, slot IDs, old status, new status, and timestamps.
