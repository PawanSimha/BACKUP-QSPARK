# Old REST API Services — `qsparking.api.v2` (archived)

> Archived 2026-11-15. The module `qsparking.api.v2` and all of its templates/handlers were deleted from the APEX REST workshop after capturing the URLs below. The old `QSPARK_*` tables were dropped in the same session (see `oracle conversation with AI.md` §12/§13). This file is historical reference only — the live module is now `qsparking.api.v3`.

## Module identity
- **Module name:** `qsparking.api.v2`
- **Base path:** `/ords/nov_2026_batch/qsparking/api/v2/`
- **Host:** `ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com`
- **Schema:** `NOV_2026_BATCH`
- **Handlers:** 9 (audit-track, analytics/kpi, audit/logs, bookings GET/POST, bookings/:id/cancel, bookings/:id/checkout, slots GET, slots/:id/status)

## Full handler URLs (captured before deletion)

| Template | Method | Full URL |
|---|---|---|
| `admin/audit-track` | POST | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/admin/audit-track |
| `analytics/kpi` | GET | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/analytics/kpi |
| `audit/logs` | GET | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/audit/logs |
| `bookings/` | GET | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/bookings/ |
| `bookings/` | POST | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/bookings/ |
| `bookings/:id/cancel` | PUT | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/bookings/:id/cancel |
| `bookings/:id/checkout` | PUT | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/bookings/:id/checkout |
| `slots/` | GET | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/slots/ |
| `slots/:id/status` | PUT | https://ga97be9115f23e9-moviestreamworkshop.adb.ap-mumbai-1.oraclecloudapps.com/ords/nov_2026_batch/qsparking/api/v2/slots/:id/status |

## Old tables dropped (2026-11-15) — pre-drop row counts

| Table | Rows |
|---|---|
| QSPARK_AUDIT_LOGS | 75 |
| QSPARK_AUDIT_TRACK | 3 |
| QSPARK_BOOKINGS | 61 |
| QSPARK_FLOORS | 4 |
| QSPARK_PARKING_SLOTS | 240 |
| QSPARK_USERS | 50 |
| QSPARK_VEHICLE_TYPES | 2 |
| QSPARK_WALLET_TRANSACTIONS | 68 |

## QSPARK_AUDIT_TRACK — backed-up rows (3) (no new-model equivalent)

| TRACK_ID | ADMIN_NAME | TIME_DATE | MODIFIED_TABLE | MODIFIED_COLUMN | WHY_MODIFIED |
|---|---|---|---|---|---|
| 1 | pawan.simha | 10-NOV-26 06.40.14.611555 AM | QSPARK_PARKING_SLOTS | status | Sensor calibration on bay B1-B06 |
| 21 | pawan.simha | 10-NOV-26 10.58.32.746809 AM | QSPARK_PARKING_SLOTS | status | Sensor calibration on bay B1-B06 |
| 22 | pawan.simha | 10-NOV-26 10.58.36.919821 AM | QSPARK_PARKING_SLOTS | status | Sensor calibration on bay B1-B06 |

## Recovery
- Dropped tables remain in the Oracle recycle bin until `PURGE`; restore with `FLASHBACK TABLE "BIN$..." TO BEFORE DROP;`.
- The old module is gone; its URL shape above is retained only for reference when building `qsparking.api.v3`.
- Source of truth for replacement data is the SQLite DB `database/parking_local.db` (see `oracle conversation with AI.md` §7).