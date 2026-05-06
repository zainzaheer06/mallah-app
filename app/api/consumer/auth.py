"""Consumer authentication routes — /auth/*

Firebase + email/password identity for the mobile app.
All business logic lives in app.modules.auth.service — this file only
handles HTTP and response serialization.
"""

from fastapi import APIRouter, status
import structlog

from app.core.config import settings
from app.core.deps import DbSession
from app.modules.auth import service
from app.modules.auth.schemas import (
    FirebaseLoginRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user with email + password",
)
async def register(payload: RegisterRequest, db: DbSession) -> TokenPair:
    _user, tokens = await service.register_user(db, payload)
    return tokens


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Log in with email + password",
)
async def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    _user, tokens = await service.login_with_password(
        db, payload.email, payload.password
    )
    return tokens


@router.post(
    "/firebase",
    response_model=TokenPair,
    summary="Log in via Firebase ID token (Google / Apple / phone OTP)",
)
async def firebase_login(payload: FirebaseLoginRequest, db: DbSession) -> TokenPair:
    _user, tokens = await service.login_with_firebase(db, payload.id_token)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Exchange refresh token for new access + refresh pair",
)
async def refresh_tokens(payload: RefreshRequest, db: DbSession) -> TokenPair:
    return await service.refresh_tokens(db, payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out (client discards tokens — no server-side blocklist in MVP)",
)
async def logout() -> None:
    return None


@router.post(
    "/password/reset-request",
    summary="Request a password reset email",
)
async def request_password_reset(
    payload: PasswordResetRequest, db: DbSession
) -> dict:
    token = await service.request_password_reset(db, payload.email)

    # In dev, surface the token in logs so testing is possible without SendGrid.
    # In production, the token is delivered via the email channel only.
    if token and settings.APP_ENV == "development":
        logger.info(
            "password_reset_token_dev",
            email=payload.email,
            token=token,
            note="Email sending not configured; use this token directly.",
        )

    # Always return the same shape — don't leak whether the email exists.
    return {
        "message": "If that email is registered, a reset link will be sent."
    }


@router.post(
    "/password/reset-confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirm password reset using emailed token",
)
async def confirm_password_reset(
    payload: PasswordResetConfirm, db: DbSession
) -> None:
    await service.confirm_password_reset(db, payload.token, payload.new_password)
    return None
