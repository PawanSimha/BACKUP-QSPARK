# QSPARK ORDS API — Templates 7–9 (qr-scan, wallet-balance, wallet-adjust)

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

## Template 7 — qr-scan

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `qr/scan` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `POST` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Scan a booking QR` |

```sql
DECLARE
  v_ref    VARCHAR2(50) := :p_booked_from;
  v_method VARCHAR2(10) := NVL(:p_scan_method, 'QR');
  v_result VARCHAR2(4000);
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  IF v_ref IS NULL THEN
    HTP.p('{"error":"missing booking_reference","code":400}');
    RETURN;
  END IF;
  v_result := QSPARK_API.scan_qr(v_ref, v_method);
  HTP.p(v_result);
END;
```

**Parameter rows (Parameters section, Add Row ×2)**

| Name | Bind Variable | Access Method | Source Type | Data Type |
|---|---|---|---|---|
| `p_booked_from` | `p_booked_from` | `IN` | `URI` | `STRING` |
| `p_scan_method` | `p_scan_method` | `IN` | `URI` | `STRING` |

---

## Template 8 — wallet-balance

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `wallet/:user_id` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `GET` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Wallet balance by user` |

```sql
DECLARE
  v_balance NUMBER;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT wallet_balance INTO v_balance
    FROM NOV_2026_BATCH.QSPARK_USERS
   WHERE user_id = :user_id;
  HTP.p('{"user_id":' || :user_id || ',"balance":' || v_balance || '}');
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    HTP.p('{"error":"user not found","code":404}');
END;
```

> `:user_id` comes from the URI — no parameter row needed.

---

## Template 9 — wallet-adjust

**Create Template**

| Field | Enter |
|---|---|
| URI Template | `wallet-adjust` |
| Priority | `0` |
| HTTP Entity Tag Type | `None` |

**Create Handler**

| Field | Select / Enter |
|---|---|
| Method | `POST` |
| Source Type | `PL/SQL` |
| Pagination Size | *(blank)* |
| Comments | `Adjust wallet balance` |

```sql
DECLARE
  v_user_id NUMBER := TO_NUMBER(:p_user_id);
  v_amount  NUMBER := TO_NUMBER(:p_amount);
  v_desc    VARCHAR2(200) := :p_description;
  v_balance NUMBER;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  IF v_user_id IS NULL OR v_amount IS NULL OR v_amount = 0 THEN
    HTP.p('{"error":"missing parameters","code":400}');
    RETURN;
  END IF;
  QSPARK_API.adjust_wallet(v_user_id, v_amount, v_desc);
  SELECT wallet_balance INTO v_balance
    FROM NOV_2026_BATCH.QSPARK_USERS
   WHERE user_id = v_user_id;
  HTP.p('{"user_id":' || v_user_id || ',"new_balance":' || v_balance || ',"status":"ok"}');
END;
```

**Parameter rows (Parameters section, Add Row ×3)**

| Name | Bind Variable | Access Method | Source Type | Data Type |
|---|---|---|---|---|
| `p_user_id` | `p_user_id` | `IN` | `URI` | `NUMBER` |
| `p_amount` | `p_amount` | `IN` | `URI` | `NUMBER` |
| `p_description` | `p_description` | `IN` | `URI` | `STRING` |

---

### Notes

- Every source starts with `OWA_UTIL.mime_header('application/json', TRUE)` — `TRUE` is mandatory.
- POST handlers read bind variables (`:p_*`), so each `:p_*` needs a matching parameter row or the call fails with `ORA-01008: not all variables bound`.
- `adjust_wallet` writes ledger rows; it must run inside a transaction with the balance update.
