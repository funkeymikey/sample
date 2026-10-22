from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.tests.assertions import assert_documented_error
from ledger.models import TransactionDirection
from ledger.tests.factories import AccountFactory, TransactionFactory

pytestmark = pytest.mark.django_db


def test_list_returns_accounts_with_their_own_balances(api_client: APIClient, django_assert_num_queries) -> None:
    saver, spender, untouched = AccountFactory(), AccountFactory(), AccountFactory()
    for direction, amount in [("CREDIT", "40.00"), ("DEBIT", "15.00"), ("CREDIT", "0.99")]:
        TransactionFactory(account=saver, direction=TransactionDirection(direction), amount=Decimal(amount))
    TransactionFactory(account=spender, direction=TransactionDirection.DEBIT, amount=Decimal("60.00"))

    with django_assert_num_queries(2):  # count + page, however many accounts
        response = api_client.get("/api/accounts/")

    body = response.json()
    assert response.status_code == 200
    assert body["count"] == 3
    balances = {account["id"]: account["balance"] for account in body["results"]}
    assert balances == {str(saver.pk): "25.99", str(spender.pk): "-60.00", str(untouched.pk): "0.00"}
    assert set(body["results"][0]) == {
        "id",
        "account_number",
        "holder_name",
        "email",
        "status",
        "balance",
        "created_at",
        "updated_at",
    }


def test_list_can_be_sorted_by_balance(api_client: APIClient) -> None:
    low, high, middle = AccountFactory(), AccountFactory(), AccountFactory()
    TransactionFactory(account=low, direction=TransactionDirection.DEBIT, amount=Decimal("5.00"))
    TransactionFactory(account=high, direction=TransactionDirection.CREDIT, amount=Decimal("500.00"))
    TransactionFactory(account=middle, direction=TransactionDirection.CREDIT, amount=Decimal("50.00"))

    response = api_client.get("/api/accounts/", {"ordering": "-balance"})

    assert [account["id"] for account in response.json()["results"]] == [str(high.pk), str(middle.pk), str(low.pk)]


def test_list_is_paginated(api_client: APIClient) -> None:
    AccountFactory.create_batch(27)

    first_page = api_client.get("/api/accounts/").json()
    second_page = api_client.get("/api/accounts/", {"page": 2}).json()

    assert first_page["count"] == 27
    assert len(first_page["results"]) == 25
    assert len(second_page["results"]) == 2
    assert second_page["next"] is None


def test_list_searches_and_filters(api_client: APIClient) -> None:
    from ledger.models import AccountStatus

    AccountFactory(account_number="ACCT1", holder_name="Ada Lovelace", email="ada@example.com")
    AccountFactory(
        account_number="ACCT2", holder_name="Grace Hopper", email="grace@navy.mil", status=AccountStatus.CLOSED
    )

    def account_numbers(params: dict[str, str]) -> list[str]:
        return [account["account_number"] for account in api_client.get("/api/accounts/", params).json()["results"]]

    assert account_numbers({"search": "lovelace"}) == ["ACCT1"]  # holder name, case-insensitive
    assert account_numbers({"search": "acct2"}) == ["ACCT2"]  # external id
    assert account_numbers({"search": "navy.mil"}) == ["ACCT2"]  # email
    assert account_numbers({"status": "CLOSED"}) == ["ACCT2"]


def test_create_account(api_client: APIClient) -> None:
    response = api_client.post(
        "/api/accounts/",
        {"account_number": "ACCT9", "holder_name": "Ada Lovelace", "status": "CLOSED"},
        format="json",
    )

    from ledger.models import Account

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "OPEN"  # status can't be set on create
    assert body["email"] == ""
    assert body["balance"] == "0.00"
    saved = Account.objects.get(pk=body["id"])
    assert (saved.account_number, saved.holder_name, saved.status) == ("ACCT9", "Ada Lovelace", "OPEN")


def test_create_account_generates_an_account_number_when_left_out(api_client: APIClient) -> None:
    without = api_client.post("/api/accounts/", {"holder_name": "Ada Lovelace"}, format="json")
    blank = api_client.post("/api/accounts/", {"holder_name": "Grace Hopper", "account_number": ""}, format="json")

    assert without.status_code == blank.status_code == 201
    numbers = [without.json()["account_number"], blank.json()["account_number"]]
    assert all(len(number) == 10 and number.isdigit() for number in numbers)
    assert numbers[0] != numbers[1]


def test_create_account_validates_input(api_client: APIClient) -> None:
    AccountFactory(account_number="ACCT1")

    duplicate = api_client.post("/api/accounts/", {"account_number": "ACCT1", "holder_name": "X"}, format="json")
    missing = api_client.post("/api/accounts/", {"email": "not-an-email"}, format="json")

    assert_documented_error(duplicate)
    assert duplicate.status_code == 400
    assert "account_number" in duplicate.json()["error"]["fields"]
    assert missing.status_code == 400
    assert set(missing.json()["error"]["fields"]) == {"holder_name", "email"}  # account_number is optional


def test_retrieve_account(api_client: APIClient) -> None:
    account = AccountFactory()
    TransactionFactory(account=account, direction=TransactionDirection.DEBIT, amount=Decimal("10.00"))

    response = api_client.get(f"/api/accounts/{account.pk}/")

    assert response.status_code == 200
    assert response.json()["balance"] == "-10.00"


@pytest.mark.parametrize("account_id", ["00000000-0000-0000-0000-000000000000", "not-a-uuid"])
def test_unknown_account_is_a_json_404(api_client: APIClient, account_id: str) -> None:
    response = api_client.get(f"/api/accounts/{account_id}/")

    assert_documented_error(response)
    assert response.status_code == 404


def test_patch_updates_fields_but_not_account_number(api_client: APIClient) -> None:
    account = AccountFactory(account_number="ACCT1")

    response = api_client.patch(
        f"/api/accounts/{account.pk}/", {"holder_name": "New Name", "account_number": "ACCT2"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["holder_name"] == "New Name"
    assert response.json()["account_number"] == "ACCT1"
    assert response.json()["balance"] == "0.00"
    account.refresh_from_db()
    assert (account.holder_name, account.account_number) == ("New Name", "ACCT1")


@pytest.mark.parametrize(
    ("changes", "invalid_field"),
    [({"email": "not-an-email"}, "email"), ({"holder_name": ""}, "holder_name"), ({"status": "FROZEN"}, "status")],
)
def test_patch_validates_input(api_client: APIClient, changes: dict[str, str], invalid_field: str) -> None:
    account = AccountFactory()

    response = api_client.patch(f"/api/accounts/{account.pk}/", changes, format="json")

    assert_documented_error(response)
    assert response.status_code == 400
    assert list(response.json()["error"]["fields"]) == [invalid_field]


def test_account_with_a_balance_can_be_closed(api_client: APIClient) -> None:
    account = AccountFactory()
    TransactionFactory(account=account, direction=TransactionDirection.CREDIT, amount=Decimal("12.34"))

    response = api_client.patch(f"/api/accounts/{account.pk}/", {"status": "CLOSED"}, format="json")

    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"
    assert response.json()["balance"] == "12.34"


def test_patch_can_close_but_closed_is_final(api_client: APIClient) -> None:
    account = AccountFactory()

    close_response = api_client.patch(f"/api/accounts/{account.pk}/", {"status": "CLOSED"}, format="json")
    reopen_response = api_client.patch(f"/api/accounts/{account.pk}/", {"status": "OPEN"}, format="json")

    assert close_response.status_code == 200
    assert close_response.json()["status"] == "CLOSED"
    assert_documented_error(reopen_response)
    assert reopen_response.status_code == 400
    assert reopen_response.json()["error"] == {
        "type": "VALIDATION_ERROR",
        "message": "Closed accounts can't be changed.",
    }


def test_accounts_cannot_be_replaced_or_deleted(api_client: APIClient) -> None:
    account = AccountFactory()

    assert api_client.put(f"/api/accounts/{account.pk}/", {}, format="json").status_code == 405
    assert api_client.delete(f"/api/accounts/{account.pk}/").status_code == 405
