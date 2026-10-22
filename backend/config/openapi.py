"""The API documentation: OpenAPI schema at /api/schema/, rendered by Redoc at /api/docs/.

The endpoint reference is generated from the views and serializers; this module holds only the
drf-spectacular settings around it.
"""

# Pinned instead of the CDN's floating `@latest`: drf-spectacular's page uses the <redoc spec-url>
# tag, which Redoc 3 no longer renders.
REDOC_DIST_URL = "https://cdn.jsdelivr.net/npm/redoc@2.5.4"

SPECTACULAR_SETTINGS = {
    "TITLE": "Ledger API",
    "DESCRIPTION": "Accounts, transactions and bulk CSV imports.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Separate request and response types (e.g. `AccountRequest` vs `Account`), so request types only
    # contain the fields a client may send.
    "COMPONENT_SPLIT_REQUEST": True,
    "REDOC_DIST": REDOC_DIST_URL,
    "REDOC_UI_SETTINGS": {
        "expandResponses": "200",
        "jsonSampleExpandLevel": 2,
        # Nested $ref schemas (e.g. the error envelope's `error` object) render collapsed by default;
        # expand one level so their fields are visible without a click.
        "schemaExpansionLevel": 1,
    },
    # Explicit names, so enums from different "status" fields don't collide.
    "ENUM_NAME_OVERRIDES": {
        "HealthStatusEnum": "health.services.HealthStatus",
        "ErrorTypeEnum": "core.exceptions.ErrorType",
        "AccountStatusEnum": "ledger.models.AccountStatus",
        "TransactionDirectionEnum": "ledger.models.TransactionDirection",
        "ImportStatusEnum": "imports.models.ImportStatus",
    },
    # Enums list exactly the values callers may send; a field's nullability is expressed by the field.
    "ENUM_ADD_EXPLICIT_BLANK_NULL_CHOICE": False,
    # Redoc already lists the allowed values, so the generated "* `A` - A" bullets only repeat them.
    "ENUM_GENERATE_CHOICE_DESCRIPTION": False,
}
