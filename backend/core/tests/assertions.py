from rest_framework.response import Response


def assert_documented_error(response: Response) -> None:
    """The response body matches the ErrorResponse schema published in the API docs."""
    from core.serializers import ErrorResponseSerializer

    serializer = ErrorResponseSerializer(data=response.json())
    assert serializer.is_valid(), serializer.errors
