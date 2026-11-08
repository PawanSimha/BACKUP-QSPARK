-- QSPARK — ORDS REST Services (parking.api.v2)
-- Target: Oracle Database 19c / 21c / 23ai with Oracle REST Data Services
-- Run as the QSPARK schema owner from SQL Workshop / SQLcl / SQL*Plus.
-- Handlers use APEX_JSON, which ships with Oracle APEX.

-- ---------------------------------------------------------------------------
-- 0. Enable ORDS for the QSPARK schema
--    Change 'QSPARK' and 'qspark' to your actual schema / URL pattern.
-- ---------------------------------------------------------------------------
BEGIN
    ORDS.ENABLE_SCHEMA(
        p_enabled             => TRUE,
        p_schema              => 'QSPARK',
        p_url_mapping_type    => 'BASE_PATH',
        p_url_mapping_pattern => 'qspark',
        p_auto_rest_auth      => FALSE
    );
    COMMIT;
END;
/

-- ---------------------------------------------------------------------------
-- 1. Module: parking.api.v2  (base path: v2/)
-- ---------------------------------------------------------------------------
BEGIN
    ORDS.DEFINE_MODULE(
        p_module_name    => 'parking.api.v2',
        p_base_path      => 'v2/',
        p_items_per_page => 250,
        p_status         => 'PUBLISHED',
        p_comments       => 'QSPARK smart parking REST API'
    );
    COMMIT;
END;
/

-- ===========================================================================
-- API 1 — GET slots/  (bay inventory, optional ?floor_id=N)
-- ===========================================================================
BEGIN
    ORDS.DEFINE_TEMPLATE(
        p_module_name    => 'parking.api.v2',
        p_pattern        => 'slots/',
        p_comments       => 'List parking bays, optionally filtered by floor'
    );

    ORDS.DEFINE_PARAMETER(
        p_module_name        => 'parking.api.v2',
        p_template_pattern   => 'slots/',
        p_method             => 'GET',
        p_name               => 'floor_id',
        p_bind_variable_name => 'floor_id',
        p_param_type        => 'QUERY',
        p_access_method     => 'IN',
        p_comments           => 'Optional floor filter (floor_id)'
    );

    ORDS.DEFINE_HANDLER(
        p_module_name    => 'parking.api.v2',
        p_template_pattern => 'slots/',
        p_method         => 'GET',
        p_source_type    => 'plsql',
        p_comments       => 'Returns real-time bay status across basements B1-B4',
        p_source         => q'[
DECLARE
    l_floor_id NUMBER := TO_NUMBER(:floor_id);
BEGIN
    APEX_JSON.OPEN_OBJECT;
    APEX_JSON.OPEN_ARRAY('items');
    FOR r IN (
        SELECT s.slot_id,
               f.floor_code,
               s.slot_number,
               vt.type_code AS vehicle_type,
               vt.hourly_rate,
               s.status
          FROM QSPARK_PARKING_SLOTS s
          JOIN QSPARK_FLOORS f
            ON f.floor_id = s.floor_id
          JOIN QSPARK_VEHICLE_TYPES vt
            ON vt.vehicle_type_id = s.vehicle_type_id
         WHERE l_floor_id IS NULL OR s.floor_id = l_floor_id
         ORDER BY s.slot_number
    ) LOOP
        APEX_JSON.OPEN_OBJECT;
        APEX_JSON.WRITE('slot_id', r.slot_id);
        APEX_JSON.WRITE('floor_code', r.floor_code);
        APEX_JSON.WRITE('slot_number', r.slot_number);
        APEX_JSON.WRITE('vehicle_type', r.vehicle_type);
        APEX_JSON.WRITE('hourly_rate', r.hourly_rate);
        APEX_JSON.WRITE('status', r.status);
        APEX_JSON.CLOSE_OBJECT;
    END LOOP;
    APEX_JSON.CLOSE_ARRAY;
    APEX_JSON.CLOSE_OBJECT;
    :status_code := 200;
EXCEPTION
    WHEN OTHERS THEN
        :status_code := 500;
        HTP.P('{"error": "Unable to load slots"}');
END;
]'
    );
    COMMIT;
END;
/

-- ===========================================================================
-- API 2 — PUT slots/:id/status  (admin override)
-- ===========================================================================
BEGIN
    ORDS.DEFINE_TEMPLATE(
        p_module_name    => 'parking.api.v2',
        p_pattern        => 'slots/:id/status',
        p_comments       => 'Admin maintenance override of a bay status'
    );

    ORDS.DEFINE_PARAMETER(
        p_module_name        => 'parking.api.v2',
        p_template_pattern   => 'slots/:id/status',
        p_method             => 'PUT',
        p_name               => 'id',
        p_bind_variable_name => 'id',
        p_param_type        => 'URI',
        p_access_method     => 'IN'
    );

    ORDS.DEFINE_PARAMETER(
        p_module_name        => 'parking.api.v2',
        p_template_pattern   => 'slots/:id/status',
        p_method             => 'PUT',
        p_name               => 'status',
        p_bind_variable_name => 'status',
        p_param_type        => 'BODY',
        p_access_method     => 'IN'
    );

    ORDS.DEFINE_PARAMETER(
        p_module_name        => 'parking.api.v2',
        p_template_pattern   => 'slots/:id/status',
        p_method             => 'PUT',
        p_name               => 'admin_user_id',
        p_bind_variable_name => 'admin_user_id',
        p_param_type        => 'BODY',
        p_access_method     => 'IN'
    );

    ORDS.DEFINE_HANDLER(
        p_module_name    => 'parking.api.v2',
        p_template_pattern => 'slots/:id/status',
        p_method         => 'PUT',
        p_source_type    => 'plsql',
        p_comments       => 'Force a bay to MAINTENANCE, OCCUPIED or AVAILABLE',
        p_source         => q'[
DECLARE
    l_old_status VARCHAR2(20);
BEGIN
    SELECT status
      INTO l_old_status
      FROM QSPARK_PARKING_SLOTS
     WHERE slot_id = TO_NUMBER(:id)
       FOR UPDATE;

    UPDATE QSPARK_PARKING_SLOTS
       SET status = :status,
           last_updated = CURRENT_TIMESTAMP
     WHERE slot_id = TO_NUMBER(:id);

    INSERT INTO QSPARK_AUDIT_LOGS
        (changed_by_user_id, slot_id, event_type, old_state, new_state, log_details)
    VALUES
        (TO_NUMBER(:admin_user_id), TO_NUMBER(:id), 'SLOT_STATUS_CHANGE',
         l_old_status, :status, 'Admin status override');

    COMMIT;
    :status_code := 200;
    APEX_JSON.OPEN_OBJECT;
    APEX_JSON.WRITE('slot_id', TO_NUMBER(:id));
    APEX_JSON.WRITE('status', :status);
    APEX_JSON.CLOSE_OBJECT;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        :status_code := 404;
        HTP.P('{"error": "Slot not found"}');
    WHEN OTHERS THEN
        ROLLBACK;
        :status_code := 500;
        HTP.P('{"error": "Slot status update failed"}');
END;
]'
    );
    COMMIT;
END;
/

-- ===========================================================================
-- API 3 — POST bookings/  (atomic reservation + wallet debit)
-- ===========================================================================
BEGIN
    ORDS.DEFINE_TEMPLATE(
        p_module_name    => 'parking.api.v2',
        p_pattern        => 'bookings/',
        p_comments       => 'Create an atomic reservation with Metro Card debit'
    );

    ORDS.DEFINE_PARAMETER(
        p_module_name => 'parking.api.v2', p_template_pattern => 'bookings/',
        p_method => 'POST', p_name => 'user_id',
        p_bind_variable_name => 'user_id', p_param_type => 'BODY', p_access_method => 'IN'
    );
    ORDS.DEFINE_PARAMETER(
        p_module_name => 'parking.api.v2', p_template_pattern => 'bookings/',
        p_method => 'POST', p_name => 'slot_id',
        p_bind_variable_name => 'slot_id', p_param_type => 'BODY', p_access_method => 'IN'
    );
    ORDS.DEFINE_PARAMETER(
        p_module_name => 'parking.api.v2', p_template_pattern => 'bookings/',
        p_method => 'POST', p_name => 'vehicle_number',
        p_bind_variable_name => 'vehicle_number', p_param_type => 'BODY', p_access_method => 'IN'
    );
    ORDS.DEFINE_PARAMETER(
        p_module_name => 'parking.api.v2', p_template_pattern => 'bookings/',
        p_method => 'POST', p_name => 'duration_hours',
        p_bind_variable_name => 'duration_hours', p_param_type => 'BODY', p_access_method => 'IN'
    );

    ORDS.DEFINE_HANDLER(
        p_module_name    => 'parking.api.v2',
        p_template_pattern => 'bookings/',
        p_method         => 'POST',
        p_source_type    => 'plsql',
        p_comments       => 'Lock slot, verify wallet, debit fare, insert booking + ledger',
        p_source         => q'[
DECLARE
    l_slot_status VARCHAR2(20);
    l_vehicle_type_id NUMBER;
    l_slot_number VARCHAR2(15);
    l_type_code VARCHAR2(15);
    l_rate NUMBER(6,2);
    l_duration NUMBER(4,1) := TO_NUMBER(:duration_hours);
    l_base NUMBER(8,2);
    l_wallet NUMBER(10,2);
    l_new_balance NUMBER(10,2);
    l_booking_id NUMBER;
    l_booking_code VARCHAR2(25);
    l_start TIMESTAMP;
    l_end TIMESTAMP;
BEGIN
    IF l_duration < 1 OR l_duration > 8 THEN
        :status_code := 400;
        HTP.P('{"error": "duration_hours must be between 1 and 8"}');
        RETURN;
    END IF;

    SELECT s.status, s.vehicle_type_id, s.slot_number
      INTO l_slot_status, l_vehicle_type_id, l_slot_number
      FROM QSPARK_PARKING_SLOTS s
     WHERE s.slot_id = TO_NUMBER(:slot_id)
       FOR UPDATE;

    IF l_slot_status != 'AVAILABLE' THEN
        :status_code := 409;
        HTP.P('{"error": "Slot is no longer available"}');
        RETURN;
    END IF;

    SELECT type_code, hourly_rate
      INTO l_type_code, l_rate
      FROM QSPARK_VEHICLE_TYPES
     WHERE vehicle_type_id = l_vehicle_type_id;

    l_base := ROUND(l_duration * l_rate, 2);

    SELECT wallet_balance
      INTO l_wallet
      FROM QSPARK_USERS
     WHERE user_id = TO_NUMBER(:user_id)
       FOR UPDATE;

    IF l_wallet < l_base THEN
        :status_code := 402;
        HTP.P('{"error": "Insufficient Metro Card wallet balance"}');
        RETURN;
    END IF;

    l_start := CURRENT_TIMESTAMP;
    l_end := l_start + NUMTODSINTERVAL(l_duration, 'HOUR');

    INSERT INTO QSPARK_BOOKINGS
        (booking_code, user_id, slot_id, vehicle_type_id, vehicle_number,
         scheduled_start, scheduled_end, duration_hours, hourly_rate_applied,
         base_amount, total_amount, status)
    VALUES
        ('TMP-' || SUBSTR(RAWTOHEX(SYS_GUID()), 1, 20),
         TO_NUMBER(:user_id), TO_NUMBER(:slot_id), l_vehicle_type_id, :vehicle_number,
         l_start, l_end, l_duration, l_rate, l_base, l_base, 'CONFIRMED')
    RETURNING booking_id INTO l_booking_id;

    l_booking_code := 'QSP-' || TO_CHAR(SYSDATE, 'MMDD') || '-' ||
                      LPAD(TO_CHAR(MOD(l_booking_id, 10000)), 4, '0');

    UPDATE QSPARK_BOOKINGS
       SET booking_code = l_booking_code
     WHERE booking_id = l_booking_id;

    l_new_balance := l_wallet - l_base;

    UPDATE QSPARK_USERS
       SET wallet_balance = l_new_balance
     WHERE user_id = TO_NUMBER(:user_id);

    INSERT INTO QSPARK_WALLET_TRANSACTIONS
        (user_id, booking_id, txn_type, previous_balance, amount, new_balance)
    VALUES
        (TO_NUMBER(:user_id), l_booking_id, 'BOOKING_DEBIT', l_wallet, l_base, l_new_balance);

    UPDATE QSPARK_PARKING_SLOTS
       SET status = 'RESERVED',
           last_updated = CURRENT_TIMESTAMP
     WHERE slot_id = TO_NUMBER(:slot_id);

    INSERT INTO QSPARK_AUDIT_LOGS
        (changed_by_user_id, slot_id, booking_id, event_type, old_state, new_state, log_details)
    VALUES
        (TO_NUMBER(:user_id), TO_NUMBER(:slot_id), l_booking_id, 'BOOKING_CREATED',
         'AVAILABLE', 'RESERVED', 'Booking ' || l_booking_code || ' created');

    COMMIT;
    :status_code := 201;
    APEX_JSON.OPEN_OBJECT;
    APEX_JSON.WRITE('booking_id', l_booking_id);
    APEX_JSON.WRITE('booking_code', l_booking_code);
    APEX_JSON.WRITE('slot_number', l_slot_number);
    APEX_JSON.WRITE('base_amount', l_base);
    APEX_JSON.WRITE('previous_wallet_balance', l_wallet);
    APEX_JSON.WRITE('new_wallet_balance', l_new_balance);
    APEX_JSON.WRITE('status', 'CONFIRMED');
    APEX_JSON.CLOSE_OBJECT;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        ROLLBACK;
        :status_code := 404;
        HTP.P('{"error": "User, slot or vehicle type not found"}');
    WHEN OTHERS THEN
        ROLLBACK;
        :status_code := 500;
        HTP.P('{"error": "Booking transaction failed"}');
END;
]'
    );
    COMMIT;
END;
/

-- ===========================================================================
-- API 4 — PUT bookings/:id/checkout  (overstay settlement)
-- ===========================================================================
BEGIN
    ORDS.DEFINE_TEMPLATE(
        p_module_name    => 'parking.api.v2',
        p_pattern        => 'bookings/:id/checkout',
        p_comments       => 'Exit settlement with 10-minute grace and overstay fine'
    );

    ORDS.DEFINE_PARAMETER(
        p_module_name => 'parking.api.v2', p_template_pattern => 'bookings/:id/checkout',
        p_method => 'PUT', p_name => 'id',
        p_bind_variable_name => 'id', p_param_type => 'URI', p_access_method => 'IN'
    );
    ORDS.DEFINE_PARAMETER(
        p_module_name => 'parking.api.v2', p_template_pattern => 'bookings/:id/checkout',
        p_method => 'PUT', p_name => 'simulated_late_hours',
        p_bind_variable_name => 'simulated_late_hours', p_param_type => 'BODY', p_access_method => 'IN'
    );

    ORDS.DEFINE_HANDLER(
        p_module_name    => 'parking.api.v2',
        p_template_pattern => 'bookings/:id/checkout',
        p_method         => 'PUT',
        p_source_type    => 'plsql',
        p_comments       => 'Compute penalty, debit wallet, free bay, complete booking',
        p_source         => q'[
DECLARE
    l_booking_id NUMBER := TO_NUMBER(:id);
    l_user_id NUMBER;
    l_slot_id NUMBER;
    l_status VARCHAR2(20);
    l_scheduled_end TIMESTAMP;
    l_base_amount NUMBER(8,2);
    l_type_code VARCHAR2(15);
    l_pen_rate NUMBER(6,2);
    l_exit TIMESTAMP;
    l_delta_hours NUMBER(8,2);
    l_overstay_hours NUMBER(5,2) := 0;
    l_penalty NUMBER(8,2) := 0;
    l_wallet NUMBER(10,2);
    l_new_balance NUMBER(10,2);
    l_total NUMBER(8,2);
BEGIN
    SELECT b.user_id, b.slot_id, b.status, b.scheduled_end, b.base_amount, vt.type_code, vt.overstay_penalty_hour
      INTO l_user_id, l_slot_id, l_status, l_scheduled_end, l_base_amount, l_type_code, l_pen_rate
      FROM QSPARK_BOOKINGS b
      JOIN QSPARK_VEHICLE_TYPES vt
        ON vt.vehicle_type_id = b.vehicle_type_id
     WHERE b.booking_id = l_booking_id
       FOR UPDATE OF b.booking_id;

    IF l_status NOT IN ('CONFIRMED', 'CHECKED_IN', 'OVERSTAY') THEN
        :status_code := 409;
        HTP.P('{"error": "Booking is not open for checkout"}');
        RETURN;
    END IF;

    l_exit := CURRENT_TIMESTAMP
              + NUMTODSINTERVAL(NVL(TO_NUMBER(:simulated_late_hours), 0), 'HOUR');

    l_delta_hours := ROUND((CAST(l_exit AS DATE) - CAST(l_scheduled_end AS DATE)) * 24, 2);

    IF l_delta_hours > (10 / 60) THEN
        l_overstay_hours := l_delta_hours;
        l_penalty := ROUND(l_delta_hours * l_pen_rate, 2);
    END IF;

    SELECT wallet_balance
      INTO l_wallet
      FROM QSPARK_USERS
     WHERE user_id = l_user_id
       FOR UPDATE;

    IF l_wallet < l_penalty THEN
        :status_code := 402;
        HTP.P('{"error": "Insufficient Metro Card wallet balance for overstay penalty"}');
        RETURN;
    END IF;

    l_new_balance := l_wallet - l_penalty;
    l_total := l_base_amount + l_penalty;

    IF l_penalty > 0 THEN
        UPDATE QSPARK_USERS
           SET wallet_balance = l_new_balance
         WHERE user_id = l_user_id;

        INSERT INTO QSPARK_WALLET_TRANSACTIONS
            (user_id, booking_id, txn_type, previous_balance, amount, new_balance)
        VALUES
            (l_user_id, l_booking_id, 'OVERSTAY_DEBIT', l_wallet, l_penalty, l_new_balance);
    END IF;

    UPDATE QSPARK_BOOKINGS
       SET actual_exit_time = l_exit,
           overstay_hours = l_overstay_hours,
           overstay_penalty = l_penalty,
           total_amount = l_total,
           status = 'COMPLETED'
     WHERE booking_id = l_booking_id;

    UPDATE QSPARK_PARKING_SLOTS
       SET status = 'AVAILABLE',
           last_updated = CURRENT_TIMESTAMP
     WHERE slot_id = l_slot_id;

    INSERT INTO QSPARK_AUDIT_LOGS
        (changed_by_user_id, slot_id, booking_id, event_type, old_state, new_state, log_details)
    VALUES
        (l_user_id, l_slot_id, l_booking_id, 'CHECKOUT_COMPLETED',
         'RESERVED', 'AVAILABLE', 'Exit settled, penalty ' || TO_CHAR(l_penalty));

    COMMIT;
    :status_code := 200;
    APEX_JSON.OPEN_OBJECT;
    APEX_JSON.WRITE('booking_id', l_booking_id);
    APEX_JSON.WRITE('overstay_hours', l_overstay_hours);
    APEX_JSON.WRITE('penalty_charged', l_penalty);
    APEX_JSON.WRITE('final_total_amount', l_total);
    APEX_JSON.WRITE('new_wallet_balance', l_new_balance);
    APEX_JSON.WRITE('status', 'COMPLETED');
    APEX_JSON.CLOSE_OBJECT;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        ROLLBACK;
        :status_code := 404;
        HTP.P('{"error": "Booking not found"}');
    WHEN OTHERS THEN
        ROLLBACK;
        :status_code := 500;
        HTP.P('{"error": "Checkout transaction failed"}');
END;
]'
    );
    COMMIT;
END;
/

-- ===========================================================================
-- API 5 — PUT bookings/:id/cancel  (instant refund)
-- ===========================================================================
BEGIN
    ORDS.DEFINE_TEMPLATE(
        p_module_name    => 'parking.api.v2',
        p_pattern        => 'bookings/:id/cancel',
        p_comments       => 'Cancellation with full base fare refund'
    );

    ORDS.DEFINE_PARAMETER(
        p_module_name => 'parking.api.v2', p_template_pattern => 'bookings/:id/cancel',
        p_method => 'PUT', p_name => 'id',
        p_bind_variable_name => 'id', p_param_type => 'URI', p_access_method => 'IN'
    );

    ORDS.DEFINE_HANDLER(
        p_module_name    => 'parking.api.v2',
        p_template_pattern => 'bookings/:id/cancel',
        p_method         => 'PUT',
        p_source_type    => 'plsql',
        p_comments       => 'Cancel booking, refund wallet, release bay',
        p_source         => q'[
DECLARE
    l_booking_id NUMBER := TO_NUMBER(:id);
    l_user_id NUMBER;
    l_slot_id NUMBER;
    l_status VARCHAR2(20);
    l_base_amount NUMBER(8,2);
    l_wallet NUMBER(10,2);
    l_new_balance NUMBER(10,2);
BEGIN
    SELECT user_id, slot_id, status, base_amount
      INTO l_user_id, l_slot_id, l_status, l_base_amount
      FROM QSPARK_BOOKINGS
     WHERE booking_id = l_booking_id
       FOR UPDATE;

    IF l_status != 'CONFIRMED' THEN
        :status_code := 409;
        HTP.P('{"error": "Only confirmed bookings can be cancelled"}');
        RETURN;
    END IF;

    SELECT wallet_balance
      INTO l_wallet
      FROM QSPARK_USERS
     WHERE user_id = l_user_id
       FOR UPDATE;

    l_new_balance := l_wallet + l_base_amount;

    UPDATE QSPARK_USERS
       SET wallet_balance = l_new_balance
     WHERE user_id = l_user_id;

    INSERT INTO QSPARK_WALLET_TRANSACTIONS
        (user_id, booking_id, txn_type, previous_balance, amount, new_balance)
    VALUES
        (l_user_id, l_booking_id, 'CANCEL_REFUND', l_wallet, l_base_amount, l_new_balance);

    UPDATE QSPARK_BOOKINGS
       SET status = 'CANCELLED'
     WHERE booking_id = l_booking_id;

    UPDATE QSPARK_PARKING_SLOTS
       SET status = 'AVAILABLE',
           last_updated = CURRENT_TIMESTAMP
     WHERE slot_id = l_slot_id;

    INSERT INTO QSPARK_AUDIT_LOGS
        (changed_by_user_id, slot_id, booking_id, event_type, old_state, new_state, log_details)
    VALUES
        (l_user_id, l_slot_id, l_booking_id, 'BOOKING_CANCELLED',
         'CONFIRMED', 'CANCELLED', 'Refund ' || TO_CHAR(l_base_amount));

    COMMIT;
    :status_code := 200;
    APEX_JSON.OPEN_OBJECT;
    APEX_JSON.WRITE('booking_id', l_booking_id);
    APEX_JSON.WRITE('refunded_amount', l_base_amount);
    APEX_JSON.WRITE('restored_wallet_balance', l_new_balance);
    APEX_JSON.WRITE('slot_status', 'AVAILABLE');
    APEX_JSON.WRITE('status', 'CANCELLED');
    APEX_JSON.CLOSE_OBJECT;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        ROLLBACK;
        :status_code := 404;
        HTP.P('{"error": "Booking not found"}');
    WHEN OTHERS THEN
        ROLLBACK;
        :status_code := 500;
        HTP.P('{"error": "Cancellation transaction failed"}');
END;
]'
    );
    COMMIT;
END;
/

-- ===========================================================================
-- API 6 — GET analytics/kpi  (occupancy, floor heatmaps, revenue)
-- ===========================================================================
BEGIN
    ORDS.DEFINE_TEMPLATE(
        p_module_name    => 'parking.api.v2',
        p_pattern        => 'analytics/kpi',
        p_comments       => 'Facility KPIs, floor heatmaps and collected revenue'
    );

    ORDS.DEFINE_HANDLER(
        p_module_name    => 'parking.api.v2',
        p_template_pattern => 'analytics/kpi',
        p_method         => 'GET',
        p_source_type    => 'plsql',
        p_comments       => 'Real-time admin analytics',
        p_source         => q'[
DECLARE
    l_total NUMBER;
    l_available NUMBER;
    l_reserved NUMBER;
    l_occupied NUMBER;
    l_maintenance NUMBER;
    l_revenue NUMBER(12,2);
BEGIN
    SELECT COUNT(*),
           COUNT(CASE WHEN status = 'AVAILABLE' THEN 1 END),
           COUNT(CASE WHEN status = 'RESERVED' THEN 1 END),
           COUNT(CASE WHEN status = 'OCCUPIED' THEN 1 END),
           COUNT(CASE WHEN status = 'MAINTENANCE' THEN 1 END)
      INTO l_total, l_available, l_reserved, l_occupied, l_maintenance
      FROM QSPARK_PARKING_SLOTS;

    SELECT NVL(SUM(total_amount), 0)
      INTO l_revenue
      FROM QSPARK_BOOKINGS
     WHERE status != 'CANCELLED';

    APEX_JSON.OPEN_OBJECT;
    APEX_JSON.WRITE('total_slots', l_total);
    APEX_JSON.WRITE('available_slots', l_available);
    APEX_JSON.WRITE('reserved_slots', l_reserved);
    APEX_JSON.WRITE('occupied_slots', l_occupied);
    APEX_JSON.WRITE('maintenance_slots', l_maintenance);
    APEX_JSON.WRITE('occupancy_rate_percent',
                    CASE WHEN l_total = 0 THEN 0
                         ELSE ROUND(100 * (l_total - l_available) / l_total, 2) END);
    APEX_JSON.WRITE('total_revenue_collected', l_revenue);

    APEX_JSON.OPEN_ARRAY('floor_heatmaps');
    FOR f IN (
        SELECT f.floor_code,
               COUNT(s.slot_id) AS total_slots,
               COUNT(CASE WHEN s.status != 'AVAILABLE' THEN 1 END) AS occupied_slots
          FROM QSPARK_FLOORS f
          LEFT JOIN QSPARK_PARKING_SLOTS s
            ON s.floor_id = f.floor_id
         GROUP BY f.floor_code
         ORDER BY f.floor_code
    ) LOOP
        APEX_JSON.OPEN_OBJECT;
        APEX_JSON.WRITE('floor_code', f.floor_code);
        APEX_JSON.WRITE('total', f.total_slots);
        APEX_JSON.WRITE('occupied', f.occupied_slots);
        APEX_JSON.WRITE('occupancy_percent',
                        CASE WHEN f.total_slots = 0 THEN 0
                             ELSE ROUND(100 * f.occupied_slots / f.total_slots, 2) END);
        APEX_JSON.CLOSE_OBJECT;
    END LOOP;
    APEX_JSON.CLOSE_ARRAY;

    APEX_JSON.CLOSE_OBJECT;
    :status_code := 200;
EXCEPTION
    WHEN OTHERS THEN
        :status_code := 500;
        HTP.P('{"error": "Unable to load analytics"}');
END;
]'
    );
    COMMIT;
END;
/
