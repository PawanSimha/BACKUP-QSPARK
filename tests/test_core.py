from datetime import datetime, timedelta

import pytest

from src.core.pricing_engine import (
    calculate_booking_fare,
    calculate_overstay_penalty,
)
from src.core.security import hash_password, verify_password

END = datetime(2026, 11, 8, 12, 0, 0)


def test_hash_and_verify():
    digest = hash_password("user123")
    assert len(digest) == 64
    assert verify_password("user123", digest)
    assert not verify_password("wrong", digest)


def test_fare_by_vehicle_type():
    assert calculate_booking_fare("BIKE", 3)["base_amount"] == 15.0
    assert calculate_booking_fare("CAR", 3)["base_amount"] == 30.0


def test_unknown_vehicle_type():
    with pytest.raises(ValueError):
        calculate_booking_fare("TRUCK", 1)


def test_grace_period_is_free():
    assert calculate_overstay_penalty("BIKE", END, END + timedelta(minutes=10)) == (0.0, 0.0)


def test_bike_and_car_overstay_rates():
    assert calculate_overstay_penalty("BIKE", END, END + timedelta(hours=1.5)) == (1.5, 15.0)
    assert calculate_overstay_penalty("CAR", END, END + timedelta(hours=1.5)) == (1.5, 30.0)


def test_thirty_minutes_late():
    assert calculate_overstay_penalty("CAR", END, END + timedelta(minutes=30)) == (0.5, 10.0)
