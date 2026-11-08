"""Booking lifecycle endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.ords_client import ords

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


class BookingRequest(BaseModel):
    user_id: int
    slot_id: int
    vehicle_number: str
    duration_hours: float


class CheckoutRequest(BaseModel):
    simulated_late_hours: float = 0.0


@router.post("", status_code=201)
def create_booking(body: BookingRequest):
    return ords.create_booking(
        body.user_id, body.slot_id, body.vehicle_number, body.duration_hours
    )


@router.get("")
def list_bookings(user_id: int | None = None):
    return {"items": ords.list_bookings(user_id)}


@router.put("/{booking_id}/checkout")
def checkout(booking_id: int, body: CheckoutRequest | None = None):
    late_hours = body.simulated_late_hours if body else 0.0
    return ords.checkout_booking(booking_id, late_hours)


@router.put("/{booking_id}/cancel")
def cancel(booking_id: int):
    return ords.cancel_booking(booking_id)
