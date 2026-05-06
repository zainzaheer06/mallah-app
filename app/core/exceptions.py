"""
Application exception hierarchy.

All domain exceptions inherit from AppException. The global exception
handler in main.py converts these to consistent JSON error responses.

Never raise raw HTTPException in service layer — raise an AppException
subclass so the layer remains framework-agnostic.
"""

from typing import Any


class AppException(Exception):  # noqa: N818 — matches FastAPI's HTTPException convention
    """Base exception for all application errors."""

    status_code: int = 500
    error_code: str = "internal_error"
    message: str = "An internal error occurred"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details or {}


# --- 4xx ---
class BadRequest(AppException):
    status_code = 400
    error_code = "bad_request"
    message = "Bad request"


class Unauthorized(AppException):
    status_code = 401
    error_code = "unauthorized"
    message = "Authentication required"


class InvalidCredentials(Unauthorized):
    error_code = "invalid_credentials"
    message = "Invalid email or password"


class TokenExpired(Unauthorized):
    error_code = "token_expired"
    message = "Token has expired"


class TokenInvalid(Unauthorized):
    error_code = "token_invalid"
    message = "Token is invalid"


class Forbidden(AppException):
    status_code = 403
    error_code = "forbidden"
    message = "You do not have permission to perform this action"


class NotFound(AppException):
    status_code = 404
    error_code = "not_found"
    message = "Resource not found"


class Conflict(AppException):
    status_code = 409
    error_code = "conflict"
    message = "Resource conflict"


class EmailAlreadyRegistered(Conflict):
    error_code = "email_already_registered"
    message = "An account with this email already exists"


class TooManyRequests(AppException):
    status_code = 429
    error_code = "too_many_requests"
    message = "Too many requests"


# --- 5xx ---
class ServiceUnavailable(AppException):
    status_code = 503
    error_code = "service_unavailable"
    message = "Service is temporarily unavailable"


class ExternalServiceError(AppException):
    status_code = 502
    error_code = "external_service_error"
    message = "An external service returned an error"
