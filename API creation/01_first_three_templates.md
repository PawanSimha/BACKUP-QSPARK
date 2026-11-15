# QSPARK ORDS API — Templates 1–3 (health, system-status, slots)

**Module:** `qsparking.api.v3` · **Base Path:** `qsparking/api/v3/` · **Schema:** `NOV_2026_BATCH`

---

## One-time setup (do this once, before any template)

**Shared Components → RESTful Data Services → Modules → Create**

| Field | Enter |
|---|---|
| Module Name | `qsparking.api.v3` |
| Base Path | `qsparking/api/v3/` |
| HTTP Entity Tag Type | `None` |

> `None` is the ETag choice for **every** template in this project. Options in APEX are `Query`, `Secure Hash`, `None` — pick `None`.

---

## The two screens you will fill for every template

**Screen 1 — Create Template** (3 fields only)

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

> ⚠️ If Source Type stays on `Collection Query`, pasting a `BEGIN … END;` block fails. Always switch to `PL/SQL` first.

---

## Template 1 — health

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `health` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Health check` |

```sql
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.p('{"status":"OK"}');
END;
```

---

## Template 2 — system-status

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `system-status` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `System status setting` |

```sql
DECLARE
  v_val VARCHAR2(500);
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT setting_value INTO v_val
    FROM NOV_2026_BATCH.QSPARK_SYSTEM_SETTINGS
   WHERE setting_key = 'SYSTEM_STATUS';
  HTP.p('{"status":"' || v_val || '"}');
END;
```

---

## Template 3 — slots

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `slots` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `All slots with live status` |

```sql
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
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
           ) ORDER BY s.floor_id, s.slot_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_V_SLOTS_LIVE s;
  HTP.p(v_json);
END;
```

> `slots` reads the view `QSPARK_V_SLOTS_LIVE` — run `oracle/07_view_slots_live.sql` first, or this handler errors.

**Test:** `GET …/ords/nov_2026_batch/qsparking/api/v3/slots` → `200` + 256 objects.

---

### Notes for all files

- `OWA_UTIL.mime_header('application/json', TRUE)` — the `TRUE` is mandatory. `FALSE` writes your JSON into the HTTP headers and the response becomes unparseable.
- `HTP.p(v_json)` where `v_json` is a CLOB works; do not use `HTP.print` on a CLOB in older ORDS builds.
- Patterns with `:name` (`slots/:slot_id`, `wallet/:user_id`) need no parameter rows — ORDS binds them from the URI.
