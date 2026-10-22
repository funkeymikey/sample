"""Sample CSV files for demos: one that imports cleanly, or one with a few deliberate errors."""

import datetime

from ledger.models import TransactionDirection

DESCRIPTIONS = {
    TransactionDirection.CREDIT: ["Payroll deposit", "Transfer in", "Refund", "Financial aid disbursement", "Interest"],
    TransactionDirection.DEBIT: ["Tuition", "Card payment", "Rent", "Transfer out", "Late fee"],
}
AMOUNT_RANGE_IN_CENTS = {
    TransactionDirection.CREDIT: (1_000, 200_000),  # $10.00 to $2,000.00
    TransactionDirection.DEBIT: (500, 50_000),  # $5.00 to $500.00
}


def sample_csv(*, rows: int, invalid: bool = False) -> str:
    """A CSV of `rows` transactions for real open accounts, with fresh references, that imports cleanly.

    With `invalid`, four rows are spoiled on purpose (an unknown account, a negative amount, a date that doesn't
    exist and a reference used twice), to show what a failed import looks like.
    Raises `ApiError` if there are no open accounts to use.
    """
    import csv
    import io
    import random
    from decimal import Decimal

    from core.exceptions import ApiError
    from imports.services import COLUMNS
    from ledger.models import Account, AccountStatus
    from ledger.services import generate_reference_id

    account_numbers = list(
        Account.objects.filter(status=AccountStatus.OPEN).values_list("account_number", flat=True)[:200]
    )
    if not account_numbers:
        raise ApiError(
            "There are no open accounts to put in a sample file.",
            detail="Open an account first, then download the sample again.",
        )

    today = datetime.date.today()
    sample_rows = []
    for index in range(rows):
        direction = TransactionDirection.DEBIT if index % 3 == 2 else TransactionDirection.CREDIT  # 2 in 3 credit
        sample_rows.append(
            {
                "account_number": random.choice(account_numbers),
                "direction": direction.value,
                "amount": str(Decimal(random.randint(*AMOUNT_RANGE_IN_CENTS[direction])) / 100),
                "transaction_date": (today - datetime.timedelta(days=random.randint(0, 60))).isoformat(),
                "reference_id": generate_reference_id(),
                "description": random.choice(DESCRIPTIONS[direction]),
            }
        )
    if invalid:
        spoil(sample_rows)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(sample_rows)
    return output.getvalue()


def spoil(rows: list[dict[str, str]]) -> None:
    """Break four rows, spread through the file, in four different ways."""
    step = max(len(rows) // 5, 1)
    positions = [min(step * number, len(rows) - 1) for number in range(1, 5)]
    rows[positions[0]]["account_number"] = "NO-SUCH-ACCOUNT"
    rows[positions[1]]["amount"] = "-25.00"
    rows[positions[2]]["transaction_date"] = f"{datetime.date.today().year}-02-30"
    rows[positions[3]].update(account_number=rows[0]["account_number"], reference_id=rows[0]["reference_id"])
