"""Fill an empty database with demo data: accounts, their transactions, and a failed and a completed import."""

import random
from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from imports.models import ImportBatch
from ledger.models import Account

# How far back the demo transactions go.
HISTORY_DAYS = 120


class Command(BaseCommand):
    help = "Fill an empty database with demo accounts, transactions and imports. Does nothing if accounts exist."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--accounts", type=int, default=30, help="How many accounts to open (default 30).")

    def handle(self, *args: object, accounts: int, **options: object) -> None:
        """Seed through the same services the API uses, so the data follows every rule real data does.

        Each account gets an opening deposit and some history, then one import fails (the sample file with
        errors) and its corrected follow-up completes. Roughly 1 in 10 accounts is closed at the end. It all
        happens in one transaction, so a failure leaves the database empty rather than half-seeded.
        """
        from django.db import transaction as db_transaction

        from ledger.models import AccountStatus
        from ledger.services import update_account

        if Account.objects.exists():
            self.stdout.write(self.style.WARNING("The database already has accounts, so nothing was seeded."))
            return

        with db_transaction.atomic():
            opened = [open_account_with_history() for _ in range(accounts)]
            failed, completed = import_samples()
            for account in random.sample(opened, max(1, accounts // 10)):
                update_account(account, status=AccountStatus.CLOSED)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {accounts} accounts, one failed import ({failed.error_count} row errors) and one "
                f"completed import ({completed.row_count} transactions)."
            )
        )


def open_account_with_history() -> Account:
    """Open an account with a random holder, an opening deposit and up to 20 more transactions."""
    import datetime
    from decimal import Decimal

    from faker import Faker

    from imports.samples import AMOUNT_RANGE_IN_CENTS, DESCRIPTIONS
    from ledger.models import TransactionDirection
    from ledger.services import create_account, post_transaction

    fake = Faker()
    email = fake.email() if random.random() < 0.75 else ""  # some holders have no email on file
    account = create_account(holder_name=fake.name(), email=email)

    today = datetime.date.today()
    dates = sorted(
        today - datetime.timedelta(days=random.randint(0, HISTORY_DAYS)) for _ in range(random.randint(3, 21))
    )
    post_transaction(
        account=account,
        direction=TransactionDirection.CREDIT,
        amount=Decimal(random.randint(50_000, 500_000)) / 100,  # $500.00 to $5,000.00
        transaction_date=dates[0],
        description="Opening deposit",
    )
    for transaction_date in dates[1:]:
        # 2 in 3 debits: the opening deposit gets spent down.
        direction = random.choice([TransactionDirection.CREDIT, TransactionDirection.DEBIT, TransactionDirection.DEBIT])
        post_transaction(
            account=account,
            direction=direction,
            amount=Decimal(random.randint(*AMOUNT_RANGE_IN_CENTS[direction])) / 100,
            transaction_date=transaction_date,
            description=random.choice(DESCRIPTIONS[direction]),
        )
    return account


def import_samples() -> tuple[ImportBatch, ImportBatch]:
    """Upload a sample file with errors (it fails), then a clean one (it completes). Returns both batches."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    from imports.samples import sample_csv
    from imports.services import import_transactions

    def upload(name: str, content: str) -> ImportBatch:
        return import_transactions(SimpleUploadedFile(name, content.encode(), content_type="text/csv"))

    failed = upload("bank-feed.csv", sample_csv(rows=25, invalid=True))
    completed = upload("bank-feed-fixed.csv", sample_csv(rows=40))
    return failed, completed
