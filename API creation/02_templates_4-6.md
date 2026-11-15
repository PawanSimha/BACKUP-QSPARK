# QSPARK ORDS API — Templates 4–6 (slot-by-id, booking-confirm, booking-cancel)

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
| Method | `GET` or `POST` (per template below) |
| Source Type | **`PL/SQL`** ← change from the default `Collection Query` |
| Pagination Size | *leave blank* |
| Comments | *leave blank, or the text below* |
| Source | paste the code block below |

---

## Template 4 — slot-by-id

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `slots/:slot_id` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `One slot by id` |

```sql
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_OBJECT(
           'slot_id'         VALUE s.slot_id,
           'slot_number'     VALUE s.slot_number,
           'floor_id'        VALUE s.floor_id,
           'vehicle_type_id' VALUE s.vehicle_type_id,
           'control_status'  VALUE s.control_status,
           'status'          VALUE s.status,
           'floor_code'      VALUE s.floor_code,
           'floor_status'    VALUE s.floor_status,
           'vehicle_type'    VALUE s.type_name,
           'hourly_rate'     VALUE s.hourly_rate,
           'overstay_rate'   VALUE s.overstay_rate
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_V_SLOTS_LIVE s
  WHERE s.slot_id = :slot_id;
  HTP.p(v_json);
END;
```

> `:slot_id` comes from the URI — no parameter row needed.

---

## Template 5 — booking-confirm

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `bookings/confirm` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `POST` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Confirm a HELD booking` |

```sql
DECLARE
  v_ref    VARCHAR2(50) := :p_booked_from;
  v_result VARCHAR2(4000);
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  IF v_ref IS NULL THEN
    HTP.p('{"error":"missing booking_reference","code":400}');
    RETURN;
  END IF;
  v_result := QSPARK_API.confirm_booking(v_ref);
  HTP.p(v_result);
END;
```

**Parameter row (required for POST — Parameters section, Add Row)**

| Name | Bind Variable | Access Method | Source Type | Data Type |
|---|---|---|---|---|
| `p_booked_from` | `p_booked_from` | `IN` | `URI` | `STRING` |

---

## Template 6 — booking-cancel

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `bookings/cancel` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `POST` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Cancel a booking` |

```sql
DECLARE
  v_ref    VARCHAR2(50) := :p_booked_from;
  v_result VARCHAR2(4000);
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  IF v_ref IS NULL THEN
    HTP.p('{"error":"missing booking_reference","code":400}');
    RETURN;
  END IF;
  v_result := QSPARK_API.cancel_booking(v_ref);
  HTP.p(v_result);
END;
```

**Parameter row (required for POST)**

| Name | Bind Variable | Access Method | Source Type | Data Type |
|---|---|---|---|---|
| `p_booked_from` | `p_booked_from` | `IN` | `URI` | `STRING` |

> Source Type `URI` means call it as `?p_booked_from=QSP123`. To accept a JSON body instead, use Source Type `REQUEST_BODY` and send `{"p_booked_from":"QSP123"}`.

---

### Notes

- Every source starts with `OWA_UTIL.mime_header('application/json', TRUE)` — the `TRUE` is mandatory.
- `QSPARK_API.confirm_booking` / `cancel_booking` return a JSON string or `ERR|<code>|<msg>`. The error branch does not yet set an HTTP status; it returns 200 with an `ERR|` body. Handle it in Flask.
- `cancel_booking` has a known defect: it does not reverse Super Admin revenue, so reconciliation will not net to zero. Fix in `05_package.sql` before wiring cancel.
