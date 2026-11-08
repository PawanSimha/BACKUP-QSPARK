"""Admin analytics endpoints."""

from fastapi import APIRouter

from src.services.ords_client import ords

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/kpi")
def kpi():
    return ords.get_analytics_kpi()
