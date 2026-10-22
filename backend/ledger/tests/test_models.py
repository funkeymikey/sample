from decimal import Decimal

import pytest
from django.db import IntegrityError

from ledger.models import Account, TransactionDirection
from ledger.tests.factories import AccountFactory, TransactionFactory

pytestmark = pytest.mark.django_db


def test_base_model_gives_uuid_primary_key_and_timestamps() -> None:
    import uuid

    account = AccountFactory()
    first_updated_at = account.updated_at

    account.holder_name = "Renamed"
    account.save()

    assert isinstance(account.pk, uuid.UUID)
    assert account.created_at is not None
    assert account.updated_at > first_updated_at


def test_account_number_is_unique() -> None:
    AccountFactory(account_number="ACCT000001")

    with pytest.raises(IntegrityError):
        AccountFactory(account_number="ACCT000001")


def test_reference_id_is_unique_per_account_only() -> None:
    first_account, second_account = AccountFactory(), AccountFactory()
    TransactionFactory(account=first_account, reference_id="REF-1")
    TransactionFactory(account=second_account, reference_id="REF-1")  # same reference, other account: fine

    with pytest.raises(IntegrityError):
        TransactionFactory(account=first_account, reference_id="REF-1")


@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("-5.00")])
def test_database_rejects_non_positive_amounts(amount: Decimal) -> None:
    with pytest.raises(IntegrityError):
        TransactionFactory(amount=amount)


def test_database_rejects_unknown_directions() -> None:
    with pytest.raises(IntegrityError):
        TransactionFactory(direction="REFUND")  # fits the column, but isn't DEBIT or CREDIT


def test_account_with_transactions_cannot_be_deleted() -> None:
    from django.db.models import ProtectedError

    transaction = TransactionFactory()

    with pytest.raises(ProtectedError):
        transaction.account.delete()


CREDIT, DEBIT = TransactionDirection.CREDIT, TransactionDirection.DEBIT


@pytest.mark.parametrize(
    ("transactions", "expected_balance"),
    [
        pytest.param([], "0.00", id="no transactions"),
        pytest.param([(CREDIT, "500.00"), (DEBIT, "120.50")], "379.50", id="credits minus debits"),
        pytest.param([(DEBIT, "75.00")], "-75.00", id="overdrawn"),
        pytest.param([(CREDIT, "10.00"), (CREDIT, "0.01"), (CREDIT, "1234.56")], "1244.57", id="credits only"),
        pytest.param([(DEBIT, "19.99"), (DEBIT, "0.01"), (DEBIT, "80.00")], "-100.00", id="debits only"),
        pytest.param(
            [
                (CREDIT, "1500.00"),
                (DEBIT, "349.99"),
                (CREDIT, "0.37"),
                (DEBIT, "1000.00"),
                (CREDIT, "25.25"),
                (DEBIT, "175.63"),
            ],
            "0.00",
            id="many mixed, nets to zero",
        ),
        pytest.param(
            [
                (CREDIT, "2500.00"),
                (DEBIT, "1200.00"),
                (DEBIT, "45.67"),
                (CREDIT, "300.10"),
                (DEBIT, "0.43"),
                (CREDIT, "99.99"),
            ],
            "1653.99",
            id="many mixed, varying amounts",
        ),
        pytest.param(
            [(CREDIT, "0.10"), (CREDIT, "0.20"), (DEBIT, "0.30")], "0.00", id="exact cents (no float rounding)"
        ),
        pytest.param(
            [(CREDIT, "9999999999.99"), (CREDIT, "9999999999.99"), (DEBIT, "0.01")],
            "19999999999.97",
            id="total larger than any single amount",
        ),
    ],
)
def test_balance(transactions: list[tuple[TransactionDirection, str]], expected_balance: str) -> None:
    account = AccountFactory()
    for direction, amount in transactions:
        TransactionFactory(account=account, direction=direction, amount=Decimal(amount))
    TransactionFactory(direction=CREDIT, amount=Decimal("999.00"))  # another account's money never counts

    assert Account.objects.with_balance().get(pk=account.pk).balance == Decimal(expected_balance)


def test_balances_are_computed_per_account_in_one_query(django_assert_num_queries) -> None:
    expected_balances = {}
    for credit, debit in [("100.00", "30.00"), ("5.00", "50.00"), ("0.00", "0.00")]:
        account = AccountFactory()
        if Decimal(credit):
            TransactionFactory(account=account, direction=CREDIT, amount=Decimal(credit))
        if Decimal(debit):
            TransactionFactory(account=account, direction=DEBIT, amount=Decimal(debit))
        expected_balances[account.pk] = Decimal(credit) - Decimal(debit)

    with django_assert_num_queries(1):
        balances = {account.pk: account.balance for account in Account.objects.with_balance()}

    assert balances == expected_balances


def test_string_representations() -> None:
    transaction = TransactionFactory(
        account=AccountFactory(account_number="ACCT1", holder_name="Ada Lovelace"),
        reference_id="REF-1",
        direction=TransactionDirection.CREDIT,
        amount=Decimal("12.50"),
    )

    assert str(transaction.account) == "ACCT1 (Ada Lovelace)"
    assert str(transaction) == "REF-1: CREDIT 12.50"
