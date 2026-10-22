from rest_framework import serializers

from imports.models import ImportBatch, ImportRowError
from ledger.models import Account
from ledger.serializers import TransactionSerializer


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = ["id", "original_filename", "status", "row_count", "error_count", "created_at", "completed_at"]
        read_only_fields = fields


class ImportRowErrorSerializer(serializers.ModelSerializer):
    raw_data = serializers.DictField(child=serializers.CharField(allow_blank=True))
    errors = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))

    class Meta:
        model = ImportRowError
        fields = ["row_number", "raw_data", "errors"]
        read_only_fields = fields


class ImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="A CSV file of transactions (UTF-8, at most 5 MB and 10,000 rows).")


class ImportRowSerializer(TransactionSerializer):
    """One CSV row: the same rules as posting a single transaction, plus the account, looked up by number.

    Needs `context["accounts"]`: the file's accounts by account number, fetched up front in one query.
    Unlike the form, a reference is required, so importing the same file twice can't post anything twice.
    """

    account_number = serializers.CharField(write_only=True)

    class Meta(TransactionSerializer.Meta):
        fields = [*TransactionSerializer.Meta.fields, "account_number"]
        extra_kwargs = {"reference_id": {"required": True, "allow_blank": False}}

    def validate_account_number(self, account_number: str) -> Account:
        from imports.services import CLOSED_ACCOUNT_MESSAGE
        from ledger.models import AccountStatus

        account = self.context["accounts"].get(account_number)
        if account is None:
            raise serializers.ValidationError("No account with this number.")
        if account.status == AccountStatus.CLOSED:
            raise serializers.ValidationError(CLOSED_ACCOUNT_MESSAGE)
        return account

    def validate(self, attrs: dict) -> dict:
        attrs["account"] = attrs.pop("account_number")
        return attrs


class SampleFileQuerySerializer(serializers.Serializer):
    rows = serializers.IntegerField(min_value=1, max_value=1000, default=25)
    invalid = serializers.BooleanField(default=False, help_text="Include a few deliberately invalid rows.")
