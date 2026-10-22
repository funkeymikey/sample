from typing import Any

import pytest
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.urls import urlpatterns as project_urlpatterns


class ItemSerializer(serializers.Serializer):
    name = serializers.CharField()


class ItemListView(APIView):
    serializer_class = ItemSerializer

    def get(self, request: Request) -> Response:
        return Response([])

    def post(self, request: Request) -> Response:
        return Response({}, status=201)


class ItemDetailView(APIView):
    serializer_class = ItemSerializer

    def get(self, request: Request, item_id: int) -> Response:
        return Response({})

    def patch(self, request: Request, item_id: int) -> Response:
        return Response({})


class ItemCloseView(APIView):
    @extend_schema(responses={200: ItemSerializer, 409: OpenApiResponse(description="The item is already closed.")})
    def post(self, request: Request, item_id: int) -> Response:
        return Response({})


def build_schema(urlpatterns: list[Any]) -> dict[str, Any]:
    from drf_spectacular.generators import SchemaGenerator

    return SchemaGenerator(patterns=urlpatterns).get_schema(request=None, public=True)


@pytest.fixture(scope="module")
def item_schema() -> dict[str, Any]:
    from django.urls import path

    return build_schema(
        [
            path("items/", ItemListView.as_view()),
            path("items/<int:item_id>/", ItemDetailView.as_view()),
            path("items/<int:item_id>/close/", ItemCloseView.as_view()),
        ]
    )


def response_codes(schema: dict[str, Any], path_name: str, method: str) -> set[str]:
    return set(schema["paths"][path_name][method]["responses"])


def test_default_error_responses_depend_on_the_operation(item_schema: dict[str, Any]) -> None:
    assert response_codes(item_schema, "/items/", "get") == {"200", "500"}
    # A plain APIView POST is documented as 200; DRF's generic create views get 201.
    assert response_codes(item_schema, "/items/", "post") == {"200", "400", "500"}
    assert response_codes(item_schema, "/items/{item_id}/", "get") == {"200", "404", "500"}
    assert response_codes(item_schema, "/items/{item_id}/", "patch") == {"200", "400", "404", "500"}


def test_default_error_responses_use_the_error_schema(item_schema: dict[str, Any]) -> None:
    response = item_schema["paths"]["/items/{item_id}/"]["patch"]["responses"]["404"]

    assert response["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/ErrorResponse"}


def test_error_schema_documents_the_error_shape(item_schema: dict[str, Any]) -> None:
    components = item_schema["components"]["schemas"]

    assert components["ErrorResponse"]["properties"]["error"] == {"$ref": "#/components/schemas/Error"}
    assert set(components["Error"]["properties"]) == {"type", "message", "detail", "fields"}
    assert set(components["Error"]["required"]) == {"type", "message"}
    assert "description" not in components["ErrorTypeEnum"]  # no redundant "* `A` - A" bullets
    assert components["ErrorTypeEnum"]["enum"] == [
        "VALIDATION_ERROR",
        "NOT_FOUND",
        "METHOD_NOT_ALLOWED",
        "CONFLICT",
        "UNSUPPORTED_MEDIA_TYPE",
        "REQUEST_ERROR",
        "INTERNAL_ERROR",
    ]


def test_explicit_responses_are_kept(item_schema: dict[str, Any]) -> None:
    assert response_codes(item_schema, "/items/{item_id}/close/", "post") == {"200", "409", "400", "404", "500"}


def test_health_documents_ok_and_500() -> None:
    schema = build_schema(project_urlpatterns)

    assert response_codes(schema, "/api/health/", "get") == {"200", "500"}


def test_every_endpoint_has_a_summary_and_a_capitalized_tag() -> None:
    schema = build_schema(project_urlpatterns)

    for path_name, operations in schema["paths"].items():
        for method, operation in operations.items():
            assert operation.get("summary"), f"{method.upper()} {path_name} needs a summary"
            assert [tag[0].isupper() for tag in operation["tags"]] == [True], f"{method.upper()} {path_name}: tags"
