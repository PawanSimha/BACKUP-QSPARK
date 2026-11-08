"""Authentication endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from src.core.security import create_token, read_token
from src.services.ords_client import ords

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login_id: str
    password: str


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """Resolve the Bearer token to a live user profile."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    user_id = read_token(authorization.split(" ", 1)[1])
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = ords.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/login")
def login(body: LoginRequest):
    user = ords.authenticate_user(body.login_id, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    return {"token": create_token(user["user_id"]), "user": user}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return ords.get_user(user["user_id"])
