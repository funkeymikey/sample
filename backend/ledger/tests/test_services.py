from unittest import mock

import pytest

from core.exceptions import ApiError
from ledger.models import Account, AccountStatus, Transaction
from ledger.services import create_account, update_account
from ledger.tests.factories import AccountFactory, TransactionFactory

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

    account = create_account(account_number="ACCT1", holder_name="Ada Lovelace", email="ada@example.com")

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

    existing = TransactionFactory(reference_id="REF-1")

    with pytest.raises(ConflictError, match="REF-1"):
        post(existing.account, reference_id="REF-1")
    assert Transaction.objects.count() == 1


def test_create_account_generates_an_account_number_when_none_is_given() -> None:

    account = create_account(holder_name="Ada Lovelace")

    assert len(account.account_number) == 10
    assert account.account_number.isdigit()


def test_generated_account_number_retries_on_a_collision() -> None:

    AccountFactory(account_number="1111111111")

    with mock.patch("ledger.services.generate_account_number", side_effect=["1111111111", "2222222222"]):
        account = create_account(holder_name="Ada Lovelace")

    assert account.account_number == "2222222222"


def test_post_transaction_generates_a_reference_when_none_is_given() -> None:
    import re

    transaction = post(AccountFactory(), reference_id="")

    assert re.fullmatch(r"TXN-[A-Z0-9]{8}", transaction.reference_id)


def test_generated_reference_retries_on_a_collision() -> None:

    existing = TransactionFactory(reference_id="TXN-AAAAAAAA")

    with mock.patch("ledger.services.generate_reference_id", side_effect=["TXN-AAAAAAAA", "TXN-BBBBBBBB"]):
        transaction = post(existing.account, reference_id="")

    assert transaction.reference_id == "TXN-BBBBBBBB"


def test_generation_gives_up_after_repeated_collisions() -> None:

    from ledger.services import GENERATION_ATTEMPTS, create_account

    AccountFactory(account_number="1111111111")

    with (
        mock.patch("ledger.services.generate_account_number", return_value="1111111111") as generate,
        pytest.raises(RuntimeError, match="Couldn't generate an unused value"),
    ):
        create_account(holder_name="Ada Lovelace")
    assert generate.call_count == GENERATION_ATTEMPTS
