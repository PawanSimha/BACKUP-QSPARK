-- oracle/07_view_slots_live.sql
-- View: QSPARK_V_SLOTS_LIVE
-- Provides live slot status (AVAILABLE/RESERVED/OCCUPIED/MAINTENANCE/INACTIVE)
-- computed from control_status + open booking events.
-- Used by: slots, reports-occupancy, admin-floors ORDS handlers.

create or replace view NOV_2026_BATCH.QSPARK_V_SLOTS_LIVE as
with slot_status_base as (
  select
    s.slot_id,
    s.slot_number,
    s.floor_id,
    s.vehicle_type_id,
    s.control_status,
    f.floor_code,
    f.floor_status,
    v.type_name,
    v.hourly_rate,
    v.overstay_rate,
    case
      when s.control_status = 'INACTIVE' then 'INACTIVE'
      when s.control_status = 'MAINTENANCE' then 'MAINTENANCE'
      when s.control_status = 'ADMIN_RESERVED' then 'RESERVED'
      when exists (
        select 1 from NOV_2026_BATCH.QSPARK_BOOKINGS b
        join NOV_2026_BATCH.QSPARK_BOOKING_EVENTS e
          on e.booking_id = b.booking_id and e.event_type = 'ENTRY'
        where b.slot_id = s.slot_id
          and b.booking_status in ('HELD','CONFIRMED')
          and not exists (
            select 1 from NOV_2026_BATCH.QSPARK_BOOKING_EVENTS x
            where x.booking_id = b.booking_id and x.event_type = 'EXIT'
          )
      ) then 'OCCUPIED'
      when exists (
        select 1 from NOV_2026_BATCH.QSPARK_BOOKINGS b
        where b.slot_id = s.slot_id
          and b.booking_status in ('HELD','CONFIRMED')
      ) then 'RESERVED'
      else 'AVAILABLE'
    end as status
  from NOV_2026_BATCH.QSPARK_PARKING_SLOTS s
  join NOV_2026_BATCH.QSPARK_VEHICLE_TYPES v on s.vehicle_type_id = v.vehicle_type_id
  join NOV_2026_BATCH.QSPARK_FLOORS f on f.floor_id = s.floor_id
)
select * from slot_status_base;