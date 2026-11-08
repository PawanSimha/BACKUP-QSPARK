"""SHA-256 password hashing for QSPARK basic authentication."""

import hashlib
import hmac
import os


def hash_password(plain_text: str) -> str:
    """Return the SHA-256 hex digest of a plain-text password."""
    return hashlib.sha256(plain_text.encode("utf-8")).hexdigest()


def verify_password(plain_text: str, hashed: str) -> bool:
    """Constant-time comparison of a plain-text password against a stored digest."""
    return hmac.compare_digest(hash_password(plain_text), hashed)


def _sign(payload: str) -> str:
    key = os.getenv("SECRET_KEY", "change_me_in_production").encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_token(user_id: int) -> str:
    """Signed session token: "<user_id>.<hmac-sha256>". Stateless, no storage."""
    payload = str(user_id)
    return f"{payload}.{_sign(payload)}"


def read_token(token: str) -> int | None:
    """Return the user_id for a valid token, or None."""
    try:
        payload, signature = token.split(".", 1)
        user_id = int(payload)
    except (AttributeError, ValueError):
        return None
    return user_id if hmac.compare_digest(signature, _sign(payload)) else None
