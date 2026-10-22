import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from imports.models import ImportStatus
from imports.samples import sample_csv
from imports.services import import_transactions
from ledger.models import AccountStatus, Transaction
from ledger.tests.factories import AccountFactory

pytestmark = pytest.mark.django_db


def parse(content: str) -> list[dict[str, str]]:
    import csv
    import io

    return list(csv.DictReader(io.StringIO(content)))


def test_sample_uses_real_open_accounts_and_both_directions() -> None:
    from ledger.models import TransactionDirection

    open_accounts = {AccountFactory().account_number for _ in range(3)}
    AccountFactory(status=AccountStatus.CLOSED)

    rows = parse(sample_csv(rows=40))

    assert len(rows) == 40
    assert {row["account_number"] for row in rows} <= open_accounts
    assert {row["direction"] for row in rows} == {TransactionDirection.CREDIT, TransactionDirection.DEBIT}
    assert len({row["reference_id"] for row in rows}) == 40


def test_a_valid_sample_imports_cleanly() -> None:
    AccountFactory.create_batch(2)

    batch = import_transactions(SimpleUploadedFile("sample.csv", sample_csv(rows=25).encode()))

    assert (batch.status, batch.error_count) == (ImportStatus.COMPLETED, 0)
    assert Transaction.objects.count() == 25


def test_an_invalid_sample_fails_with_a_few_deliberate_errors() -> None:
    AccountFactory.create_batch(2)

    batch = import_transactions(SimpleUploadedFile("sample.csv", sample_csv(rows=25, invalid=True).encode()))

    assert batch.status == ImportStatus.FAILED
    assert Transaction.objects.count() == 0
    failed_fields = sorted(field for row_error in batch.row_errors.all() for field in row_error.errors)
    assert failed_fields == ["account_number", "amount", "reference_id", "transaction_date"]


def test_a_sample_needs_an_open_account() -> None:
    from core.exceptions import ApiError

    AccountFactory(status=AccountStatus.CLOSED)

    with pytest.raises(ApiError, match="no open accounts"):
        sample_csv(rows=5)


@pytest.mark.parametrize("rows", [1, 2, 3, 5])
def test_an_invalid_sample_fails_however_small_it_is(rows: int) -> None:
    AccountFactory()

    batch = import_transactions(SimpleUploadedFile("sample.csv", sample_csv(rows=rows, invalid=True).encode()))

    assert batch.status == ImportStatus.FAILED
    assert Transaction.objects.count() == 0
