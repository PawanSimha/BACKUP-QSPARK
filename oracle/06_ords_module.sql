-- oracle/06_ords_module.sql
-- SUPERSEDED. Do not run. This defines 17 templates that do not match the real
-- route contracts. Use 08a_ords_helpers.sql, 08b_ords_reads.sql and
-- 08c_ords_writes.sql instead (53 templates, 64 handlers).
--
-- QSPARK ORDS module: qsparking.api.v3
-- Run in APEX REST workshop UI (not SQL Developer PL/SQL)
-- The user already built qsparking.api.v2 via this exact same UI
-- Module name in APEX: qsparking.api.v3 (same shape as v2)
-- Base path: qsparking/api/v3
-- Schema: NOV_2026_BATCH
-- Tables: 11 QSPARK_* tables
-- Handlers: hand-written for money/booking flows
-- Important: every handler source must begin with:
--   OWA_UTIL.mime_header('application/json', TRUE);
-- The TRUE parameter closes the header block so HTP.p writes to the body.

-- STEP A: Create the module
-- In APEX: Shared Components → RESTful Data Services → Modules
--   Name: qsparking.api.v3
--   Base Path: qsparking/api/v3
--   Items Per Page: 0
--   Status: PUBLISHED
--   Comments: QSPARK Phase 1 — Oracle migration

-- STEP B: Create templates (one per URL pattern)
-- Each template needs:
--   Template Name, Pattern, Method (GET/POST/PUT/DELETE),
--   Source Type (plsql), Source (the PL/SQL body)

-- Template: health (GET)
-- Pattern: health
-- Method: GET
-- Source Type: plsql
-- Source:
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.p('{"status":"OK"}');
END;

-- Template: system-status (GET)
-- Pattern: system-status
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_val VARCHAR2(500);
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT setting_value INTO v_val FROM NOV_2026_BATCH.QSPARK_SYSTEM_SETTINGS
    WHERE setting_key = 'SYSTEM_STATUS';
  HTP.print(v_val);
END;

-- Template: slots (GET)
-- Pattern: slots
-- Method: GET
-- Source Type: plsql
-- Source:
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
             'floor_code'      VALUE f.floor_code,
             'floor_status'    VALUE f.floor_status,
             'vehicle_type'    VALUE v.type_name,
             'hourly_rate'     VALUE v.hourly_rate,
             'overstay_rate'   VALUE v.overstay_rate
           ) ORDER BY s.floor_id, s.slot_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_PARKING_SLOTS s
  JOIN NOV_2026_BATCH.QSPARK_VEHICLE_TYPES v ON s.vehicle_type_id = v.vehicle_type_id
  JOIN NOV_2026_BATCH.QSPARK_FLOORS f ON f.floor_id = s.floor_id;
  HTP.print(v_json);
END;

-- Template: slot-by-id (GET)
-- Pattern: slots/:slot_id
-- Method: GET
-- Source Type: plsql
-- Source:
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
           'floor_code'      VALUE f.floor_code,
           'floor_status'    VALUE f.floor_status,
           'vehicle_type'    VALUE v.type_name,
           'hourly_rate'     VALUE v.hourly_rate,
           'overstay_rate'   VALUE v.overstay_rate
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_PARKING_SLOTS s
  JOIN NOV_2026_BATCH.QSPARK_VEHICLE_TYPES v ON s.vehicle_type_id = v.vehicle_type_id
  JOIN NOV_2026_BATCH.QSPARK_FLOORS f ON f.floor_id = s.floor_id
  WHERE s.slot_id = :slot_id;
  HTP.print(v_json);
END;

-- Template: bookings-confirm (POST)
-- Pattern: bookings/confirm
-- Method: POST
-- Source Type: plsql
-- Source:
DECLARE
  v_ref VARCHAR2(50) := NVL(HTF.getAllParams('p_booked_from'),NULL);
  v_result VARCHAR2(4000);
BEGIN
  IF v_ref IS NULL OR v_ref = '' THEN
    OWA_UTIL.mime_header('application/json', TRUE);
    HTP.p('{"error":"missing booking_reference","code":400}');
    RETURN;
  END IF;
  v_result := QSPARK_API.confirm_booking(v_ref);
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.print(v_result);
END;

-- Template: bookings-cancel (POST)
-- Pattern: bookings/cancel
-- Method: POST
-- Source Type: plsql
-- Source:
DECLARE
  v_ref VARCHAR2(50) := NVL(HTF.getAllParams('p_booked_from'),NULL);
  v_result VARCHAR2(4000);
BEGIN
  IF v_ref IS NULL OR v_ref = '' THEN
    OWA_UTIL.mime_header('application/json', TRUE);
    HTP.p('{"error":"missing booking_reference","code":400}');
    RETURN;
  END IF;
  v_result := QSPARK_API.cancel_booking(v_ref);
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.print(v_result);
END;

-- Template: qr-scan (POST)
-- Pattern: qr/scan
-- Method: POST
-- Source Type: plsql
-- Source:
DECLARE
  v_ref VARCHAR2(50) := NVL(HTF.getAllParams('p_booked_from'),NULL);
  v_method VARCHAR2(10) := NVL(HTF.getAllParams('p_scan_method'),'QR');
  v_result VARCHAR2(4000);
BEGIN
  IF v_ref IS NULL OR v_ref = '' THEN
    OWA_UTIL.mime_header('application/json', TRUE);
    HTP.p('{"error":"missing booking_reference","code":400}');
    RETURN;
  END IF;
  v_result := QSPARK_API.scan_qr(v_ref, v_method);
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.print(v_result);
END;

-- Template: wallet-balance (GET)
-- Pattern: wallet/:user_id
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_user_id NUMBER := :user_id;
  v_balance NUMBER;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT wallet_balance INTO v_balance FROM NOV_2026_BATCH.QSPARK_USERS WHERE user_id = v_user_id;
  HTP.p('{"user_id":'||v_user_id||',"balance":'||v_balance||'}');
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    OWA_UTIL.mime_header('application/json', TRUE);
    HTP.p('{"error":"user not found","code":404}');
END;

-- Template: wallet-adjust (POST)
-- Pattern: wallet-adjust
-- Method: POST
-- Source Type: plsql
-- Source:
DECLARE
  v_user_id NUMBER := TO_NUMBER(HTF.getAllParams('p_user_id',0));
  v_amount NUMBER := TO_NUMBER(HTF.getAllParams('p_amount',0));
  v_desc VARCHAR2(200) := NVL(HTF.getAllParams('p_description'),NULL);
  v_result VARCHAR2(4000);
  v_balance NUMBER;
BEGIN
  IF v_user_id = 0 OR v_amount = 0 THEN
    OWA_UTIL.mime_header('application/json', TRUE);
    HTP.p('{"error":"missing parameters","code":400}');
    RETURN;
  END IF;
  QSPARK_API.adjust_wallet(v_user_id, v_amount, v_desc);
  SELECT wallet_balance INTO v_balance FROM NOV_2026_BATCH.QSPARK_USERS WHERE user_id = v_user_id;
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.p('{"user_id":'||v_user_id||',"new_balance":'||v_balance||',"status":"ok"}');
END;

-- Template: admin-floors (GET)
-- Pattern: admin/floors
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'floor_id' VALUE f.floor_id,
             'floor_code' VALUE f.floor_code,
             'status' VALUE f.floor_status
           ) ORDER BY f.floor_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_FLOORS f;
  HTP.print(v_json);
END;

-- Template: admin-users (GET)
-- Pattern: admin/users
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'user_id' VALUE u.user_id,
             'full_name' VALUE u.full_name,
             'phone' VALUE u.phone,
             'balance' VALUE u.wallet_balance
           ) ORDER BY u.user_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_USERS u;
  HTP.print(v_json);
END;

-- Template: admin-rules (GET)
-- Pattern: admin/cancellation-rules
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'rule_id' VALUE r.rule_id,
             'code' VALUE r.rule_code,
             'refund' VALUE r.refund_percent,
             'penalty' VALUE r.penalty_percent
           ) ORDER BY r.rule_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_CANCELLATION_RULES r;
  HTP.print(v_json);
END;

-- Template: reports-occupancy (GET)
-- Pattern: reports/occupancy
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_total NUMBER := 0;
  v_occ NUMBER := 0;
  v_pct NUMBER := 0;
  v_json CLOB;
BEGIN
  SELECT COUNT(*) INTO v_total FROM NOV_2026_BATCH.QSPARK_PARKING_SLOTS WHERE control_status = 'ACTIVE';
  SELECT COUNT(*) INTO v_occ FROM NOV_2026_BATCH.QSPARK_BOOKINGS b
    JOIN NOV_2026_BATCH.QSPARK_PARKING_SLOTS s ON b.slot_id = s.slot_id
    WHERE b.booking_status IN ('HELD','CONFIRMED') AND s.control_status = 'ACTIVE';
  IF v_total > 0 THEN
    v_pct := ROUND(v_occ*100/v_total,2);
  END IF;
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.p('{"occupancy_percent":'||v_pct||',"total_slots":'||v_total||',"occupied":'||v_occ||'}');
END;

-- Template: reports-revenue (GET)
-- Pattern: reports/revenue
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'amount' VALUE rc.amount,
             'type' VALUE rc.collection_type,
             'date' VALUE TO_CHAR(rc.created_at,'YYYY-MM-DD')
           ) ORDER BY rc.created_at
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_REVENUE_COLLECTIONS rc;
  HTP.print(v_json);
END;

-- Template: master-floors (GET)
-- Pattern: master/floors
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'floor_id' VALUE f.floor_id,
             'floor_code' VALUE f.floor_code,
             'status' VALUE f.floor_status
           ) ORDER BY f.floor_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_FLOORS f;
  HTP.print(v_json);
END;

-- Template: master-vehicle-types (GET)
-- Pattern: master/vehicle-types
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'vehicle_type_id' VALUE v.vehicle_type_id,
             'type_name' VALUE v.type_name,
             'rate' VALUE v.hourly_rate,
             'overstay' VALUE v.overstay_rate
           ) ORDER BY v.vehicle_type_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_VEHICLE_TYPES v;
  HTP.print(v_json);
END;

-- Template: master-slots (GET)
-- Pattern: master/slots
-- Method: GET
-- Source Type: plsql
-- Source:
DECLARE
  v_json CLOB;
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
             'slot_id' VALUE s.slot_id,
             'slot_number' VALUE s.slot_number,
             'floor_id' VALUE s.floor_id,
             'status' VALUE s.control_status,
             'vehicle' VALUE v.type_name,
             'rate' VALUE v.hourly_rate,
             'overstay' VALUE v.overstay_rate
           ) ORDER BY s.floor_id, s.slot_id
         ) INTO v_json
  FROM NOV_2026_BATCH.QSPARK_PARKING_SLOTS s
  JOIN NOV_2026_BATCH.QSPARK_VEHICLE_TYPES v ON s.vehicle_type_id = v.vehicle_type_id
  GROUP BY s.slot_id, s.slot_number, s.floor_id, s.control_status, v.type_name, v.hourly_rate, v.overstay_rate;
  HTP.print(v_json);
END;

-- STEP C: Create handlers (map templates to handler names)
-- In APEX: each template gets a handler with a unique name.
-- The handler name must be unique within the module.
-- Handler names (matching the template names for clarity):
--   health, system-status, slots, slot-by-id, booking-confirm, booking-cancel,
--   qr-scan, wallet-balance, wallet-adjust, admin-floors, admin-users,
--   admin-rules, reports-occupancy, reports-revenue, master-floors,
--   master-vehicle-types, master-slots

-- STEP D: Apply and test
-- After creating all templates + handlers, click Apply.
-- Then test each endpoint in the APEX interface or via curl/Postman.

-- QUICK TEST PROMPT:
-- After Step D, run in SQL*Plus/SQL Developer:
-- SET SERVEROUTPUT ON
-- BEGIN
--   DBMS_OUTPUT.PUT_LINE(
--     QSPARK_API.confirm_booking('<a real HELD booking_reference>')
--   );
--   ROLLBACK;
-- END;
-- /
-- This proves the money path works before ORDS is even validated.

-- After successful ORDS module creation + the above smoke test,
-- write src/services/ords.py to proxy Flask → ORDS,
-- then rewire one blueprint (e.g., slots or bookings) to call ORDS.

-- END OF FILE