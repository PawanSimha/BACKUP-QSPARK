# QSPARK ORDS API — Templates 16–17 (master-vehicle-types, master-slots)

**Module:** `qsparking.api.v3` · **Base Path:** `qsparking/api/v3/` · **Schema:** `NOV_2026_BATCH`

> Module already created by File 1. Do not create it again. Only 2 templates remain.

---

## The two screens you will fill for every template

**Screen 1 — Create Template**

| Field | Enter |
|---|---|
| URI Template | the pattern below |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Screen 2 — Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | **`PL/SQL`** ← change from the default `Collection Query` |
| Pagination Size | *leave blank* |
| Comments | *leave blank, or the text below* |
| Source | paste the code block below |

---

## Template 16 — master-vehicle-types

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `master/vehicle-types` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Master vehicle types` |

```sql
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'vehicle_type_id' VALUE v.vehicle_type_id,
             'type_name'       VALUE v.type_name,
             'rate'            VALUE v.hourly_rate,
             'overstay'        VALUE v.overstay_rate
           ) ORDER BY v.vehicle_type_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_VEHICLE_TYPES v;
  HTP.p(v_json);
END;
```

---

## Template 17 — master-slots

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `master/slots` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Master slots` |

```sql
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'slot_id'     VALUE s.slot_id,
             'slot_number' VALUE s.slot_number,
             'floor_id'    VALUE s.floor_id,
             'status'      VALUE s.control_status,
             'vehicle'     VALUE s.type_name,
             'rate'        VALUE s.hourly_rate,
             'overstay'    VALUE s.overstay_rate
           ) ORDER BY s.floor_id, s.slot_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_V_SLOTS_LIVE s;
  HTP.p(v_json);
END;
```

> Uses `QSPARK_V_SLOTS_LIVE` — run `oracle/07_view_slots_live.sql` first.

---

## All 17 templates — checklist

| # | URI Template | Method | File |
|---|---|---|---|
| 1 | `health` | GET | 01 |
| 2 | `system-status` | GET | 01 |
| 3 | `slots` | GET | 01 |
| 4 | `slots/:slot_id` | GET | 02 |
| 5 | `bookings/confirm` | POST | 02 |
| 6 | `bookings/cancel` | POST | 02 |
| 7 | `qr/scan` | POST | 03 |
| 8 | `wallet/:user_id` | GET | 03 |
| 9 | `wallet-adjust` | POST | 03 |
| 10 | `admin/floors` | GET | 04 |
| 11 | `admin/users` | GET | 04 |
| 12 | `admin/cancellation-rules` | GET | 04 |
| 13 | `reports/occupancy` | GET | 05 |
| 14 | `reports/revenue` | GET | 05 |
| 15 | `master/floors` | GET | 05 |
| 16 | `master/vehicle-types` | GET | 06 |
| 17 | `master/slots` | GET | 06 |

**Every template:** Priority `0`, HTTP Entity Tag Type `None`.
**Every handler:** Source Type `PL/SQL`, Pagination Size blank.

---

### Notes

- Every source starts with `OWA_UTIL.mime_header('application/json', TRUE)` — `TRUE` is mandatory. `FALSE` puts the JSON in the HTTP headers and the response becomes unparseable.
- POST handlers (5, 6, 7, 9) need their `:p_*` bind variables declared as parameter rows, or they fail with `ORA-01008`.
