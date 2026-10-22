from http import HTTPStatus
from typing import Any

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiResponse

from core.serializers import ErrorResponseSerializer

WRITE_METHODS = {"POST", "PUT", "PATCH"}

ERROR_RESPONSES = {
    HTTPStatus.BAD_REQUEST: OpenApiResponse(ErrorResponseSerializer, description="The request data is invalid."),
    HTTPStatus.NOT_FOUND: OpenApiResponse(ErrorResponseSerializer, description="No object with this id."),
    HTTPStatus.INTERNAL_SERVER_ERROR: OpenApiResponse(ErrorResponseSerializer, description="Unexpected server error."),
}


class ApiAutoSchema(AutoSchema):
    """Adds the standard error responses to every operation, so views only declare the unusual ones.

    Every operation can return 500, writes can return 400, and operations on a single object
    (paths with an `{id}`-style parameter) can return 404. Codes a view declares itself are kept.
    """

    def _get_response_bodies(self, direction: str = "response") -> dict[str, Any]:
        responses = super()._get_response_bodies(direction)

        error_codes = [HTTPStatus.INTERNAL_SERVER_ERROR]
        if self.method in WRITE_METHODS:
            error_codes.append(HTTPStatus.BAD_REQUEST)
        if "{" in self.path:
            error_codes.append(HTTPStatus.NOT_FOUND)

        for status_code in error_codes:
            code = str(status_code.value)
            if code not in responses:
                responses[code] = self._get_response_for_code(ERROR_RESPONSES[status_code], code)
        return responses
