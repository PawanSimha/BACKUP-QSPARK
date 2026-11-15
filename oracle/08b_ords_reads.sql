-- oracle/08b_ords_reads.sql
-- STEP 2 of 3. Run after 08a finished clean. Creates 5 reusable read procedures
-- and 34 GET handlers (33 routes + the legacy 'slots' alias).
--
-- Identity: ORDS has no session. The Flask proxy passes ?actor_user_id= and
-- ?actor_role= from the Flask session. Never expose these endpoints directly.

SET DEFINE OFF
SET SERVEROUTPUT ON

-- ---------------------------------------------------------------------------
-- Reusable readers (each backs 1-2 templates)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE qspark_r_floors IS
  v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'floor_id'          VALUE floor_id,
           'floor_code'        VALUE floor_code,
           'floor_status'      VALUE floor_status,
           'total_slots'       VALUE total_slots,
           'available_slots'   VALUE available_slots,
           'reserved_slots'    VALUE reserved_slots,
           'occupied_slots'    VALUE occupied_slots,
           'maintenance_slots' VALUE maintenance_slots))
    INTO v
    FROM (SELECT f.floor_id, f.floor_code, f.floor_status,
                 COUNT(s.slot_id) AS total_slots,
                 SUM(CASE WHEN s.status = 'AVAILABLE'   THEN 1 ELSE 0 END) AS available_slots,
                 SUM(CASE WHEN s.status = 'RESERVED'    THEN 1 ELSE 0 END) AS reserved_slots,
                 SUM(CASE WHEN s.status = 'OCCUPIED'    THEN 1 ELSE 0 END) AS occupied_slots,
                 SUM(CASE WHEN s.status = 'MAINTENANCE' THEN 1 ELSE 0 END) AS maintenance_slots
            FROM qspark_floors f
            LEFT JOIN qspark_v_slots_live s ON s.floor_id = f.floor_id
           GROUP BY f.floor_id, f.floor_code, f.floor_status
           ORDER BY f.floor_code);
  qspark_items(v);
END;
/

CREATE OR REPLACE PROCEDURE qspark_r_vtypes(p_active_only NUMBER DEFAULT 0) IS
  v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'vehicle_type_id' VALUE vehicle_type_id,
           'type_name'       VALUE type_name,
           'hourly_rate'     VALUE hourly_rate,
           'overstay_rate'   VALUE overstay_rate,
           'is_active'       VALUE is_active))
    INTO v
    FROM (SELECT vehicle_type_id, type_name, hourly_rate, overstay_rate, is_active
            FROM qspark_vehicle_types
           WHERE p_active_only = 0 OR is_active = 1
           ORDER BY vehicle_type_id);
  qspark_items(v);
END;
/

CREATE OR REPLACE PROCEDURE qspark_r_slots(p_floor NUMBER DEFAULT NULL) IS
  v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'slot_id'         VALUE slot_id,
           'slot_number'     VALUE slot_number,
           'floor_id'        VALUE floor_id,
           'vehicle_type_id' VALUE vehicle_type_id,
           'control_status'  VALUE control_status,
           'status'          VALUE status,
           'floor_code'      VALUE floor_code,
           'vehicle_type'    VALUE vehicle_type,
           'occupant'        VALUE occupant FORMAT JSON) RETURNING CLOB)
    INTO v
    FROM (SELECT s.slot_id, s.slot_number, s.floor_id, s.vehicle_type_id,
                 s.control_status, s.status, s.floor_code, s.type_name AS vehicle_type,
                 (SELECT JSON_OBJECT(
                           'booking_reference' VALUE b.booking_reference,
                           'full_name'         VALUE u.full_name,
                           'username'          VALUE u.username,
                           'vehicle_number'    VALUE b.vehicle_number,
                           'booked_from'       VALUE b.booked_from,
                           'booked_until'      VALUE b.booked_until,
                           'booking_status'    VALUE b.booking_status,
                           'entry_time'        VALUE (SELECT MAX(e.created_at)
                                                        FROM qspark_booking_events e
                                                       WHERE e.booking_id = b.booking_id
                                                         AND e.event_type = 'ENTRY'))
                    FROM qspark_bookings b
                    JOIN qspark_users u ON u.user_id = b.user_id
                   WHERE b.slot_id = s.slot_id
                     AND b.booking_status IN ('HELD', 'CONFIRMED')
                     AND ROWNUM = 1) AS occupant
            FROM qspark_v_slots_live s
           WHERE p_floor IS NULL OR s.floor_id = p_floor
           ORDER BY s.floor_id, s.slot_number);
  qspark_items(v);
END;
/

CREATE OR REPLACE PROCEDURE qspark_r_users IS
  v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'user_id'        VALUE user_id,
           'admin_id'       VALUE admin_id,
           'full_name'      VALUE full_name,
           'email'          VALUE email,
           'phone'          VALUE phone,
           'gender'         VALUE gender,
           'company_name'   VALUE company_name,
           'username'       VALUE username,
           'role'           VALUE role,
           'wallet_balance' VALUE wallet_balance,
           'account_status' VALUE account_status,
           'created_at'     VALUE created_at))
    INTO v
    FROM (SELECT user_id, admin_id, full_name, email, phone, gender, company_name,
                 username, role, wallet_balance, account_status, created_at
            FROM qspark_users
           ORDER BY role, user_id);
  qspark_items(v);
END;
/

CREATE OR REPLACE PROCEDURE qspark_r_rules IS
  v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'rule_id'          VALUE rule_id,
           'rule_code'        VALUE rule_code,
           'rule_name'        VALUE rule_name,
           'min_hours_before' VALUE min_hours_before,
           'max_hours_before' VALUE max_hours_before,
           'is_no_show'       VALUE is_no_show,
           'refund_percent'   VALUE refund_percent,
           'penalty_percent'  VALUE penalty_percent,
           'description'      VALUE description,
           'is_active'        VALUE is_active))
    INTO v
    FROM (SELECT rule_id, rule_code, rule_name, min_hours_before, max_hours_before,
                 is_no_show, refund_percent, penalty_percent, description, is_active
            FROM qspark_cancellation_rules
           ORDER BY rule_code);
  qspark_items(v);
END;
/

-- ---------------------------------------------------------------------------
-- slots
-- ---------------------------------------------------------------------------
BEGIN
  qspark_h('api/slots/availability', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'slot_id' VALUE slot_id, 'slot_number' VALUE slot_number,
           'floor_id' VALUE floor_id, 'vehicle_type_id' VALUE vehicle_type_id,
           'control_status' VALUE control_status, 'status' VALUE status,
           'floor_code' VALUE floor_code, 'vehicle_type' VALUE type_name,
           'hourly_rate' VALUE hourly_rate, 'overstay_rate' VALUE overstay_rate))
    INTO v FROM (SELECT * FROM qspark_v_slots_live ORDER BY floor_id, slot_number);
  qspark_json(NVL(v, '[]'));
END;!');

  qspark_h('slots', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'slot_id' VALUE slot_id, 'slot_number' VALUE slot_number,
           'floor_id' VALUE floor_id, 'vehicle_type_id' VALUE vehicle_type_id,
           'control_status' VALUE control_status, 'status' VALUE status,
           'floor_code' VALUE floor_code, 'vehicle_type' VALUE type_name,
           'hourly_rate' VALUE hourly_rate, 'overstay_rate' VALUE overstay_rate))
    INTO v FROM (SELECT * FROM qspark_v_slots_live ORDER BY floor_id, slot_number);
  qspark_json(NVL(v, '[]'));
END;!');

  qspark_h('api/slots/floors', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'floor_id' VALUE floor_id, 'floor_code' VALUE floor_code,
           'floor_status' VALUE floor_status, 'total_slots' VALUE total_slots,
           'available_slots' VALUE available_slots))
    INTO v
    FROM (SELECT f.floor_id, f.floor_code, f.floor_status,
                 COUNT(s.slot_id) AS total_slots,
                 SUM(CASE WHEN s.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_slots
            FROM qspark_floors f
            LEFT JOIN qspark_v_slots_live s ON s.floor_id = f.floor_id
           WHERE f.floor_status <> 'INACTIVE'
           GROUP BY f.floor_id, f.floor_code, f.floor_status
           ORDER BY f.floor_code);
  qspark_items(v);
END;!');

  qspark_h('api/slots/vehicle-types', 'GET', q'!
BEGIN qspark_r_vtypes(1); END;!');

  qspark_h('api/slots/:slot_id', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_OBJECT(
           'slot_id' VALUE slot_id, 'slot_number' VALUE slot_number,
           'floor_id' VALUE floor_id, 'vehicle_type_id' VALUE vehicle_type_id,
           'control_status' VALUE control_status, 'status' VALUE status,
           'floor_code' VALUE floor_code, 'vehicle_type' VALUE type_name,
           'hourly_rate' VALUE hourly_rate, 'overstay_rate' VALUE overstay_rate)
    INTO v FROM qspark_v_slots_live WHERE slot_id = qspark_num(:slot_id);
  IF v IS NULL THEN qspark_err(404, 'Slot not found'); ELSE qspark_json(v); END IF;
EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Slot not found');
END;!');

  -- -------------------------------------------------------------------------
  -- bookings
  -- -------------------------------------------------------------------------
  qspark_h('api/bookings/my', 'GET', q'!
DECLARE v CLOB; n NUMBER;
BEGIN
  IF qspark_num(:actor_user_id) IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'booking_id' VALUE booking_id, 'booking_reference' VALUE booking_reference,
           'user_id' VALUE user_id, 'slot_id' VALUE slot_id,
           'vehicle_format' VALUE vehicle_format, 'vehicle_number' VALUE vehicle_number,
           'booked_from' VALUE booked_from, 'booked_until' VALUE booked_until,
           'hold_expires_at' VALUE hold_expires_at,
           'hourly_rate_applied' VALUE hourly_rate_applied,
           'overstay_rate_applied' VALUE overstay_rate_applied,
           'estimated_amount' VALUE estimated_amount,
           'booking_status' VALUE booking_status,
           'floor_code' VALUE floor_code, 'slot_number' VALUE slot_number,
           'vehicle_type' VALUE vehicle_type, 'has_entered' VALUE has_entered))
    INTO v
    FROM (SELECT b.booking_id, b.booking_reference, b.user_id, b.slot_id, b.vehicle_format,
                 b.vehicle_number, b.booked_from, b.booked_until, b.hold_expires_at,
                 b.hourly_rate_applied, b.overstay_rate_applied, b.estimated_amount,
                 b.booking_status, f.floor_code, s.slot_number, vt.type_name AS vehicle_type,
                 CASE WHEN EXISTS (SELECT 1 FROM qspark_booking_events e
                                    WHERE e.booking_id = b.booking_id AND e.event_type = 'ENTRY')
                       AND NOT EXISTS (SELECT 1 FROM qspark_booking_events x
                                        WHERE x.booking_id = b.booking_id AND x.event_type = 'EXIT')
                      THEN 1 ELSE 0 END AS has_entered
            FROM qspark_bookings b
            JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
            JOIN qspark_floors f ON f.floor_id = s.floor_id
            JOIN qspark_vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
           WHERE b.user_id = qspark_num(:actor_user_id)
           ORDER BY b.booked_from DESC);
  qspark_items(v);
END;!');

  qspark_h('api/bookings/:ref', 'GET', q'!
DECLARE v CLOB; v_id NUMBER; v_owner NUMBER;
BEGIN
  SELECT b.booking_id, b.user_id INTO v_id, v_owner
    FROM qspark_bookings b WHERE b.booking_reference = :ref;
  IF qspark_num(:actor_user_id) IS NOT NULL AND v_owner <> qspark_num(:actor_user_id)
     AND NVL(:actor_role, 'CUSTOMER') NOT IN ('ADMIN', 'SUPER_ADMIN') THEN
    qspark_err(403, 'Not authorized'); RETURN;
  END IF;
  SELECT JSON_OBJECT(
           'booking_id' VALUE b.booking_id, 'booking_reference' VALUE b.booking_reference,
           'user_id' VALUE b.user_id, 'slot_id' VALUE b.slot_id,
           'vehicle_format' VALUE b.vehicle_format, 'vehicle_number' VALUE b.vehicle_number,
           'booked_from' VALUE b.booked_from, 'booked_until' VALUE b.booked_until,
           'hold_expires_at' VALUE b.hold_expires_at,
           'hourly_rate_applied' VALUE b.hourly_rate_applied,
           'overstay_rate_applied' VALUE b.overstay_rate_applied,
           'estimated_amount' VALUE b.estimated_amount,
           'booking_status' VALUE b.booking_status,
           'applied_cancellation_rule_id' VALUE b.applied_cancellation_rule_id,
           'floor_code' VALUE f.floor_code, 'slot_number' VALUE s.slot_number,
           'vehicle_type' VALUE vt.type_name,
           'full_name' VALUE u.full_name, 'phone' VALUE u.phone,
           'events' VALUE (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                                     'event_type' VALUE e.event_type,
                                     'scan_method' VALUE e.scan_method,
                                     'created_at' VALUE e.created_at))
                             FROM qspark_booking_events e WHERE e.booking_id = b.booking_id)
           FORMAT JSON RETURNING CLOB)
    INTO v
    FROM qspark_bookings b
    JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
    JOIN qspark_floors f ON f.floor_id = s.floor_id
    JOIN qspark_vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
    JOIN qspark_users u ON u.user_id = b.user_id
   WHERE b.booking_reference = :ref;
  qspark_json(v);
EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Booking not found');
END;!');

  qspark_h('api/bookings/wallet/transactions/me', 'GET', q'!
DECLARE v CLOB; b NUMBER;
BEGIN
  IF qspark_num(:actor_user_id) IS NULL THEN qspark_err(401, 'Authentication required'); RETURN; END IF;
  SELECT wallet_balance INTO b FROM qspark_users WHERE user_id = qspark_num(:actor_user_id);
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'transaction_reference' VALUE transaction_reference,
           'transaction_type' VALUE transaction_type, 'direction' VALUE direction,
           'amount' VALUE amount, 'balance_after' VALUE balance_after,
           'description' VALUE description, 'created_at' VALUE created_at))
    INTO v
    FROM (SELECT transaction_reference, transaction_type, direction, amount,
                 balance_after, description, created_at
            FROM qspark_wallet_transactions
           WHERE user_id = qspark_num(:actor_user_id)
           ORDER BY created_at DESC);
  SELECT JSON_OBJECT('wallet_balance' VALUE b,
                          'transactions' VALUE NVL(v, '[]') FORMAT JSON RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'User not found');
END;!');

  -- -------------------------------------------------------------------------
  -- admin reads
  -- -------------------------------------------------------------------------
  qspark_h('api/admin/dashboard', 'GET', q'!
DECLARE v_total NUMBER; v_av NUMBER; v_rs NUMBER; v_oc NUMBER; v_mt NUMBER;
        v_rev NUMBER; v_users NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_total FROM qspark_parking_slots;
  SELECT NVL(SUM(CASE WHEN status = 'AVAILABLE'   THEN 1 ELSE 0 END), 0),
         NVL(SUM(CASE WHEN status = 'RESERVED'    THEN 1 ELSE 0 END), 0),
         NVL(SUM(CASE WHEN status = 'OCCUPIED'    THEN 1 ELSE 0 END), 0),
         NVL(SUM(CASE WHEN status = 'MAINTENANCE' THEN 1 ELSE 0 END), 0)
    INTO v_av, v_rs, v_oc, v_mt FROM qspark_v_slots_live;
  SELECT NVL(SUM(CASE WHEN collection_type = 'REFUND_REVERSAL' THEN -amount ELSE amount END), 0)
    INTO v_rev FROM qspark_revenue_collections;
  SELECT COUNT(*) INTO v_users FROM qspark_users
   WHERE role = 'CUSTOMER' AND account_status = 'ACTIVE';
  qspark_json(JSON_OBJECT(
    'total_slots' VALUE v_total, 'available_slots' VALUE v_av,
    'reserved_slots' VALUE v_rs, 'occupied_slots' VALUE v_oc,
    'maintenance_slots' VALUE v_mt, 'total_revenue' VALUE ROUND(v_rev, 2),
    'active_users' VALUE v_users));
END;!');

  qspark_h('api/admin/bookings', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'booking_reference' VALUE booking_reference, 'booking_status' VALUE booking_status,
           'booked_from' VALUE booked_from, 'booked_until' VALUE booked_until,
           'estimated_amount' VALUE estimated_amount, 'vehicle_number' VALUE vehicle_number,
           'vehicle_format' VALUE vehicle_format, 'username' VALUE username,
           'full_name' VALUE full_name, 'role' VALUE role, 'floor_code' VALUE floor_code,
           'slot_number' VALUE slot_number, 'vehicle_type' VALUE vehicle_type,
           'entry_time' VALUE entry_time, 'exit_time' VALUE exit_time))
    INTO v
    FROM (SELECT b.booking_reference, b.booking_status, b.booked_from, b.booked_until,
                 b.estimated_amount, b.vehicle_number, b.vehicle_format,
                 u.username, u.full_name, u.role, f.floor_code, s.slot_number,
                 vt.type_name AS vehicle_type,
                 (SELECT MAX(be.created_at) FROM qspark_booking_events be
                   WHERE be.booking_id = b.booking_id AND be.event_type = 'ENTRY') AS entry_time,
                 (SELECT MAX(be.created_at) FROM qspark_booking_events be
                   WHERE be.booking_id = b.booking_id AND be.event_type = 'EXIT') AS exit_time
            FROM qspark_bookings b
            JOIN qspark_users u ON u.user_id = b.user_id
            JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
            JOIN qspark_floors f ON f.floor_id = s.floor_id
            JOIN qspark_vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
           WHERE (:status IS NULL OR b.booking_status = :status)
             AND (:floor IS NULL OR f.floor_code = :floor)
             AND (:vehicle_type IS NULL OR vt.type_name = :vehicle_type)
             AND (:date_from IS NULL OR b.booked_from >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD'))
             AND (:date_to IS NULL OR b.booked_from < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1)
             AND (:user_search IS NULL
                  OR LOWER(u.username) LIKE '%' || LOWER(:user_search) || '%'
                  OR LOWER(u.full_name) LIKE '%' || LOWER(:user_search) || '%')
           ORDER BY b.booked_from DESC);
  SELECT JSON_OBJECT('items' VALUE NVL(v, '[]') FORMAT JSON,
    'total' VALUE (SELECT COUNT(*) FROM qspark_bookings) RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
END;!');

  qspark_h('api/admin/users', 'GET', q'!BEGIN qspark_r_users; END;!');
  qspark_h('api/admin/master/users', 'GET', q'!BEGIN qspark_r_users; END;!');

  qspark_h('api/admin/users/:user_id', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_OBJECT('user_id' VALUE user_id, 'admin_id' VALUE admin_id,
           'full_name' VALUE full_name, 'email' VALUE email, 'phone' VALUE phone,
           'gender' VALUE gender, 'company_name' VALUE company_name,
           'username' VALUE username, 'role' VALUE role,
           'wallet_balance' VALUE wallet_balance, 'account_status' VALUE account_status,
           'created_at' VALUE created_at)
    INTO v FROM qspark_users WHERE user_id = qspark_num(:user_id);
  IF v IS NULL THEN qspark_err(404, 'User not found'); ELSE qspark_json(v); END IF;
EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'User not found');
END;!');

  qspark_h('api/admin/users/:user_id/wallet', 'GET', q'!
DECLARE v CLOB; b NUMBER;
BEGIN
  SELECT wallet_balance INTO b FROM qspark_users WHERE user_id = qspark_num(:user_id);
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'transaction_reference' VALUE transaction_reference,
           'transaction_type' VALUE transaction_type, 'direction' VALUE direction,
           'amount' VALUE amount, 'balance_after' VALUE balance_after,
           'description' VALUE description, 'created_at' VALUE created_at))
    INTO v
    FROM (SELECT transaction_reference, transaction_type, direction, amount,
                 balance_after, description, created_at
            FROM qspark_wallet_transactions
           WHERE user_id = qspark_num(:user_id) ORDER BY created_at DESC);
  SELECT JSON_OBJECT('user_id' VALUE qspark_num(:user_id), 'wallet_balance' VALUE b,
                          'transactions' VALUE NVL(v, '[]') FORMAT JSON RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'User not found');
END;!');

  qspark_h('api/admin/floors', 'GET', q'!BEGIN qspark_r_floors; END;!');
  qspark_h('api/admin/master/floors', 'GET', q'!BEGIN qspark_r_floors; END;!');
  qspark_h('api/admin/vehicle-types', 'GET', q'!BEGIN qspark_r_vtypes(0); END;!');
  qspark_h('api/admin/master/vehicle-types', 'GET', q'!BEGIN qspark_r_vtypes(0); END;!');
  qspark_h('api/admin/slots', 'GET', q'!BEGIN qspark_r_slots(qspark_num(:floor_id)); END;!');
  qspark_h('api/admin/master/slots', 'GET', q'!BEGIN qspark_r_slots(qspark_num(:floor_id)); END;!');
  qspark_h('api/admin/cancellation-rules', 'GET', q'!BEGIN qspark_r_rules; END;!');
  qspark_h('api/admin/master/cancellation-rules', 'GET', q'!BEGIN qspark_r_rules; END;!');

  -- -------------------------------------------------------------------------
  -- reports
  -- -------------------------------------------------------------------------
  qspark_h('api/admin/reports/occupancy', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'floor_code' VALUE floor_code, 'floor_status' VALUE floor_status,
           'total_slots' VALUE total_slots, 'occupied_slots' VALUE occupied_slots,
           'occupancy_percent' VALUE CASE WHEN total_slots = 0 THEN 0
                                          ELSE ROUND(100 * occupied_slots / total_slots, 2) END)
    INTO v
    FROM (SELECT f.floor_code, f.floor_status,
                 COUNT(s.slot_id) AS total_slots,
                 NVL(SUM(CASE WHEN s.status IN ('RESERVED', 'OCCUPIED') THEN 1 ELSE 0 END), 0) AS occupied_slots
            FROM qspark_floors f
            LEFT JOIN qspark_v_slots_live s ON s.floor_id = f.floor_id
           WHERE (:date_from IS NULL OR EXISTS (SELECT 1 FROM qspark_bookings b
                                                 WHERE b.slot_id = s.slot_id
                                                   AND b.booked_from >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD')))
             AND (:date_to IS NULL OR EXISTS (SELECT 1 FROM qspark_bookings b
                                               WHERE b.slot_id = s.slot_id
                                                 AND b.booked_from < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1))
           GROUP BY f.floor_id, f.floor_code, f.floor_status
           ORDER BY f.floor_code));
  SELECT JSON_OBJECT('floor_heatmaps' VALUE NVL(v, '[]') FORMAT JSON,
                          'date_from' VALUE :date_from, 'date_to' VALUE :date_to RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
END;!');

  qspark_h('api/admin/reports/revenue', 'GET', q'!
DECLARE v CLOB; g NUMBER;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'floor_code' VALUE floor_code, 'booking_count' VALUE booking_count,
           'total_revenue' VALUE total_revenue, 'net_revenue' VALUE net_revenue))
    INTO v
    FROM (SELECT f.floor_code,
                 COUNT(DISTINCT b.booking_id) AS booking_count,
                 ROUND(SUM(rc.amount), 2) AS total_revenue,
                 ROUND(SUM(CASE WHEN rc.collection_type = 'REFUND_REVERSAL' THEN -rc.amount
                                ELSE rc.amount END), 2) AS net_revenue
            FROM qspark_revenue_collections rc
            JOIN qspark_bookings b ON b.booking_id = rc.booking_id
            JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
            JOIN qspark_floors f ON f.floor_id = s.floor_id
           WHERE (:date_from IS NULL OR rc.created_at >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD'))
             AND (:date_to IS NULL OR rc.created_at < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1)
           GROUP BY f.floor_id, f.floor_code
           ORDER BY f.floor_code);
  SELECT NVL(ROUND(SUM(amount), 2), 0) INTO g FROM qspark_revenue_collections
   WHERE (:date_from IS NULL OR created_at >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD'))
     AND (:date_to IS NULL OR created_at < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1);
  SELECT JSON_OBJECT('floor_revenue' VALUE NVL(v, '[]') FORMAT JSON,
                          'grand_total' VALUE g,
                          'date_from' VALUE :date_from, 'date_to' VALUE :date_to RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
END;!');

  qspark_h('api/admin/reports/revenue-summary', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'collection_type' VALUE collection_type, 'count' VALUE cnt,
           'total_amount' VALUE total_amount))
    INTO v
    FROM (SELECT collection_type, COUNT(*) AS cnt, ROUND(SUM(amount), 2) AS total_amount
            FROM qspark_revenue_collections
           WHERE (:date_from IS NULL OR created_at >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD'))
             AND (:date_to IS NULL OR created_at < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1)
           GROUP BY collection_type);
  SELECT JSON_OBJECT('revenue_summary' VALUE NVL(v, '[]') FORMAT JSON RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
END;!');

  -- -------------------------------------------------------------------------
  -- super admin reads
  -- -------------------------------------------------------------------------
  qspark_h('api/super-admin/admins', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'user_id' VALUE user_id, 'admin_id' VALUE admin_id, 'full_name' VALUE full_name,
           'phone' VALUE phone, 'email' VALUE email, 'gender' VALUE gender,
           'company_name' VALUE company_name, 'username' VALUE username,
           'account_status' VALUE account_status, 'wallet_balance' VALUE wallet_balance,
           'created_at' VALUE created_at, 'role' VALUE role))
    INTO v
    FROM (SELECT user_id, admin_id, full_name, phone, email, gender, company_name,
                 username, account_status, wallet_balance, created_at, role
            FROM qspark_users
           WHERE role IN ('ADMIN', 'SUPER_ADMIN')
           ORDER BY role, admin_id);
  qspark_items(v);
END;!');

  qspark_h('api/super-admin/admins/:user_id', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_OBJECT('user_id' VALUE user_id, 'admin_id' VALUE admin_id,
           'full_name' VALUE full_name, 'phone' VALUE phone, 'email' VALUE email,
           'gender' VALUE gender, 'company_name' VALUE company_name,
           'username' VALUE username, 'account_status' VALUE account_status,
           'wallet_balance' VALUE wallet_balance, 'created_at' VALUE created_at,
           'role' VALUE role)
    INTO v FROM qspark_users
   WHERE user_id = qspark_num(:user_id) AND role IN ('ADMIN', 'SUPER_ADMIN');
  IF v IS NULL THEN qspark_err(404, 'Admin not found'); ELSE qspark_json(v); END IF;
EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'Admin not found');
END;!');

  qspark_h('api/super-admin/users/:user_id/wallet', 'GET', q'!
DECLARE v CLOB; b NUMBER;
BEGIN
  SELECT wallet_balance INTO b FROM qspark_users WHERE user_id = qspark_num(:user_id);
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'transaction_id' VALUE transaction_id,
           'transaction_reference' VALUE transaction_reference,
           'transaction_type' VALUE transaction_type, 'direction' VALUE direction,
           'amount' VALUE amount, 'balance_after' VALUE balance_after,
           'description' VALUE description, 'created_at' VALUE created_at))
    INTO v
    FROM (SELECT transaction_id, transaction_reference, transaction_type, direction,
                 amount, balance_after, description, created_at
            FROM qspark_wallet_transactions
           WHERE user_id = qspark_num(:user_id) ORDER BY created_at DESC);
  SELECT JSON_OBJECT('user_id' VALUE qspark_num(:user_id), 'wallet_balance' VALUE b,
                          'transactions' VALUE NVL(v, '[]') FORMAT JSON RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
EXCEPTION WHEN NO_DATA_FOUND THEN qspark_err(404, 'User not found');
END;!');

  qspark_h('api/super-admin/analytics/overview', 'GET', q'!
DECLARE v_cust NUMBER; v_book NUMBER; v_done NUMBER; v_rev NUMBER;
        v_slots NUMBER; v_occ NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_cust FROM qspark_users WHERE role = 'CUSTOMER' AND account_status = 'ACTIVE';
  SELECT COUNT(*) INTO v_book FROM qspark_bookings
   WHERE (:date_from IS NULL OR booked_from >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD'))
     AND (:date_to IS NULL OR booked_from < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1);
  SELECT COUNT(*) INTO v_done FROM qspark_bookings WHERE booking_status = 'COMPLETED';
  SELECT NVL(SUM(CASE WHEN collection_type = 'REFUND_REVERSAL' THEN -amount ELSE amount END), 0)
    INTO v_rev FROM qspark_revenue_collections;
  SELECT COUNT(*) INTO v_slots FROM qspark_parking_slots;
  SELECT NVL(SUM(CASE WHEN status IN ('RESERVED', 'OCCUPIED') THEN 1 ELSE 0 END), 0)
    INTO v_occ FROM qspark_v_slots_live;
  qspark_json(JSON_OBJECT(
    'total_customers' VALUE v_cust, 'total_bookings' VALUE v_book,
    'completed_bookings' VALUE v_done, 'net_revenue' VALUE ROUND(v_rev, 2),
    'total_slots' VALUE v_slots, 'occupied_slots' VALUE v_occ,
    'occupancy_percent' VALUE CASE WHEN v_slots = 0 THEN 0
                                   ELSE ROUND(100 * v_occ / v_slots, 2) END));
END;!');

  qspark_h('api/super-admin/analytics/overtime', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'day' VALUE TO_CHAR(created_at, 'YYYY-MM-DD'),
           'count' VALUE cnt, 'amount' VALUE amount))
    INTO v
    FROM (SELECT TRUNC(created_at) AS created_at, COUNT(*) AS cnt, NVL(SUM(amount), 0) AS amount
            FROM qspark_wallet_transactions
           WHERE transaction_type = 'OVERTIME_DEBIT'
           GROUP BY TRUNC(created_at)
           ORDER BY TRUNC(created_at) DESC
           FETCH FIRST 30 ROWS ONLY);
  SELECT JSON_OBJECT('overtime' VALUE NVL(v, '[]') FORMAT JSON RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
END;!');

  qspark_h('api/super-admin/analytics/floor-heatmap', 'GET', q'!
DECLARE v CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT(
           'floor_code' VALUE floor_code, 'floor_status' VALUE floor_status,
           'total_slots' VALUE total_slots, 'occupied_slots' VALUE occupied_slots,
           'occupancy_percent' VALUE CASE WHEN total_slots = 0 THEN 0
                                          ELSE ROUND(100 * occupied_slots / total_slots, 2) END)
    INTO v
    FROM (SELECT f.floor_code, f.floor_status, COUNT(s.slot_id) AS total_slots,
                 NVL(SUM(CASE WHEN s.status IN ('RESERVED', 'OCCUPIED') THEN 1 ELSE 0 END), 0) AS occupied_slots
            FROM qspark_floors f
            LEFT JOIN qspark_v_slots_live s ON s.floor_id = f.floor_id
           GROUP BY f.floor_id, f.floor_code, f.floor_status
           ORDER BY f.floor_code));
  SELECT JSON_OBJECT('floors' VALUE NVL(v, '[]') FORMAT JSON RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
END;!');

  qspark_h('api/super-admin/analytics/revenue', 'GET', q'!
DECLARE vf CLOB; vv CLOB; vd CLOB;
BEGIN
  SELECT JSON_ARRAYAGG(JSON_OBJECT('floor_code' VALUE floor_code, 'amount' VALUE amount)) INTO vf
    FROM (SELECT f.floor_code, NVL(SUM(rc.amount), 0) AS amount
            FROM qspark_revenue_collections rc
            JOIN qspark_bookings b ON b.booking_id = rc.booking_id
            JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
            JOIN qspark_floors f ON f.floor_id = s.floor_id
           WHERE (:date_from IS NULL OR b.booked_from >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD'))
             AND (:date_to IS NULL OR b.booked_from < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1)
           GROUP BY f.floor_code ORDER BY f.floor_code);
  SELECT JSON_ARRAYAGG(JSON_OBJECT('type_name' VALUE type_name, 'amount' VALUE amount)) INTO vv
    FROM (SELECT vt.type_name, NVL(SUM(rc.amount), 0) AS amount
            FROM qspark_revenue_collections rc
            JOIN qspark_bookings b ON b.booking_id = rc.booking_id
            JOIN qspark_parking_slots s ON s.slot_id = b.slot_id
            JOIN qspark_vehicle_types vt ON vt.vehicle_type_id = s.vehicle_type_id
           WHERE (:date_from IS NULL OR b.booked_from >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD'))
             AND (:date_to IS NULL OR b.booked_from < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1)
           GROUP BY vt.type_name);
  SELECT JSON_ARRAYAGG(JSON_OBJECT('day' VALUE TO_CHAR(created_at, 'YYYY-MM-DD'),
                                   'amount' VALUE amount)) INTO vd
    FROM (SELECT TRUNC(rc.created_at) AS created_at, NVL(SUM(rc.amount), 0) AS amount
            FROM qspark_revenue_collections rc
            JOIN qspark_bookings b ON b.booking_id = rc.booking_id
           WHERE (:date_from IS NULL OR b.booked_from >= TO_TIMESTAMP(:date_from, 'YYYY-MM-DD'))
             AND (:date_to IS NULL OR b.booked_from < TO_TIMESTAMP(:date_to, 'YYYY-MM-DD') + 1)
           GROUP BY TRUNC(rc.created_at) ORDER BY TRUNC(rc.created_at));
  SELECT JSON_OBJECT('by_floor' VALUE NVL(vf, '[]') FORMAT JSON,
                          'by_vehicle_type' VALUE NVL(vv, '[]') FORMAT JSON,
                          'by_day' VALUE NVL(vd, '[]') FORMAT JSON RETURNING CLOB) INTO v FROM dual;
  qspark_json(v);
END;!');

  -- -------------------------------------------------------------------------
  -- system reads
  -- -------------------------------------------------------------------------
  qspark_h('api/system/status', 'GET', q'!
DECLARE v VARCHAR2(500);
BEGIN
  SELECT setting_value INTO v FROM qspark_system_settings WHERE setting_key = 'SYSTEM_STATUS';
  qspark_json(JSON_OBJECT('system_status' VALUE v));
EXCEPTION WHEN NO_DATA_FOUND THEN
  qspark_json(JSON_OBJECT('system_status' VALUE 'ONLINE'));
END;!');

  qspark_h('api/system/super-admin/session', 'GET', q'!
DECLARE v NUMBER := 20; u TIMESTAMP(0);
BEGIN
  BEGIN
    SELECT TO_NUMBER(setting_value), updated_at INTO v, u
      FROM qspark_system_settings WHERE setting_key = 'SESSION_IDLE_TIMEOUT';
  EXCEPTION WHEN NO_DATA_FOUND THEN NULL;
  END;
  qspark_json(JSON_OBJECT('idle_timeout_minutes' VALUE v,
                          'absolute_max_minutes' VALUE 20,
                          'updated_at' VALUE u));
END;!');

  COMMIT;
END;
/

-- Expected: 64 handlers (63 routes + the 'slots' alias)
SELECT COUNT(*) AS handler_count
  FROM user_ords_handlers h
  JOIN user_ords_templates t ON t.id = h.template_id
  JOIN user_ords_modules m ON m.id = t.module_id
 WHERE m.name = 'qsparking.api.v3';
