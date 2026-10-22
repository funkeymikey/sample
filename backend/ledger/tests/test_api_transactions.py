import datetime
from typing import Any

import pytest
from rest_framework.test import APIClient

from core.tests.assertions import assert_documented_error
from ledger.models import AccountStatus, Transaction
from ledger.tests.factories import AccountFactory, TransactionFactory

pytestmark = pytest.mark.django_db

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def transactions_url(account_id: Any) -> str:
    return f"/api/accounts/{account_id}/transactions/"


def transaction_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "direction": "DEBIT",
        "amount": "125.50",
        "transaction_date": "2026-09-01",
        "reference_id": "REF-1",
        "description": "Fall tuition",
        **overrides,
    }


def test_create_transaction(api_client: APIClient) -> None:
    account = AccountFactory()

    response = api_client.post(transactions_url(account.pk), transaction_payload(), format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == "125.50"  # money is a string, never a float
    assert body["account"] == str(account.pk)
    assert set(body) == {
        "id",
        "account",
        "direction",
        "amount",
        "transaction_date",
        "reference_id",
        "description",
        "created_at",
    }


def test_account_in_the_body_is_ignored(api_client: APIClient) -> None:
    account, other_account = AccountFactory(), AccountFactory()

    response = api_client.post(
        transactions_url(account.pk), transaction_payload(account=str(other_account.pk)), format="json"
    )

    assert response.status_code == 201
    assert response.json()["account"] == str(account.pk)


@pytest.mark.parametrize(
    ("overrides", "invalid_field"),
    [
        ({"amount": "0.00"}, "amount"),
        ({"amount": "-5.00"}, "amount"),
        ({"amount": "10.005"}, "amount"),  # more than 2 decimal places: rejected, never rounded
        ({"direction": "SIDEWAYS"}, "direction"),
        ({"transaction_date": "2026-02-30"}, "transaction_date"),
        ({"amount": "12345678901.00"}, "amount"),  # 13 digits: more than the column holds
    ],
)
def test_create_transaction_validates_input(
    api_client: APIClient, overrides: dict[str, str], invalid_field: str
) -> None:
    account = AccountFactory()

    response = api_client.post(transactions_url(account.pk), transaction_payload(**overrides), format="json")

    assert_documented_error(response)
    assert response.status_code == 400
    assert list(response.json()["error"]["fields"]) == [invalid_field]
    assert Transaction.objects.count() == 0


@pytest.mark.parametrize("reference", [{}, {"reference_id": ""}], ids=["left out", "blank"])
def test_create_transaction_generates_a_reference_when_none_is_given(
    api_client: APIClient, reference: dict[str, str]
) -> None:
    import re

    payload = {**transaction_payload(), **reference}
    if not reference:
        del payload["reference_id"]
    account = AccountFactory()

    response = api_client.post(transactions_url(account.pk), payload, format="json")

    assert response.status_code == 201
    assert re.fullmatch(r"TXN-[A-Z0-9]{8}", response.json()["reference_id"])


def test_posting_to_an_unknown_account_is_a_404(api_client: APIClient) -> None:
    response = api_client.post(transactions_url(UNKNOWN_ID), transaction_payload(), format="json")

    assert_documented_error(response)
    assert response.status_code == 404


def test_closed_account_cannot_receive_transactions(api_client: APIClient) -> None:
    account = AccountFactory(status=AccountStatus.CLOSED)

    response = api_client.post(transactions_url(account.pk), transaction_payload(), format="json")

    assert_documented_error(response)
    assert response.status_code == 400
    assert response.json()["error"] == {
        "type": "VALIDATION_ERROR",
        "message": "Closed accounts can't receive transactions.",
    }
    assert Transaction.objects.count() == 0


def test_duplicate_reference_is_a_conflict(api_client: APIClient) -> None:
    existing = TransactionFactory(reference_id="REF-1")

    response = api_client.post(transactions_url(existing.account.pk), transaction_payload(), format="json")

    assert_documented_error(response)
    assert response.status_code == 409
    assert "REF-1" in response.json()["error"]["message"]


def test_list_shows_only_that_account_filtered_by_direction_and_date(
    api_client: APIClient, django_assert_num_queries
) -> None:
    from ledger.models import TransactionDirection

    account = AccountFactory()
    september_15 = datetime.date(2026, 9, 15)
    matching = TransactionFactory(account=account, direction=TransactionDirection.CREDIT, transaction_date=september_15)
    TransactionFactory(account=account, direction=TransactionDirection.DEBIT, transaction_date=september_15)
    TransactionFactory(
        account=account, direction=TransactionDirection.CREDIT, transaction_date=datetime.date(2026, 8, 1)
    )
    TransactionFactory(direction=TransactionDirection.CREDIT, transaction_date=september_15)  # another account

    with django_assert_num_queries(3):  # account lookup + count + page, however many rows
        response = api_client.get(
            transactions_url(account.pk),
            {"direction": "CREDIT", "transaction_date_after": "2026-09-01", "transaction_date_before": "2026-09-30"},
        )

    assert response.status_code == 200
    assert [transaction["id"] for transaction in response.json()["results"]] == [str(matching.pk)]


def test_list_is_newest_first(api_client: APIClient) -> None:
    account = AccountFactory()
    older = TransactionFactory(account=account, transaction_date=datetime.date(2026, 1, 1))
    newer = TransactionFactory(account=account, transaction_date=datetime.date(2026, 6, 1))

    response = api_client.get(transactions_url(account.pk))

    assert [transaction["id"] for transaction in response.json()["results"]] == [str(newer.pk), str(older.pk)]


def test_listing_an_unknown_account_is_a_404(api_client: APIClient) -> None:
    response = api_client.get(transactions_url(UNKNOWN_ID))

    assert_documented_error(response)
    assert response.status_code == 404


def test_there_is_no_list_of_all_transactions(api_client: APIClient) -> None:
    assert api_client.get("/api/transactions/").status_code == 404
    assert api_client.post("/api/transactions/", transaction_payload(), format="json").status_code == 404


def test_retrieve_transaction(api_client: APIClient) -> None:
    transaction = TransactionFactory()

    response = api_client.get(f"/api/transactions/{transaction.pk}/")

    assert response.status_code == 200
    assert response.json()["reference_id"] == transaction.reference_id


def test_transactions_are_immutable(api_client: APIClient) -> None:
    transaction = TransactionFactory()
    url = f"/api/transactions/{transaction.pk}/"

    assert api_client.patch(url, {"description": "edited"}, format="json").status_code == 405
    assert api_client.put(url, {}, format="json").status_code == 405
    assert api_client.delete(url).status_code == 405


def test_create_transaction_requires_fields(api_client: APIClient) -> None:
    account = AccountFactory()

    response = api_client.post(transactions_url(account.pk), {}, format="json")

    assert response.status_code == 400
    assert set(response.json()["error"]["fields"]) == {
        "direction",
        "amount",
        "transaction_date",
    }  # reference is optional


def test_description_is_optional(api_client: APIClient) -> None:
    account = AccountFactory()
    payload = transaction_payload()
    del payload["description"]

    response = api_client.post(transactions_url(account.pk), payload, format="json")

    assert response.status_code == 201
    assert response.json()["description"] == ""


def test_posted_transactions_add_up_to_the_account_balance(api_client: APIClient) -> None:
    account = AccountFactory()
    postings = [
        ("CREDIT", "1000.00"),  # paycheck
        ("DEBIT", "64.37"),  # groceries
        ("DEBIT", "1200.00"),  # rent: overdrawn
        ("CREDIT", "300.00"),  # transfer in
        ("DEBIT", "0.63"),  # fee
        ("CREDIT", "15.01"),  # refund
    ]

    for number, (direction, amount) in enumerate(postings, start=1):
        response = api_client.post(
            transactions_url(account.pk),
            transaction_payload(direction=direction, amount=amount, reference_id=f"REF-{number}"),
            format="json",
        )
        assert response.status_code == 201

    account_response = api_client.get(f"/api/accounts/{account.pk}/")
    list_response = api_client.get(transactions_url(account.pk))

    assert account_response.json()["balance"] == "50.01"  # 1315.01 in, 1265.00 out
    assert list_response.json()["count"] == len(postings)


def test_date_range_is_inclusive(api_client: APIClient) -> None:
    account = AccountFactory()
    first_day = TransactionFactory(account=account, transaction_date=datetime.date(2026, 9, 1))
    last_day = TransactionFactory(account=account, transaction_date=datetime.date(2026, 9, 30))
    TransactionFactory(account=account, transaction_date=datetime.date(2026, 10, 1))

    response = api_client.get(
        transactions_url(account.pk), {"transaction_date_after": "2026-09-01", "transaction_date_before": "2026-09-30"}
    )

    assert {transaction["id"] for transaction in response.json()["results"]} == {str(first_day.pk), str(last_day.pk)}


def test_closed_account_transactions_can_still_be_viewed(api_client: APIClient) -> None:
    account = AccountFactory(status=AccountStatus.CLOSED)
    TransactionFactory(account=account)

    response = api_client.get(transactions_url(account.pk))

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_unknown_transaction_is_a_404(api_client: APIClient) -> None:
    response = api_client.get(f"/api/transactions/{UNKNOWN_ID}/")

    assert_documented_error(response)
    assert response.status_code == 404
