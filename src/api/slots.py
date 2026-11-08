"""Parking slot endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.ords_client import ords

router = APIRouter(prefix="/api/slots", tags=["slots"])


class SlotStatusUpdate(BaseModel):
    status: str
    admin_user_id: int


@router.get("")
def list_slots(floor_id: int | None = None):
    return {"items": ords.get_slots(floor_id)}


@router.put("/{slot_id}/status")
def update_status(slot_id: int, body: SlotStatusUpdate):
    admin = ords.get_user(body.admin_user_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin user not found")
    if admin["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    ords.update_slot_status(slot_id, body.status, body.admin_user_id)
    return {"slot_id": slot_id, "status": body.status}
