from rest_framework import serializers

from core.exceptions import ErrorType


class ErrorSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=ErrorType.choices)
    message = serializers.CharField()
    detail = serializers.CharField(required=False, help_text="Extra context, when there is any.")
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        help_text="Validation errors only: messages for each invalid field (`non_field_errors` for the rest).",
    )


class ErrorResponseSerializer(serializers.Serializer):
    """The body of every error response (see `core.exceptions.api_exception_handler`)."""

    error = ErrorSerializer()
