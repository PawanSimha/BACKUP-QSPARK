# QSPARK — Product Requirements Document (`prd.md`)

## 1. Executive Summary & Project Purpose
QSPARK is an enterprise-grade Smart Parking Slot Booking and Management System developed to solve physical garage congestion, eliminate double-booking disputes, and automate fare collection. Built to fulfill CEO mandates, the solution decouples a Python 3.14 (FastAPI) application from an Oracle APEX database using Oracle REST Data Services (ORDS).

The platform introduces a closed-loop internal "Metro Card" wallet system where users maintain a prepaid balance, allowing end-to-end booking, cancellation refunds, and late-exit overstay penalty deductions without third-party payment gateways, credit cards, or external SMS/Email APIs.

## 2. CEO Mandates & Non-Negotiable Constraints
1. **Language & Backend:** Python (FastAPI framework for asynchronous, high-speed RESTful services).
2. **Database Engine:** Oracle APEX / Oracle Database (19c/21c/23ai) using SQL Workshop and APEX RESTful Services.
3. **Connectivity Layer:** Oracle REST Data Services (ORDS) as the decoupled HTTP integration bridge.
4. **Roles:** Two distinct roles:
   - **`ADMIN`:** Facility management, real-time floor heatmaps, slot maintenance overrides, and master audit ledger inspection.
   - **`USER`:** Slot availability search, live fare calculation, wallet-based payment, digital pass generation, and self-service cancellation/checkout.
5. **No External Payment/Messaging Gateways:** Zero external dependencies on Razorpay, Stripe, UPI APIs, Twilio, or SendGrid. All payments are internal ledger debits against user wallet balances.
6. **Authentication Model:** Basic authentication using username or email + SHA-256 hashed passwords. No complex third-party OAuth.
7. **Run Live Capability:** The application must run live in real time (`http://localhost:8000`), featuring a visual basement grid, instant pricing calculations, and interactive demo simulators.

## 3. Facility Topology & Slot Capacity (240 Total Slots)
The facility consists of 4 distinct basement parking levels, each structured with a dedicated allocation for two-wheelers and four-wheelers:

| Floor Code | Floor Name | Bike Capacity (₹5/hr) | Car Capacity (₹10/hr) | Total Capacity | Slot Numbering Scheme |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`B1`** | Basement Level 1 | 40 | 20 | 60 | `B1-B01` to `B1-B40` (Bikes), `B1-C01` to `B1-C20` (Cars) |
| **`B2`** | Basement Level 2 | 40 | 20 | 60 | `B2-B01` to `B2-B40` (Bikes), `B2-C01` to `B2-C20` (Cars) |
| **`B3`** | Basement Level 3 | 40 | 20 | 60 | `B3-B01` to `B3-B40` (Bikes), `B3-C01` to `B3-C20` (Cars) |
| **`B4`** | Basement Level 4 | 40 | 20 | 60 | `B4-B01` to `B4-B40` (Bikes), `B4-C01` to `B4-C20` (Cars) |
| **Total** | **4 Basements** | **160 Bikes** | **80 Cars** | **240 Bays** | Uniform grid layout |

## 4. User Profiles & Seed Accounts (50 Pre-loaded Accounts)
The system is pre-populated with 50 specific user profiles loaded via `qspark_apex_dataload.xlsx`:
- **First 3 Accounts are `ADMIN` (`USER_ID` 1001 to 1003):**
  1. `Karan Tulsani` (`karan.tulsani@qspark.com`, username: `karan.tulsani`, password: `admin123`, wallet: `₹1,000.00`)
  2. `Lalaji Gajera` (`lalaji.gajera@qspark.com`, username: `lalaji.gajera`, password: `admin123`, wallet: `₹1,000.00`)
  3. `Pawan Simha R` (`pawan.simha@qspark.com`, username: `pawan.simha`, password: `admin123`, wallet: `₹1,000.00`)
- **Remaining 47 Accounts are `USER` (`USER_ID` 1004 to 1050):**
  - Harshitha M N (`harshitha@qspark.com`), Abhijna (`abhijna@qspark.com`), Nikhil Suresh Naik (`nikhil.naik@qspark.com`), etc.
  - Default password for all regular users: `user123` (stored as SHA-256 hash).
  - Default initial Metro Card wallet balance: `₹500.00` each.
- **New User Registration Flow:**
  - New users sign up with Full Name, Username, Email, and Plain Password.
  - Backend computes `hashlib.sha256(password.encode()).hexdigest()` and assigns starting balance `₹500.00`.

## 5. Commercial Rules, Tariffs & Overstay Penalties

### 5.1 Fixed Base Tariffs
- **Two-Wheeler (`BIKE`):** **₹5.00 per hour**
- **Four-Wheeler (`CAR`):** **₹10.00 per hour**
- **Upfront Fare Calculation:**
  $$\text{Base Amount} = \text{Duration in Hours} \times \text{Hourly Rate (₹5 or ₹10)}$$

### 5.2 Overstay Penalty Algorithm
When a vehicle remains parked beyond its scheduled reservation window:
$$\Delta t = \text{Actual Exit Timestamp} - \text{Scheduled End Timestamp}$$
1. **Grace Period:** A 10-minute ($0.166\text{ hr}$) buffer is allowed with zero penalty ($\text{Penalty} = ₹0.00$).
2. **Penalty Enforcement (Exit $> 10\text{ mins}$ late):**
   - **Bike Overstay Rate:** **₹10.00 per hour**
   - **Car Overstay Rate:** **₹20.00 per hour**
   - $$\text{Overstay Penalty} = \Delta t_{\text{hours}} \times \text{Penalty Rate (₹10 or ₹20)}$$
3. **Settlement:** The penalty is automatically debited from the user's `wallet_balance` upon exit and logged in `QSPARK_WALLET_TRANSACTIONS` as `OVERSTAY_DEBIT`.

## 6. Closed-Loop Metro Card ("Smart Pass") Wallet Model
1. **Wallet Balance Check:** When the user clicks **Proceed to Pay**, the system checks `wallet_balance >= base_amount`. If insufficient, booking is blocked with an informative alert.
2. **Booking Confirmation (Debit):** Upon clicking **Pay from Wallet**, an atomic transaction:
   - Deducts `base_amount` from `QSPARK_USERS.wallet_balance`.
   - Records a `BOOKING_DEBIT` ledger row in `QSPARK_WALLET_TRANSACTIONS` (`previous_balance`, `amount`, `new_balance`).
   - Sets slot status to `RESERVED`.
   - Creates the active reservation in `QSPARK_BOOKINGS`.
3. **Cancellation (Instant Refund):** If the user cancels an upcoming confirmed reservation:
   - The booking transitions to `CANCELLED`.
   - The slot immediately reverts to `AVAILABLE`.
   - The full `base_amount` is credited back to `QSPARK_USERS.wallet_balance`.
   - A `CANCEL_REFUND` ledger row is added to `QSPARK_WALLET_TRANSACTIONS`.

## 7. Functional Requirements & Feature Modules

### 7.1 Module 1: Authentication & Session
- Form login accepting Username or Email + Password.
- Backend verifies input against `QSPARK_USERS.password_hash` using SHA-256.
- Top navigation bar dynamically updates to show logged-in user name, role badge, and live Metro Card balance.

### 7.2 Module 2: Visual Basement Grid (`B1–B4`)
- Interactive floor selector tabs (`B1`, `B2`, `B3`, `B4`).
- Real-time rendering of all 60 bays per floor (40 Bikes, 20 Cars).
- Color-coded bay states: Green (`AVAILABLE`), Amber (`RESERVED`), Red (`OCCUPIED`), Gray (`MAINTENANCE`).
- Clicking any available bay selects it and populates the booking panel.

### 7.3 Module 3: Booking & Digital Pass Generation
- Inputs: Slot ID (pre-filled), Vehicle Registration Number, Vehicle Type (Bike/Car), Duration (1 to 8 hours).
- Live calculator displaying: Duration $\times$ Rate = Total Deductible.
- On payment confirmation, displays a printable **Digital Parking Pass Modal** showing:
  - Unique Booking Code (`QSP-1108-XXXX`)
  - Assigned Slot Number (e.g., `B2-B14`) and Basement Floor
  - License Plate & Vehicle Classification
  - Validity Window (`scheduled_start` to `scheduled_end`)
  - Optical QR Code simulation for boom barrier scanning.

### 7.4 Module 4: Self-Service Booking Drawer & Exit Simulator
- Table of user's active and completed bookings.
- **Cancel Button:** Cancels booking, frees the slot, and executes instant wallet refund.
- **Exit & Settle Simulator:** Simulates vehicle checkout with selectable delay options (On-Time, 30 Mins Late, 1.5 Hours Late) to demonstrate automated overstay penalty calculations during live presentations.

### 7.5 Module 5: Admin Command Center & Analytics
- **KPI Summary Cards:** Total Bays (240), Current Occupancy Rate (%), Active Vehicles Parked, Total Gross Revenue Collected.
- **Basement Utilization Heatmap:** 4 progress bars showing individual live occupancy ratios for `B1`, `B2`, `B3`, and `B4`.
- **Chart.js Visualizations:** Bay status distribution doughnut chart + Bike vs. Car revenue comparison bar chart.
- **Slot Maintenance Overrides:** Dropdown table allowing admins to force any bay into `MAINTENANCE`, `OCCUPIED`, or `AVAILABLE`.
- **Master Audit Trail:** Searchable historical ledger of all bookings, customer IDs, overstay incidents, and wallet transactions.
