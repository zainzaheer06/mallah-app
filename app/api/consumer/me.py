"""Consumer profile + addresses — /me/*

All endpoints require authentication. Business logic lives in
app.modules.auth.service — this file only handles HTTP.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUserId, DbSession
from app.modules.auth import service
from app.modules.auth.schemas import (
    AddressCreate,
    AddressPublic,
    AddressUpdate,
    PasswordChangeRequest,
    UserPublic,
    UserUpdate,
)

router = APIRouter(prefix="/me", tags=["me"])


# ── Profile ──────────────────────────────────────────────────────────────

@router.get("", response_model=UserPublic, summary="Get current user profile")
async def get_me(user_id: CurrentUserId, db: DbSession) -> UserPublic:
    user = await service.get_me(db, user_id)
    return UserPublic.model_validate(user)


@router.patch(
    "",
    response_model=UserPublic,
    summary="Update profile (display_name, email, language, default_city, gender, date_of_birth)",
)
async def update_me(
    payload: UserUpdate, user_id: CurrentUserId, db: DbSession
) -> UserPublic:
    user = await service.update_me(db, user_id, payload)
    return UserPublic.model_validate(user)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete account (PDPL-compliant anonymization)",
)
async def delete_me(user_id: CurrentUserId, db: DbSession) -> None:
    await service.soft_delete_account(db, user_id)
    return None


@router.post(
    "/password/change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password (requires current password)",
    tags=["auth", "me"],
)
async def change_password(
    payload: PasswordChangeRequest, user_id: CurrentUserId, db: DbSession
) -> None:
    await service.change_password(
        db, user_id, payload.old_password, payload.new_password
    )
    return None


# ── Addresses ────────────────────────────────────────────────────────────

@router.post(
    "/addresses",
    response_model=AddressPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new address",
)
async def create_address(
    payload: AddressCreate, user_id: CurrentUserId, db: DbSession
) -> AddressPublic:
    addr = await service.create_address(db, user_id, payload)
    return AddressPublic.model_validate(addr)


@router.get(
    "/addresses",
    response_model=list[AddressPublic],
    summary="List addresses (default first, then most recent)",
)
async def list_addresses(
    user_id: CurrentUserId, db: DbSession
) -> list[AddressPublic]:
    addrs = await service.list_addresses(db, user_id)
    return [AddressPublic.model_validate(a) for a in addrs]


@router.patch(
    "/addresses/{address_id}",
    response_model=AddressPublic,
    summary="Update an address (setting is_default=true un-defaults the previous one)",
)
async def update_address(
    address_id: UUID,
    payload: AddressUpdate,
    user_id: CurrentUserId,
    db: DbSession,
) -> AddressPublic:
    addr = await service.update_address(db, user_id, address_id, payload)
    return AddressPublic.model_validate(addr)


@router.delete(
    "/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an address",
)
async def delete_address(
    address_id: UUID, user_id: CurrentUserId, db: DbSession
) -> None:
    await service.delete_address(db, user_id, address_id)
    return None
