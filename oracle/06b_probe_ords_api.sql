-- oracle/06b_probe_ords_api.sql
-- Purpose: discover the EXACT ORDS.DEFINE_* signatures + what already exists,
--          before generating 63 handlers instead of 17.
-- Run in SQL Developer connected as NOV_2026_BATCH.
-- Sections 1, 4, 7, 8 may fail with ORA-00942 (ORDS_METADATA not visible to
-- this schema). If they fail, skip them — 2, 3, 9 are the ones that matter.

-- ---------------------------------------------------------------------------
-- 1. ORDS version  (optional)
-- ---------------------------------------------------------------------------
SELECT 'ORDS version' AS what, version AS value
  FROM ords_metadata.ords_version;

-- ---------------------------------------------------------------------------
-- 2. Which schema owns the ORDS package
-- ---------------------------------------------------------------------------
SELECT owner, object_name, procedure_name
  FROM all_procedures
 WHERE object_name = 'ORDS'
   AND procedure_name IN ('DEFINE_MODULE','DEFINE_TEMPLATE','DEFINE_HANDLER',
                          'DELETE_MODULE','DELETE_TEMPLATE','DELETE_HANDLER')
 ORDER BY owner, procedure_name;

-- ---------------------------------------------------------------------------
-- 3. THE IMPORTANT ONE — full argument list. This is what stops PLS-00306.
-- ---------------------------------------------------------------------------
SELECT owner,
       procedure_name,
       position,
       argument_name,
       data_type,
       in_out,
       defaulted
  FROM all_arguments
 WHERE object_name = 'ORDS'
   AND procedure_name IN ('DEFINE_MODULE','DEFINE_TEMPLATE','DEFINE_HANDLER')
 ORDER BY procedure_name, subprogram_id, position;

-- ---------------------------------------------------------------------------
-- 4. Existing module status  (optional)
-- ---------------------------------------------------------------------------
SELECT name, status, uri_prefix
  FROM ords_metadata.ords_modules
 WHERE name = 'qsparking.api.v3';

-- ---------------------------------------------------------------------------
-- 5. How many templates / handlers exist today?  (optional)
--     Tells us whether APEX-created objects are counted consistently.
-- ---------------------------------------------------------------------------
SELECT m.name AS module_name,
       COUNT(DISTINCT t.id)  AS template_count,
       COUNT(h.id)           AS handler_count
  FROM ords_metadata.ords_modules m
  LEFT JOIN ords_metadata.ords_templates t ON t.module_id = m.id
  LEFT JOIN ords_metadata.ords_template_handlers h ON h.template_id = t.id
 WHERE m.name = 'qsparking.api.v3'
 GROUP BY m.name;

-- ---------------------------------------------------------------------------
-- 6. Is this schema ORDS-enabled, and which privileges exist?
--     Decides whether ORDS-level auth is possible at all (63 open endpoints
--     is a security hole otherwise).
-- ---------------------------------------------------------------------------
SELECT id, schema, pattern, status
  FROM ords_metadata.user_ords_schemas
 WHERE schema = 'NOV_2026_BATCH';

SELECT id, name, description
  FROM ords_metadata.ords_privileges
 ORDER BY id;

-- ---------------------------------------------------------------------------
-- 7. Signature probe — template + handler, then delete both.
--    DEFINE_HANDLER is the call that raised PLS-00306 before, so it must be
--    probed, not just DEFINE_TEMPLATE.
-- ---------------------------------------------------------------------------
BEGIN
  ORDS.DEFINE_TEMPLATE(
    p_module_name => 'qsparking.api.v3',
    p_pattern     => 'probe7',
    p_priority    => 0,
    p_etag_type   => 'NONE',
    p_etag_query  => NULL,
    p_comments    => 'signature probe - safe to delete');
END;
/

BEGIN
  ORDS.DEFINE_HANDLER(
    p_module_name    => 'qsparking.api.v3',
    p_pattern        => 'probe7',
    p_method         => 'GET',
    p_source_type    => 'plsql/block',
    p_items_per_page => 0,
    p_mimes_allowed  => NULL,
    p_comments       => 'signature probe',
    p_source         => 'BEGIN OWA_UTIL.mime_header(''application/json'', TRUE); HTP.p(''{"probe":"ok"}''); END;');
END;
/

COMMIT;

-- Test in a browser/Postman AFTER this block:
--   GET .../ords/nov_2026_batch/qsparking/api/v3/probe7
--   200 {"probe":"ok"}   -> scripting works, generate all 63
--   404                  -> template/handler not published; check p_status
--   555                  -> handler ran but source is wrong

-- ---------------------------------------------------------------------------
-- 7b. Does ORDS accept PATCH?  5 of the 30 write handlers need it.
--     If this block raises ORA-20997 / invalid p_method, those 5 routes must
--     become POST in Flask instead of PATCH.
-- ---------------------------------------------------------------------------
BEGIN
  ORDS.DEFINE_TEMPLATE(
    p_module_name => 'qsparking.api.v3',
    p_pattern     => 'probe7b',
    p_priority    => 0,
    p_etag_type   => 'NONE',
    p_etag_query  => NULL,
    p_comments    => 'PATCH probe - safe to delete');
END;
/

BEGIN
  ORDS.DEFINE_HANDLER(
    p_module_name    => 'qsparking.api.v3',
    p_pattern        => 'probe7b',
    p_method         => 'PATCH',
    p_source_type    => 'plsql/block',
    p_items_per_page => 0,
    p_mimes_allowed  => NULL,
    p_comments       => 'PATCH probe',
    p_source         => 'BEGIN OWA_UTIL.mime_header(''application/json'', TRUE); HTP.p(''{"patch":"ok"}''); END;');
END;
/

COMMIT;

-- Test: PATCH .../ords/nov_2026_batch/qsparking/api/v3/probe7b

-- ---------------------------------------------------------------------------
-- 8. Cleanup
-- ---------------------------------------------------------------------------
BEGIN
  ORDS.DELETE_TEMPLATE(
    p_module_name => 'qsparking.api.v3',
    p_pattern     => 'probe7');
END;
/

BEGIN
  ORDS.DELETE_TEMPLATE(
    p_module_name => 'qsparking.api.v3',
    p_pattern     => 'probe7b');
END;
/

COMMIT;

-- ---------------------------------------------------------------------------
-- THE REAL COUNT (from app.url_map, not from markdown/api.md)
-- ---------------------------------------------------------------------------
-- 74 method+path pairs total
--   11 stay in Flask  ->  63 must become ORDS handlers
--   63 handlers live in 52 templates (11 templates carry 2-3 methods each)
--
--   33 READ  (GET)
--   30 WRITE (13 POST, 7 PUT, 5 PATCH, 5 DELETE)
--
-- Templates with more than one method:
--   /api/admin/cancellation-rules          GET POST
--   /api/admin/cancellation-rules/:rule_id PUT DELETE
--   /api/admin/users                       GET POST
--   /api/admin/users/:user_id              GET PUT DELETE
--   /api/super-admin/admins                GET POST
--   /api/super-admin/admins/:user_id       GET PUT DELETE
--   /api/super-admin/floors/:floor_id      PUT DELETE
--   /api/super-admin/slots/:slot_id        PUT DELETE
--   /api/system/super-admin/session        GET PATCH
--
-- NOTE: ORDS patterns use :bind syntax, not Flask converters.
--   /api/admin/users/<int:user_id>  ->  api/admin/users/:user_id
--
-- Stays in Flask (11) - cannot be ORDS:
--   POST auth/login            (verifies password hash)
--   POST auth/setup-admin      (creates password hash)
--   POST auth/logout           (cookie only)
--   POST auth/session/end      (cookie only)
--   GET  auth/me               (cookie only)
--   GET  admin/reports/occupancy-csv      (streams CSV bytes)
--   GET  admin/reports/revenue-csv        (streams CSV bytes)
--   GET  super-admin/reports/occupancy.csv (streams CSV bytes)
--   GET  super-admin/reports/revenue.csv   (streams CSV bytes)
--   POST qr/generate           (returns PNG bytes)
--   GET  super-admin/db-tables/:table_name (dynamic column list)
--
-- The 17 templates in 06_ords_module.sql cover ~27% of the 63 and several
-- contracts do not match (admin/users has no filters there, master-slots
-- returns control_status instead of live status, system-status returns a
-- bare string). 06_ords_module.sql must be regenerated, not extended.
-- ---------------------------------------------------------------------------
