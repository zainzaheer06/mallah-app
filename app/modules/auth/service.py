"""
Auth service layer.

All business rules live here. Routers should be thin shells that:
    1. validate input via Pydantic
    2. call the service
    3. return the response

The service is framework-agnostic: it knows about SQLAlchemy and our
domain exceptions, but never about FastAPI HTTP-specifics.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from jose import JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    NotFound,
    TokenInvalid,
    BadRequest,
)
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth import firebase
from app.modules.auth.models import AuthProvider, User
from app.modules.auth.schemas import (
    RegisterRequest,
    TokenPair,
    UserUpdate,
)

logger = structlog.get_logger()


# ============================================================================
# Helpers
# ============================================================================
def _build_token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, is_admin=user.is_admin),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
    return (await db.execute(stmt)).scalar_one_or_none()


async def _get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    return (await db.execute(stmt)).scalar_one_or_none()


async def _get_user_by_firebase_uid(db: AsyncSession, fb_uid: str) -> User | None:
    stmt = select(User).where(User.firebase_uid == fb_uid, User.deleted_at.is_(None))
    return (await db.execute(stmt)).scalar_one_or_none()


async def _touch_last_login(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_login_at=datetime.now(UTC))
    )


# ============================================================================
# Public service functions
# ============================================================================
async def register_user(db: AsyncSession, payload: RegisterRequest) -> tuple[User, TokenPair]:
    """Create a new email/password user and return tokens."""
    if await _get_user_by_email(db, payload.email):
        raise EmailAlreadyRegistered()

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
        language=payload.language,
        auth_provider=AuthProvider.EMAIL,
    )
    db.add(user)
    await db.flush()  # populate user.id without committing
    await _touch_last_login(db, user.id)

    logger.info("user_registered", user_id=str(user.id), provider="email")
    return user, _build_token_pair(user)


# A precomputed bcrypt hash of an unknowable password, used as a dummy
# target so timing of "user not found" matches "wrong password".
_DUMMY_BCRYPT_HASH = "$2b$12$CwTycUXWue0Thq9StjUM0uJ8.fJv3X3y5w8zZ3yYQX8L6N1zN0vYO"


async def login_with_password(
    db: AsyncSession, email: str, password: str
) -> tuple[User, TokenPair]:
    """Email + password login."""
    user = await _get_user_by_email(db, email)

    # Constant-time-ish: always run verify_password even if user is None,
    # to avoid leaking via timing whether the email exists.
    if user is None or user.hashed_password is None:
        verify_password(password, _DUMMY_BCRYPT_HASH)
        raise InvalidCredentials()

    if not verify_password(password, user.hashed_password):
        raise InvalidCredentials()

    if not user.is_active:
        raise InvalidCredentials("Account is suspended")

    await _touch_last_login(db, user.id)
    logger.info("user_login", user_id=str(user.id), provider="email")
    return user, _build_token_pair(user)


async def login_with_firebase(
    db: AsyncSession, id_token: str
) -> tuple[User, TokenPair]:
    """
    Verify a Firebase ID token and return our session tokens.

    On first login, auto-create a local user record linked by firebase_uid.
    On subsequent logins, link by firebase_uid (or by email if a local
    email/password user with the same email already exists).
    """
    claims = firebase.verify_id_token(id_token)
    fb_uid: str = claims["uid"]
    fb_email: str | None = claims.get("email")
    fb_name: str | None = claims.get("name")
    sign_in_provider: str = claims.get("firebase", {}).get("sign_in_provider", "")

    # Map Firebase sign-in provider -> our AuthProvider enum
    provider_map = {
        "google.com": AuthProvider.FIREBASE_GOOGLE,
        "apple.com": AuthProvider.FIREBASE_APPLE,
        "phone": AuthProvider.FIREBASE_PHONE,
    }
    auth_provider = provider_map.get(sign_in_provider, AuthProvider.FIREBASE_GOOGLE)

    # 1) Try by firebase_uid
    user = await _get_user_by_firebase_uid(db, fb_uid)

    # 2) If not found and we have an email, link to existing email user
    if user is None and fb_email:
        existing = await _get_user_by_email(db, fb_email.lower())
        if existing is not None:
            existing.firebase_uid = fb_uid
            user = existing

    # 3) Otherwise, provision a new user
    if user is None:
        if not fb_email:
            # Phone-only login without an email — generate a placeholder.
            # Real product can prompt the user to add an email later.
            fb_email = f"phone_{fb_uid}@phone.firebase.invalid"
        user = User(
            email=fb_email.lower(),
            firebase_uid=fb_uid,
            display_name=fb_name,
            auth_provider=auth_provider,
            is_email_verified=bool(claims.get("email_verified", False)),
        )
        db.add(user)
        await db.flush()
        logger.info(
            "user_registered",
            user_id=str(user.id),
            provider=auth_provider.value,
        )

    if not user.is_active:
        raise InvalidCredentials("Account is suspended")

    await _touch_last_login(db, user.id)
    logger.info("user_login", user_id=str(user.id), provider=auth_provider.value)
    return user, _build_token_pair(user)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    """Exchange a valid refresh token for a new access+refresh pair."""
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except JWTError as e:
        raise TokenInvalid(str(e)) from e

    user_id = UUID(payload["sub"])
    user = await _get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise TokenInvalid("User no longer exists or is inactive")

    return _build_token_pair(user)


async def get_me(db: AsyncSession, user_id: UUID) -> User:
    user = await _get_user_by_id(db, user_id)
    if user is None:
        raise NotFound("User not found")
    return user


async def update_me(db: AsyncSession, user_id: UUID, payload: UserUpdate) -> User:
    user = await get_me(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    # If email is changing, ensure no other active user has it
    if "email" in data and data["email"] != user.email:
        existing = await _get_user_by_email(db, data["email"])
        if existing is not None and existing.id != user.id:
            raise EmailAlreadyRegistered()
        # Email changes invalidate prior verification
        user.is_email_verified = False

    for field, value in data.items():
        setattr(user, field, value)
    await db.flush()
    logger.info("user_updated", user_id=str(user.id), fields=list(data.keys()))
    return user


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    """
    Generate a password-reset token for the given email.

    Returns the token if the user exists; returns None otherwise.
    The router intentionally returns the same response either way to avoid
    leaking which emails are registered.
    """
    user = await _get_user_by_email(db, email)
    if user is None:
        return None
    return create_password_reset_token(user.id)


async def confirm_password_reset(
    db: AsyncSession, token: str, new_password: str
) -> None:
    try:
        payload = decode_token(token, expected_type="password_reset")
    except JWTError as e:
        raise TokenInvalid(str(e)) from e

    user_id = UUID(payload["sub"])
    user = await _get_user_by_id(db, user_id)
    if user is None:
        raise TokenInvalid("User no longer exists")

    user.hashed_password = hash_password(new_password)
    await db.flush()
    logger.info("password_reset_completed", user_id=str(user.id))


async def soft_delete_account(db: AsyncSession, user_id: UUID) -> None:
    """
    PDPL-compliant soft delete.

    Anonymizes PII fields and sets deleted_at. Keeps the row so foreign
    keys from analytics tables (user_events, redirect_logs) stay valid.
    Full hard-anonymization pipeline is Phase 2.
    """
    user = await _get_user_by_id(db, user_id)
    if user is None:
        raise NotFound("User not found")

    now = datetime.now(UTC)
    # Email is replaced with a deterministic anonymized string so the unique
    # index stays satisfied.
    user.email = f"deleted_{user.id}@deleted.mallah.local"
    user.hashed_password = None
    user.firebase_uid = None
    user.display_name = None
    user.phone_number = None
    user.is_active = False
    user.deleted_at = now
    await db.flush()
    logger.info("user_soft_deleted", user_id=str(user_id))

async def change_password(
    db: AsyncSession,
    user_id: UUID,
    old_password: str,
    new_password: str,
) -> None:
    """
    Change password for a logged-in user.

    Verifies the old password before writing the new one. This is the
    security check that distinguishes change-password from reset-password —
    if a stolen access token is used to call this endpoint, the attacker
    still can't change the password without knowing the current one.

    Raises InvalidCredentials if the old password is wrong.
    Raises BadRequest if the user has no password (signed up via Firebase).
    """
    user = await _get_user_by_id(db, user_id)
    if user is None:
        raise NotFound("User not found")

    # Firebase-only users (Google / phone OTP) don't have a local password.
    # They need to set one via a separate "add password" flow rather than
    # change-password. For D1 we just reject; Phase 2 can add the set flow.
    if user.hashed_password is None:
        raise BadRequest(
            "This account doesn't have a password. "
            "Sign in with your original method (Google / phone)."
        )

    if not verify_password(old_password, user.hashed_password):
        raise InvalidCredentials("Current password is incorrect")

    if old_password == new_password:
        raise BadRequest("New password must be different from the current one")

    user.hashed_password = hash_password(new_password)
    await db.flush()
    logger.info("password_changed", user_id=str(user.id))    


# ============================================================================
# Address management
# ============================================================================

from app.modules.auth.models import UserAddress
from app.modules.auth.schemas import AddressCreate, AddressUpdate


async def _get_address(
    db: AsyncSession, user_id: UUID, address_id: UUID
) -> UserAddress | None:
    """Find an address belonging to the given user. Returns None if missing."""
    stmt = select(UserAddress).where(
        UserAddress.id == address_id,
        UserAddress.user_id == user_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _clear_default_addresses(db: AsyncSession, user_id: UUID) -> None:
    """Un-set is_default on all of this user's addresses."""
    await db.execute(
        update(UserAddress)
        .where(UserAddress.user_id == user_id, UserAddress.is_default.is_(True))
        .values(is_default=False)
    )


async def create_address(
    db: AsyncSession, user_id: UUID, payload: AddressCreate
) -> UserAddress:
    """
    Create an address for the user.

    If the user has no addresses yet, the new address auto-becomes default.
    If the payload sets is_default=True, un-default any existing default first.
    """
    # Check whether this is the user's first address
    existing_count = (
        await db.execute(
            select(UserAddress.id).where(UserAddress.user_id == user_id)
        )
    ).scalars().all()

    is_first = len(existing_count) == 0

    # If first OR caller explicitly wants this default, ensure single default
    if payload.is_default or is_first:
        await _clear_default_addresses(db, user_id)
        is_default = True
    else:
        is_default = False

    addr = UserAddress(
        user_id=user_id,
        label=payload.label,
        address_line=payload.address_line,
        city=payload.city,
        district=payload.district,
        country=payload.country or "SA",
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_default=is_default,
    )
    db.add(addr)
    await db.flush()
    logger.info("address_created", user_id=str(user_id), address_id=str(addr.id))
    return addr


async def list_addresses(
    db: AsyncSession, user_id: UUID
) -> list[UserAddress]:
    """List addresses for the user, default first then most-recently-updated."""
    stmt = (
        select(UserAddress)
        .where(UserAddress.user_id == user_id)
        .order_by(UserAddress.is_default.desc(), UserAddress.updated_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def update_address(
    db: AsyncSession,
    user_id: UUID,
    address_id: UUID,
    payload: AddressUpdate,
) -> UserAddress:
    """
    Update an address. Setting is_default=True un-defaults previous default.
    """
    addr = await _get_address(db, user_id, address_id)
    if addr is None:
        raise NotFound("Address not found")

    data = payload.model_dump(exclude_unset=True)

    # Handle default switching
    if data.get("is_default") is True and not addr.is_default:
        await _clear_default_addresses(db, user_id)

    for field, value in data.items():
        setattr(addr, field, value)

    await db.flush()
    logger.info(
        "address_updated",
        user_id=str(user_id),
        address_id=str(addr.id),
        fields=list(data.keys()),
    )
    return addr


async def delete_address(
    db: AsyncSession, user_id: UUID, address_id: UUID
) -> None:
    """Delete an address. No auto-promote of another default in MVP."""
    addr = await _get_address(db, user_id, address_id)
    if addr is None:
        raise NotFound("Address not found")

    await db.delete(addr)
    await db.flush()
    logger.info(
        "address_deleted", user_id=str(user_id), address_id=str(address_id)
    )
