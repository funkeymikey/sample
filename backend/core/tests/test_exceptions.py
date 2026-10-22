import logging

import pytest
from rest_framework.response import Response
from rest_framework.test import APIClient

from core.serializers import ErrorResponseSerializer

pytestmark = pytest.mark.urls("core.tests.error_urls")


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def assert_documented_error(response: Response) -> None:
    """The response body matches the ErrorResponse schema published in the API docs."""
    serializer = ErrorResponseSerializer(data=response.json())
    assert serializer.is_valid(), serializer.errors


def handler_log_levels(caplog: pytest.LogCaptureFixture) -> list[int]:
    """Levels logged by the exception handler (Django's own request logger is ignored)."""
    return [record.levelno for record in caplog.records if record.name == "core.exceptions"]


def test_api_error_returns_its_status_and_message(client: APIClient, caplog: pytest.LogCaptureFixture) -> None:
    response = client.get("/raise/conflict/")

    assert_documented_error(response)
    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "type": "CONFLICT",
            "message": "Account is closed.",
            "detail": "Closed accounts can't receive transactions.",
        }
    }
    assert handler_log_levels(caplog) == [logging.WARNING]


def test_plain_api_error_is_a_400_with_default_message(client: APIClient) -> None:
    response = client.get("/raise/api-error/")

    assert_documented_error(response)
    assert response.status_code == 400
    assert response.json() == {"error": {"type": "VALIDATION_ERROR", "message": "Invalid request data."}}


def test_django_404_uses_error_shape(client: APIClient) -> None:
    response = client.get("/raise/django-404/")
    no_message_response = client.get("/raise/django-404-no-message/")

    assert_documented_error(response)
    assert response.status_code == 404
    assert response.json()["error"] == {"type": "NOT_FOUND", "message": "No account with that id."}
    assert_documented_error(no_message_response)
    assert no_message_response.json()["error"] == {"type": "NOT_FOUND", "message": "Not found."}


def test_validation_error_lists_field_errors(client: APIClient) -> None:
    response = client.post("/validate/", {}, format="json")

    assert_documented_error(response)
    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "VALIDATION_ERROR",
            "message": "Invalid request data.",
            "fields": {"external_id": ["This field is required."]},
        }
    }


def test_non_field_validation_error_uses_non_field_errors_key(client: APIClient) -> None:
    response = client.post("/validate-non-field/", {}, format="json")

    assert_documented_error(response)
    assert response.status_code == 400
    assert response.json()["error"]["fields"] == {"non_field_errors": ["Amount and direction don't match."]}


def test_other_drf_errors_use_error_shape(client: APIClient) -> None:
    method_response = client.delete("/validate/")
    parse_response = client.post("/validate/", "{not json", content_type="application/json")

    assert_documented_error(method_response)
    assert method_response.status_code == 405
    assert method_response.json()["error"]["type"] == "METHOD_NOT_ALLOWED"
    assert_documented_error(parse_response)
    assert parse_response.status_code == 400
    assert parse_response.json()["error"]["type"] == "VALIDATION_ERROR"


def test_unexpected_error_returns_generic_500_and_logs_traceback(
    client: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    response = client.get("/raise/unexpected/")

    assert_documented_error(response)
    assert response.status_code == 500
    assert response.json() == {
        "error": {"type": "INTERNAL_ERROR", "message": "An error occurred while handling your request."}
    }
    assert "secret internal detail" not in response.content.decode()
    assert handler_log_levels(caplog) == [logging.ERROR]
    [record] = [record for record in caplog.records if record.name == "core.exceptions"]
    assert record.exc_info is not None
