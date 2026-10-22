import pytest

from core.exceptions import ApiError
from ledger.models import Account, AccountStatus, Transaction
from ledger.services import update_account
from ledger.tests.factories import AccountFactory

pytestmark = pytest.mark.django_db


def post(account: Account, reference_id: str = "REF-1") -> Transaction:
    """Post a fixed 25.00 debit to `account`."""
    import datetime
    from decimal import Decimal

    from ledger.models import TransactionDirection
    from ledger.services import post_transaction

    return post_transaction(
        account=account,
        direction=TransactionDirection.DEBIT,
        amount=Decimal("25.00"),
        transaction_date=datetime.date(2026, 9, 1),
        reference_id=reference_id,
    )


def test_create_account_starts_open() -> None:
    from ledger.services import create_account

    account = create_account(external_id="ACCT1", holder_name="Ada Lovelace", email="ada@example.com")

    assert account.status == AccountStatus.OPEN


def test_update_account_changes_fields_and_can_close() -> None:
    account = AccountFactory()

    updated = update_account(account, holder_name="New Name", status=AccountStatus.CLOSED)

    account.refresh_from_db()
    assert updated.holder_name == account.holder_name == "New Name"
    assert account.status == AccountStatus.CLOSED


def test_closed_account_cannot_be_changed() -> None:
    account = AccountFactory(status=AccountStatus.CLOSED)

    for changes in [{"status": AccountStatus.OPEN}, {"holder_name": "New Name"}]:
        with pytest.raises(ApiError, match="Closed accounts can't be changed") as raised:
            update_account(account, **changes)
        assert type(raised.value) is ApiError  # a plain 400, not a ConflictError (409)


def test_post_transaction_creates_it() -> None:
    account = AccountFactory()

    transaction = post(account)

    saved = Transaction.objects.get()
    assert saved == transaction
    assert (saved.account, saved.direction, saved.amount, saved.reference_id) == (account, "DEBIT", 25, "REF-1")


def test_closed_account_cannot_receive_transactions() -> None:
    account = AccountFactory(status=AccountStatus.CLOSED)

    with pytest.raises(ApiError, match="Closed accounts can't receive transactions") as raised:
        post(account)
    assert type(raised.value) is ApiError  # a plain 400, not a ConflictError (409)
    assert Transaction.objects.count() == 0


def test_duplicate_reference_is_a_conflict() -> None:
    from core.exceptions import ConflictError
    from ledger.tests.factories import TransactionFactory

    existing = TransactionFactory(reference_id="REF-1")

    with pytest.raises(ConflictError, match="REF-1"):
        post(existing.account, reference_id="REF-1")
    assert Transaction.objects.count() == 1
