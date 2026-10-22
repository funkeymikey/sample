import factory

from imports.models import ImportBatch, ImportStatus


class ImportBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ImportBatch

    original_filename = "transactions.csv"
    status = ImportStatus.COMPLETED
    row_count = 0
    error_count = 0
