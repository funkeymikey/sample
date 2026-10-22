import uuid

from django.db import models


class BaseModel(models.Model):
    """The base for every table: a UUID primary key plus `created_at` and `updated_at`, maintained automatically."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
