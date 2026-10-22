import logging
from unittest import mock

import pytest
from django.db import OperationalError
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_reports_ok() -> None:
    response = APIClient().get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_logged_500_when_database_is_down(caplog: pytest.LogCaptureFixture) -> None:
    with mock.patch("health.services.connection.cursor", side_effect=OperationalError("connection refused")):
        response = APIClient().get(reverse("health"))

    assert response.status_code == 500
    assert response.json()["error"]["type"] == "INTERNAL_ERROR"
    assert "connection refused" not in response.content.decode()
    assert [record.levelno for record in caplog.records if record.name == "core.exceptions"] == [logging.ERROR]


def test_api_docs_render() -> None:
    client = APIClient()

    assert client.get(reverse("redoc")).status_code == 200
    assert client.get(reverse("schema")).status_code == 200
