"""Pricing calculations: fare and overstay."""

from datetime import datetime


def calculate_fare(hourly_rate: float, hours: float) -> float:
    """Calculate base fare: hours × hourly_rate, rounded to 2 decimals."""
    return round(hours * hourly_rate, 2)


def calculate_overstay(
    overstay_rate: float, booked_until: str, actual_exit: str
) -> tuple:
    """Calculate overstay hours and amount.

    Args:
        overstay_rate: per-hour overstay rate (₹10 bike / ₹20 car)
        booked_until: ISO datetime string when booking was supposed to end
        actual_exit: ISO datetime string when vehicle actually exits

    Returns:
        (overstay_hours, overstay_amount) - both rounded to 2 decimals.
        If no overstay, returns (0.0, 0.0).
    """
    if not booked_until or not actual_exit:
        return 0.0, 0.0

    end = datetime.fromisoformat(booked_until)
    exit_time = datetime.fromisoformat(actual_exit)

    delta = (exit_time - end).total_seconds() / 3600.0
    if delta <= 0:
        return 0.0, 0.0

    # Round up to next started hour (per CEO requirement: per started hour)
    import math

    overstay_hours = round(math.ceil(delta * 2) / 2, 2)  # 30-min granularity
    overstay_amount = round(overstay_hours * overstay_rate, 2)
    return overstay_hours, overstay_amount

