# QSPARK: product requirements document (`prd.md`)

## 1. Executive summary and purpose
QSPARK is a smart parking slot booking and management system for enterprise use. It tackles physical garage congestion, double-booking disputes and manual fare collection. To meet the CEO mandates, the Python 3.14 (FastAPI) application is decoupled from the Oracle APEX database through Oracle REST Data Services (ORDS).

The platform runs a closed-loop internal "Metro Card" wallet. Users keep a prepaid balance and use it for booking, cancellation refunds and late-exit overstay penalties. No third-party payment gateway, credit card or external SMS/email API is involved.

## 2. CEO mandates and constraints
1. **Language and backend:** Python with FastAPI for asynchronous REST services.
2. **Database engine:** Oracle APEX / Oracle Database (19c/21c/23ai) using SQL Workshop and APEX RESTful Services.
3. **Connectivity:** Oracle REST Data Services (ORDS) as the HTTP bridge between the two.
4. **Roles:** two of them.
   - **`ADMIN`:** facility management, real-time floor heatmaps, slot maintenance overrides and master audit ledger inspection.
   - **`USER`:** slot availability search, live fare calculation, wallet payment, digital pass generation, self-service cancellation and checkout.
5. **No external payment or messaging gateways.** Nothing depends on Razorpay, Stripe, UPI APIs, Twilio or SendGrid. All payments are ledger debits against the user's wallet.
6. **Authentication:** basic auth with username or email plus a SHA-256 hashed password. No third-party OAuth.
7. **Live demo capability:** the app must run at `http://localhost:8000` with a visual basement grid, instant pricing and interactive simulators.

## 3. Facility topology and slot capacity (240 slots)
The facility has 4 basement levels, each split between two-wheelers and four-wheelers:

| Floor Code | Floor Name | Bike Capacity (₹5/hr) | Car Capacity (₹10/hr) | Total Capacity | Slot Numbering Scheme |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`B1`** | Basement Level 1 | 40 | 20 | 60 | `B1-B01` to `B1-B40` (Bikes), `B1-C01` to `B1-C20` (Cars) |
| **`B2`** | Basement Level 2 | 40 | 20 | 60 | `B2-B01` to `B2-B40` (Bikes), `B2-C01` to `B2-C20` (Cars) |
| **`B3`** | Basement Level 3 | 40 | 20 | 60 | `B3-B01` to `B3-B40` (Bikes), `B3-C01` to `B3-C20` (Cars) |
| **`B4`** | Basement Level 4 | 40 | 20 | 60 | `B4-B01` to `B4-B40` (Bikes), `B4-C01` to `B4-C20` (Cars) |
| **Total** | **4 Basements** | **160 Bikes** | **80 Cars** | **240 Bays** | Uniform grid layout |

## 4. User profiles and seed accounts (50 pre-loaded)
The system ships with 50 user profiles loaded from `qspark_apex_dataload.xlsx`:

- **First 3 accounts are `ADMIN` (`USER_ID` 1001 to 1003):**
  1. `Karan Tulsani` (`karan.tulsani@qspark.com`, username `karan.tulsani`, password `admin123`, wallet `₹1,000.00`)
  2. `Lalaji Gajera` (`lalaji.gajera@qspark.com`, username `lalaji.gajera`, password `admin123`, wallet `₹1,000.00`)
  3. `Pawan Simha R` (`pawan.simha@qspark.com`, username `pawan.simha`, password `admin123`, wallet `₹1,000.00`)
- **The other 47 accounts are `USER` (`USER_ID` 1004 to 1050):**
  - Default password for every regular user: `user123`, stored as a SHA-256 hash.
  - Default Metro Card balance: `₹500.00` each.
  - Roster as loaded from `qspark_apex_dataload.xlsx`:

| User ID | Full Name | Username | Email | Role | Wallet |
| :---: | :--- | :--- | :--- | :---: | :---: |
| 1001 | Karan Tulsani | `karan.tulsani` | karan.tulsani@qspark.com | ADMIN | ₹1,000.00 |
| 1002 | Lalaji Gajera | `lalaji.gajera` | lalaji.gajera@qspark.com | ADMIN | ₹1,000.00 |
| 1003 | Pawan Simha R | `pawan.simha` | pawan.simha@qspark.com | ADMIN | ₹1,000.00 |
| 1004 | Harshitha M N | `harshitha` | harshitha@qspark.com | USER | ₹500.00 |
| 1005 | Abhijna | `abhijna` | abhijna@qspark.com | USER | ₹500.00 |
| 1006 | Manprit | `manprit` | manprit@qspark.com | USER | ₹500.00 |
| 1007 | Mythili N | `mythili` | mythili@qspark.com | USER | ₹500.00 |
| 1008 | Meghana Gopal | `meghana.gopal` | meghana.gopal@qspark.com | USER | ₹500.00 |
| 1009 | Yoshitha T | `yoshitha` | yoshitha@qspark.com | USER | ₹500.00 |
| 1010 | Yuvraj Umang M | `yuvraj.umang` | yuvraj.umang@qspark.com | USER | ₹500.00 |
| 1011 | Girish D R | `girish` | girish@qspark.com | USER | ₹500.00 |
| 1012 | Jaswanth S | `jaswanth` | jaswanth@qspark.com | USER | ₹500.00 |
| 1013 | Rohith R | `rohith` | rohith@qspark.com | USER | ₹500.00 |
| 1014 | Lipika Devarahatti | `lipika.devarahatti` | lipika.devarahatti@qspark.com | USER | ₹500.00 |
| 1015 | Harshita Hegde | `harshita.hegde` | harshita.hegde@qspark.com | USER | ₹500.00 |
| 1016 | Bharati Kumari | `bharati.kumari` | bharati.kumari@qspark.com | USER | ₹500.00 |
| 1017 | Kamutala Abhinav | `kamutala.abhinav` | kamutala.abhinav@qspark.com | USER | ₹500.00 |
| 1018 | Nikunj Gupta | `nikunj.gupta` | nikunj.gupta@qspark.com | USER | ₹500.00 |
| 1019 | Videsh Kumar | `videsh.kumar` | videsh.kumar@qspark.com | USER | ₹500.00 |
| 1020 | Arangan Shankar | `arangan.shankar` | arangan.shankar@qspark.com | USER | ₹500.00 |
| 1021 | Chinnaswamy Palani | `chinnaswamy.palani` | chinnaswamy.palani@qspark.com | USER | ₹500.00 |
| 1022 | Nikhil Suresh Naik | `nikhil.naik` | nikhil.naik@qspark.com | USER | ₹500.00 |
| 1023 | Aditya U | `aditya` | aditya@qspark.com | USER | ₹500.00 |
| 1024 | Vivek | `vivek` | vivek@qspark.com | USER | ₹500.00 |
| 1025 | Atman Mishra | `atman.mishra` | atman.mishra@qspark.com | USER | ₹500.00 |
| 1026 | Kousal Reddy | `kousal.reddy` | kousal.reddy@qspark.com | USER | ₹500.00 |
| 1027 | Likitha K | `likitha` | likitha@qspark.com | USER | ₹500.00 |
| 1028 | Abhishek Paul P | `abhishek.paul` | abhishek.paul@qspark.com | USER | ₹500.00 |
| 1029 | Janiya Mariya Tomy | `janiya.tomy` | janiya.tomy@qspark.com | USER | ₹500.00 |
| 1030 | Gaurav Ahuja | `gaurav.ahuja` | gaurav.ahuja@qspark.com | USER | ₹500.00 |
| 1031 | Pramila Baburao More | `pramila.more` | pramila.more@qspark.com | USER | ₹500.00 |
| 1032 | Vandana D Patel | `vandana.patel` | vandana.patel@qspark.com | USER | ₹500.00 |
| 1033 | Joel Rajive | `joel.rajive` | joel.rajive@qspark.com | USER | ₹500.00 |
| 1034 | Jagadeesh Jairam Jaisinghani | `jagadeesh.jaisinghani` | jagadeesh.jaisinghani@qspark.com | USER | ₹500.00 |
| 1035 | Vancy Arokiya | `vancy.arokiya` | vancy.arokiya@qspark.com | USER | ₹500.00 |
| 1036 | Prerna | `prerna` | prerna@qspark.com | USER | ₹500.00 |
| 1037 | Roshan Baig M | `roshan.baig` | roshan.baig@qspark.com | USER | ₹500.00 |
| 1038 | Bishal Debnath | `bishal.debnath` | bishal.debnath@qspark.com | USER | ₹500.00 |
| 1039 | Haylee Dhiresh Desai | `haylee.desai` | haylee.desai@qspark.com | USER | ₹500.00 |
| 1040 | Minni Parnami | `minni.parnami` | minni.parnami@qspark.com | USER | ₹500.00 |
| 1041 | Munmun Gupta | `munmun.gupta` | munmun.gupta@qspark.com | USER | ₹500.00 |
| 1042 | Piyush Patel | `piyush.patel` | piyush.patel@qspark.com | USER | ₹500.00 |
| 1043 | Tilak Bahadur Shah | `tilak.shah` | tilak.shah@qspark.com | USER | ₹500.00 |
| 1044 | Sharan S | `sharan` | sharan@qspark.com | USER | ₹500.00 |
| 1045 | Dhruvil Pandya | `dhruvil.pandya` | dhruvil.pandya@qspark.com | USER | ₹500.00 |
| 1046 | Diksha Patel | `diksha.patel` | diksha.patel@qspark.com | USER | ₹500.00 |
| 1047 | Suma Paralada | `suma.paralada` | suma.paralada@qspark.com | USER | ₹500.00 |
| 1048 | Bhagyashree Shrikant Wagh | `bhagyashree.wagh` | bhagyashree.wagh@qspark.com | USER | ₹500.00 |
| 1049 | Gopal Mahendra Reddy | `gopal.reddy` | gopal.reddy@qspark.com | USER | ₹500.00 |
| 1050 | Janardhana M T | `janardhana` | janardhana@qspark.com | USER | ₹500.00 |
- **New user registration flow:**
  - Sign up with full name, username, email and a plain password.
  - The backend computes `hashlib.sha256(password.encode()).hexdigest()` and starts the account at `₹500.00`.

## 5. Tariffs and overstay penalties

### 5.1 Fixed base tariffs
- **Two-wheeler (`BIKE`):** **₹5.00 per hour**
- **Four-wheeler (`CAR`):** **₹10.00 per hour**
- **Upfront fare:**
  $$\text{Base Amount} = \text{Duration in Hours} \times \text{Hourly Rate (₹5 or ₹10)}$$

### 5.2 Overstay penalty
When a vehicle stays parked past its scheduled window:
$$\Delta t = \text{Actual Exit Timestamp} - \text{Scheduled End Timestamp}$$
1. **Grace period:** 10 minutes ($0.166\text{ hr}$) at zero penalty ($\text{Penalty} = ₹0.00$).
2. **Past the grace period (exit more than 10 minutes late):**
   - **Bike overstay rate:** **₹10.00 per hour**
   - **Car overstay rate:** **₹20.00 per hour**
   - $$\text{Overstay Penalty} = \Delta t_{\text{hours}} \times \text{Penalty Rate (₹10 or ₹20)}$$
3. **Settlement:** the penalty is debited from `wallet_balance` at exit and logged in `QSPARK_WALLET_TRANSACTIONS` as `OVERSTAY_DEBIT`.

## 6. Closed-loop Metro Card ("Smart Pass") wallet
1. **Balance check:** when the user clicks **Proceed to pay**, the system checks `wallet_balance >= base_amount`. If the balance is short, the booking is blocked with an alert.
2. **Booking confirmation (debit):** clicking **Pay from wallet** runs one atomic transaction that:
   - deducts `base_amount` from `QSPARK_USERS.wallet_balance`,
   - records a `BOOKING_DEBIT` row in `QSPARK_WALLET_TRANSACTIONS` (`previous_balance`, `amount`, `new_balance`),
   - sets the slot status to `RESERVED`,
   - creates the active reservation in `QSPARK_BOOKINGS`.
3. **Cancellation (instant refund):** when a user cancels an upcoming confirmed reservation:
   - the booking moves to `CANCELLED`,
   - the slot returns to `AVAILABLE`,
   - the full `base_amount` is credited back to `QSPARK_USERS.wallet_balance`,
   - a `CANCEL_REFUND` row is added to `QSPARK_WALLET_TRANSACTIONS`.

## 7. Functional requirements

### 7.1 Module 1: authentication and session
- Login form taking username or email plus password.
- The backend checks the input against `QSPARK_USERS.password_hash` using SHA-256.
- The navbar shows the logged-in user's name, role badge and live Metro Card balance.

### 7.2 Module 2: visual basement grid (`B1–B4`)
- Interactive floor tabs (`B1`, `B2`, `B3`, `B4`).
- All 60 bays per floor render live (40 bikes, 20 cars).
- Bay colours: green (`AVAILABLE`), amber (`RESERVED`), red (`OCCUPIED`), grey (`MAINTENANCE`).
- Clicking an available bay selects it and fills the booking panel.

### 7.3 Module 3: booking and digital pass
- Inputs: slot ID (pre-filled), vehicle registration number, vehicle type (bike/car), duration (1 to 8 hours).
- Live calculator showing duration $\times$ rate = amount to be deducted.
- After payment the printable **digital parking pass** modal shows:
  - a unique booking code (`QSP-1108-XXXX`),
  - the assigned slot number (e.g. `B2-B14`) and basement floor,
  - licence plate and vehicle class,
  - the validity window (`scheduled_start` to `scheduled_end`),
  - a simulated optical QR code for the boom barrier scanner.

### 7.4 Module 4: bookings drawer and exit simulator
- Table of the user's active and completed bookings.
- **Cancel button:** cancels the booking, frees the slot and refunds the wallet instantly.
- **Exit & settle simulator:** simulates checkout with selectable delays (on time, 30 minutes late, 1.5 hours late) so overstay penalties can be demonstrated during presentations.

### 7.5 Module 5: admin command center and analytics
- **KPI cards:** total bays (240), current occupancy rate (%), active vehicles parked, total gross revenue collected.
- **Basement utilisation heatmap:** 4 progress bars with live occupancy ratios for `B1`, `B2`, `B3` and `B4`.
- **Chart.js charts:** bay status distribution doughnut plus a bike vs car revenue bar chart.
- **Slot maintenance overrides:** a dropdown table that lets an admin force any bay into `MAINTENANCE`, `OCCUPIED` or `AVAILABLE`.
- **Master audit trail:** searchable history of bookings, customer IDs, overstay incidents and wallet transactions.
- **Admin audit register (`QSPARK_AUDIT_TRACK`):** a manual form where an admin records a change by selecting the modified table and column and giving a reason. Six columns: `admin_name`, `time_date`, `modified_table`, `modified_column`, `why_modified` and an auto-generated identity `track_id`. Nothing is captured automatically; the admin submits each row.
