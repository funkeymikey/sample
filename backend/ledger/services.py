import datetime
from decimal import Decimal

from django.db import transaction as db_transaction

from core.exceptions import ApiError
from ledger.models import Account, AccountStatus, Transaction, TransactionDirection


def create_account(*, external_id: str, holder_name: str, email: str = "") -> Account:
    """Open a new account. New accounts always start OPEN."""
    return Account.objects.create(external_id=external_id, holder_name=holder_name, email=email)


def update_account(account: Account, **changes: object) -> Account:
    """Apply `changes` (holder_name, email, status) to an account and return it.

    Raises `ApiError` (a 400) if the account is CLOSED: closing is final, so a closed account can't be
    edited or reopened. The row is locked while checking, so a concurrent close can't slip past.
    """
    with db_transaction.atomic():
        locked_account = Account.objects.select_for_update().get(pk=account.pk)
        if locked_account.status == AccountStatus.CLOSED:
            raise ApiError("Closed accounts can't be changed.")
        for field_name, value in changes.items():
            setattr(locked_account, field_name, value)
        locked_account.save(update_fields=[*changes, "updated_at"])
    return locked_account


def post_transaction(
    *,
    account: Account,
    direction: TransactionDirection,
    amount: Decimal,
    transaction_date: datetime.date,
    reference_id: str,
    description: str = "",
) -> Transaction:
    """Post a transaction to an account and return it.

    Raises `ApiError` (a 400) if the account is CLOSED, and `ConflictError` (a 409) if the account
    already has a transaction with this `reference_id` (reposting the same source record is rejected,
    not duplicated). The account row is locked while posting, so the transaction can't land on an
    account that's being closed.
    """
    from django.db import IntegrityError

    from core.exceptions import ConflictError

    with db_transaction.atomic():
        locked_account = Account.objects.select_for_update().get(pk=account.pk)
        if locked_account.status == AccountStatus.CLOSED:
            raise ApiError("Closed accounts can't receive transactions.")
        try:
            with db_transaction.atomic():
                return Transaction.objects.create(
                    account=locked_account,
                    direction=direction,
                    amount=amount,
                    transaction_date=transaction_date,
                    reference_id=reference_id,
                    description=description,
                )
        except IntegrityError as error:
            raise ConflictError(
                f"A transaction with reference_id {reference_id!r} already exists for this account."
            ) from error
