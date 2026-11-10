"""QSPARK FastAPI entrypoint."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402

from src.api import admin, analytics, auth, bookings, slots  # noqa: E402
from src.services.ords_client import (  # noqa: E402
    InsufficientFunds,
    InvalidRequest,
    InvalidState,
    NotFound,
    OrdsError,
    UnsupportedInLiveMode,
    ords,
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="QSPARK Smart Parking API")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(auth.router)
app.include_router(slots.router)
app.include_router(bookings.router)
app.include_router(analytics.router)
app.include_router(admin.router)

_STATUS_BY_ERROR = (
    (NotFound, 404),
    (InvalidRequest, 400),
    (InvalidState, 409),
    (InsufficientFunds, 402),
    (UnsupportedInLiveMode, 501),
)


@app.exception_handler(OrdsError)
async def ords_error_handler(_, exc: OrdsError):
    status = next((code for cls, code in _STATUS_BY_ERROR if isinstance(exc, cls)), 500)
    return JSONResponse({"error": str(exc)}, status_code=status)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "simulation_mode": ords.simulation_mode,
            "mode_label": "ORDS Local Emulator (Active)"
            if ords.simulation_mode
            else "Oracle APEX ORDS (Live)",
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/health")
def root_health():
    return {"status": "ok", "mode": "live" if not ords.simulation_mode else "simulation"}


@app.get("/api/status")
def status():
    return {
        "mode": "local_emulator" if ords.simulation_mode else "live_ords",
        "label": "ORDS Local Emulator (Active)"
        if ords.simulation_mode
        else "Oracle APEX ORDS (Live)",
        "simulation_mode": ords.simulation_mode,
        "ords_base_url": ords.base_url,
    }
