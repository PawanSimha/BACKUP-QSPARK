-- oracle/05_package.sql
-- QSPARK_API PL/SQL package
-- Procedures: hold/confirm/cancel/scan_qr/adjust_wallet
-- Run after oracle/04_identity.sql has been executed successfully.
-- All PK columns are populated by BEFORE INSERT triggers + sequences
-- (triggers have WHEN (NEW.pk_col IS NULL) to allow explicit IDs).

CREATE OR REPLACE PACKAGE QSPARK_API IS
  -- Hold a parking slot for a new booking
  -- Returns: booking_reference
  FUNCTION hold_booking(
    p_slot_id INTEGER,
    p_vehicle_number VARCHAR2 DEFAULT NULL,
    p_vehicle_format VARCHAR2 DEFAULT 'std1',
    p_booked_from TIMESTAMP,
    p_booked_until TIMESTAMP,
    p_user_id INTEGER DEFAULT NULL
  ) RETURN VARCHAR2;

  -- Confirm a held booking
  -- Returns: 'CONFIRMED|amount_debited|new_wallet_balance|qr_generated|message'
  FUNCTION confirm_booking(
    p_booking_reference VARCHAR2
  ) RETURN VARCHAR2;

  -- Cancel a booking
  -- Returns: 'CANCELLED|refund_amount|penalty_amount|net_credit|message'
  FUNCTION cancel_booking(
    p_booking_reference VARCHAR2
  ) RETURN VARCHAR2;

  -- Process QR scan (ENTRY or EXIT)
  -- Returns: status message
  FUNCTION scan_qr(
    p_booking_reference VARCHAR2,
    p_scan_method VARCHAR2 DEFAULT 'QR'
  ) RETURN VARCHAR2;

  -- Adjust user wallet (SUPER_ADMIN only)
  PROCEDURE adjust_wallet(
    p_user_id INTEGER,
    p_amount NUMERIC,
    p_description VARCHAR2 DEFAULT NULL
  );

  -- Get current system status
  FUNCTION get_system_status RETURN VARCHAR2;

  -- Get wallet balance
  FUNCTION get_wallet_balance(p_user_id INTEGER) RETURN NUMERIC;
END QSPARK_API;
/
-- Package body

CREATE OR REPLACE PACKAGE BODY QSPARK_API IS

  -- Hold a parking slot for a new booking
  FUNCTION hold_booking(
    p_slot_id INTEGER,
    p_vehicle_number VARCHAR2 DEFAULT NULL,
    p_vehicle_format VARCHAR2 DEFAULT 'std1',
    p_booked_from TIMESTAMP,
    p_booked_until TIMESTAMP,
    p_user_id INTEGER DEFAULT NULL
  ) RETURN VARCHAR2 IS
    v_booking_ref VARCHAR2(50);
    v_hourly_rate NUMBER;
    v_overstay_rate NUMBER;
    v_floor_status VARCHAR2(20);
    v_slot_status VARCHAR2(20);
    v_duration_hours NUMBER;
    v_count INTEGER;
  BEGIN
    -- Look up slot details and rates using schema-qualified names
    SELECT s.control_status, v.hourly_rate, v.overstay_rate, f.floor_status
    INTO v_slot_status, v_hourly_rate, v_overstay_rate, v_floor_status
    FROM NOV_2026_BATCH.QSPARK_PARKING_SLOTS s
    JOIN NOV_2026_BATCH.QSPARK_VEHICLE_TYPES v ON s.vehicle_type_id = v.vehicle_type_id
    JOIN NOV_2026_BATCH.QSPARK_FLOORS f ON s.floor_id = f.floor_id
    WHERE s.slot_id = p_slot_id;

    -- Check slot is available
    IF v_slot_status != 'ACTIVE' THEN
      RETURN 'Slot is not active';
    END IF;

    -- Check floor is open
    IF v_floor_status != 'OPEN' THEN
      RETURN 'Floor is not open';
    END IF;

    -- Check vehicle number uniqueness for active bookings (if provided)
    IF p_vehicle_number IS NOT NULL THEN
      SELECT COUNT(*) INTO v_count FROM NOV_2026_BATCH.QSPARK_BOOKINGS
      WHERE vehicle_number = p_vehicle_number
        AND booking_status IN ('HELD', 'CONFIRMED')
        AND booked_until > p_booked_from;
      IF v_count > 0 THEN
        RETURN 'Vehicle number already has an active booking';
      END IF;
    END IF;

    -- Generate booking reference
    v_booking_ref := 'QS' || TO_CHAR(SYSTIMESTAMP, 'YYYYMMDDHH24MISS') || LPAD(TO_NUMBER(TO_CHAR(SYSDATE, 'SSSS')), 4, '0');

    -- Calculate duration in hours: DATE subtraction gives fractional days; *24 converts to hours
    v_duration_hours := (CAST(p_booked_until AS DATE) - CAST(p_booked_from AS DATE)) * 24;

    -- Create the booking with HELD status
    INSERT INTO NOV_2026_BATCH.QSPARK_BOOKINGS (
      booking_reference, user_id, slot_id, vehicle_format, vehicle_number,
      booked_from, booked_until, booking_status, hourly_rate_applied, overstay_rate_applied,
      estimated_amount, created_by
    ) VALUES (
      v_booking_ref, p_user_id, p_slot_id, p_vehicle_format, p_vehicle_number,
      p_booked_from, p_booked_until, 'HELD',
      v_hourly_rate, v_overstay_rate,
      ROUND(v_hourly_rate * v_duration_hours, 2),
      p_user_id
    );

    RETURN v_booking_ref;
  END hold_booking;

  -- Confirm a held booking
  FUNCTION confirm_booking(
    p_booking_reference VARCHAR2
  ) RETURN VARCHAR2 IS
    v_booking NOV_2026_BATCH.QSPARK_BOOKINGS%ROWTYPE;
    v_user NOV_2026_BATCH.QSPARK_USERS%ROWTYPE;
    v_sa   NOV_2026_BATCH.QSPARK_USERS%ROWTYPE;
    v_slot NOV_2026_BATCH.QSPARK_PARKING_SLOTS%ROWTYPE;
    v_floor NOV_2026_BATCH.QSPARK_FLOORS%ROWTYPE;
    v_cancellation NOV_2026_BATCH.QSPARK_CANCELLATION_RULES%ROWTYPE;
    v_new_wallet NUMERIC;
    v_cust_txn_id NUMBER;
    v_sa_txn_id NUMBER;
    v_refund_amount NUMERIC;
    v_penalty_amount NUMERIC;
    v_entry varchar2(1);
  BEGIN
    -- Lock the booking row first
    SELECT * INTO v_booking FROM NOV_2026_BATCH.QSPARK_BOOKINGS WHERE booking_reference = p_booking_reference FOR UPDATE;

    -- Check booking is in HELD status
    IF v_booking.booking_status != 'HELD' THEN
      ROLLBACK;
      RETURN 'ERR|409|Booking is ' || v_booking.booking_status || ', not HELD';
    END IF;

    -- Lock user row and revalidate slot/floor with row-level locks
    SELECT * INTO v_user FROM NOV_2026_BATCH.QSPARK_USERS WHERE user_id = v_booking.user_id FOR UPDATE;
    SELECT * INTO v_slot FROM NOV_2026_BATCH.QSPARK_PARKING_SLOTS WHERE slot_id = v_booking.slot_id FOR UPDATE;

    -- Look up floor status
    SELECT * INTO v_floor FROM NOV_2026_BATCH.QSPARK_FLOORS WHERE floor_id = v_slot.floor_id FOR UPDATE;

    IF v_floor.floor_status != 'OPEN' THEN
      ROLLBACK;
      RETURN 'ERR|409|That floor is closed. Choose another slot.';
    END IF;

    -- Re-check overlap on the slot (exclude current booking)
    SELECT COUNT(*) INTO v_entry FROM NOV_2026_BATCH.QSPARK_BOOKINGS b2
    WHERE b2.slot_id = v_booking.slot_id
      AND b2.booking_status IN ('HELD', 'CONFIRMED')
      AND b2.booked_from < v_booking.booked_until
      AND b2.booked_until > v_booking.booked_from
      AND b2.booking_id != v_booking.booking_id;

    IF v_entry > 0 THEN
      ROLLBACK;
      RETURN 'ERR|409|Another booking now overlaps this slot. Choose another slot.';
    END IF;

    -- Look up cancellation rule
    IF v_booking.applied_cancellation_rule_id IS NOT NULL THEN
      SELECT * INTO v_cancellation FROM NOV_2026_BATCH.QSPARK_CANCELLATION_RULES WHERE rule_id = v_booking.applied_cancellation_rule_id;
    ELSE
      v_cancellation.refund_percent := 0;
      v_cancellation.penalty_percent := 100;
    END IF;

    -- Resolve Super Admin account
    BEGIN
      SELECT * INTO v_sa FROM NOV_2026_BATCH.QSPARK_USERS WHERE role = 'SUPER_ADMIN' AND ROWNUM = 1 FOR UPDATE;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        ROLLBACK;
        RETURN 'ERR|500|Super Admin account missing';
    END;

    -- Funds check: customer wallet >= estimated_amount
    v_new_wallet := v_user.wallet_balance - v_booking.estimated_amount;
    IF v_new_wallet < 0 THEN
      ROLLBACK;
      RETURN 'ERR|402|Insufficient wallet balance';
    END IF;

    -- Customer debit: UPDATE users + INSERT wallet_transaction RETURNING transaction_id
    UPDATE NOV_2026_BATCH.QSPARK_USERS SET wallet_balance = v_new_wallet WHERE user_id = v_user.user_id;

    INSERT INTO NOV_2026_BATCH.QSPARK_WALLET_TRANSACTIONS (
      transaction_reference, user_id, booking_id,
      transaction_type, direction, amount, balance_after,
      description
    ) VALUES (
      'TXN-' || TO_CHAR(CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Kolkata' AS DATE), 'YYYYMMDD-HH24MISS')
        || '-' || SUBSTR(RAWTOHEX(SYS_GUID()), 1, 8),
      v_user.user_id, v_booking.booking_id,
      'BOOKING_DEBIT', 'DEBIT', v_booking.estimated_amount, v_new_wallet,
      'Booking confirmation charge'
    )
    RETURNING transaction_id INTO v_cust_txn_id;

    -- Super Admin revenue credit: UPDATE real SA user + INSERT wallet_transaction RETURNING transaction_id
    v_new_wallet := v_sa.wallet_balance + v_booking.estimated_amount;
    UPDATE NOV_2026_BATCH.QSPARK_USERS SET wallet_balance = v_new_wallet WHERE user_id = v_sa.user_id;

    INSERT INTO NOV_2026_BATCH.QSPARK_WALLET_TRANSACTIONS (
      transaction_reference, user_id, booking_id,
      transaction_type, direction, amount, balance_after,
      description
    ) VALUES (
      'TXN-' || TO_CHAR(CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Kolkata' AS DATE), 'YYYYMMDD-HH24MISS')
        || '-' || SUBSTR(RAWTOHEX(SYS_GUID()), 1, 8),
      v_sa.user_id, v_booking.booking_id,
      'SUPER_ADMIN_REVENUE_CREDIT', 'CREDIT', v_booking.estimated_amount, v_new_wallet,
      'Revenue collection from booking'
    )
    RETURNING transaction_id INTO v_sa_txn_id;

    -- Record revenue collection with REAL txn ids and REAL super_admin_user_id
    INSERT INTO NOV_2026_BATCH.QSPARK_REVENUE_COLLECTIONS (
      source_user_id, super_admin_user_id, booking_id,
      customer_wallet_transaction_id, super_admin_wallet_transaction_id,
      collection_type, amount, created_by
    ) VALUES (
      v_user.user_id, v_sa.user_id, v_booking.booking_id,
      v_cust_txn_id, v_sa_txn_id,
      'BOOKING_CHARGE', v_booking.estimated_amount, v_user.user_id
    );

    -- Update booking status to CONFIRMED
    UPDATE NOV_2026_BATCH.QSPARK_BOOKINGS SET booking_status = 'CONFIRMED' WHERE booking_reference = p_booking_reference;

    -- Audit log
    INSERT INTO NOV_2026_BATCH.QSPARK_AUDIT_LOGS (
      action_type, entity_type, entity_id, old_values, new_values, created_by
    ) VALUES (
      'BOOKING_CONFIRM', 'bookings', v_booking.booking_id,
      NULL,
      '{"booking_status":"CONFIRMED","amount":' || v_booking.estimated_amount || ',"user_id":' || v_user.user_id || '}',
      v_user.user_id
    );

    RETURN 'CONFIRMED|' || v_booking.estimated_amount || '|' || v_new_wallet || '|true|Booking confirmed. QR generated';
  END confirm_booking;

  -- Cancel a booking
  FUNCTION cancel_booking(
    p_booking_reference VARCHAR2
  ) RETURN VARCHAR2 IS
    v_booking NOV_2026_BATCH.QSPARK_BOOKINGS%ROWTYPE;
    v_user NOV_2026_BATCH.QSPARK_USERS%ROWTYPE;
    v_cancellation NOV_2026_BATCH.QSPARK_CANCELLATION_RULES%ROWTYPE;
    v_refund_amount NUMERIC;
    v_penalty_amount NUMERIC;
    v_net_credit NUMERIC;
    v_new_wallet NUMERIC;
    v_msg VARCHAR2(200);
  BEGIN
    -- Look up the booking
    SELECT * INTO v_booking FROM NOV_2026_BATCH.QSPARK_BOOKINGS WHERE booking_reference = p_booking_reference;

    -- Check booking is cancellable
    IF v_booking.booking_status NOT IN ('HELD', 'CONFIRMED') THEN
      RETURN 'Booking cannot be cancelled in current status';
    END IF;

    -- Look up user
    SELECT * INTO v_user FROM NOV_2026_BATCH.QSPARK_USERS WHERE user_id = v_booking.user_id;

    -- Look up cancellation rule
    IF v_booking.applied_cancellation_rule_id IS NOT NULL THEN
      SELECT * INTO v_cancellation FROM NOV_2026_BATCH.QSPARK_CANCELLATION_RULES WHERE rule_id = v_booking.applied_cancellation_rule_id;
    ELSE
      v_cancellation.refund_percent := 0;
      v_cancellation.penalty_percent := 100;
    END IF;

    -- Calculate refund and penalty
    v_refund_amount := v_booking.estimated_amount * v_cancellation.refund_percent / 100;
    v_penalty_amount := v_booking.estimated_amount * v_cancellation.penalty_percent / 100;
    v_net_credit := v_refund_amount;

    -- Update booking status to CANCELLED
    UPDATE NOV_2026_BATCH.QSPARK_BOOKINGS SET booking_status = 'CANCELLED' WHERE booking_reference = p_booking_reference;

    -- Credit wallet with refund amount
    v_new_wallet := v_user.wallet_balance + v_net_credit;
    UPDATE NOV_2026_BATCH.QSPARK_USERS SET wallet_balance = v_new_wallet WHERE user_id = v_user.user_id;

    -- Record wallet transaction (REFUND/CREDIT)
    INSERT INTO NOV_2026_BATCH.QSPARK_WALLET_TRANSACTIONS (
      transaction_reference, user_id, booking_id,
      transaction_type, direction, amount, balance_after,
      description
    ) VALUES (
      'TXN' || TO_CHAR(SYSTIMESTAMP, 'YYYYMMDDHH24MISS') || LPAD(TO_NUMBER(TO_CHAR(SYSDATE, 'SSSS')), 4, '0'),
      v_user.user_id, v_booking.booking_id,
      'CANCELLATION_REFUND', 'CREDIT', v_net_credit, v_new_wallet,
      'Booking cancellation refund'
    );

    v_msg := 'Booking cancelled. Refund of ' || v_refund_amount || ' processed. Penalty of ' || v_penalty_amount || ' forfeited.';

    RETURN 'CANCELLED|' || v_refund_amount || '|' || v_penalty_amount || '|' || v_net_credit || '|' || v_msg;
  END cancel_booking;

  -- Process QR scan (ENTRY or EXIT)
  FUNCTION scan_qr(
    p_booking_reference VARCHAR2,
    p_scan_method VARCHAR2 DEFAULT 'QR'
  ) RETURN VARCHAR2 IS
    v_booking NOV_2026_BATCH.QSPARK_BOOKINGS%ROWTYPE;
    v_entry_count INTEGER;
    v_overstay_days NUMBER;
    v_overstay_amount NUMERIC;
    v_entry_ts TIMESTAMP;
  BEGIN
    -- Look up the booking
    SELECT * INTO v_booking FROM NOV_2026_BATCH.QSPARK_BOOKINGS WHERE booking_reference = p_booking_reference;

    -- Check if there's already an ENTRY event
    SELECT COUNT(*) INTO v_entry_count FROM NOV_2026_BATCH.QSPARK_BOOKING_EVENTS
    WHERE booking_id = v_booking.booking_id AND event_type = 'ENTRY';

    IF v_entry_count = 0 THEN
      -- This is an ENTRY scan
      IF v_booking.booking_status != 'CONFIRMED' THEN
        RETURN 'Booking is not CONFIRMED; cannot ENTRY';
      END IF;

      -- Check for existing ENTRY event
      IF v_entry_count > 0 THEN
        RETURN 'ENTRY event already recorded for this booking';
      END IF;

      -- Record ENTRY event
      INSERT INTO NOV_2026_BATCH.QSPARK_BOOKING_EVENTS (
        booking_id, event_type, scan_method, created_by
      ) VALUES (
        v_booking.booking_id, 'ENTRY', p_scan_method, v_booking.user_id
      );

      RETURN 'ENTRY recorded successfully';
    ELSE
      -- This is an EXIT scan
      IF v_booking.booking_status != 'CONFIRMED' THEN
        RETURN 'Booking is not CONFIRMED; cannot EXIT';
      END IF;

      -- Check for existing EXIT event
      SELECT COUNT(*) INTO v_entry_count FROM NOV_2026_BATCH.QSPARK_BOOKING_EVENTS
      WHERE booking_id = v_booking.booking_id AND event_type = 'EXIT';
      IF v_entry_count > 0 THEN
        RETURN 'EXIT event already recorded for this booking';
      END IF;

      -- Get the entry event timestamp
      SELECT created_at INTO v_entry_ts FROM NOV_2026_BATCH.QSPARK_BOOKING_EVENTS
      WHERE booking_id = v_booking.booking_id AND event_type = 'ENTRY';

      -- Calculate overstay days from entry to now (DATE - DATE gives fractional days)
      v_overstay_days := CAST(SYSTIMESTAMP AS DATE) - CAST(v_entry_ts AS DATE);

      -- Get the vehicle type's overstay rate via slot
      SELECT v.overstay_rate INTO v_overstay_amount
      FROM NOV_2026_BATCH.QSPARK_PARKING_SLOTS s
      JOIN NOV_2026_BATCH.QSPARK_VEHICLE_TYPES v ON s.vehicle_type_id = v.vehicle_type_id
      WHERE s.slot_id = v_booking.slot_id;

      -- Calculate overstay amount
      v_overstay_amount := GREATEST(0, v_overstay_amount * GREATEST(0, v_overstay_days));

      -- Record EXIT event
      INSERT INTO NOV_2026_BATCH.QSPARK_BOOKING_EVENTS (
        booking_id, event_type, scan_method, event_note, created_by
      ) VALUES (
        v_booking.booking_id, 'EXIT', p_scan_method,
        'Overstay: ' || ROUND(v_overstay_days, 2) || ' days, amount: ' || v_overstay_amount,
        v_booking.user_id
      );

      RETURN 'EXIT recorded successfully. Overstay: ' || ROUND(v_overstay_days, 2) || ' days, amount: ' || v_overstay_amount;
    END IF;
  END scan_qr;

  -- Adjust user wallet (SUPER_ADMIN only)
  PROCEDURE adjust_wallet(
    p_user_id INTEGER,
    p_amount NUMERIC,
    p_description VARCHAR2 DEFAULT NULL
  ) IS
    v_current_balance NUMERIC;
  BEGIN
    -- Get current balance
    SELECT wallet_balance INTO v_current_balance FROM NOV_2026_BATCH.QSPARK_USERS WHERE user_id = p_user_id;

    -- Apply adjustment
    v_current_balance := v_current_balance + p_amount;

    -- Check for negative balance
    IF v_current_balance < 0 THEN
      RAISE_APPLICATION_ERROR(-20001, 'Insufficient wallet balance for adjustment');
    END IF;

    -- Update user wallet
    UPDATE NOV_2026_BATCH.QSPARK_USERS SET wallet_balance = v_current_balance WHERE user_id = p_user_id;

    -- Record wallet transaction
    INSERT INTO NOV_2026_BATCH.QSPARK_WALLET_TRANSACTIONS (
      transaction_reference, user_id, booking_id,
      transaction_type, direction, amount, balance_after,
      description
    ) VALUES (
      'TXN' || TO_CHAR(SYSTIMESTAMP, 'YYYYMMDDHH24MISS') || LPAD(TO_NUMBER(TO_CHAR(SYSDATE, 'SSSS')), 4, '0'),
      p_user_id, NULL,
      'ADMIN_ADJUSTMENT', CASE WHEN p_amount >= 0 THEN 'CREDIT' ELSE 'DEBIT' END,
      ABS(p_amount), v_current_balance,
      p_description
    );
  END adjust_wallet;

  -- Get current system status
  FUNCTION get_system_status RETURN VARCHAR2 IS
    v_status VARCHAR2(20);
  BEGIN
    SELECT setting_value INTO v_status FROM NOV_2026_BATCH.QSPARK_SYSTEM_SETTINGS WHERE setting_key = 'SYSTEM_STATUS';
    RETURN v_status;
  END get_system_status;

  -- Get wallet balance
  FUNCTION get_wallet_balance(p_user_id INTEGER) RETURN NUMERIC IS
    v_balance NUMERIC;
  BEGIN
    SELECT wallet_balance INTO v_balance FROM NOV_2026_BATCH.QSPARK_USERS WHERE user_id = p_user_id;
    RETURN v_balance;
  END get_wallet_balance;

END QSPARK_API;
/