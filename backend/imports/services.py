"""Importing transactions from a CSV file: all rows are posted, or none are."""

import csv
import io
from dataclasses import dataclass

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction as db_transaction
from django.utils import timezone

from core.exceptions import ApiError
from imports.models import ImportBatch, ImportStatus
from ledger.models import Account, Transaction

REQUIRED_COLUMNS = ["account_number", "direction", "amount", "transaction_date", "reference_id"]
COLUMNS = [*REQUIRED_COLUMNS, "description"]
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000


@dataclass
class Row:
    """One data row: its line in the file (the header is line 1) and its values for the known columns."""

    line: int
    values: dict[str, str]


CLOSED_ACCOUNT_MESSAGE = "Closed accounts can't receive transactions."
REFERENCE_TAKEN_MESSAGE = "This account already has a transaction with this reference."


@dataclass
class ValidRow:
    """A row that passed validation, and its validated values (ready to create a transaction from)."""

    row: Row
    data: dict


@dataclass
class RowProblem:
    """An invalid row and the messages for each of its invalid columns."""

    row: Row
    errors: dict[str, list[str]]


def import_transactions(upload: UploadedFile) -> ImportBatch:
    """Import a CSV file of transactions and return its batch.

    Problems with the file itself (too big, not text, no rows, missing columns) raise `ApiError` and create no
    batch. Otherwise the file is kept exactly as uploaded, for auditing, and every row is validated: if any row
    is invalid, the batch is FAILED with its row errors and nothing is posted; if all are valid, they're all
    posted together and the batch is COMPLETED.

    Validation only reads, so it runs without a transaction or locks, however long the file. The accounts are
    locked only for the short write at the end (see `post_rows`), which re-checks anything that could have
    changed since validation.
    """
    from imports.models import ImportFile

    content = read_upload(upload)
    rows = parse_rows(content)
    with db_transaction.atomic():
        batch = ImportBatch.objects.create(original_filename=upload.name or "upload.csv", row_count=len(rows))
        ImportFile.objects.create(batch=batch, content=content)
    try:
        accounts = {
            account.account_number: account
            for account in Account.objects.filter(account_number__in={row.values["account_number"] for row in rows})
        }
        valid_rows, problems = validate_rows(rows, accounts)
        if not problems:
            problems = post_rows(batch, valid_rows)
        if problems:
            fail_with_problems(batch, problems)
    except Exception:
        # Leave a record of the attempt rather than a batch stuck in PROCESSING.
        ImportBatch.objects.filter(pk=batch.pk).update(status=ImportStatus.FAILED, completed_at=timezone.now())
        raise
    return batch


def post_rows(batch: ImportBatch, valid_rows: list["ValidRow"]) -> list["RowProblem"]:
    """Post validated rows in one short transaction and mark the batch COMPLETED; or, if anything changed since
    validation, post nothing and return the problems.

    Validation ran without locks, so two things could have changed: an account was closed, or a reference was
    posted. Inside the transaction, the accounts are locked (in a fixed order, so concurrent imports can't
    deadlock) and both are re-checked. Posting and closing take the same account locks, so once these checks
    pass, nothing can change them before the insert commits.
    """
    from ledger.models import AccountStatus

    account_ids = {valid.data["account"].pk for valid in valid_rows}
    with db_transaction.atomic():
        # Postgres can't combine FOR UPDATE with COUNT, so lock the still-open accounts' rows and compare in Python.
        open_account_ids = set(
            Account.objects.select_for_update()
            .filter(pk__in=account_ids, status=AccountStatus.OPEN)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        taken_references = set(
            Transaction.objects.filter(
                account_id__in=account_ids, reference_id__in={valid.data["reference_id"] for valid in valid_rows}
            ).values_list("account_id", "reference_id")
        )
        problems = []
        for valid in valid_rows:
            account_id = valid.data["account"].pk
            if account_id not in open_account_ids:
                problems.append(RowProblem(valid.row, {"account_number": [CLOSED_ACCOUNT_MESSAGE]}))
            elif (account_id, valid.data["reference_id"]) in taken_references:
                problems.append(RowProblem(valid.row, {"reference_id": [REFERENCE_TAKEN_MESSAGE]}))
        if problems:
            return problems

        Transaction.objects.bulk_create(Transaction(import_batch=batch, **valid.data) for valid in valid_rows)
        batch.status = ImportStatus.COMPLETED
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "completed_at", "updated_at"])
    return []


def fail_with_problems(batch: ImportBatch, problems: list["RowProblem"]) -> None:
    """Save the row errors and mark the batch FAILED. Nothing was posted."""
    from imports.models import ImportRowError

    with db_transaction.atomic():
        ImportRowError.objects.bulk_create(
            ImportRowError(batch=batch, row_number=problem.row.line, raw_data=problem.row.values, errors=problem.errors)
            for problem in problems
        )
        batch.status = ImportStatus.FAILED
        batch.error_count = len(problems)
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "error_count", "completed_at", "updated_at"])


def read_upload(upload: UploadedFile) -> bytes:
    """The uploaded file's bytes. Raises `ApiError` if it's over `MAX_FILE_BYTES`, without reading it."""
    if upload.size and upload.size > MAX_FILE_BYTES:
        raise ApiError(f"The file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    return upload.read()


def parse_rows(content: bytes) -> list[Row]:
    """Parse a CSV file into rows of the known columns (header names and values trimmed, header case ignored).

    Raises `ApiError` when the file can't be imported at all: not UTF-8 text, malformed, empty, missing a
    required column, or more than `MAX_ROWS` rows. Unknown columns are ignored, so a downloaded error file
    (with its extra `errors` column) can be fixed and uploaded again. Blank rows, including the comma-only rows
    spreadsheets export, are skipped; each row keeps its real line number for error messages.
    """
    try:
        text = content.decode("utf-8-sig")  # utf-8-sig drops the byte order mark Excel adds
    except UnicodeDecodeError as error:
        raise ApiError("The file isn't UTF-8 text.", detail="Save it as CSV (UTF-8) and upload it again.") from error

    reader = csv.DictReader(io.StringIO(text))
    try:
        if not reader.fieldnames:
            raise ApiError("The file is empty.")
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise ApiError(
                f"The file is missing required columns: {', '.join(missing)}.",
                detail=f"Expected columns: {', '.join(COLUMNS)} (description is optional).",
            )
        rows = []
        for row in reader:
            if len(rows) == MAX_ROWS:
                raise ApiError(f"The file has more than {MAX_ROWS:,} rows. Split it and upload each part.")
            values = {column: (row.get(column) or "").strip() for column in COLUMNS}
            if any(values.values()):
                rows.append(Row(line=reader.line_num, values=values))
    except csv.Error as error:
        raise ApiError("The file isn't a valid CSV file.", detail=str(error)) from error
    if not rows:
        raise ApiError("The file has no rows, only a header.")
    return rows


def validate_rows(rows: list[Row], accounts: dict[str, Account]) -> tuple[list[ValidRow], list[RowProblem]]:
    """Validate every row and collect all the problems, rather than stopping at the first. Only reads.

    Returns the valid rows (with their validated values) and the problems with the invalid ones. Rows go
    through the same serializer rules as posting one transaction; references are also checked against the
    database and against earlier rows in the file. The database is queried once for existing references,
    however many rows there are.
    """
    from imports.serializers import ImportRowSerializer

    existing_references = set(
        Transaction.objects.filter(
            account__in=accounts.values(), reference_id__in={row.values["reference_id"] for row in rows}
        ).values_list("account_id", "reference_id")
    )
    first_line_with_reference: dict[tuple, int] = {}
    valid_rows = []
    problems = []
    for row in rows:
        serializer = ImportRowSerializer(
            data={**row.values, "direction": row.values["direction"].upper()}, context={"accounts": accounts}
        )
        if not serializer.is_valid():
            errors = {field: [str(message) for message in messages] for field, messages in serializer.errors.items()}
            problems.append(RowProblem(row, errors))
            continue
        data = serializer.validated_data
        reference = (data["account"].pk, data["reference_id"])
        if reference in existing_references:
            problems.append(RowProblem(row, {"reference_id": [REFERENCE_TAKEN_MESSAGE]}))
        elif reference in first_line_with_reference:
            message = f"Duplicates the reference on line {first_line_with_reference[reference]}."
            problems.append(RowProblem(row, {"reference_id": [message]}))
        else:
            first_line_with_reference[reference] = row.line
            valid_rows.append(ValidRow(row, data))
    return valid_rows, problems


def errors_csv(batch: ImportBatch) -> str:
    """The failed rows as a CSV to fix and upload again: the original columns plus an `errors` column.

    Uploads ignore unknown columns, so the `errors` column can stay in place.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[*COLUMNS, "errors"], lineterminator="\n")
    writer.writeheader()
    for row_error in batch.row_errors.all():
        messages = " ".join(
            f"{field}: {' '.join(field_messages)}" for field, field_messages in row_error.errors.items()
        )
        writer.writerow({**row_error.raw_data, "errors": messages})
    return output.getvalue()
