"""QSPARK fare and overstay-penalty business rules."""

from datetime import datetime

GRACE_PERIOD_HOURS = 10 / 60  # 10-minute buffer, zero penalty

# vehicle_type -> (hourly rate, overstay penalty per hour)
TARIFFS = {
    "BIKE": (5.00, 10.00),
    "CAR": (10.00, 20.00),
}


def _rates(vehicle_type: str) -> tuple[float, float]:
    try:
        return TARIFFS[vehicle_type.upper()]
    except (AttributeError, KeyError):
        raise ValueError(f"Unsupported vehicle type: {vehicle_type!r}") from None


def calculate_booking_fare(vehicle_type: str, duration_hours: float) -> dict:
    """Base fare for a reservation, paid upfront from the Metro Card wallet."""
    hourly_rate, _ = _rates(vehicle_type)
    duration = float(duration_hours)
    if duration <= 0:
        raise ValueError("duration_hours must be greater than zero")

    return {
        "vehicle_type": vehicle_type.upper(),
        "duration_hours": duration,
        "hourly_rate": hourly_rate,
        "base_amount": round(duration * hourly_rate, 2),
    }


def calculate_overstay_penalty(
    vehicle_type: str, scheduled_end: datetime, actual_exit: datetime
) -> tuple[float, float]:
    """Return (overstay_hours, penalty). Time inside the grace period is free."""
    _, penalty_rate = _rates(vehicle_type)

    # Compare before rounding: 10 minutes rounds to 0.17, which would breach its own grace.
    late_hours = (actual_exit - scheduled_end).total_seconds() / 3600
    if late_hours <= GRACE_PERIOD_HOURS:
        return 0.0, 0.0

    late_hours = round(late_hours, 2)
    return late_hours, round(late_hours * penalty_rate, 2)
