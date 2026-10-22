from decimal import Decimal

from rest_framework import serializers

from ledger.models import BALANCE_MAX_DIGITS, Account, Transaction


class AccountSerializer(serializers.ModelSerializer):
    """An account as the API returns it, and the body for creating one."""

    balance = serializers.DecimalField(
        max_digits=BALANCE_MAX_DIGITS,
        decimal_places=2,
        read_only=True,
        help_text="Credits minus debits: positive is money held, negative means the account is overdrawn.",
    )

    class Meta:
        model = Account
        fields = ["id", "external_id", "holder_name", "email", "status", "balance", "created_at", "updated_at"]
        # Everything else is input. New accounts always start OPEN, so `status` is read-only here.
        read_only_fields = ["id", "status", "balance", "created_at", "updated_at"]


class AccountUpdateSerializer(serializers.ModelSerializer):
    """The editable fields of an account. `external_id` can't change after create."""

    class Meta:
        model = Account
        fields = ["holder_name", "email", "status"]


class TransactionSerializer(serializers.ModelSerializer):
    """A transaction as the API returns it, and the body for posting one (the account comes from the URL)."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        help_text="Always positive, at most 2 decimal places; the sign comes from `direction`.",
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "direction",
            "amount",
            "transaction_date",
            "reference_id",
            "description",
            "created_at",
        ]
        # Everything else is input. The account comes from the URL.
        read_only_fields = ["id", "account", "created_at"]
        # Duplicate reference_ids are rejected by the service as a 409, not here as a 400.
        validators: list = []
