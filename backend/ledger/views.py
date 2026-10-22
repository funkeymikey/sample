from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import filters, generics
from rest_framework.request import Request
from rest_framework.response import Response

from core.serializers import ErrorResponseSerializer
from ledger.filters import AccountFilter, TransactionFilter
from ledger.models import Account, Transaction
from ledger.serializers import AccountSerializer, AccountUpdateSerializer, TransactionSerializer

DUPLICATE_REFERENCE_RESPONSE = OpenApiResponse(
    ErrorResponseSerializer, description="The account already has a transaction with this `reference_id`."
)

ACCOUNTS_TAG = "Accounts"
TRANSACTIONS_TAG = "Transactions"


@extend_schema_view(
    get=extend_schema(
        summary="List accounts",
        description="Accounts with their current balances. Search by account number, name or email, "
        "filter by `status`, and sort with `ordering` (for example `-balance`).",
        tags=[ACCOUNTS_TAG],
    ),
    post=extend_schema(
        summary="Open an account",
        description="New accounts always start OPEN, with a zero balance. "
        "Leave out `account_number` to have one generated.",
        tags=[ACCOUNTS_TAG],
    ),
)
class AccountListView(generics.ListCreateAPIView):
    """List accounts (with balances) or open a new one."""

    queryset = Account.objects.with_balance()
    serializer_class = AccountSerializer
    filterset_class = AccountFilter
    filter_backends = [*generics.ListCreateAPIView.filter_backends, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["account_number", "holder_name", "email"]
    ordering_fields = ["account_number", "holder_name", "balance", "created_at"]
    # Explicit, because Django drops Meta.ordering on aggregate queries like the balance.
    ordering = ["account_number"]

    def perform_create(self, serializer: AccountSerializer) -> None:
        from ledger.services import create_account

        account = create_account(**serializer.validated_data)
        serializer.instance = Account.objects.with_balance().get(pk=account.pk)


@extend_schema_view(
    get=extend_schema(
        summary="Get an account", description="One account, with its current balance.", tags=[ACCOUNTS_TAG]
    )
)
class AccountDetailView(generics.RetrieveAPIView):
    """View or edit one account. Accounts are never deleted: set `status` to CLOSED instead."""

    queryset = Account.objects.with_balance()
    serializer_class = AccountSerializer

    @extend_schema(
        summary="Update an account",
        description="Change an account's name, email or status. Set `status` to CLOSED to close it: closing is "
        "final, and a closed account can't be changed (400). `account_number` can't be changed, and accounts are "
        "never deleted.",
        request=AccountUpdateSerializer,
        responses={200: AccountSerializer},
        tags=[ACCOUNTS_TAG],
    )
    def patch(self, request: Request, pk: str) -> Response:
        """Edit an account's name, email or status. Closed accounts can't be changed (400)."""
        from ledger.services import update_account

        account = self.get_object()
        serializer = AccountUpdateSerializer(account, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_account(account, **serializer.validated_data)
        return Response(AccountSerializer(self.get_object()).data)


@extend_schema_view(
    get=extend_schema(
        summary="List an account's transactions",
        description="Newest first. Filter by `direction` and a `transaction_date` range.",
        tags=[TRANSACTIONS_TAG],
    ),
    post=extend_schema(
        summary="Post a transaction",
        description="Post a transaction to the account. Leave out `reference_id` to have one generated. "
        "A closed account is a 400; a duplicate `reference_id` is a 409.",
        responses={201: TransactionSerializer, 409: DUPLICATE_REFERENCE_RESPONSE},
        tags=[TRANSACTIONS_TAG],
    ),
)
class AccountTransactionListView(generics.ListCreateAPIView):
    """List one account's transactions, or post a new one to it."""

    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter

    def get_account(self) -> Account:
        """The account from the URL, or a 404."""
        return generics.get_object_or_404(Account, pk=self.kwargs["pk"])

    def get_queryset(self) -> QuerySet[Transaction]:
        """Return the transactions for the account in the URL (a 404 if that account doesn't exist).

        The other views can set `queryset = ...` once, up front. This one can't, because it doesn't know
        which account to show until a request arrives with an account id in the URL.
        """
        # When building the API docs, drf-spectacular calls this method without a real request, so there's
        # no account id to look up. Returning an empty result lets it document the endpoint without crashing.
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()

        return Transaction.objects.filter(account=self.get_account())

    def perform_create(self, serializer: TransactionSerializer) -> None:
        from ledger.services import post_transaction

        serializer.instance = post_transaction(account=self.get_account(), **serializer.validated_data)


@extend_schema_view(
    get=extend_schema(
        summary="Get a transaction",
        description="Transactions can't be edited or deleted. To correct one, post a transaction for the same "
        "amount in the opposite direction.",
        tags=[TRANSACTIONS_TAG],
    )
)
class TransactionDetailView(generics.RetrieveAPIView):
    """View one transaction. Transactions can't be edited or deleted: post a reversal instead."""

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
