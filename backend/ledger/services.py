import datetime
import secrets
from collections.abc import Callable
from decimal import Decimal

from django.db import IntegrityError
from django.db import transaction as db_transaction

from core.exceptions import ApiError
from ledger.models import Account, AccountStatus, Transaction, TransactionDirection

# Generated values are random, so a collision is possible but rare; give up after this many tries.
GENERATION_ATTEMPTS = 5


def generate_account_number() -> str:
    """A random 10-digit account number. It might already be taken: callers retry on a collision."""
    return f"{secrets.randbelow(10**10):010d}"


def generate_reference_id() -> str:
    """A random transaction reference like "TXN-8F3K2Q7M". It might already be taken: callers retry on a collision."""
    import string

    alphabet = string.ascii_uppercase + string.digits
    return f"TXN-{''.join(secrets.choice(alphabet) for _ in range(8))}"


def create_with_generated_value[T](create: Callable[[str], T], generate: Callable[[], str]) -> T:
    """Call `create` with a generated value, retrying with a new one if a unique constraint rejects it.

    Each attempt runs in its own savepoint, so a collision doesn't break an enclosing transaction.
    Raises `RuntimeError` if every attempt collides, which in practice means something is wrong.
    """
    for _ in range(GENERATION_ATTEMPTS):
        try:
            with db_transaction.atomic():
                return create(generate())
        except IntegrityError:
            continue
    raise RuntimeError(f"Couldn't generate an unused value in {GENERATION_ATTEMPTS} attempts.")


def create_account(*, holder_name: str, email: str = "", account_number: str = "") -> Account:
    """Open a new account and return it. New accounts always start OPEN.

    Without an `account_number`, a random 10-digit one is generated.
    """
    if account_number:
        return Account.objects.create(account_number=account_number, holder_name=holder_name, email=email)
    return create_with_generated_value(
        lambda number: Account.objects.create(account_number=number, holder_name=holder_name, email=email),
        generate_account_number,
    )


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
    reference_id: str = "",
    description: str = "",
) -> Transaction:
    """Post a transaction to an account and return it.

    Without a `reference_id`, a random one like "TXN-8F3K2Q7M" is generated. Raises `ApiError` (a 400) if the
    account is CLOSED, and `ConflictError` (a 409) if a given `reference_id` is already used on the account
    (reposting the same source record is rejected, not duplicated). The account row is locked while posting,
    so the transaction can't land on an account that's being closed.
    """
    from core.exceptions import ConflictError

    with db_transaction.atomic():
        locked_account = Account.objects.select_for_update().get(pk=account.pk)
        if locked_account.status == AccountStatus.CLOSED:
            raise ApiError("Closed accounts can't receive transactions.")

        def create(reference: str) -> Transaction:
            return Transaction.objects.create(
                account=locked_account,
                direction=direction,
                amount=amount,
                transaction_date=transaction_date,
                reference_id=reference,
                description=description,
            )

        if not reference_id:
            return create_with_generated_value(create, generate_reference_id)
        try:
            with db_transaction.atomic():
                return create(reference_id)
        except IntegrityError as error:
            raise ConflictError(
                f"A transaction with reference_id {reference_id!r} already exists for this account."
            ) from error
