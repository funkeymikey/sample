from django.db import migrations, models
from django_migration_linter import IgnoreMigration


class Migration(migrations.Migration):
    """Rename `external_id` to `account_number`, keeping the existing values, and update help texts.

    The migration linter flags column renames because, during a zero-downtime deploy, servers still running
    the old code would query the old column name. This app has no such deploys (migrations run before the
    app restarts), so the rename is safe here; elsewhere it would be done in steps (add, copy, switch, drop).
    """

    dependencies = [
        ("ledger", "0001_initial"),
    ]

    operations = [
        IgnoreMigration(),
        migrations.RenameField(
            model_name="account",
            old_name="external_id",
            new_name="account_number",
        ),
        migrations.AlterField(
            model_name="account",
            name="account_number",
            field=models.CharField(
                help_text="Unique, and can't change after create. Generated (10 random digits) when left blank.",
                max_length=32,
                unique=True,
            ),
        ),
        migrations.AlterModelOptions(
            name="account",
            options={"ordering": ["account_number"]},
        ),
        migrations.AlterField(
            model_name="transaction",
            name="reference_id",
            field=models.CharField(
                help_text="The source system's ID, unique per account, so reposting is idempotent. "
                'Generated ("TXN-" and 8 letters or digits) when left blank.',
                max_length=64,
            ),
        ),
    ]
