-- oracle/01_drop_old.sql
-- Drops ALL QSPARK_* objects in the current schema. Other interns' objects are untouched.
-- Tables go to the RECYCLE BIN (no PURGE) -> recoverable via FLASHBACK TABLE.
-- Run as the NOV_2026_BATCH schema owner in SQL Developer.

SET SERVEROUTPUT ON

-- 0. Sanity check
SELECT user AS current_schema FROM dual;

-- 1. Pre-drop inventory (save this output)
SELECT table_name, num_rows FROM user_tables
WHERE table_name LIKE 'QSPARK%' ORDER BY table_name;

-- 2. Drop every QSPARK_* table (CASCADE CONSTRAINTS handles internal FKs)
BEGIN
  FOR t IN (SELECT table_name FROM user_tables WHERE table_name LIKE 'QSPARK%') LOOP
    BEGIN
      EXECUTE IMMEDIATE 'DROP TABLE ' || t.table_name || ' CASCADE CONSTRAINTS';
      DBMS_OUTPUT.PUT_LINE('dropped table: ' || t.table_name);
    EXCEPTION WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE('skip table ' || t.table_name || ': ' || SQLERRM);
    END;
  END LOOP;
END;
/

-- 3. Drop leftover sequences (best effort)
BEGIN
  FOR s IN (SELECT sequence_name FROM user_sequences WHERE sequence_name LIKE 'QSPARK%') LOOP
    BEGIN
      EXECUTE IMMEDIATE 'DROP SEQUENCE ' || s.sequence_name;
      DBMS_OUTPUT.PUT_LINE('dropped sequence: ' || s.sequence_name);
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
  END LOOP;
END;
/

-- 4. Drop leftover packages / triggers / views / procs / funcs (best effort)
BEGIN
  FOR o IN (SELECT object_name, object_type FROM user_objects
            WHERE object_name LIKE 'QSPARK%'
              AND object_type IN ('PACKAGE','PACKAGE BODY','TRIGGER','VIEW','PROCEDURE','FUNCTION')) LOOP
    BEGIN
      EXECUTE IMMEDIATE 'DROP ' || o.object_type || ' ' || o.object_name;
      DBMS_OUTPUT.PUT_LINE('dropped ' || o.object_type || ': ' || o.object_name);
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
  END LOOP;
END;
/

-- 5. Post-drop verification: should return NO rows
SELECT table_name FROM user_tables WHERE table_name LIKE 'QSPARK%' ORDER BY table_name;

-- 6. Recovery path (run only if you need to undo)
-- SELECT object_name, original_name, type, droptime FROM user_recyclebin WHERE original_name LIKE 'QSPARK%';
-- FLASHBACK TABLE "BIN$..." TO BEFORE DROP;
