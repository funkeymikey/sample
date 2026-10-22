"""Helpers for building CSV uploads in tests."""

from django.core.files.uploadedfile import SimpleUploadedFile

HEADER = "account_number,direction,amount,transaction_date,reference_id,description"


def csv_upload(*lines: str, header: str = HEADER, name: str = "transactions.csv") -> SimpleUploadedFile:
    """An uploaded CSV file with `header` and then `lines`."""
    content = "\n".join([header, *lines, ""])  # ends with a newline
    return SimpleUploadedFile(name, content.encode(), content_type="text/csv")
