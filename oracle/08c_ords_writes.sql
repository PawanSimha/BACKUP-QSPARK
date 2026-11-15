-- oracle/08c_ords_writes.sql
-- STEP 3 of 3. Run after 08b finished clean. Creates 30 write handlers.
--
-- Request bodies arrive in :body (JSON). Identity arrives as query params
-- ?actor_user_id= and ?actor_role=, injected by the Flask proxy from the
-- Flask session. Passwords are hashed in Flask; these handlers receive
-- password_hash and never see or return a plaintext password.
--
-- Every response is HTTP 200 with a "code" key; Flask maps it to the status.

SET DEFINE OFF
SET SERVEROUTPUT ON

-- ---------------------------------------------------------------------------
-- Shared write helpers
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION qspark_wallet_txn(p_user NUMBER, p_booking NUMBER, p_type VARCHAR2,
  p_dir VARCHAR2, p_amount NUMBER, p_balance NUMBER, p_desc VARCHAR2, p_actor NUMBER)
RETURN NUMBER IS
  v_id NUMBER;
BEGIN
  INSERT INTO qspark_wallet_transactions
    (transaction_reference, user_id, booking_id, transaction_type, direction, amount,
     balance_after, description, created_by)
  VALUES (qspark_ref('TXN'), p_user, p_booking, p_type, p_dir, p_amount, p_balance, p_desc, p_actor)
  RETURNING transaction_id INTO v_id;
  RETURN v_id;
END;
/

CREATE OR REPLACE FUNCTION qspark_sa_user RETURN NUMBER IS
  v NUMBER;
BEGIN
  SELECT MIN(user_id) INTO v FROM qspark_users WHERE role = 'SUPER_ADMIN';
  RETURN v;
END;
/

CREATE OR REPLACE FUNCTION qspark_system_online RETURN NUMBER IS
  v VARCHAR2(500);
BEGIN
  SELECT setting_value INTO v FROM qspark_system_settings WHERE setting_key = 'SYSTEM_STATUS';
  RETURN CASE WHEN v = 'ONLINE' THEN 1 ELSE 0 END;
EXCEPTION WHEN NO_DATA_FOUND THEN RETURN 1;
END;
/

CREATE OR REPLACE PROCEDURE qspark_expire_holds IS
BEGIN
  UPDATE qspark_bookings SET booking_status = 'EXPIRED'
   WHERE booking_status = 'HELD' AND hold_expires_at IS NOT NULL
     AND hold_expires_at < SYSTIMESTAMP;
END;
/

-- ---------------------------------------------------------------------------
-- Booking lifecycle
-- ---------------------------------------------------------------------------
BEGIN
  qspark_h('api/bookings/hold', 'POST', q'!
DECLARE
  v_uid NUMBER := qspark_num(:actor_user_id);
  v_role VARCHAR2(20) := NVL(:actor_role, 'CUSTOMER');
  v_slot NUMBER := qspark_num(JSON_VALUE(:body, '$.slot_id'));
  v_vnum VARCHAR2(20) := UPPER(TRIM(JSON_VALUE(:body, '$.vehicle_number')));
  v_fmt VARCHAR2(10) := NVL(JSON_VALUE(:body, '$.vehicle_format'), 'std1');
  v_booker NUMBER; v_from TIMESTAMP(0); v_until TIMESTAMP(0); v_dur NUMBER;
  v_hr NUMBER; v_or NUMBER; v_est NUMBER; v_slotno VARCHAR2(20); v_vtype VARCHAR2(50);
  v_floor_st VARCHAR2(20); v_ctl VARCHAR2(20); v_status VARCHAR2(20); v_cnt NUMBER;
  v_ref VARCHAR2(50); v_from_s VARCHAR2(20); v_until_s VARCHAR2(20);
BEGIN
  IF v_uid IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_slot IS NULL OR v_vnum IS NULL
     OR JSON_VALUE(:body, '$.booked_from') IS NULL
     OR JSON_VALUE(:body, '$.booked_until') IS NULL THEN
    qspark_err(400, 'slot_id, vehicle_number, booked_from, booked_until required'); RETURN;
  END IF;
  IF NOT REGEXP_LIKE(v_vnum, '^([A-Z]{2} [0-9]{2} [A-Z] [0-9]{4}|[A-Z]{2} [0-9]{2} [A-Z]{2} [0-9]{4}|[A-Z]{2} [0-9]{2} [A-Z]{3} [0-9]{4}|[0-9]{2} BH [0-9]{4} [A-Z]{2})$') THEN
    qspark_err(400, 'invalid vehicle number format'); RETURN;
  END IF;
  IF v_fmt NOT IN ('std1', 'std2', 'std3', 'bhr') THEN
    qspark_err(400, 'Invalid vehicle_format'); RETURN;
  END IF;
  BEGIN
    v_from  := TO_TIMESTAMP(REPLACE(SUBSTR(JSON_VALUE(:body, '$.booked_from'), 1, 19), 'T', ' '), 'YYYY-MM-DD HH24:MI:SS');
    v_until := TO_TIMESTAMP(REPLACE(SUBSTR(JSON_VALUE(:body, '$.booked_until'), 1, 19), 'T', ' '), 'YYYY-MM-DD HH24:MI:SS');
  EXCEPTION WHEN OTHERS THEN qspark_err(400, 'Invalid datetime format'); RETURN;
  END;
  IF EXTRACT(HOUR FROM CAST(v_from AS DATE)) < 5 OR EXTRACT(HOUR FROM CAST(v_until AS DATE)) > 23 THEN
    qspark_err(400, 'Bookings allowed only between 05:00 and 23:00'); RETURN;
  END IF;
  v_dur := ROUND((CAST(v_until AS DATE) - CAST(v_from AS DATE)) * 24, 2);
  IF v_dur <= 0 THEN qspark_err(400, 'End time must be after start time'); RETURN; END IF;
  IF v_dur > 18 THEN qspark_err(400, 'Maximum booking duration is 18 hours'); RETURN; END IF;

  IF qspark_system_online = 0 AND v_role NOT IN ('ADMIN', 'SUPER_ADMIN') THEN
    qspark_err(503, 'System is OFFLINE. Bookings are disabled.'); RETURN;
  END IF;

  v_booker := v_uid;
  IF v_role IN ('ADMIN', 'SUPER_ADMIN') AND JSON_VALUE(:body, '$.user_id') IS NOT NULL THEN
    v_booker := qspark_num(JSON_VALUE(:body, '$.user_id'));
    IF v_booker IS NULL THEN qspark_err(400, 'Invalid user_id'); RETURN; END IF;
  END IF;

  BEGIN
    SELECT account_status INTO v_status FROM qspark_users WHERE user_id = v_booker;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(403, 'Account not active'); RETURN;
  END;
  IF v_status <> 'ACTIVE' THEN qspark_err(403, 'Account not active'); RETURN; END IF;

  BEGIN
    SELECT s.slot_number, vt.type_name, vt.hourly_rate, vt.overstay_rate, f.floor_status, s.control_status
      INTO v_slotno, v_vtype, v_hr, v_or, v_floor_st, v_ctl
      FROM qspark_parking_slots s
      JOIN qspark_floors f ON f.floor_id = s.floor_id
      JOIN qspark_vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
     WHERE s.slot_id = v_slot;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Slot not found'); RETURN;
  END;
  IF v_floor_st <> 'OPEN' THEN qspark_err(409, 'Floor is not open for bookings'); RETURN; END IF;
  IF v_ctl <> 'ACTIVE' THEN qspark_err(409, 'Slot is not available for booking'); RETURN; END IF;

  SELECT COUNT(*) INTO v_cnt FROM qspark_bookings
   WHERE slot_id = v_slot AND booking_status IN ('HELD', 'CONFIRMED')
     AND booked_from < v_until AND booked_until > v_from;
  IF v_cnt > 0 THEN qspark_err(409, 'Slot already has an overlapping booking'); RETURN; END IF;

  SELECT COUNT(*) INTO v_cnt FROM qspark_bookings
   WHERE vehicle_number = v_vnum AND booking_status IN ('HELD', 'CONFIRMED');
  IF v_cnt > 0 THEN qspark_err(409, 'Vehicle already has an active booking'); RETURN; END IF;

  v_est := ROUND(v_dur * v_hr, 2);
  v_ref := qspark_ref('QSP');
  v_from_s  := TO_CHAR(v_from, 'YYYY-MM-DD"T"HH24:MI:SS');
  v_until_s := TO_CHAR(v_until, 'YYYY-MM-DD"T"HH24:MI:SS');

  INSERT INTO qspark_bookings
    (booking_reference, user_id, slot_id, vehicle_format, vehicle_number, booked_from,
     booked_until, hold_expires_at, hourly_rate_applied, overstay_rate_applied,
     estimated_amount, booking_status, created_by)
  VALUES (v_ref, v_booker, v_slot, v_fmt, v_vnum, v_from, v_until,
          SYSTIMESTAMP + INTERVAL '30' MINUTE, v_hr, v_or, v_est, 'HELD', v_uid);

  qspark_json(JSON_OBJECT(
    'booking_reference' VALUE v_ref, 'user_id' VALUE v_booker, 'slot_id' VALUE v_slot,
    'slot_number' VALUE v_slotno, 'vehicle_type' VALUE v_vtype,
    'vehicle_number' VALUE v_vnum, 'booked_from' VALUE v_from_s,
    'booked_until' VALUE v_until_s, 'duration_hours' VALUE v_dur,
    'hourly_rate' VALUE v_hr, 'estimated_amount' VALUE v_est,
    'booking_status' VALUE 'HELD',
    'message' VALUE 'Slot held. Confirm within 30 minutes.'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/bookings/:ref/confirm', 'POST', q'!
DECLARE
  v CLOB;
  v_uid NUMBER := qspark_num(:actor_user_id);
  v_role VARCHAR2(20) := NVL(:actor_role, 'CUSTOMER');
  v_bid NUMBER; v_owner NUMBER; v_slot NUMBER; v_amt NUMBER; v_status VARCHAR2(20);
  v_wallet NUMBER; v_sa NUMBER; v_sa_wallet NUMBER; v_new NUMBER; v_sa_new NUMBER;
  v_cid NUMBER; v_sid NUMBER; v_cnt NUMBER; v_ctl VARCHAR2(20); v_floor VARCHAR2(20);
BEGIN
  IF v_uid IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF qspark_system_online = 0 AND v_role NOT IN ('ADMIN', 'SUPER_ADMIN') THEN
    qspark_err(503, 'System is OFFLINE'); RETURN;
  END IF;
  qspark_expire_holds;

  BEGIN
    SELECT b.booking_id, b.user_id, b.slot_id, b.estimated_amount, b.booking_status, u.wallet_balance
      INTO v_bid, v_owner, v_slot, v_amt, v_status, v_wallet
      FROM qspark_bookings b JOIN qspark_users u ON u.user_id = b.user_id
     WHERE b.booking_reference = :ref;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Booking not found'); RETURN;
  END;

  IF v_owner <> v_uid AND v_role NOT IN ('ADMIN', 'SUPER_ADMIN') THEN
    qspark_err(403, 'Not authorized'); RETURN;
  END IF;
  IF v_status <> 'HELD' THEN qspark_err(409, 'Booking is ' || v_status || ', not HELD'); RETURN; END IF;

  SELECT s.control_status, f.floor_status INTO v_ctl, v_floor
    FROM qspark_parking_slots s JOIN qspark_floors f ON f.floor_id = s.floor_id
   WHERE s.slot_id = v_slot;
  IF v_ctl <> 'ACTIVE' THEN qspark_err(409, 'That slot is no longer available. Choose another slot.'); RETURN; END IF;
  IF v_floor <> 'OPEN' THEN qspark_err(409, 'That floor is closed. Choose another slot.'); RETURN; END IF;

  SELECT COUNT(*) INTO v_cnt FROM qspark_bookings
   WHERE slot_id = v_slot AND booking_status IN ('HELD', 'CONFIRMED')
     AND booking_id <> v_bid
     AND booked_from < (SELECT booked_until FROM qspark_bookings WHERE booking_id = v_bid)
     AND booked_until > (SELECT booked_from FROM qspark_bookings WHERE booking_id = v_bid);
  IF v_cnt > 0 THEN
    qspark_err(409, 'Another booking now overlaps this slot. Choose another slot.'); RETURN;
  END IF;

  IF v_wallet < v_amt THEN
    qspark_json(JSON_OBJECT('code' VALUE 402, 'error' VALUE 'Insufficient wallet balance',
      'wallet_balance' VALUE v_wallet, 'required' VALUE v_amt)); RETURN;
  END IF;

  v_sa := qspark_sa_user;
  IF v_sa IS NULL THEN qspark_err(500, 'Super Admin account missing'); RETURN; END IF;

  v_new := ROUND(v_wallet - v_amt, 2);
  UPDATE qspark_users SET wallet_balance = v_new WHERE user_id = v_owner;
  v_cid := qspark_wallet_txn(v_owner, v_bid, 'BOOKING_DEBIT', 'DEBIT', v_amt, v_new,
                             'Booking ' || :ref, v_uid);

  SELECT wallet_balance INTO v_sa_wallet FROM qspark_users WHERE user_id = v_sa;
  v_sa_new := ROUND(v_sa_wallet + v_amt, 2);
  UPDATE qspark_users SET wallet_balance = v_sa_new WHERE user_id = v_sa;
  v_sid := qspark_wallet_txn(v_sa, v_bid, 'SUPER_ADMIN_REVENUE_CREDIT', 'CREDIT', v_amt, v_sa_new,
                             'Revenue ' || :ref, v_uid);

  INSERT INTO qspark_revenue_collections
    (source_user_id, super_admin_user_id, booking_id, customer_wallet_transaction_id,
     super_admin_wallet_transaction_id, collection_type, amount, created_by)
  VALUES (v_owner, v_sa, v_bid, v_cid, v_sid, 'BOOKING_CHARGE', v_amt, v_uid);

  UPDATE qspark_bookings SET booking_status = 'CONFIRMED', updated_by = v_uid
   WHERE booking_id = v_bid;

  SELECT JSON_OBJECT('booking_reference' VALUE :ref, 'booking_status' VALUE 'CONFIRMED',
    'amount_debited' VALUE v_amt, 'new_wallet_balance' VALUE v_new,
    'qr_generated' VALUE 'true' FORMAT JSON,
    'message' VALUE 'Booking confirmed. QR generated.' RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/bookings/:ref/cancel', 'POST', q'!
DECLARE
  v_uid NUMBER := qspark_num(:actor_user_id);
  v_bid NUMBER; v_owner NUMBER; v_status VARCHAR2(20); v_amt NUMBER; v_from TIMESTAMP(0);
  v_wallet NUMBER; v_hrs NUMBER; v_pct NUMBER := 0; v_pen NUMBER := 0; v_rule NUMBER;
  v_paid NUMBER := 0; v_refund NUMBER := 0; v_penalty NUMBER := 0; v_net NUMBER := 0;
  v_new NUMBER; v_sa NUMBER; v_sa_w NUMBER; v_sa_new NUMBER; v_cid NUMBER; v_sid NUMBER; v_cnt NUMBER;
BEGIN
  IF v_uid IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  BEGIN
    SELECT b.booking_id, b.user_id, b.booking_status, b.estimated_amount, b.booked_from, u.wallet_balance
      INTO v_bid, v_owner, v_status, v_amt, v_from, v_wallet
      FROM qspark_bookings b JOIN qspark_users u ON u.user_id = b.user_id
     WHERE b.booking_reference = :ref;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Booking not found'); RETURN;
  END;
  IF v_owner <> v_uid THEN qspark_err(403, 'Not authorized'); RETURN; END IF;
  IF v_status NOT IN ('HELD', 'CONFIRMED') THEN
    qspark_err(409, 'Only HELD or CONFIRMED bookings can be cancelled'); RETURN;
  END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_booking_events e
   WHERE e.booking_id = v_bid AND e.event_type = 'ENTRY'
     AND NOT EXISTS (SELECT 1 FROM qspark_booking_events x
                      WHERE x.booking_id = v_bid AND x.event_type = 'EXIT');
  IF v_cnt > 0 THEN qspark_err(409, 'Cannot cancel: vehicle has entered and not exited'); RETURN; END IF;

  v_hrs := ROUND((CAST(v_from AS DATE) - CAST(SYSTIMESTAMP AS DATE)) * 24, 4);
  BEGIN
    SELECT rule_id, refund_percent, penalty_percent INTO v_rule, v_pct, v_pen
      FROM (SELECT rule_id, refund_percent, penalty_percent
              FROM qspark_cancellation_rules
             WHERE is_active = 1 AND is_no_show = 0 AND min_hours_before IS NOT NULL
               AND v_hrs >= min_hours_before
               AND (max_hours_before IS NULL OR v_hrs < max_hours_before)
             ORDER BY min_hours_before DESC)
     WHERE ROWNUM = 1;
  EXCEPTION WHEN NO_DATA_FOUND THEN v_rule := NULL; v_pct := 0; v_pen := 0;
  END;

  IF v_status = 'CONFIRMED' THEN v_paid := v_amt; END IF;
  v_refund  := ROUND(v_paid * v_pct / 100, 2);
  v_penalty := ROUND(v_paid * v_pen / 100, 2);
  v_net     := ROUND(v_refund - v_penalty, 2);
  v_new     := ROUND(v_wallet + v_net, 2);

  IF v_net <> 0 THEN
    UPDATE qspark_users SET wallet_balance = v_new WHERE user_id = v_owner;
    v_cid := qspark_wallet_txn(v_owner, v_bid, 'CANCELLATION_REFUND',
               CASE WHEN v_net > 0 THEN 'CREDIT' ELSE 'DEBIT' END, ABS(v_net), v_new,
               'Cancellation ' || :ref, v_uid);
    v_sa := qspark_sa_user;
    IF v_sa IS NOT NULL THEN
      SELECT wallet_balance INTO v_sa_w FROM qspark_users WHERE user_id = v_sa;
      v_sa_new := ROUND(v_sa_w - v_net, 2);
      UPDATE qspark_users SET wallet_balance = v_sa_new WHERE user_id = v_sa;
      v_sid := qspark_wallet_txn(v_sa, v_bid, 'REVENUE_REFUND_REVERSAL',
                 CASE WHEN v_net > 0 THEN 'DEBIT' ELSE 'CREDIT' END, ABS(v_net), v_sa_new,
                 'Refund reversal ' || :ref, v_uid);
      INSERT INTO qspark_revenue_collections
        (source_user_id, super_admin_user_id, booking_id, customer_wallet_transaction_id,
         super_admin_wallet_transaction_id, collection_type, amount, created_by)
      VALUES (v_owner, v_sa, v_bid, v_cid, v_sid, 'REFUND_REVERSAL', ABS(v_net), v_uid);
    END IF;
  ELSE
    v_new := v_wallet;
  END IF;

  UPDATE qspark_bookings SET booking_status = 'CANCELLED',
         applied_cancellation_rule_id = v_rule, updated_by = v_uid
   WHERE booking_id = v_bid;
  qspark_audit('BOOKING_CANCELLED', 'bookings', v_bid, v_status, 'CANCELLED', v_uid);

  qspark_json(JSON_OBJECT('booking_reference' VALUE :ref, 'booking_status' VALUE 'CANCELLED',
    'refund_amount' VALUE v_refund, 'penalty_amount' VALUE v_penalty,
    'net_credit' VALUE v_net, 'new_wallet_balance' VALUE v_new,
    'message' VALUE 'Booking cancelled.'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/qr/scan', 'POST', q'!
DECLARE
  v_uid NUMBER := qspark_num(:actor_user_id);
  v_role VARCHAR2(20) := NVL(:actor_role, 'CUSTOMER');
  v_ref VARCHAR2(50) := JSON_VALUE(:body, '$.booking_reference');
  v_method VARCHAR2(10) := UPPER(NVL(JSON_VALUE(:body, '$.scan_method'), 'QR'));
  v_bid NUMBER; v_owner NUMBER; v_slot NUMBER; v_status VARCHAR2(20);
  v_slotno VARCHAR2(20); v_vnum VARCHAR2(20); v_name VARCHAR2(100);
  v_or NUMBER; v_until TIMESTAMP(0); v_wallet NUMBER; v_cnt NUMBER;
  v_hours NUMBER := 0; v_amt NUMBER := 0; v_new NUMBER; v_sa NUMBER; v_sa_w NUMBER;
  v_sa_new NUMBER; v_cid NUMBER; v_sid NUMBER; v_now TIMESTAMP(0) := CAST(SYSTIMESTAMP AS TIMESTAMP(0));
  v_exit TIMESTAMP(0);
BEGIN
  IF v_uid IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_ref IS NULL THEN qspark_err(400, 'booking_reference required'); RETURN; END IF;
  IF v_method NOT IN ('QR', 'MANUAL') THEN v_method := 'QR'; END IF;

  BEGIN
    SELECT b.booking_id, b.user_id, b.slot_id, b.booking_status, s.slot_number,
           b.vehicle_number, u.full_name, vt.overstay_rate, b.booked_until, u.wallet_balance
      INTO v_bid, v_owner, v_slot, v_status, v_slotno, v_vnum, v_name, v_or, v_until, v_wallet
      FROM qspark_bookings b
      JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
      JOIN qspark_vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
      JOIN qspark_users u ON u.user_id = b.user_id
     WHERE b.booking_reference = v_ref;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Booking not found'); RETURN;
  END;

  IF v_role NOT IN ('ADMIN', 'SUPER_ADMIN') AND v_owner <> v_uid THEN
    qspark_err(403, 'Not authorized to scan this booking'); RETURN;
  END IF;

  SELECT COUNT(*) INTO v_cnt FROM qspark_booking_events WHERE booking_id = v_bid AND event_type = 'ENTRY';
  IF v_cnt = 0 THEN
    IF v_status <> 'CONFIRMED' THEN qspark_err(409, 'Booking must be CONFIRMED to enter'); RETURN; END IF;
    INSERT INTO qspark_booking_events (booking_id, event_type, scan_method, created_by)
    VALUES (v_bid, 'ENTRY', v_method, v_uid);
    qspark_json(JSON_OBJECT('action' VALUE 'ENTRY', 'booking_reference' VALUE v_ref,
      'user_name' VALUE v_name, 'vehicle_number' VALUE v_vnum, 'slot_number' VALUE v_slotno,
      'entry_time' VALUE TO_CHAR(v_now, 'YYYY-MM-DD"T"HH24:MI:SS'),
      'message' VALUE 'Entry granted'));
    RETURN;
  END IF;

  BEGIN
    SELECT MIN(created_at) INTO v_exit FROM qspark_booking_events
     WHERE booking_id = v_bid AND event_type = 'EXIT';
  EXCEPTION WHEN OTHERS THEN v_exit := NULL;
  END;
  IF v_exit IS NOT NULL THEN
    qspark_json(JSON_OBJECT('code' VALUE 409, 'error' VALUE 'Vehicle already exited',
      'exit_time' VALUE v_exit)); RETURN;
  END IF;

  IF v_now > v_until THEN
    v_hours := CEIL((CAST(v_now AS DATE) - CAST(v_until AS DATE)) * 48) / 2;
    v_amt := ROUND(v_hours * v_or, 2);
  END IF;

  IF v_amt > 0 THEN
    IF v_wallet < v_amt THEN
      qspark_json(JSON_OBJECT('code' VALUE 409, 'action' VALUE 'EXIT_BLOCKED',
        'booking_reference' VALUE v_ref, 'overstay_hours' VALUE v_hours,
        'overstay_amount' VALUE v_amt, 'wallet_balance' VALUE v_wallet,
        'message' VALUE 'Overtime due Rs ' || v_amt || '. Pay to unblock exit.'));
      RETURN;
    END IF;
    v_new := ROUND(v_wallet - v_amt, 2);
    UPDATE qspark_users SET wallet_balance = v_new WHERE user_id = v_owner;
    v_cid := qspark_wallet_txn(v_owner, v_bid, 'OVERTIME_DEBIT', 'DEBIT', v_amt, v_new,
                               'Overstay ' || v_ref, v_uid);
    v_sa := qspark_sa_user;
    IF v_sa IS NOT NULL THEN
      SELECT wallet_balance INTO v_sa_w FROM qspark_users WHERE user_id = v_sa;
      v_sa_new := ROUND(v_sa_w + v_amt, 2);
      UPDATE qspark_users SET wallet_balance = v_sa_new WHERE user_id = v_sa;
      v_sid := qspark_wallet_txn(v_sa, v_bid, 'SUPER_ADMIN_REVENUE_CREDIT', 'CREDIT', v_amt,
                                 v_sa_new, 'Overstay revenue ' || v_ref, v_uid);
      INSERT INTO qspark_revenue_collections
        (source_user_id, super_admin_user_id, booking_id, customer_wallet_transaction_id,
         super_admin_wallet_transaction_id, collection_type, amount, created_by)
      VALUES (v_owner, v_sa, v_bid, v_cid, v_sid, 'OVERTIME_CHARGE', v_amt, v_uid);
    END IF;
  END IF;

  INSERT INTO qspark_booking_events (booking_id, event_type, scan_method, event_note, created_by)
  VALUES (v_bid, 'EXIT', v_method, 'overstay_hours=' || v_hours || ', overstay_amount=' || v_amt, v_uid);
  UPDATE qspark_parking_slots SET control_status = 'ACTIVE' WHERE slot_id = v_slot;
  UPDATE qspark_bookings SET booking_status = 'COMPLETED', updated_by = v_uid WHERE booking_id = v_bid;

  qspark_json(JSON_OBJECT('action' VALUE 'EXIT', 'booking_reference' VALUE v_ref,
    'user_name' VALUE v_name, 'vehicle_number' VALUE v_vnum, 'slot_number' VALUE v_slotno,
    'exit_time' VALUE TO_CHAR(v_now, 'YYYY-MM-DD"T"HH24:MI:SS'),
    'overstay_hours' VALUE v_hours, 'overstay_amount' VALUE v_amt,
    'message' VALUE 'Exit granted'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  -- compatibility alias: same handler source
  qspark_h('api/admin/qr/scan', 'POST', q'!
DECLARE
  v_uid NUMBER := qspark_num(:actor_user_id);
  v_role VARCHAR2(20) := NVL(:actor_role, 'CUSTOMER');
  v_ref VARCHAR2(50) := JSON_VALUE(:body, '$.booking_reference');
  v_method VARCHAR2(10) := UPPER(NVL(JSON_VALUE(:body, '$.scan_method'), 'QR'));
  v_bid NUMBER; v_owner NUMBER; v_slot NUMBER; v_status VARCHAR2(20);
  v_slotno VARCHAR2(20); v_vnum VARCHAR2(20); v_name VARCHAR2(100);
  v_or NUMBER; v_until TIMESTAMP(0); v_wallet NUMBER; v_cnt NUMBER;
  v_hours NUMBER := 0; v_amt NUMBER := 0; v_new NUMBER; v_sa NUMBER; v_sa_w NUMBER;
  v_sa_new NUMBER; v_cid NUMBER; v_sid NUMBER; v_now TIMESTAMP(0) := CAST(SYSTIMESTAMP AS TIMESTAMP(0));
  v_exit TIMESTAMP(0);
BEGIN
  IF v_uid IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_ref IS NULL THEN qspark_err(400, 'booking_reference required'); RETURN; END IF;
  IF v_method NOT IN ('QR', 'MANUAL') THEN v_method := 'QR'; END IF;
  BEGIN
    SELECT b.booking_id, b.user_id, b.slot_id, b.booking_status, s.slot_number,
           b.vehicle_number, u.full_name, vt.overstay_rate, b.booked_until, u.wallet_balance
      INTO v_bid, v_owner, v_slot, v_status, v_slotno, v_vnum, v_name, v_or, v_until, v_wallet
      FROM qspark_bookings b
      JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
      JOIN qspark_vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
      JOIN qspark_users u ON u.user_id = b.user_id
     WHERE b.booking_reference = v_ref;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Booking not found'); RETURN;
  END;
  IF v_role NOT IN ('ADMIN', 'SUPER_ADMIN') AND v_owner <> v_uid THEN
    qspark_err(403, 'Not authorized to scan this booking'); RETURN;
  END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_booking_events WHERE booking_id = v_bid AND event_type = 'ENTRY';
  IF v_cnt = 0 THEN
    IF v_status <> 'CONFIRMED' THEN qspark_err(409, 'Booking must be CONFIRMED to enter'); RETURN; END IF;
    INSERT INTO qspark_booking_events (booking_id, event_type, scan_method, created_by)
    VALUES (v_bid, 'ENTRY', v_method, v_uid);
    qspark_json(JSON_OBJECT('action' VALUE 'ENTRY', 'booking_reference' VALUE v_ref,
      'user_name' VALUE v_name, 'vehicle_number' VALUE v_vnum, 'slot_number' VALUE v_slotno,
      'entry_time' VALUE TO_CHAR(v_now, 'YYYY-MM-DD"T"HH24:MI:SS'),
      'message' VALUE 'Entry granted'));
    RETURN;
  END IF;
  BEGIN
    SELECT MIN(created_at) INTO v_exit FROM qspark_booking_events
     WHERE booking_id = v_bid AND event_type = 'EXIT';
  EXCEPTION WHEN OTHERS THEN v_exit := NULL;
  END;
  IF v_exit IS NOT NULL THEN
    qspark_json(JSON_OBJECT('code' VALUE 409, 'error' VALUE 'Vehicle already exited',
      'exit_time' VALUE v_exit)); RETURN;
  END IF;
  IF v_now > v_until THEN
    v_hours := CEIL((CAST(v_now AS DATE) - CAST(v_until AS DATE)) * 48) / 2;
    v_amt := ROUND(v_hours * v_or, 2);
  END IF;
  IF v_amt > 0 THEN
    IF v_wallet < v_amt THEN
      qspark_json(JSON_OBJECT('code' VALUE 409, 'action' VALUE 'EXIT_BLOCKED',
        'booking_reference' VALUE v_ref, 'overstay_hours' VALUE v_hours,
        'overstay_amount' VALUE v_amt, 'wallet_balance' VALUE v_wallet,
        'message' VALUE 'Overtime due Rs ' || v_amt || '. Pay to unblock exit.'));
      RETURN;
    END IF;
    v_new := ROUND(v_wallet - v_amt, 2);
    UPDATE qspark_users SET wallet_balance = v_new WHERE user_id = v_owner;
    v_cid := qspark_wallet_txn(v_owner, v_bid, 'OVERTIME_DEBIT', 'DEBIT', v_amt, v_new,
                               'Overstay ' || v_ref, v_uid);
    v_sa := qspark_sa_user;
    IF v_sa IS NOT NULL THEN
      SELECT wallet_balance INTO v_sa_w FROM qspark_users WHERE user_id = v_sa;
      v_sa_new := ROUND(v_sa_w + v_amt, 2);
      UPDATE qspark_users SET wallet_balance = v_sa_new WHERE user_id = v_sa;
      v_sid := qspark_wallet_txn(v_sa, v_bid, 'SUPER_ADMIN_REVENUE_CREDIT', 'CREDIT', v_amt,
                                 v_sa_new, 'Overstay revenue ' || v_ref, v_uid);
      INSERT INTO qspark_revenue_collections
        (source_user_id, super_admin_user_id, booking_id, customer_wallet_transaction_id,
         super_admin_wallet_transaction_id, collection_type, amount, created_by)
      VALUES (v_owner, v_sa, v_bid, v_cid, v_sid, 'OVERTIME_CHARGE', v_amt, v_uid);
    END IF;
  END IF;
  INSERT INTO qspark_booking_events (booking_id, event_type, scan_method, event_note, created_by)
  VALUES (v_bid, 'EXIT', v_method, 'overstay_hours=' || v_hours || ', overstay_amount=' || v_amt, v_uid);
  UPDATE qspark_parking_slots SET control_status = 'ACTIVE' WHERE slot_id = v_slot;
  UPDATE qspark_bookings SET booking_status = 'COMPLETED', updated_by = v_uid WHERE booking_id = v_bid;
  qspark_json(JSON_OBJECT('action' VALUE 'EXIT', 'booking_reference' VALUE v_ref,
    'user_name' VALUE v_name, 'vehicle_number' VALUE v_vnum, 'slot_number' VALUE v_slotno,
    'exit_time' VALUE TO_CHAR(v_now, 'YYYY-MM-DD"T"HH24:MI:SS'),
    'overstay_hours' VALUE v_hours, 'overstay_amount' VALUE v_amt,
    'message' VALUE 'Exit granted'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  COMMIT;
END;
/

-- ---------------------------------------------------------------------------
-- Admin: users, wallet, slots, rules
-- ---------------------------------------------------------------------------
BEGIN
  qspark_h('api/admin/users', 'POST', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_name VARCHAR2(100) := TRIM(JSON_VALUE(:body, '$.full_name'));
  v_email VARCHAR2(255) := LOWER(TRIM(JSON_VALUE(:body, '$.email')));
  v_phone VARCHAR2(20) := TRIM(JSON_VALUE(:body, '$.phone'));
  v_gender VARCHAR2(20) := JSON_VALUE(:body, '$.gender');
  v_company VARCHAR2(200) := JSON_VALUE(:body, '$.company_name');
  v_user VARCHAR2(100) := LOWER(TRIM(JSON_VALUE(:body, '$.username')));
  v_hash VARCHAR2(256) := JSON_VALUE(:body, '$.password_hash');
  v_id NUMBER; v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_name IS NULL OR v_phone IS NULL OR v_user IS NULL OR v_hash IS NULL THEN
    qspark_err(400, 'full_name, phone, username and password_hash are required'); RETURN;
  END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_users WHERE email = v_email;
  IF v_cnt > 0 THEN qspark_err(409, 'Email already registered'); RETURN; END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_users WHERE username = v_user;
  IF v_cnt > 0 THEN qspark_err(409, 'Username already taken'); RETURN; END IF;

  INSERT INTO qspark_users (admin_id, full_name, email, phone, gender, company_name, username,
                            password_hash, role, wallet_balance, account_status, created_by)
  VALUES (NULL, v_name, v_email, v_phone, v_gender, v_company, v_user, v_hash, 'CUSTOMER',
          1000, 'PENDING', v_actor)
  RETURNING user_id INTO v_id;

  qspark_audit('CREATE_USER', 'users', v_id, NULL,
               '{"username":"' || v_user || '"}', v_actor);
  qspark_json(JSON_OBJECT('user_id' VALUE v_id, 'username' VALUE v_user,
    'message' VALUE 'Customer created'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/users/:user_id', 'PUT', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:user_id);
  v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_users WHERE user_id = v_id;
  IF v_cnt = 0 THEN qspark_err(404, 'User not found'); RETURN; END IF;

  UPDATE qspark_users SET
    full_name      = NVL(TRIM(JSON_VALUE(:body, '$.full_name')), full_name),
    email          = NVL(LOWER(TRIM(JSON_VALUE(:body, '$.email'))), email),
    phone          = NVL(TRIM(JSON_VALUE(:body, '$.phone')), phone),
    gender         = NVL(JSON_VALUE(:body, '$.gender'), gender),
    company_name   = NVL(JSON_VALUE(:body, '$.company_name'), company_name),
    account_status = NVL(JSON_VALUE(:body, '$.account_status'), account_status),
    updated_by     = v_actor
   WHERE user_id = v_id;

  qspark_audit('UPDATE_USER', 'users', v_id, NULL, :body, v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'User updated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/users/:user_id', 'DELETE', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:user_id);
  v_role VARCHAR2(20);
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  BEGIN
    SELECT role INTO v_role FROM qspark_users WHERE user_id = v_id;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'User not found'); RETURN;
  END;
  IF v_role = 'SUPER_ADMIN' THEN qspark_err(403, 'Cannot delete a Super Admin'); RETURN; END IF;
  UPDATE qspark_users SET account_status = 'DELETED', updated_by = v_actor WHERE user_id = v_id;
  qspark_audit('DELETE_USER', 'users', v_id, v_role, 'DELETED', v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'User deleted'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/users/:user_id/wallet-adjustments', 'POST', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:user_id);
  v_amt NUMBER := qspark_num(JSON_VALUE(:body, '$.amount'));
  v_note VARCHAR2(200) := JSON_VALUE(:body, '$.description');
  v_before NUMBER; v_after NUMBER; v_dir VARCHAR2(10); v_dummy NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_amt IS NULL OR v_amt = 0 THEN qspark_err(400, 'amount must be a non-zero number'); RETURN; END IF;
  BEGIN
    SELECT wallet_balance INTO v_before FROM qspark_users WHERE user_id = v_id FOR UPDATE;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'User not found'); RETURN;
  END;
  v_after := ROUND(v_before + v_amt, 2);
  IF v_after < 0 THEN qspark_err(409, 'Adjustment would make the wallet negative'); RETURN; END IF;
  v_dir := CASE WHEN v_amt > 0 THEN 'CREDIT' ELSE 'DEBIT' END;

  UPDATE qspark_users SET wallet_balance = v_after, updated_by = v_actor WHERE user_id = v_id;
  v_dummy := qspark_wallet_txn(v_id, NULL, 'ADMIN_ADJUSTMENT', v_dir, ABS(v_amt), v_after,
                            NVL(v_note, 'Admin adjustment'), v_actor);
  qspark_audit('WALLET_ADJUSTMENT', 'users', v_id, TO_CHAR(v_before), TO_CHAR(v_after), v_actor);

  qspark_json(JSON_OBJECT('user_id' VALUE v_id, 'adjustment' VALUE v_amt,
    'previous_balance' VALUE v_before, 'new_balance' VALUE v_after));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/slots/:slot_id/control-status', 'PATCH', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:slot_id);
  v_st VARCHAR2(20) := UPPER(JSON_VALUE(:body, '$.control_status'));
  v_old VARCHAR2(20); v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_st NOT IN ('ACTIVE', 'MAINTENANCE', 'ADMIN_RESERVED', 'INACTIVE') THEN
    qspark_err(400, 'control_status must be ACTIVE, MAINTENANCE, ADMIN_RESERVED or INACTIVE'); RETURN;
  END IF;
  BEGIN
    SELECT control_status INTO v_old FROM qspark_parking_slots WHERE slot_id = v_id FOR UPDATE;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Slot not found'); RETURN;
  END;
  IF v_st IN ('MAINTENANCE', 'INACTIVE') THEN
    SELECT COUNT(*) INTO v_cnt FROM qspark_bookings
     WHERE slot_id = v_id AND booking_status IN ('HELD', 'CONFIRMED');
    IF v_cnt > 0 THEN qspark_err(409, 'Slot has an active booking'); RETURN; END IF;
  END IF;
  UPDATE qspark_parking_slots SET control_status = v_st, updated_by = v_actor WHERE slot_id = v_id;
  qspark_audit('SLOT_STATUS', 'parking_slots', v_id, v_old, v_st, v_actor);
  qspark_json(JSON_OBJECT('slot_id' VALUE v_id, 'control_status' VALUE v_st));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/master/floors/:floor_id', 'PUT', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:floor_id);
  v_st VARCHAR2(20) := UPPER(JSON_VALUE(:body, '$.floor_status'));
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_st NOT IN ('OPEN', 'CLOSED', 'INACTIVE') THEN
    qspark_err(400, 'floor_status must be OPEN, CLOSED or INACTIVE'); RETURN;
  END IF;
  UPDATE qspark_floors SET floor_status = v_st, updated_by = v_actor WHERE floor_id = v_id;
  IF SQL%ROWCOUNT = 0 THEN qspark_err(404, 'Floor not found'); RETURN; END IF;
  qspark_audit('FLOOR_STATUS', 'floors', v_id, NULL, v_st, v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Floor updated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/master/slots/:slot_id/status', 'PUT', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:slot_id);
  v_st VARCHAR2(20) := UPPER(JSON_VALUE(:body, '$.control_status'));
  v_old VARCHAR2(20); v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_st NOT IN ('ACTIVE', 'MAINTENANCE', 'ADMIN_RESERVED', 'INACTIVE') THEN
    qspark_err(400, 'control_status must be ACTIVE, MAINTENANCE, ADMIN_RESERVED or INACTIVE'); RETURN;
  END IF;
  BEGIN
    SELECT control_status INTO v_old FROM qspark_parking_slots WHERE slot_id = v_id FOR UPDATE;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Slot not found'); RETURN;
  END;
  IF v_st IN ('MAINTENANCE', 'INACTIVE') THEN
    SELECT COUNT(*) INTO v_cnt FROM qspark_bookings
     WHERE slot_id = v_id AND booking_status IN ('HELD', 'CONFIRMED');
    IF v_cnt > 0 THEN qspark_err(409, 'Slot has an active booking'); RETURN; END IF;
  END IF;
  UPDATE qspark_parking_slots SET control_status = v_st, updated_by = v_actor WHERE slot_id = v_id;
  qspark_audit('SLOT_STATUS', 'parking_slots', v_id, v_old, v_st, v_actor);
  qspark_json(JSON_OBJECT('slot_id' VALUE v_id, 'control_status' VALUE v_st));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/cancellation-rules', 'POST', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  INSERT INTO qspark_cancellation_rules
    (rule_code, rule_name, min_hours_before, max_hours_before, is_no_show,
     refund_percent, penalty_percent, description, is_active, created_by)
  VALUES (UPPER(TRIM(JSON_VALUE(:body, '$.rule_code'))),
          TRIM(JSON_VALUE(:body, '$.rule_name')),
          qspark_num(JSON_VALUE(:body, '$.min_hours_before')),
          qspark_num(JSON_VALUE(:body, '$.max_hours_before')),
          NVL(qspark_num(JSON_VALUE(:body, '$.is_no_show')), 0),
          NVL(qspark_num(JSON_VALUE(:body, '$.refund_percent')), 0),
          NVL(qspark_num(JSON_VALUE(:body, '$.penalty_percent')), 0),
          JSON_VALUE(:body, '$.description'),
          NVL(qspark_num(JSON_VALUE(:body, '$.is_active')), 1), v_actor)
  RETURNING rule_id INTO v_id;
  qspark_audit('CREATE_RULE', 'cancellation_rules', v_id, NULL, :body, v_actor);
  qspark_json(JSON_OBJECT('rule_id' VALUE v_id, 'message' VALUE 'Rule created'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/cancellation-rules/:rule_id', 'PUT', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:rule_id);
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  UPDATE qspark_cancellation_rules SET
    rule_name        = NVL(TRIM(JSON_VALUE(:body, '$.rule_name')), rule_name),
    min_hours_before = NVL(qspark_num(JSON_VALUE(:body, '$.min_hours_before')), min_hours_before),
    max_hours_before = NVL(qspark_num(JSON_VALUE(:body, '$.max_hours_before')), max_hours_before),
    is_no_show       = NVL(qspark_num(JSON_VALUE(:body, '$.is_no_show')), is_no_show),
    refund_percent   = NVL(qspark_num(JSON_VALUE(:body, '$.refund_percent')), refund_percent),
    penalty_percent  = NVL(qspark_num(JSON_VALUE(:body, '$.penalty_percent')), penalty_percent),
    description      = NVL(JSON_VALUE(:body, '$.description'), description),
    is_active        = NVL(qspark_num(JSON_VALUE(:body, '$.is_active')), is_active),
    updated_by       = v_actor
   WHERE rule_id = v_id;
  IF SQL%ROWCOUNT = 0 THEN qspark_err(404, 'Rule not found'); RETURN; END IF;
  qspark_audit('UPDATE_RULE', 'cancellation_rules', v_id, NULL, :body, v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Rule updated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/admin/cancellation-rules/:rule_id', 'DELETE', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:rule_id);
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  UPDATE qspark_cancellation_rules SET is_active = 0, updated_by = v_actor WHERE rule_id = v_id;
  IF SQL%ROWCOUNT = 0 THEN qspark_err(404, 'Rule not found'); RETURN; END IF;
  qspark_audit('DELETE_RULE', 'cancellation_rules', v_id, '1', '0', v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Rule deactivated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  COMMIT;
END;
/

-- ---------------------------------------------------------------------------
-- Super Admin: admins, wallet, floors, slots, bookings
-- ---------------------------------------------------------------------------
BEGIN
  qspark_h('api/super-admin/admins', 'POST', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_name VARCHAR2(100) := TRIM(JSON_VALUE(:body, '$.full_name'));
  v_email VARCHAR2(255) := LOWER(TRIM(JSON_VALUE(:body, '$.email')));
  v_phone VARCHAR2(20) := TRIM(JSON_VALUE(:body, '$.phone'));
  v_user VARCHAR2(100) := LOWER(TRIM(JSON_VALUE(:body, '$.username')));
  v_hash VARCHAR2(256) := JSON_VALUE(:body, '$.password_hash');
  v_aid VARCHAR2(50); v_id NUMBER; v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_name IS NULL OR v_phone IS NULL OR v_user IS NULL OR v_hash IS NULL THEN
    qspark_err(400, 'full_name, phone, username and password_hash are required'); RETURN;
  END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_users WHERE username = v_user OR email = v_email;
  IF v_cnt > 0 THEN qspark_err(409, 'Username or email already exists'); RETURN; END IF;

  v_aid := 'ADM' || TO_CHAR(SYSTIMESTAMP, 'YYMMDDHH24MISSFF3');
  INSERT INTO qspark_users (admin_id, full_name, email, phone, gender, company_name, username,
                            password_hash, role, wallet_balance, account_status, created_by)
  VALUES (v_aid, v_name, v_email, v_phone, JSON_VALUE(:body, '$.gender'),
          JSON_VALUE(:body, '$.company_name'), v_user, v_hash, 'ADMIN', 1000, 'ACTIVE', v_actor)
  RETURNING user_id INTO v_id;

  qspark_audit('CREATE_ADMIN', 'users', v_id, NULL, '{"admin_id":"' || v_aid || '"}', v_actor);
  qspark_json(JSON_OBJECT('user_id' VALUE v_id, 'admin_id' VALUE v_aid,
    'message' VALUE 'Admin created'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/admins/:user_id', 'PUT', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:user_id);
  v_role VARCHAR2(20);
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  BEGIN
    SELECT role INTO v_role FROM qspark_users WHERE user_id = v_id;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Admin not found'); RETURN;
  END;
  IF v_role <> 'ADMIN' THEN qspark_err(403, 'Only ADMIN accounts can be edited'); RETURN; END IF;
  UPDATE qspark_users SET
    full_name    = NVL(TRIM(JSON_VALUE(:body, '$.full_name')), full_name),
    email        = NVL(LOWER(TRIM(JSON_VALUE(:body, '$.email'))), email),
    phone        = NVL(TRIM(JSON_VALUE(:body, '$.phone')), phone),
    gender       = NVL(JSON_VALUE(:body, '$.gender'), gender),
    company_name = NVL(JSON_VALUE(:body, '$.company_name'), company_name),
    updated_by   = v_actor
   WHERE user_id = v_id;
  qspark_audit('UPDATE_ADMIN', 'users', v_id, NULL, :body, v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Admin updated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/admins/:user_id', 'DELETE', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:user_id);
  v_role VARCHAR2(20);
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  BEGIN
    SELECT role INTO v_role FROM qspark_users WHERE user_id = v_id;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Admin not found'); RETURN;
  END;
  IF v_role <> 'ADMIN' THEN qspark_err(403, 'Only ADMIN accounts can be deleted'); RETURN; END IF;
  UPDATE qspark_users SET account_status = 'DELETED', updated_by = v_actor WHERE user_id = v_id;
  qspark_audit('DELETE_ADMIN', 'users', v_id, v_role, 'DELETED', v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Admin deleted'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/admins/:user_id/status', 'PATCH', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:user_id);
  v_st VARCHAR2(20) := UPPER(JSON_VALUE(:body, '$.account_status'));
  v_role VARCHAR2(20);
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_st NOT IN ('ACTIVE', 'PENDING', 'SUSPENDED', 'DELETED') THEN
    qspark_err(400, 'account_status must be ACTIVE, PENDING, SUSPENDED or DELETED'); RETURN;
  END IF;
  BEGIN
    SELECT role INTO v_role FROM qspark_users WHERE user_id = v_id;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Admin not found'); RETURN;
  END;
  IF v_role <> 'ADMIN' THEN qspark_err(403, 'Only ADMIN accounts can be changed'); RETURN; END IF;
  UPDATE qspark_users SET account_status = v_st, updated_by = v_actor WHERE user_id = v_id;
  qspark_audit('ADMIN_STATUS', 'users', v_id, v_role, v_st, v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Status updated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/users/:user_id/wallet-adjustments', 'POST', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:user_id);
  v_amt NUMBER := qspark_num(JSON_VALUE(:body, '$.amount'));
  v_note VARCHAR2(200) := JSON_VALUE(:body, '$.description');
  v_before NUMBER; v_after NUMBER; v_dir VARCHAR2(10); v_dummy NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_amt IS NULL OR v_amt = 0 THEN qspark_err(400, 'amount must be a non-zero number'); RETURN; END IF;
  BEGIN
    SELECT wallet_balance INTO v_before FROM qspark_users WHERE user_id = v_id FOR UPDATE;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'User not found'); RETURN;
  END;
  v_after := ROUND(v_before + v_amt, 2);
  IF v_after < 0 THEN qspark_err(409, 'Adjustment would make the wallet negative'); RETURN; END IF;
  v_dir := CASE WHEN v_amt > 0 THEN 'CREDIT' ELSE 'DEBIT' END;
  UPDATE qspark_users SET wallet_balance = v_after, updated_by = v_actor WHERE user_id = v_id;
  v_dummy := qspark_wallet_txn(v_id, NULL, 'ADMIN_ADJUSTMENT', v_dir, ABS(v_amt), v_after,
                            NVL(v_note, 'Admin adjustment'), v_actor);
  qspark_audit('WALLET_ADJUSTMENT', 'users', v_id, TO_CHAR(v_before), TO_CHAR(v_after), v_actor);
  qspark_json(JSON_OBJECT('user_id' VALUE v_id, 'adjustment' VALUE v_amt,
    'previous_balance' VALUE v_before, 'new_balance' VALUE v_after));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/floors', 'POST', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_code VARCHAR2(20) := UPPER(TRIM(JSON_VALUE(:body, '$.floor_code')));
  v_id NUMBER; v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_code IS NULL THEN qspark_err(400, 'floor_code is required'); RETURN; END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_floors WHERE floor_code = v_code;
  IF v_cnt > 0 THEN qspark_err(409, 'Floor code already exists'); RETURN; END IF;
  INSERT INTO qspark_floors (floor_code, floor_status, created_by)
  VALUES (v_code, 'OPEN', v_actor) RETURNING floor_id INTO v_id;
  qspark_audit('CREATE_FLOOR', 'floors', v_id, NULL, v_code, v_actor);
  qspark_json(JSON_OBJECT('floor_id' VALUE v_id, 'floor_code' VALUE v_code));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/floors/:floor_id', 'PUT', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:floor_id);
  v_st VARCHAR2(20) := UPPER(JSON_VALUE(:body, '$.floor_status'));
  v_code VARCHAR2(20) := UPPER(TRIM(JSON_VALUE(:body, '$.floor_code')));
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_st IS NOT NULL AND v_st NOT IN ('OPEN', 'CLOSED', 'INACTIVE') THEN
    qspark_err(400, 'floor_status must be OPEN, CLOSED or INACTIVE'); RETURN;
  END IF;
  UPDATE qspark_floors SET
    floor_code   = NVL(v_code, floor_code),
    floor_status = NVL(v_st, floor_status),
    updated_by   = v_actor
   WHERE floor_id = v_id;
  IF SQL%ROWCOUNT = 0 THEN qspark_err(404, 'Floor not found'); RETURN; END IF;
  qspark_audit('UPDATE_FLOOR', 'floors', v_id, NULL, :body, v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Floor updated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/floors/:floor_id', 'DELETE', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:floor_id);
  v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_bookings b
    JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
   WHERE s.floor_id = v_id AND b.booking_status IN ('HELD', 'CONFIRMED');
  IF v_cnt > 0 THEN qspark_err(409, 'Floor has active bookings'); RETURN; END IF;
  UPDATE qspark_floors SET floor_status = 'INACTIVE', updated_by = v_actor WHERE floor_id = v_id;
  IF SQL%ROWCOUNT = 0 THEN qspark_err(404, 'Floor not found'); RETURN; END IF;
  qspark_audit('DELETE_FLOOR', 'floors', v_id, NULL, 'INACTIVE', v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Floor deactivated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/floors/:floor_id/slots', 'POST', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_fid NUMBER := qspark_num(:floor_id);
  v_num VARCHAR2(20) := UPPER(TRIM(JSON_VALUE(:body, '$.slot_number')));
  v_vt NUMBER := qspark_num(JSON_VALUE(:body, '$.vehicle_type_id'));
  v_id NUMBER; v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_num IS NULL OR v_vt IS NULL THEN
    qspark_err(400, 'slot_number and vehicle_type_id are required'); RETURN;
  END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_floors WHERE floor_id = v_fid;
  IF v_cnt = 0 THEN qspark_err(404, 'Floor not found'); RETURN; END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_vehicle_types WHERE vehicle_type_id = v_vt;
  IF v_cnt = 0 THEN qspark_err(404, 'Vehicle type not found'); RETURN; END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_parking_slots WHERE floor_id = v_fid AND slot_number = v_num;
  IF v_cnt > 0 THEN qspark_err(409, 'Slot number already exists on this floor'); RETURN; END IF;

  INSERT INTO qspark_parking_slots (floor_id, vehicle_type_id, slot_number, control_status, created_by)
  VALUES (v_fid, v_vt, v_num, 'ACTIVE', v_actor) RETURNING slot_id INTO v_id;
  qspark_audit('CREATE_SLOT', 'parking_slots', v_id, NULL, v_num, v_actor);
  qspark_json(JSON_OBJECT('slot_id' VALUE v_id, 'slot_number' VALUE v_num));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/slots/:slot_id', 'PUT', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:slot_id);
  v_num VARCHAR2(20) := UPPER(TRIM(JSON_VALUE(:body, '$.slot_number')));
  v_vt NUMBER := qspark_num(JSON_VALUE(:body, '$.vehicle_type_id'));
  v_st VARCHAR2(20) := UPPER(JSON_VALUE(:body, '$.control_status'));
  v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_parking_slots WHERE slot_id = v_id;
  IF v_cnt = 0 THEN qspark_err(404, 'Slot not found'); RETURN; END IF;
  IF v_st IN ('MAINTENANCE', 'INACTIVE') THEN
    SELECT COUNT(*) INTO v_cnt FROM qspark_bookings
     WHERE slot_id = v_id AND booking_status IN ('HELD', 'CONFIRMED');
    IF v_cnt > 0 THEN qspark_err(409, 'Slot has an active booking'); RETURN; END IF;
  END IF;
  UPDATE qspark_parking_slots SET
    slot_number     = NVL(v_num, slot_number),
    vehicle_type_id = NVL(v_vt, vehicle_type_id),
    control_status  = NVL(v_st, control_status),
    updated_by      = v_actor
   WHERE slot_id = v_id;
  qspark_audit('UPDATE_SLOT', 'parking_slots', v_id, NULL, :body, v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Slot updated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/slots/:slot_id', 'DELETE', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_id NUMBER := qspark_num(:slot_id);
  v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_bookings
   WHERE slot_id = v_id AND booking_status IN ('HELD', 'CONFIRMED');
  IF v_cnt > 0 THEN qspark_err(409, 'Slot has an active booking'); RETURN; END IF;
  UPDATE qspark_parking_slots SET control_status = 'INACTIVE', updated_by = v_actor WHERE slot_id = v_id;
  IF SQL%ROWCOUNT = 0 THEN qspark_err(404, 'Slot not found'); RETURN; END IF;
  qspark_audit('DELETE_SLOT', 'parking_slots', v_id, NULL, 'INACTIVE', v_actor);
  qspark_json(JSON_OBJECT('message' VALUE 'Slot deactivated'));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/super-admin/bookings/:ref/cancel', 'POST', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_bid NUMBER; v_owner NUMBER; v_status VARCHAR2(20); v_amt NUMBER; v_from TIMESTAMP(0);
  v_wallet NUMBER; v_hrs NUMBER; v_pct NUMBER; v_refund NUMBER := 0; v_new NUMBER;
  v_sa NUMBER; v_sa_w NUMBER; v_sa_new NUMBER; v_cid NUMBER; v_sid NUMBER; v_cnt NUMBER;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  BEGIN
    SELECT b.booking_id, b.user_id, b.booking_status, b.estimated_amount, b.booked_from, u.wallet_balance
      INTO v_bid, v_owner, v_status, v_amt, v_from, v_wallet
      FROM qspark_bookings b JOIN qspark_users u ON u.user_id = b.user_id
     WHERE b.booking_reference = :ref;
  EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Booking not found'); RETURN;
  END;
  IF v_status NOT IN ('HELD', 'CONFIRMED') THEN
    qspark_err(409, 'Only HELD or CONFIRMED bookings can be cancelled'); RETURN;
  END IF;
  SELECT COUNT(*) INTO v_cnt FROM qspark_booking_events e
   WHERE e.booking_id = v_bid AND e.event_type = 'ENTRY'
     AND NOT EXISTS (SELECT 1 FROM qspark_booking_events x
                      WHERE x.booking_id = v_bid AND x.event_type = 'EXIT');
  IF v_cnt > 0 THEN qspark_err(409, 'Cannot cancel: vehicle has entered and not exited'); RETURN; END IF;

  v_hrs := ROUND((CAST(v_from AS DATE) - CAST(SYSTIMESTAMP AS DATE)) * 24, 4);
  v_pct := CASE WHEN v_hrs > 24 THEN 100 WHEN v_hrs >= 1 THEN 50 ELSE 0 END;
  IF v_status = 'CONFIRMED' THEN v_refund := ROUND(v_amt * v_pct / 100, 2); END IF;
  v_new := ROUND(v_wallet + v_refund, 2);

  IF v_refund > 0 THEN
    UPDATE qspark_users SET wallet_balance = v_new WHERE user_id = v_owner;
    v_cid := qspark_wallet_txn(v_owner, v_bid, 'CANCELLATION_REFUND', 'CREDIT', v_refund, v_new,
                               'Admin cancellation ' || :ref, v_actor);
    v_sa := qspark_sa_user;
    IF v_sa IS NOT NULL THEN
      SELECT wallet_balance INTO v_sa_w FROM qspark_users WHERE user_id = v_sa;
      v_sa_new := ROUND(v_sa_w - v_refund, 2);
      UPDATE qspark_users SET wallet_balance = v_sa_new WHERE user_id = v_sa;
      v_sid := qspark_wallet_txn(v_sa, v_bid, 'REVENUE_REFUND_REVERSAL', 'DEBIT', v_refund,
                                 v_sa_new, 'Refund reversal ' || :ref, v_actor);
      INSERT INTO qspark_revenue_collections
        (source_user_id, super_admin_user_id, booking_id, customer_wallet_transaction_id,
         super_admin_wallet_transaction_id, collection_type, amount, created_by)
      VALUES (v_owner, v_sa, v_bid, v_cid, v_sid, 'REFUND_REVERSAL', v_refund, v_actor);
    END IF;
  END IF;

  UPDATE qspark_bookings SET booking_status = 'CANCELLED', updated_by = v_actor
   WHERE booking_id = v_bid;
  qspark_audit('BOOKING_CANCELLED', 'bookings', v_bid, v_status, 'CANCELLED', v_actor);
  qspark_json(JSON_OBJECT('booking_reference' VALUE :ref, 'booking_status' VALUE 'CANCELLED',
    'refund_amount' VALUE v_refund));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  COMMIT;
END;
/

-- ---------------------------------------------------------------------------
-- System + profile
-- ---------------------------------------------------------------------------
BEGIN
  qspark_h('api/system/super-admin/session', 'PATCH', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_val NUMBER := qspark_num(JSON_VALUE(:body, '$.idle_timeout_minutes'));
  v_old VARCHAR2(500);
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_val IS NULL OR v_val NOT IN (5, 10, 15, 20) THEN
    qspark_err(400, 'allowed: 5,10,15,20'); RETURN;
  END IF;
  BEGIN
    SELECT setting_value INTO v_old FROM qspark_system_settings
     WHERE setting_key = 'SESSION_IDLE_TIMEOUT' FOR UPDATE;
  EXCEPTION WHEN NO_DATA_FOUND THEN
    INSERT INTO qspark_system_settings (setting_key, setting_value, description)
    VALUES ('SESSION_IDLE_TIMEOUT', '20', 'Idle session timeout in minutes');
    v_old := '20';
  END;
  UPDATE qspark_system_settings SET setting_value = TO_CHAR(v_val), updated_by = v_actor
   WHERE setting_key = 'SESSION_IDLE_TIMEOUT';
  qspark_audit('SESSION_TIMEOUT_CHANGE', 'system_settings', NULL, v_old, TO_CHAR(v_val), v_actor);
  qspark_json(JSON_OBJECT('idle_timeout_minutes' VALUE v_val));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/system/super-admin/system/status', 'PATCH', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_val VARCHAR2(20) := UPPER(JSON_VALUE(:body, '$.system_status'));
  v_old VARCHAR2(500);
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_val NOT IN ('ONLINE', 'OFFLINE') THEN
    qspark_err(400, 'system_status must be ONLINE or OFFLINE'); RETURN;
  END IF;
  BEGIN
    SELECT setting_value INTO v_old FROM qspark_system_settings
     WHERE setting_key = 'SYSTEM_STATUS' FOR UPDATE;
  EXCEPTION WHEN NO_DATA_FOUND THEN
    INSERT INTO qspark_system_settings (setting_key, setting_value, description)
    VALUES ('SYSTEM_STATUS', 'ONLINE', 'Global system status');
    v_old := 'ONLINE';
  END;
  UPDATE qspark_system_settings SET setting_value = v_val, updated_by = v_actor
   WHERE setting_key = 'SYSTEM_STATUS';
  qspark_audit(CASE WHEN v_val = 'ONLINE' THEN 'SYSTEM_ONLINE' ELSE 'SYSTEM_OFFLINE' END,
               'system_settings', NULL, v_old, v_val, v_actor);
  qspark_json(JSON_OBJECT('system_status' VALUE v_val));
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  qspark_h('api/auth/me', 'PATCH', q'!
DECLARE
  v_actor NUMBER := qspark_num(:actor_user_id);
  v_name VARCHAR2(100) := TRIM(JSON_VALUE(:body, '$.full_name'));
  v_phone VARCHAR2(20) := TRIM(JSON_VALUE(:body, '$.phone'));
  v_gender VARCHAR2(20) := JSON_VALUE(:body, '$.gender');
  v_company VARCHAR2(200) := JSON_VALUE(:body, '$.company_name');
  v_changed NUMBER := 0; v CLOB;
BEGIN
  IF v_actor IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  IF v_name IS NOT NULL THEN
    IF LENGTH(v_name) = 0 THEN qspark_err(400, 'full_name cannot be empty'); RETURN; END IF;
    UPDATE qspark_users SET full_name = v_name WHERE user_id = v_actor; v_changed := 1;
  END IF;
  IF v_phone IS NOT NULL THEN
    IF NOT REGEXP_LIKE(v_phone, '^[0-9]{10}$') THEN qspark_err(400, 'phone must be 10 digits'); RETURN; END IF;
    UPDATE qspark_users SET phone = v_phone WHERE user_id = v_actor; v_changed := 1;
  END IF;
  IF v_gender IS NOT NULL THEN
    IF v_gender NOT IN ('MALE', 'FEMALE', 'OTHER', 'PREFER_NOT_TO_SAY') THEN
      qspark_err(400, 'Invalid gender'); RETURN;
    END IF;
    UPDATE qspark_users SET gender = v_gender WHERE user_id = v_actor; v_changed := 1;
  END IF;
  IF v_company IS NOT NULL THEN
    UPDATE qspark_users SET company_name = v_company WHERE user_id = v_actor; v_changed := 1;
  END IF;
  IF v_changed = 0 THEN qspark_err(400, 'No updatable fields'); RETURN; END IF;

  UPDATE qspark_users SET updated_by = v_actor WHERE user_id = v_actor;
  SELECT JSON_OBJECT('user_id' VALUE user_id, 'admin_id' VALUE admin_id,
    'full_name' VALUE full_name, 'email' VALUE email, 'phone' VALUE phone,
    'gender' VALUE gender, 'company_name' VALUE company_name, 'username' VALUE username,
    'role' VALUE role, 'wallet_balance' VALUE wallet_balance,
    'account_status' VALUE account_status, 'created_at' VALUE created_at)
    INTO v FROM qspark_users WHERE user_id = v_actor;
  qspark_json(v);
EXCEPTION WHEN OTHERS THEN
  ROLLBACK; qspark_err(500, SQLERRM);
END;!');

  COMMIT;
END;
/

-- Expected: 64 handlers total (34 reads + 30 writes)
SELECT COUNT(*) AS handler_count
  FROM user_ords_handlers h
  JOIN user_ords_templates t ON t.id = h.template_id
  JOIN user_ords_modules m ON m.id = t.module_id
 WHERE m.name = 'qsparking.api.v3';
