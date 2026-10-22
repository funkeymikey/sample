import pytest
from rest_framework.test import APIClient

from core.tests.assertions import assert_documented_error
from imports.tests.factories import ImportBatchFactory
from ledger.tests.factories import AccountFactory

pytestmark = pytest.mark.django_db

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def upload(api_client: APIClient, *lines: str):
    from imports.tests.csv_files import csv_upload

    return api_client.post("/api/imports/", {"file": csv_upload(*lines)}, format="multipart")


def test_uploading_a_valid_file(api_client: APIClient) -> None:
    AccountFactory(account_number="1001")

    response = upload(api_client, "1001,CREDIT,10.00,2026-09-01,REF-1,")

    assert response.status_code == 201
    body = response.json()
    assert (body["status"], body["row_count"], body["error_count"]) == ("COMPLETED", 1, 0)
    assert body["original_filename"] == "transactions.csv"
    assert set(body) == {
        "id",
        "original_filename",
        "status",
        "row_count",
        "error_count",
        "created_at",
        "completed_at",
    }


def test_uploading_a_file_with_bad_rows_creates_a_failed_batch(api_client: APIClient) -> None:
    response = upload(api_client, "9999,CREDIT,10.00,2026-09-01,REF-1,")

    assert response.status_code == 201  # the batch was created; its status says it failed
    assert (response.json()["status"], response.json()["error_count"]) == ("FAILED", 1)


def test_problems_with_the_file_itself_are_a_400(api_client: APIClient) -> None:
    missing_file = api_client.post("/api/imports/", {}, format="multipart")
    header_only = upload(api_client)

    assert_documented_error(missing_file)
    assert missing_file.status_code == 400
    assert "file" in missing_file.json()["error"]["fields"]
    assert_documented_error(header_only)
    assert header_only.json()["error"]["message"] == "The file has no rows, only a header."


def test_listing_and_viewing_imports(api_client: APIClient) -> None:

    older = ImportBatchFactory(original_filename="older.csv")
    newer = ImportBatchFactory(original_filename="newer.csv")

    list_response = api_client.get("/api/imports/")
    detail_response = api_client.get(f"/api/imports/{older.pk}/")

    assert [batch["id"] for batch in list_response.json()["results"]] == [str(newer.pk), str(older.pk)]
    assert detail_response.json()["original_filename"] == "older.csv"
    assert api_client.get(f"/api/imports/{UNKNOWN_ID}/").status_code == 404


def test_row_errors_as_json_and_as_a_csv_to_fix_and_reupload(api_client: APIClient) -> None:
    import csv
    import io

    AccountFactory(account_number="1001")
    batch_id = upload(
        api_client,
        "1001,CREDIT,10.00,2026-09-01,REF-1,fine",
        "9999,CREDIT,10.00,2026-09-01,REF-2,unknown account",
        "1001,CREDIT,-1.00,2026-02-30,REF-3,two problems",
    ).json()["id"]

    errors = api_client.get(f"/api/imports/{batch_id}/errors/").json()
    csv_response = api_client.get(f"/api/imports/{batch_id}/errors.csv")

    assert [row_error["row_number"] for row_error in errors["results"]] == [3, 4]
    assert errors["results"][0]["errors"] == {"account_number": ["No account with this number."]}
    assert csv_response.status_code == 200
    assert csv_response["Content-Type"] == "text/csv"
    assert "attachment" in csv_response["Content-Disposition"]
    rows = list(csv.DictReader(io.StringIO(csv_response.content.decode())))
    assert [row["reference_id"] for row in rows] == ["REF-2", "REF-3"]
    assert rows[1]["errors"] == (
        "amount: Ensure this value is greater than or equal to 0.01. "
        "transaction_date: Date has wrong format. Use one of these formats instead: YYYY-MM-DD."
    )


def test_errors_for_an_unknown_import_are_a_404(api_client: APIClient) -> None:
    assert api_client.get(f"/api/imports/{UNKNOWN_ID}/errors/").status_code == 404
    assert api_client.get(f"/api/imports/{UNKNOWN_ID}/errors.csv").status_code == 404


def test_downloading_a_sample_file(api_client: APIClient) -> None:
    AccountFactory()

    valid = api_client.get("/api/imports/sample.csv", {"rows": 3})
    invalid = api_client.get("/api/imports/sample.csv", {"invalid": "true"})

    assert valid.status_code == invalid.status_code == 200
    assert valid["Content-Type"] == "text/csv"
    assert len(valid.content.decode().strip().splitlines()) == 4  # header + 3 rows
    assert "sample-with-errors.csv" in invalid["Content-Disposition"]


@pytest.mark.parametrize("rows", ["0", "1001", "many"])
def test_sample_size_is_validated(api_client: APIClient, rows: str) -> None:
    AccountFactory()

    response = api_client.get("/api/imports/sample.csv", {"rows": rows})

    assert_documented_error(response)
    assert response.status_code == 400
    assert "rows" in response.json()["error"]["fields"]


def test_a_sample_without_open_accounts_is_a_clear_400(api_client: APIClient) -> None:
    response = api_client.get("/api/imports/sample.csv")

    assert_documented_error(response)
    assert response.status_code == 400
    assert "no open accounts" in response.json()["error"]["message"]


def test_completed_import_links_its_transactions(api_client: APIClient) -> None:
    account = AccountFactory(account_number="1001")
    batch_id = upload(api_client, "1001,CREDIT,10.00,2026-09-01,REF-1,").json()["id"]

    transaction = api_client.get(f"/api/accounts/{account.pk}/transactions/").json()["results"][0]

    assert transaction["import_batch"] == batch_id


def test_downloading_the_original_file(api_client: APIClient) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    AccountFactory(account_number="1001")
    content = b"account_number,direction,amount,transaction_date,reference_id\r\n1001,CREDIT,1.00,2026-09-01,R1\r\n"
    batch_id = api_client.post(
        "/api/imports/", {"file": SimpleUploadedFile("June 2026.csv", content)}, format="multipart"
    ).json()["id"]

    response = api_client.get(f"/api/imports/{batch_id}/file/")

    assert response.status_code == 200
    assert response.content == content
    assert response["Content-Type"] == "text/csv"
    assert response["Content-Disposition"] == 'attachment; filename="June 2026.csv"'


def test_original_file_of_an_import_without_one_is_a_404(api_client: APIClient) -> None:
    batch = ImportBatchFactory()  # e.g. uploaded before files were kept

    missing_file = api_client.get(f"/api/imports/{batch.pk}/file/")
    missing_import = api_client.get(f"/api/imports/{UNKNOWN_ID}/file/")

    assert_documented_error(missing_file)
    assert missing_file.status_code == 404
    assert missing_file.json()["error"]["message"] == "The original file wasn't kept for this import."
    assert missing_import.status_code == 404


def test_listing_imports_never_loads_their_files(api_client: APIClient, django_assert_num_queries) -> None:
    AccountFactory(account_number="1001")
    for number in range(3):
        upload(api_client, f"1001,CREDIT,1.00,2026-09-01,REF-{number},")

    with django_assert_num_queries(2):  # count + page; the files live in another table
        response = api_client.get("/api/imports/")

    assert response.json()["count"] == 3


def test_an_upload_that_isnt_multipart_is_a_415(api_client: APIClient) -> None:
    response = api_client.post("/api/imports/", {"file": "account_number,direction"}, format="json")

    assert_documented_error(response)
    assert response.status_code == 415
    assert response.json()["error"]["type"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.parametrize("rows", [1, 1000])
def test_sample_size_limits_are_inclusive(api_client: APIClient, rows: int) -> None:
    AccountFactory()

    response = api_client.get("/api/imports/sample.csv", {"rows": rows})

    assert response.status_code == 200
    assert len(response.content.decode().strip().splitlines()) == rows + 1  # plus the header


def test_row_errors_are_paginated(api_client: APIClient) -> None:
    batch_id = upload(api_client, *[f"9999,CREDIT,1.00,2026-09-01,REF-{number}," for number in range(30)]).json()["id"]

    first_page = api_client.get(f"/api/imports/{batch_id}/errors/").json()
    second_page = api_client.get(f"/api/imports/{batch_id}/errors/", {"page": 2}).json()

    assert first_page["count"] == 30
    assert len(first_page["results"]) == 25
    assert [row_error["row_number"] for row_error in second_page["results"]] == [27, 28, 29, 30, 31]


def test_an_import_shows_up_in_the_account_balance(api_client: APIClient) -> None:
    account = AccountFactory(account_number="1001")

    upload(
        api_client,
        "1001,CREDIT,250.00,2026-09-01,REF-1,deposit",
        "1001,DEBIT,75.25,2026-09-02,REF-2,withdrawal",
        "1001,CREDIT,0.50,2026-09-03,REF-3,interest",
    )

    assert api_client.get(f"/api/accounts/{account.pk}/").json()["balance"] == "175.25"
