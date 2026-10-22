from django.db import models

from core.models import BaseModel


class ImportStatus(models.TextChoices):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"  # every row was valid, and all of them were posted
    FAILED = "FAILED"  # at least one row was invalid, so none were posted


class ImportBatch(BaseModel):
    """One uploaded CSV file of transactions. Imports are all-or-nothing, and never deleted."""

    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=ImportStatus.choices, default=ImportStatus.PROCESSING)
    row_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0, help_text="How many rows had errors.")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.status})"


class ImportFile(BaseModel):
    """The file exactly as uploaded, kept so every import can be audited.

    A table of its own, so listing or reading imports never loads file contents by accident.
    """

    batch = models.OneToOneField(ImportBatch, on_delete=models.PROTECT, related_name="file")
    content = models.BinaryField(help_text="The uploaded bytes, unchanged (at most 5 MB).")

    def __str__(self) -> str:
        return f"File of {self.batch.original_filename}"


class ImportRowError(BaseModel):
    """The problems with one row of a failed import."""

    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="row_errors")
    row_number = models.PositiveIntegerField(help_text="The line in the file (the header is line 1).")
    raw_data = models.JSONField(help_text="The row as uploaded, column by column.")
    errors = models.JSONField(help_text="The messages for each invalid column.")

    class Meta:
        ordering = ["row_number"]

    def __str__(self) -> str:
        return f"Line {self.row_number} of {self.batch.original_filename}"
