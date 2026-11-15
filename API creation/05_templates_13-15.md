# QSPARK ORDS API — Templates 13–15 (reports-occupancy, reports-revenue, master-floors)

**Module:** `qsparking.api.v3` · **Base Path:** `qsparking/api/v3/` · **Schema:** `NOV_2026_BATCH`

> Module already created by File 1. Do not create it again.

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

## Template 13 — reports-occupancy

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `reports/occupancy` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Occupancy summary` |

```sql
DECLARE
  v_total NUMBER := 0;
  v_occ   NUMBER := 0;
  v_pct   NUMBER := 0;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT COUNT(*) INTO v_total
    FROM NOV_2026_BATCH.QSPARK_PARKING_SLOTS
   WHERE control_status = 'ACTIVE';
  SELECT COUNT(*) INTO v_occ
    FROM NOV_2026_BATCH.QSPARK_V_SLOTS_LIVE s
   WHERE s.status = 'OCCUPIED';
  IF v_total > 0 THEN
    v_pct := ROUND(v_occ * 100 / v_total, 2);
  END IF;
  HTP.p('{"occupancy_percent":' || v_pct ||
        ',"total_slots":' || v_total ||
        ',"occupied":' || v_occ || '}');
END;
```

> Uses `QSPARK_V_SLOTS_LIVE` — run `oracle/07_view_slots_live.sql` first.

---

## Template 14 — reports-revenue

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `reports/revenue` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Revenue collections` |

```sql
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'amount' VALUE rc.amount,
             'type'   VALUE rc.collection_type,
             'date'   VALUE TO_CHAR(rc.created_at, 'YYYY-MM-DD')
           ) ORDER BY rc.created_at
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_REVENUE_COLLECTIONS rc;
  HTP.p(v_json);
END;
```

---

## Template 15 — master-floors

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `master/floors` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Master floors` |

```sql
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'floor_id'   VALUE f.floor_id,
             'floor_code' VALUE f.floor_code,
             'status'     VALUE f.floor_status
           ) ORDER BY f.floor_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_FLOORS f;
  HTP.p(v_json);
END;
```

---

### Notes

- Every source starts with `OWA_UTIL.mime_header('application/json', TRUE)` — `TRUE` is mandatory.
- `reports-occupancy` counts only slots whose live status is `OCCUPIED`, so it no longer double-counts HELD bookings.
