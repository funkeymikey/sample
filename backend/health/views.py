from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from health.services import HealthStatus, do_health_check

HealthSerializer = inline_serializer("Health", {"status": serializers.ChoiceField(choices=HealthStatus.choices)})


class HealthView(APIView):
    """Report whether the API is up and can reach the database."""

    @extend_schema(
        summary="Health check",
        description=(
            "Runs a trivial query against the database. Intended for uptime checks and load balancers: "
            "anything other than a 200 means the API can't serve requests. If the database is unreachable, "
            "the response is the standard 500 error."
        ),
        responses={
            200: OpenApiResponse(
                HealthSerializer,
                description="The API is up and the database is reachable.",
                examples=[OpenApiExample("Healthy", value={"status": HealthStatus.OK})],
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Return 200 `{"status": "ok"}`; a database failure becomes the exception handler's 500."""
        return Response(do_health_check())
