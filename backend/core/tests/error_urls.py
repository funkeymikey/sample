"""Throwaway views that raise each kind of error, for the exception handler tests."""

from django.http import Http404
from django.urls import path
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import ApiError, ConflictError


class AccountSerializer(serializers.Serializer):
    external_id = serializers.CharField()


class RaisingView(APIView):
    """Raise whatever exception the URL asks for."""

    exceptions = {
        "conflict": lambda: ConflictError("Account is closed.", detail="Closed accounts can't receive transactions."),
        "api-error": lambda: ApiError("Amount is too large."),
        "django-404": lambda: Http404("No account with that id."),
        "django-404-no-message": lambda: Http404(),
        "unexpected": lambda: RuntimeError("secret internal detail"),
    }

    def get(self, request: Request, kind: str) -> Response:
        raise self.exceptions[kind]()


class ValidatingView(APIView):
    def post(self, request: Request) -> Response:
        AccountSerializer(data=request.data).is_valid(raise_exception=True)
        return Response({})


class NonFieldValidatingView(APIView):
    def post(self, request: Request) -> Response:
        raise serializers.ValidationError("Amount and direction don't match.")


urlpatterns = [
    path("raise/<str:kind>/", RaisingView.as_view()),
    path("validate/", ValidatingView.as_view()),
    path("validate-non-field/", NonFieldValidatingView.as_view()),
]
