import pytest

from imports.models import ImportBatch
from ledger.models import Account

pytestmark = pytest.mark.django_db


def seed(**options: object) -> str:
    import io

    from django.core.management import call_command

    output = io.StringIO()
    call_command("seed_demo", stdout=output, **options)
    return output.getvalue()


def test_seed_demo_fills_an_empty_database_with_accounts_transactions_and_imports() -> None:
    from imports.models import ImportStatus
    from ledger.models import AccountStatus

    output = seed(accounts=12)

    accounts = Account.objects.with_balance()
    assert accounts.count() == 12
    assert accounts.filter(status=AccountStatus.CLOSED).count() == 1
    assert not accounts.filter(transactions__isnull=True).exists()
    assert accounts.filter(balance__gt=0).exists()

    completed, failed = ImportBatch.objects.order_by("status")
    assert (completed.status, failed.status) == (ImportStatus.COMPLETED, ImportStatus.FAILED)
    assert completed.transactions.count() == completed.row_count
    assert failed.error_count == 4
    assert not failed.transactions.exists()
    assert "Seeded 12 accounts" in output


def test_seed_demo_leaves_a_database_that_already_has_accounts_alone() -> None:
    from ledger.tests.factories import AccountFactory

    AccountFactory()

    output = seed()

    assert Account.objects.count() == 1
    assert not ImportBatch.objects.exists()
    assert "already has accounts" in output
