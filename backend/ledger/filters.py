import django_filters

from ledger.models import Account, Transaction


class AccountFilter(django_filters.FilterSet):
    class Meta:
        model = Account
        fields = ["status"]


class TransactionFilter(django_filters.FilterSet):
    """Filters for one account's transactions (the account comes from the URL)."""

    transaction_date = django_filters.DateFromToRangeFilter(
        help_text="Use `transaction_date_after` and/or `transaction_date_before` (inclusive)."
    )

    class Meta:
        model = Transaction
        fields = ["direction", "transaction_date"]
