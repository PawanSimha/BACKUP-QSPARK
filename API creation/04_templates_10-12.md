# QSPARK ORDS API — Templates 10–12 (admin-floors, admin-users, admin-rules)

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

## Template 10 — admin-floors

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `admin/floors` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Floors list` |

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

## Template 11 — admin-users

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `admin/users` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Users list` |

```sql
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'user_id'   VALUE u.user_id,
             'full_name' VALUE u.full_name,
             'phone'     VALUE u.phone,
             'balance'   VALUE u.wallet_balance
           ) ORDER BY u.user_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_USERS u;
  HTP.p(v_json);
END;
```

> Never add `password_hash` to this projection. It must not reach the browser.

---

## Template 12 — admin-rules

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `admin/cancellation-rules` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Cancellation rules` |

```sql
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'rule_id' VALUE r.rule_id,
             'code'    VALUE r.rule_code,
             'refund'  VALUE r.refund_percent,
             'penalty' VALUE r.penalty_percent
           ) ORDER BY r.rule_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_CANCELLATION_RULES r;
  HTP.p(v_json);
END;
```

---

### Notes

- These three handlers are unauthenticated at the ORDS layer. Authorization still lives in Flask (`require_admin` / `require_role`). Do not expose these URLs publicly without that guard.
- Every source starts with `OWA_UTIL.mime_header('application/json', TRUE)` — `TRUE` is mandatory.
