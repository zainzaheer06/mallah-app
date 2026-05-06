"""
Auth module — User and UserAddress ORM models.

Schema notes:
- `id` is UUIDv4 (not bigserial) so user IDs are non-enumerable in URLs.
- `email` is citext-style (lowercased on write) to make it
  case-insensitive without requiring the citext extension.
- Soft-delete via `deleted_at`; the PDPL endpoint anonymizes PII fields
  on delete rather than purging the row (keeps FK integrity for analytics).
"""

from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AuthProvider(str, Enum):  # noqa: UP042 — StrEnum on 3.11 changes serialization
    """How the user authenticated. Stored on the user row for analytics."""

    EMAIL = "email"
    FIREBASE_GOOGLE = "firebase_google"
    FIREBASE_APPLE = "firebase_apple"
    FIREBASE_PHONE = "firebase_phone"


class UserLanguage(str, Enum):  # noqa: UP042
    """User's preferred language for UI + notifications."""

    EN = "en"
    AR = "ar"


class Gender(str, Enum):  # noqa: UP042
    """User's gender as collected on the profile-completion screen."""

    MALE = "male"
    FEMALE = "female"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    # Identity
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Firebase linkage
    firebase_uid: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True, index=True
    )
    auth_provider: Mapped[AuthProvider] = mapped_column(
        SQLEnum(AuthProvider, name="auth_provider", native_enum=False),
        default=AuthProvider.EMAIL,
        nullable=False,
    )

    # Profile
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    language: Mapped[UserLanguage] = mapped_column(
        SQLEnum(UserLanguage, name="user_language", native_enum=False),
        default=UserLanguage.EN,
        nullable=False,
    )
    default_city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    gender: Mapped[Gender | None] = mapped_column(
        SQLEnum(Gender, name="gender", native_enum=False),
        nullable=True,
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    addresses: Mapped[list["UserAddress"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_users_email_active",
            "email",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
    )


class UserAddress(Base):
    __tablename__ = "user_addresses"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Mapped[str] = mapped_column(String(40), nullable=False)
    address_line: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default="SA", nullable=False)

    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="addresses")