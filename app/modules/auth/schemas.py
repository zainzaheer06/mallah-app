"""
Pydantic schemas for the auth module.

All request bodies and response models are explicitly typed. Email is
normalized (lowercased + stripped) at validation time so the database
never sees mixed-case duplicates.
"""

from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.auth.models import AuthProvider, UserLanguage,Gender



# ============================================================================
# Auth — request bodies
# ============================================================================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    language: UserLanguage = UserLanguage.EN

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class FirebaseLoginRequest(BaseModel):
    """
    The mobile/web client gets an ID token from Firebase
    (Google / Apple / phone OTP) and forwards it here. We verify it
    server-side via Firebase Admin SDK and mint our own JWT pair.
    """

    id_token: str = Field(min_length=10)


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

class PasswordChangeRequest(BaseModel):
    """
    For an already-logged-in user changing their password.

    Distinct from password reset — reset uses an emailed token (forgot-password
    flow), change requires the OLD password as a security check (settings flow).
    """

    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)    


# ============================================================================
# Auth — response bodies
# ============================================================================
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


# ============================================================================
# User — read/update
# ============================================================================
class UserPublic(BaseModel):
    """Safe to return to the user themselves. Does NOT include hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str | None
    phone_number: str | None
    language: UserLanguage
    default_city: str | None
    gender: Gender | None
    date_of_birth: date | None
    auth_provider: AuthProvider
    is_email_verified: bool
    is_admin: bool
    created_at: datetime




class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    language: UserLanguage | None = None
    default_city: str | None = Field(default=None, max_length=80)
    gender: Gender | None = None
    date_of_birth: date | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        return v.strip().lower() if v else v

    @field_validator("date_of_birth")
    @classmethod
    def must_be_reasonable(cls, v: date | None) -> date | None:
        if v is None:
            return v
        from datetime import date as dt
        today = dt.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if v > today:
            raise ValueError("Date of birth cannot be in the future")
        if age > 120:
            raise ValueError("Date of birth is too far in the past")
        if age < 13:
            raise ValueError("You must be at least 13 to use this app")
        return v




# ============================================================================
# Address — CRUD
# ============================================================================
class AddressCreate(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    address_line: str = Field(min_length=1, max_length=500)
    city: str = Field(min_length=1, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    country: str = Field(default="SA", min_length=2, max_length=2)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=40)
    address_line: str | None = Field(default=None, min_length=1, max_length=500)
    city: str | None = Field(default=None, min_length=1, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_default: bool | None = None


class AddressPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    address_line: str
    city: str
    district: str | None
    country: str
    latitude: float | None
    longitude: float | None
    is_default: bool
    created_at: datetime
