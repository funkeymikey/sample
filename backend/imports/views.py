from django.db.models import QuerySet
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from imports.models import ImportBatch, ImportRowError
from imports.serializers import (
    ImportBatchSerializer,
    ImportRowErrorSerializer,
    ImportUploadSerializer,
    SampleFileQuerySerializer,
)

IMPORTS_TAG = "Imports"
CSV_FILE_RESPONSE = OpenApiResponse(OpenApiTypes.STR, description="A CSV file, sent as a download.")


def csv_download(content: str, filename: str) -> HttpResponse:
    """A CSV file response that browsers save as `filename`."""
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@extend_schema_view(
    get=extend_schema(summary="List imports", description="Uploaded CSV files, newest first.", tags=[IMPORTS_TAG]),
)
class ImportListView(generics.ListAPIView):
    """List CSV imports, or upload a new one."""

    queryset = ImportBatch.objects.all()
    serializer_class = ImportBatchSerializer
    parser_classes = [MultiPartParser]

    @extend_schema(
        summary="Upload a CSV of transactions",
        description="All-or-nothing: if every row is valid, every row is posted (status COMPLETED); if any row is "
        "invalid, nothing is posted (status FAILED) and the row errors are saved. Either way the new import is "
        "returned with a 201. Problems with the file itself (too big, not CSV, missing columns) are a 400, and "
        "no import is created.",
        request={"multipart/form-data": ImportUploadSerializer},
        responses={201: ImportBatchSerializer},
        tags=[IMPORTS_TAG],
    )
    def post(self, request: Request) -> Response:
        from rest_framework import status

        from imports.services import import_transactions

        upload_serializer = ImportUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        batch = import_transactions(upload_serializer.validated_data["file"])
        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


@extend_schema_view(get=extend_schema(summary="Get an import", tags=[IMPORTS_TAG]))
class ImportDetailView(generics.RetrieveAPIView):
    """One CSV import: its status and row counts."""

    queryset = ImportBatch.objects.all()
    serializer_class = ImportBatchSerializer


@extend_schema_view(
    get=extend_schema(
        summary="List an import's row errors",
        description="Each invalid row of a failed import, with its line in the file (the header is line 1).",
        tags=[IMPORTS_TAG],
    )
)
class ImportErrorListView(generics.ListAPIView):
    """The invalid rows of one import."""

    serializer_class = ImportRowErrorSerializer

    def get_queryset(self) -> QuerySet[ImportRowError]:
        """Return the row errors of the import in the URL (a 404 if that import doesn't exist)."""
        # When building the API docs, drf-spectacular calls this method without a real request, so there's
        # no import id to look up. Returning an empty result lets it document the endpoint without crashing.
        if getattr(self, "swagger_fake_view", False):
            return ImportRowError.objects.none()
        batch = generics.get_object_or_404(ImportBatch, pk=self.kwargs["pk"])
        return batch.row_errors.all()


class ImportErrorCsvView(APIView):
    @extend_schema(
        summary="Download an import's row errors as CSV",
        description="The invalid rows with their original columns plus an `errors` column. Fix them in place and "
        "upload the file again: unknown columns like `errors` are ignored.",
        parameters=[OpenApiParameter("id", OpenApiTypes.UUID, OpenApiParameter.PATH)],
        responses={(200, "text/csv"): CSV_FILE_RESPONSE},
        tags=[IMPORTS_TAG],
    )
    def get(self, request: Request, pk: str) -> HttpResponse:
        from pathlib import Path

        from imports.services import errors_csv

        batch = generics.get_object_or_404(ImportBatch, pk=pk)
        return csv_download(errors_csv(batch), f"{Path(batch.original_filename).stem}-errors.csv")


class ImportFileView(APIView):
    @extend_schema(
        summary="Download an import's original file",
        description="The file exactly as it was uploaded, for auditing. A 404 for imports from before files were kept.",
        parameters=[OpenApiParameter("id", OpenApiTypes.UUID, OpenApiParameter.PATH)],
        responses={(200, "text/csv"): CSV_FILE_RESPONSE},
        tags=[IMPORTS_TAG],
    )
    def get(self, request: Request, pk: str) -> HttpResponse:
        from rest_framework.exceptions import NotFound

        from imports.models import ImportFile

        batch = generics.get_object_or_404(ImportBatch, pk=pk)
        try:
            content = ImportFile.objects.values_list("content", flat=True).get(batch=batch)
        except ImportFile.DoesNotExist as error:
            raise NotFound("The original file wasn't kept for this import.") from error
        response = HttpResponse(bytes(content), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{batch.original_filename}"'
        return response


class SampleFileView(APIView):
    @extend_schema(
        summary="Download a sample CSV",
        description="A file of transactions for real open accounts that imports cleanly, or, with `invalid=true`, "
        "one with a few deliberate errors. A 400 if there are no open accounts.",
        parameters=[SampleFileQuerySerializer],
        responses={(200, "text/csv"): CSV_FILE_RESPONSE},
        tags=[IMPORTS_TAG],
    )
    def get(self, request: Request) -> HttpResponse:
        from imports.samples import sample_csv

        query = SampleFileQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        invalid = query.validated_data["invalid"]
        content = sample_csv(rows=query.validated_data["rows"], invalid=invalid)
        return csv_download(content, "sample-with-errors.csv" if invalid else "sample.csv")
