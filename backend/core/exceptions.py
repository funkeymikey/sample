"""API errors and the exception handler that turns every error into one response shape.

Raise an `ApiError` (or subclass) anywhere in a request to return a 4xx. DRF's own exceptions are
reshaped the same way, and anything unexpected becomes a generic 500. Every response looks like:

    {
        "error": {
            "type": "VALIDATION_ERROR",
            "message": "Human-readable message",
            "detail": "Extra context (optional)",
            "fields": {"field_name": ["error"]}  # validation errors only
        }
    }
"""

import logging
from http import HTTPStatus
from typing import Any

from django.db import models
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import set_rollback

LOGGER = logging.getLogger(__name__)

DEFAULT_ERROR_MESSAGE = "An error occurred while handling your request."
VALIDATION_ERROR_MESSAGE = "Invalid request data."


class ErrorType(models.TextChoices):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    REQUEST_ERROR = "REQUEST_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Error type for the statuses DRF's built-in exceptions use; any other 4xx becomes REQUEST_ERROR.
DRF_STATUS_ERROR_TYPE = {
    HTTPStatus.BAD_REQUEST: ErrorType.VALIDATION_ERROR,
    HTTPStatus.NOT_FOUND: ErrorType.NOT_FOUND,
    HTTPStatus.METHOD_NOT_ALLOWED: ErrorType.METHOD_NOT_ALLOWED,
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE: ErrorType.UNSUPPORTED_MEDIA_TYPE,
}


class ApiError(Exception):
    """An error that reaches the client as a 4xx: a 400 `VALIDATION_ERROR` unless a subclass says otherwise.

    Callers can override the default message and add a `detail`.
    """

    status_code = HTTPStatus.BAD_REQUEST
    error_type = ErrorType.VALIDATION_ERROR
    default_message = VALIDATION_ERROR_MESSAGE

    def __init__(self, message: str | None = None, *, detail: str | None = None) -> None:
        self.message = message or self.default_message
        self.detail = detail
        super().__init__(self.message)


class ConflictError(ApiError):
    status_code = HTTPStatus.CONFLICT
    error_type = ErrorType.CONFLICT
    default_message = "A conflict occurred trying to perform this action."


def api_exception_handler(exception: Exception, context: dict[str, Any]) -> Response:
    """Turn any exception raised in a DRF view into the standard error response, and log it.

    `ApiError`s and DRF exceptions keep their 4xx status and message. Anything else is a 500 with
    a generic message; its details go only to the log, never to the client.
    """
    # DRF's generic views raise Django's Http404 for unknown ids.
    if isinstance(exception, Http404):
        exception = exceptions.NotFound(str(exception) or None)

    error: dict[str, Any]
    if isinstance(exception, ApiError):
        status_code = exception.status_code
        error = {"type": exception.error_type, "message": exception.message}
        if exception.detail:
            error["detail"] = exception.detail
    elif isinstance(exception, exceptions.ValidationError):
        status_code = HTTPStatus.BAD_REQUEST
        fields = exception.detail
        if not isinstance(fields, dict):
            fields = {api_settings.NON_FIELD_ERRORS_KEY: fields}
        error = {"type": ErrorType.VALIDATION_ERROR, "message": VALIDATION_ERROR_MESSAGE, "fields": fields}
    elif isinstance(exception, exceptions.APIException):
        status_code = HTTPStatus(exception.status_code)
        error_type = DRF_STATUS_ERROR_TYPE.get(status_code, ErrorType.REQUEST_ERROR)
        error = {"type": error_type, "message": str(exception.detail)}
    else:
        status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        error = {"type": ErrorType.INTERNAL_ERROR, "message": DEFAULT_ERROR_MESSAGE}

    log_exception(exception, context, status_code)
    set_rollback()
    return Response({"error": error}, status=status_code)


def log_exception(exception: Exception, context: dict[str, Any], status_code: HTTPStatus) -> None:
    """Log a handled exception: 5xx as ERROR with the traceback, 4xx as WARNING without one."""
    request = context["request"]
    message = f"{status_code} {request.method} {request.path}: {type(exception).__name__}: {exception}"
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        LOGGER.error(message, exc_info=exception)
    else:
        LOGGER.warning(message)
