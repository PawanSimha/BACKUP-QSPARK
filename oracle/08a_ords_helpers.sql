-- oracle/08a_ords_helpers.sql
-- STEP 1 of 3. Run this FIRST, alone. It must finish with no errors.
-- Creates 7 helper objects + 53 templates on module qsparking.api.v3.
-- Safe to re-run: DEFINE_TEMPLATE overwrites by (module, pattern).

SET DEFINE OFF
SET SERVEROUTPUT ON

-- ---------------------------------------------------------------------------
-- Response helpers
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE qspark_json(p_json CLOB) IS
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.p(p_json);
END;
/

-- Overload for short objects. JSON_OBJECT without RETURNING yields VARCHAR2(4000),
-- which is the only form PL/SQL accepts when the object has no FORMAT JSON value.
CREATE OR REPLACE PROCEDURE qspark_json(p_json VARCHAR2) IS
BEGIN
  OWA_UTIL.mime_header('application/json', TRUE);
  HTP.p(p_json);
END;
/

CREATE OR REPLACE PROCEDURE qspark_items(p_arr CLOB) IS
BEGIN
  qspark_json(JSON_OBJECT('items' VALUE NVL(p_arr, '[]') FORMAT JSON RETURNING CLOB));
END;
/

CREATE OR REPLACE PROCEDURE qspark_err(p_code NUMBER, p_msg VARCHAR2) IS
BEGIN
  qspark_json(JSON_OBJECT('code' VALUE p_code, 'error' VALUE p_msg));
END;
/

-- Every response is HTTP 200. The JSON body carries "code"; the Flask proxy
-- maps that to the real HTTP status. ORDS needs no :status juggling.
CREATE OR REPLACE PROCEDURE qspark_audit(p_action VARCHAR2, p_entity VARCHAR2, p_id NUMBER,
                                         p_old VARCHAR2 DEFAULT NULL, p_new VARCHAR2 DEFAULT NULL,
                                         p_actor NUMBER DEFAULT NULL) IS
BEGIN
  INSERT INTO qspark_audit_logs (action_type, entity_type, entity_id, old_values, new_values, created_by)
  VALUES (p_action, p_entity, p_id, p_old, p_new, p_actor);
END;
/

CREATE OR REPLACE FUNCTION qspark_ref(p_prefix VARCHAR2) RETURN VARCHAR2 IS
BEGIN
  RETURN p_prefix || '-' || TO_CHAR(SYSTIMESTAMP, 'YYYYMMDD-HH24MISSFF6') || '-'
         || SUBSTR(RAWTOHEX(SYS_GUID()), 1, 8);
END;
/

CREATE OR REPLACE FUNCTION qspark_num(p VARCHAR2) RETURN NUMBER IS
BEGIN
  RETURN TO_NUMBER(p);
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END;
/

-- ---------------------------------------------------------------------------
-- ORDS definition helpers
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE qspark_tpl(p_pattern VARCHAR2, p_priority PLS_INTEGER DEFAULT 0) IS
BEGIN
  ORDS.DEFINE_TEMPLATE(
    p_module_name => 'qsparking.api.v3',
    p_pattern     => p_pattern,
    p_priority    => p_priority,
    p_etag_type   => 'NONE',
    p_etag_query  => NULL,
    p_comments    => NULL);
END;
/

CREATE OR REPLACE PROCEDURE qspark_h(p_pattern VARCHAR2, p_method VARCHAR2, p_source CLOB) IS
BEGIN
  ORDS.DEFINE_HANDLER(
    p_module_name    => 'qsparking.api.v3',
    p_pattern        => p_pattern,
    p_method         => p_method,
    p_source_type    => 'plsql/block',
    p_items_per_page => 0,
    p_mimes_allowed  => NULL,
    p_comments       => NULL,
    p_source         => p_source);
END;
/

-- ---------------------------------------------------------------------------
-- 53 templates. Priority 1 on the two catch-all bind templates so the literal
-- siblings (/my, /floors, /vehicle-types, /availability) win.
-- ---------------------------------------------------------------------------
BEGIN
  -- slots
  qspark_tpl('api/slots/availability');
  qspark_tpl('api/slots/floors');
  qspark_tpl('api/slots/vehicle-types');
  qspark_tpl('api/slots/:slot_id', 1);
  qspark_tpl('slots');                    -- legacy alias used by src/api/slots.py

  -- bookings
  qspark_tpl('api/bookings/hold');
  qspark_tpl('api/bookings/my');
  qspark_tpl('api/bookings/:ref', 1);
  qspark_tpl('api/bookings/:ref/confirm');
  qspark_tpl('api/bookings/:ref/cancel');
  qspark_tpl('api/bookings/wallet/transactions/me');

  -- qr
  qspark_tpl('api/qr/scan');
  qspark_tpl('api/admin/qr/scan');        -- compatibility alias

  -- admin
  qspark_tpl('api/admin/dashboard');
  qspark_tpl('api/admin/bookings');
  qspark_tpl('api/admin/users');
  qspark_tpl('api/admin/users/:user_id');
  qspark_tpl('api/admin/users/:user_id/wallet');
  qspark_tpl('api/admin/users/:user_id/wallet-adjustments');
  qspark_tpl('api/admin/slots');
  qspark_tpl('api/admin/slots/:slot_id/control-status');
  qspark_tpl('api/admin/floors');
  qspark_tpl('api/admin/vehicle-types');
  qspark_tpl('api/admin/cancellation-rules');
  qspark_tpl('api/admin/cancellation-rules/:rule_id');

  -- admin master (compatibility aliases)
  qspark_tpl('api/admin/master/floors');
  qspark_tpl('api/admin/master/floors/:floor_id');
  qspark_tpl('api/admin/master/slots');
  qspark_tpl('api/admin/master/slots/:slot_id/status');
  qspark_tpl('api/admin/master/users');
  qspark_tpl('api/admin/master/vehicle-types');
  qspark_tpl('api/admin/master/cancellation-rules');

  -- reports
  qspark_tpl('api/admin/reports/occupancy');
  qspark_tpl('api/admin/reports/revenue');
  qspark_tpl('api/admin/reports/revenue-summary');

  -- super admin
  qspark_tpl('api/super-admin/admins');
  qspark_tpl('api/super-admin/admins/:user_id');
  qspark_tpl('api/super-admin/admins/:user_id/status');
  qspark_tpl('api/super-admin/users/:user_id/wallet');
  qspark_tpl('api/super-admin/users/:user_id/wallet-adjustments');
  qspark_tpl('api/super-admin/floors');
  qspark_tpl('api/super-admin/floors/:floor_id');
  qspark_tpl('api/super-admin/floors/:floor_id/slots');
  qspark_tpl('api/super-admin/slots/:slot_id');
  qspark_tpl('api/super-admin/bookings/:ref/cancel');
  qspark_tpl('api/super-admin/analytics/overview');
  qspark_tpl('api/super-admin/analytics/overtime');
  qspark_tpl('api/super-admin/analytics/floor-heatmap');
  qspark_tpl('api/super-admin/analytics/revenue');

  -- system
  qspark_tpl('api/system/status');
  qspark_tpl('api/system/super-admin/session');
  qspark_tpl('api/system/super-admin/system/status');

  -- profile
  qspark_tpl('api/auth/me');

  COMMIT;
END;
/

-- Expected: 53 rows
SELECT COUNT(*) AS template_count
  FROM user_ords_templates t
  JOIN user_ords_modules m ON m.id = t.module_id
 WHERE m.name = 'qsparking.api.v3';
