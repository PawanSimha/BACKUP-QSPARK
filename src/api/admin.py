"""Admin audit-track endpoint."""

from pydantic import BaseModel

from fastapi import APIRouter

from src.services.ords_client import ords

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AuditTrackRequest(BaseModel):
    admin_name: str
    modified_table: str
    modified_column: str | None = None
    why_modified: str | None = None


@router.post("/audit-track", status_code=201)
def audit_track(payload: AuditTrackRequest):
    return ords.insert_audit_track(**payload.model_dump())
