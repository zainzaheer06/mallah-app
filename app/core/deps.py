"""
Reusable FastAPI dependencies.

Endpoint signatures should depend on these rather than reach into the
db / security modules directly. This keeps routers thin and testable.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import Forbidden, TokenInvalid, Unauthorized
from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UUID:
    """
    Extract and validate the user_id from a Bearer access token.

    Raises Unauthorized if the header is missing.
    Raises TokenInvalid if the token is malformed, expired, or wrong type.
    """
    if credentials is None:
        raise Unauthorized("Missing Authorization header")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        return UUID(payload["sub"])
    except JWTError as e:
        raise TokenInvalid("Token is invalid or expired") from e
    except (KeyError, ValueError, UnicodeDecodeError) as e:
        raise TokenInvalid("Token is malformed") from e


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]


async def get_current_admin_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UUID:
    """Same as get_current_user_id but requires is_admin claim."""
    if credentials is None:
        raise Unauthorized("Missing Authorization header")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        if not payload.get("is_admin"):
            raise Forbidden("Admin access required")
        return UUID(payload["sub"])
    except JWTError as e:
        raise TokenInvalid("Token is invalid or expired") from e


CurrentAdminId = Annotated[UUID, Depends(get_current_admin_id)]


async def verify_ingest_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """
    Authenticate the scraping team's POSTs to /ingest endpoints.

    Uses a shared secret rather than user JWT because the scraper is a
    machine-to-machine caller, not a human user.
    """
    if x_api_key != settings.INGEST_API_KEY:
        raise Unauthorized("Invalid or missing X-API-Key header")


def get_request_id(request: Request) -> str:
    """Per-request correlation id, set by the request_id middleware."""
    return getattr(request.state, "request_id", "unknown")
