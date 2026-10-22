import datetime
from decimal import Decimal

import factory

from ledger.models import Account, AccountStatus, Transaction, TransactionDirection


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Account

    external_id = factory.Sequence(lambda number: f"ACCT{number:06d}")
    holder_name = factory.Faker("name")
    email = factory.Faker("email")
    status = AccountStatus.OPEN


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    account = factory.SubFactory(AccountFactory)
    direction = TransactionDirection.DEBIT
    amount = Decimal("100.00")
    transaction_date = datetime.date(2026, 9, 1)
    reference_id = factory.Sequence(lambda number: f"REF{number:08d}")
    description = ""
