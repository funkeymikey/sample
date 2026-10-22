from django.db import models
from django.db.models import Q

from core.models import BaseModel


class AccountStatus(models.TextChoices):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class TransactionDirection(models.TextChoices):
    DEBIT = "DEBIT"  # money out (a withdrawal or charge): decreases the balance
    CREDIT = "CREDIT"  # money in (a deposit or payment): increases it


MONEY_MAX_DIGITS = 12
BALANCE_MAX_DIGITS = 14  # room for the sum of many transactions


class AccountQuerySet(models.QuerySet):
    def with_balance(self) -> "AccountQuerySet":
        """Annotate each account with `balance`: credits minus debits, like a bank account.

        Positive is money held; negative means the account is overdrawn (it owes money).

        Computed in the same query as the accounts themselves, rather than stored (see README, design decisions).
        """
        from decimal import Decimal

        from django.db.models import Case, DecimalField, F, Sum, Value, When
        from django.db.models.functions import Coalesce

        signed_amount = Case(
            When(transactions__direction=TransactionDirection.CREDIT, then=F("transactions__amount")),
            default=-F("transactions__amount"),  # otherwise, a debit
        )
        return self.annotate(
            balance=Coalesce(
                Sum(signed_amount),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=BALANCE_MAX_DIGITS, decimal_places=2),
            )
        )


class Account(BaseModel):
    account_number = models.CharField(
        max_length=32,
        unique=True,
        help_text="Unique, and can't change after create. Generated (10 random digits) when left blank.",
    )
    holder_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=6, choices=AccountStatus.choices, default=AccountStatus.OPEN)

    objects = AccountQuerySet.as_manager()

    class Meta:
        ordering = ["account_number"]

    def __str__(self) -> str:
        return f"{self.account_number} ({self.holder_name})"


class Transaction(BaseModel):
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transactions")
    direction = models.CharField(max_length=6, choices=TransactionDirection.choices)
    amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=2, help_text="Always positive; the sign comes from `direction`."
    )
    transaction_date = models.DateField()
    reference_id = models.CharField(
        max_length=64,
        help_text="The source system's ID, unique per account, so reposting is idempotent. "
        'Generated ("TXN-" and 8 letters or digits) when left blank.',
    )
    description = models.CharField(max_length=255, blank=True)
    import_batch = models.ForeignKey(
        "imports.ImportBatch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
        help_text="The CSV import that posted this transaction, if any.",
    )

    class Meta:
        ordering = ["-transaction_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["account", "reference_id"], name="unique_reference_per_account"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="transaction_amount_positive"),
            models.CheckConstraint(
                condition=Q(direction__in=TransactionDirection.values), name="transaction_direction_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reference_id}: {self.direction} {self.amount}"
