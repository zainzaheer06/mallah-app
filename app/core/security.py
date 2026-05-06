"""
Security primitives: password hashing, JWT issuance and verification.

Tokens have explicit `type` claims ("access" | "refresh" | "password_reset")
so a refresh token can never be used as an access token.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

TokenType = Literal["access", "refresh", "password_reset"]

# Bcrypt has a hard 72-byte input limit; passwords longer than this are
# truncated to keep behavior consistent. Calling code should rely on the
# Pydantic max_length=128 to surface this to the user before it hits here.
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_input(password: str) -> bytes:
    """Encode + safely truncate to bcrypt's 72-byte input limit."""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


# --- Passwords ---
def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (cost factor 12)."""
    hashed = bcrypt.hashpw(_to_bcrypt_input(password), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Constant-time password verification.

    Returns False rather than raising if the stored hash is malformed —
    avoids leaking via exceptions whether a user's hash is corrupted.
    """
    try:
        return bcrypt.checkpw(_to_bcrypt_input(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT ---
def _create_token(
    subject: str | UUID,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: UUID, is_admin: bool = False) -> str:
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"is_admin": is_admin},
    )


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(
        user_id,
        "refresh",
        timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def create_password_reset_token(user_id: UUID) -> str:
    return _create_token(
        user_id,
        "password_reset",
        timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Raises JWTError if signature is bad, token is expired, or `type` claim
    doesn't match what the caller expected. This prevents refresh tokens
    from being used as access tokens, etc.
    """
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != expected_type:
        raise JWTError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
    return payload
