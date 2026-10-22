import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """A DRF test client. (pytest-django's own `client` fixture is Django's plain test client.)"""
    return APIClient()
