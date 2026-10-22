from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from core.exceptions import ApiError
from imports.models import ImportBatch, ImportStatus
from imports.services import import_transactions
from imports.tests.csv_files import csv_upload
from ledger.models import AccountStatus, Transaction
from ledger.tests.factories import AccountFactory, TransactionFactory

pytestmark = pytest.mark.django_db


def test_a_valid_file_posts_every_row() -> None:
    from decimal import Decimal

    from ledger.models import TransactionDirection

    first, second = AccountFactory(account_number="1001"), AccountFactory(account_number="1002")

    batch = import_transactions(
        csv_upload(
            "1001,CREDIT,100.00,2026-09-01,REF-1,Paycheck",
            "1001,DEBIT,25.50,2026-09-02,REF-2,",
            "1002,credit,0.01,2026-09-03,REF-1,Interest",  # direction is case-insensitive
        )
    )

    assert (batch.status, batch.row_count, batch.error_count) == (ImportStatus.COMPLETED, 3, 0)
    assert batch.completed_at is not None
    posted = Transaction.objects.order_by("reference_id", "account__account_number")
    assert [(t.account, t.reference_id, t.direction, t.amount) for t in posted] == [
        (first, "REF-1", TransactionDirection.CREDIT, Decimal("100.00")),
        (second, "REF-1", TransactionDirection.CREDIT, Decimal("0.01")),
        (first, "REF-2", TransactionDirection.DEBIT, Decimal("25.50")),
    ]
    assert all(transaction.import_batch == batch for transaction in posted)


def test_any_invalid_row_fails_the_whole_file_and_posts_nothing() -> None:

    AccountFactory(account_number="1001")
    AccountFactory(account_number="1002", status=AccountStatus.CLOSED)
    TransactionFactory(account__account_number="1003", reference_id="TAKEN")

    batch = import_transactions(
        csv_upload(
            "1001,CREDIT,100.00,2026-09-01,REF-1,Fine",  # line 2: valid
            "9999,CREDIT,1.00,2026-09-01,REF-2,",  # line 3: unknown account
            "1002,CREDIT,1.00,2026-09-01,REF-3,",  # line 4: closed account
            "1001,SIDEWAYS,1.00,2026-09-01,REF-4,",  # line 5: bad direction
            "1001,CREDIT,-5.00,2026-09-01,REF-5,",  # line 6: negative amount
            "1001,CREDIT,10.005,2026-09-01,REF-6,",  # line 7: too many decimal places
            "1001,CREDIT,1.00,2026-02-30,REF-7,",  # line 8: no such date
            "1001,CREDIT,1.00,2026-09-01,,",  # line 9: missing reference
            "1001,CREDIT,1.00,2026-09-01,REF-1,",  # line 10: duplicates line 2's reference
            "1003,CREDIT,1.00,2026-09-01,TAKEN,",  # line 11: reference already in the database
        )
    )

    assert (batch.status, batch.row_count, batch.error_count) == (ImportStatus.FAILED, 10, 9)
    assert Transaction.objects.count() == 1  # only the pre-existing one
    errors = {row_error.row_number: row_error.errors for row_error in batch.row_errors.all()}
    assert errors == {
        3: {"account_number": ["No account with this number."]},
        4: {"account_number": ["Closed accounts can't receive transactions."]},
        5: {"direction": ['"SIDEWAYS" is not a valid choice.']},
        6: {"amount": ["Ensure this value is greater than or equal to 0.01."]},
        7: {"amount": ["Ensure that there are no more than 2 decimal places."]},
        8: {"transaction_date": ["Date has wrong format. Use one of these formats instead: YYYY-MM-DD."]},
        9: {"reference_id": ["This field may not be blank."]},
        10: {"reference_id": ["Duplicates the reference on line 2."]},
        11: {"reference_id": ["This account already has a transaction with this reference."]},
    }
    first_error = batch.row_errors.get(row_number=3)
    assert first_error.raw_data == {
        "account_number": "9999",
        "direction": "CREDIT",
        "amount": "1.00",
        "transaction_date": "2026-09-01",
        "reference_id": "REF-2",
        "description": "",
    }


def test_an_import_takes_the_same_number_of_queries_however_many_rows() -> None:
    from django.test.utils import CaptureQueriesContext

    def queries_to_import(row_count: int, account_number: str) -> int:
        AccountFactory(account_number=account_number)
        rows = [f"{account_number},CREDIT,1.00,2026-09-01,REF-{number}," for number in range(row_count)]
        with CaptureQueriesContext(connection) as queries:
            batch = import_transactions(csv_upload(*rows))
        assert batch.status == ImportStatus.COMPLETED
        return len(queries)

    assert queries_to_import(50, "1001") == queries_to_import(500, "1002")
    assert Transaction.objects.count() == 550


def test_extra_columns_and_column_order_are_ignored_and_values_are_trimmed() -> None:
    AccountFactory(account_number="1001")

    batch = import_transactions(
        csv_upload(
            " REF-1 , 2026-09-01 ,25.00,CREDIT, 1001 ,whatever",
            header="reference_id,transaction_date,amount,DIRECTION,Account_Number,errors",
        )
    )

    assert batch.status == ImportStatus.COMPLETED
    assert Transaction.objects.get().reference_id == "REF-1"


def test_a_byte_order_mark_from_excel_is_ignored() -> None:
    AccountFactory(account_number="1001")
    content = "﻿account_number,direction,amount,transaction_date,reference_id\n1001,CREDIT,1.00,2026-09-01,R\n"

    batch = import_transactions(SimpleUploadedFile("excel.csv", content.encode()))

    assert batch.status == ImportStatus.COMPLETED


@pytest.mark.parametrize(
    ("upload", "message"),
    [
        (SimpleUploadedFile("empty.csv", b""), "The file is empty."),
        (csv_upload(), "The file has no rows, only a header."),
        (csv_upload(header="account_number,amount"), "The file is missing required columns:"),
        (SimpleUploadedFile("binary.csv", b"\xff\xfe\x00bad"), "The file isn't UTF-8 text."),
    ],
    ids=["empty", "header only", "missing columns", "not text"],
)
def test_problems_with_the_file_itself_are_rejected_without_a_batch(upload: SimpleUploadedFile, message: str) -> None:

    with pytest.raises(ApiError, match=message):
        import_transactions(upload)
    assert ImportBatch.objects.count() == 0


def test_files_over_the_size_limit_are_rejected() -> None:
    with mock.patch("imports.services.MAX_FILE_BYTES", 50), pytest.raises(ApiError, match="larger than"):
        import_transactions(csv_upload("1001,CREDIT,1.00,2026-09-01,REF-1,a long enough description to pass 50"))


def test_files_over_the_row_limit_are_rejected() -> None:
    from imports.services import MAX_ROWS

    with mock.patch("imports.services.MAX_ROWS", 2), pytest.raises(ApiError, match="more than 2 rows"):
        import_transactions(csv_upload(*["1001,CREDIT,1.00,2026-09-01,REF,"] * 3))
    assert MAX_ROWS == 10_000


def test_a_malformed_csv_is_rejected() -> None:
    oversized_field = "x" * 200_000  # bigger than the csv module allows in one field

    with pytest.raises(ApiError, match="isn't a valid CSV file"):
        import_transactions(csv_upload(f"1001,CREDIT,1.00,2026-09-01,REF-1,{oversized_field}"))


def test_an_unexpected_failure_leaves_the_batch_failed_rather_than_processing() -> None:

    AccountFactory(account_number="1001")

    with (
        mock.patch("imports.services.Transaction.objects.bulk_create", side_effect=RuntimeError("database fell over")),
        pytest.raises(RuntimeError),
    ):
        import_transactions(csv_upload("1001,CREDIT,1.00,2026-09-01,REF-1,"))

    batch = ImportBatch.objects.get()
    assert batch.status == ImportStatus.FAILED
    assert batch.completed_at is not None
    assert Transaction.objects.count() == 0


def test_string_representations() -> None:
    AccountFactory(account_number="1001")
    batch = import_transactions(csv_upload("9999,CREDIT,1.00,2026-09-01,REF-1,", name="june.csv"))

    assert str(batch) == "june.csv (FAILED)"
    assert str(batch.row_errors.get()) == "Line 2 of june.csv"
    assert str(batch.file) == "File of june.csv"


def test_the_uploaded_file_is_kept_exactly_as_uploaded() -> None:
    AccountFactory(account_number="1001")
    # Excel's byte order mark, odd header case, an extra column and Windows line endings: all kept as-is.
    content = (
        "\ufeffAccount_Number,direction,amount,transaction_date,reference_id,Notes\r\n"
        "1001,credit,1.00,2026-09-01,R1,x\r\n"
    )

    batch = import_transactions(SimpleUploadedFile("excel export.csv", content.encode()))

    assert bytes(batch.file.content) == content.encode()


def test_a_failed_import_keeps_its_file_too() -> None:
    batch = import_transactions(csv_upload("9999,CREDIT,1.00,2026-09-01,REF-1,"))

    assert batch.status == ImportStatus.FAILED
    assert bytes(batch.file.content).startswith(b"account_number,")


def test_a_rejected_file_is_not_kept() -> None:
    from imports.models import ImportFile

    with pytest.raises(ApiError):
        import_transactions(csv_upload())  # header only

    assert ImportFile.objects.count() == 0


def test_an_import_with_a_file_or_row_errors_cannot_be_deleted() -> None:
    from django.db.models import ProtectedError

    batch = import_transactions(csv_upload("9999,CREDIT,1.00,2026-09-01,REF-1,"))  # failed: has both

    with pytest.raises(ProtectedError):
        batch.delete()
    assert ImportBatch.objects.filter(pk=batch.pk).exists()


def test_blank_rows_from_spreadsheet_exports_are_skipped() -> None:
    AccountFactory(account_number="1001")
    upload = csv_upload("1001,CREDIT,1.00,2026-09-01,REF-1,", ",,,,,", "", " , , , , , ", ",,,,,")

    batch = import_transactions(upload)

    assert (batch.status, batch.row_count) == (ImportStatus.COMPLETED, 1)


def test_errors_report_the_real_line_in_the_file_even_after_blank_lines() -> None:
    AccountFactory(account_number="1001")
    upload = csv_upload(
        "1001,CREDIT,1.00,2026-09-01,REF-1,",  # line 2
        "",  # line 3: empty
        ",,,,,",  # line 4: commas only
        "9999,CREDIT,1.00,2026-09-01,REF-2,",  # line 5: unknown account
    )

    batch = import_transactions(upload)

    assert [row_error.row_number for row_error in batch.row_errors.all()] == [5]


def run_between_validation_and_writing(action):
    """Patch the import so `action` runs after validation finishes but before anything is written."""
    from imports import services

    real_validate_rows = services.validate_rows

    def validate_then_act(*args, **kwargs):
        result = real_validate_rows(*args, **kwargs)
        action()
        return result

    return mock.patch("imports.services.validate_rows", side_effect=validate_then_act)


def test_an_account_closed_after_validation_fails_the_import() -> None:
    from ledger.models import Account

    AccountFactory(account_number="1001")
    AccountFactory(account_number="1002")
    closing = lambda: Account.objects.filter(account_number="1002").update(status=AccountStatus.CLOSED)  # noqa: E731

    with run_between_validation_and_writing(closing):
        batch = import_transactions(
            csv_upload("1001,CREDIT,1.00,2026-09-01,REF-1,", "1002,CREDIT,1.00,2026-09-01,REF-2,")
        )

    assert (batch.status, batch.error_count) == (ImportStatus.FAILED, 1)
    assert batch.row_errors.get().errors == {"account_number": ["Closed accounts can't receive transactions."]}
    assert Transaction.objects.count() == 0


def test_a_reference_posted_after_validation_fails_the_import() -> None:
    account = AccountFactory(account_number="1001")
    posting = lambda: TransactionFactory(account=account, reference_id="REF-2")  # noqa: E731

    with run_between_validation_and_writing(posting):
        batch = import_transactions(
            csv_upload("1001,CREDIT,1.00,2026-09-01,REF-1,", "1001,CREDIT,1.00,2026-09-01,REF-2,")
        )

    assert (batch.status, batch.error_count) == (ImportStatus.FAILED, 1)
    assert batch.row_errors.get().row_number == 3
    assert Transaction.objects.count() == 1  # only the one posted in between


@pytest.mark.django_db(transaction=True)  # real commits, so "inside a transaction" means the import's own
def test_validation_runs_outside_any_transaction() -> None:

    AccountFactory(account_number="1001")
    seen_in_transaction = []

    with run_between_validation_and_writing(lambda: seen_in_transaction.append(connection.in_atomic_block)):
        batch = import_transactions(csv_upload("1001,CREDIT,1.00,2026-09-01,REF-1,"))

    assert seen_in_transaction == [False]
    assert batch.status == ImportStatus.COMPLETED
