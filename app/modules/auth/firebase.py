"""
Firebase Admin SDK wrapper.

Initialized lazily so the app can boot even when Firebase credentials
aren't configured yet (per the roadmap: D1 ships with email/password
fallback if creds arrive late). When creds DO arrive, no code changes
are needed — just env vars.
"""

from __future__ import annotations

import json
from threading import Lock
from typing import Any

import structlog

from app.core.config import settings
from app.core.exceptions import ServiceUnavailable, TokenInvalid

logger = structlog.get_logger()

_app: Any | None = None
_lock = Lock()


def _init_firebase() -> Any:
    """Lazy, thread-safe init of the Firebase Admin app."""
    global _app
    if _app is not None:
        return _app

    with _lock:
        if _app is not None:
            return _app

        if not settings.firebase_enabled:
            raise ServiceUnavailable(
                "Firebase is not configured on this server. "
                "Email/password auth is still available."
            )

        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError as e:
            raise ServiceUnavailable("firebase-admin is not installed") from e

        if settings.FIREBASE_CREDENTIALS_JSON:
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)

        _app = firebase_admin.initialize_app(
            cred, {"projectId": settings.FIREBASE_PROJECT_ID}
        )
        logger.info("firebase_initialized", project_id=settings.FIREBASE_PROJECT_ID)
        return _app


def verify_id_token(id_token: str) -> dict[str, Any]:
    """
    Verify a Firebase-issued ID token. Returns the decoded claims dict
    on success (which contains uid, email, name, sign_in_provider, etc.).

    Raises TokenInvalid on bad/expired tokens.
    Raises ServiceUnavailable if Firebase isn't configured at all.
    """
    _init_firebase()

    try:
        from firebase_admin import auth as fb_auth
        return fb_auth.verify_id_token(id_token, check_revoked=False)
    except Exception as e:
        # firebase_admin raises a variety of exception types; we collapse
        # them all into TokenInvalid for the API layer.
        raise TokenInvalid(f"Firebase token verification failed: {e}") from e
