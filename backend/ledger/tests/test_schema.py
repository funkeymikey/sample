from typing import Any

import pytest


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    from drf_spectacular.generators import SchemaGenerator

    return SchemaGenerator().get_schema(request=None, public=True)


def query_parameters(schema: dict[str, Any], path: str, method: str) -> set[str]:
    return {
        parameter["name"] for parameter in schema["paths"][path][method]["parameters"] if parameter["in"] == "query"
    }


def test_only_duplicate_references_are_documented_as_409(schema: dict[str, Any]) -> None:
    assert "409" in schema["paths"]["/api/accounts/{id}/transactions/"]["post"]["responses"]
    assert "409" not in schema["paths"]["/api/accounts/{id}/"]["patch"]["responses"]


def test_transactions_are_only_listed_per_account(schema: dict[str, Any]) -> None:
    assert "/api/transactions/" not in schema["paths"]
    assert query_parameters(schema, "/api/accounts/{id}/transactions/", "get") == {
        "direction",
        "transaction_date_after",
        "transaction_date_before",
        "page",
    }


def test_request_bodies_only_contain_writable_fields(schema: dict[str, Any]) -> None:
    components = schema["components"]["schemas"]

    assert set(components["TransactionRequest"]["properties"]) == {
        "direction",
        "amount",
        "transaction_date",
        "reference_id",
        "description",
    }
    assert set(components["AccountRequest"]["properties"]) == {"account_number", "holder_name", "email"}
    assert set(components["PatchedAccountUpdateRequest"]["properties"]) == {"holder_name", "email", "status"}


def test_transaction_endpoints_are_grouped_together(schema: dict[str, Any]) -> None:
    transaction_operations = [
        schema["paths"]["/api/accounts/{id}/transactions/"]["get"],
        schema["paths"]["/api/accounts/{id}/transactions/"]["post"],
        schema["paths"]["/api/transactions/{id}/"]["get"],
    ]

    assert [operation["tags"] for operation in transaction_operations] == [["Transactions"]] * 3
