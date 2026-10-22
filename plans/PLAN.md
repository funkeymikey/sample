# Code Sample: Plan

A small, well-built CRUD app with bulk file upload. The aim is clean structure, real-world organization, sensible validation, and good tests, not a long feature list. It also will make keep the stack small - ie, everything's synchronous, there's no celery running async file imports.

**Stack:** Django + Django REST Framework (API), Vue 3 + Vite (frontend), PostgreSQL (database), Docker Compose (local dev).

**Audience:** reviewers in higher-ed SIS / PeopleSoft roles first, banking / fintech second.

---

## 1. Domain: Accounts and Transactions

The app is a small ledger.

- **Account**: works like a bank account: it holds money, and goes negative when it owes. In banking terms, a customer's deposit account.
- **Transaction**: money in or out of an account. A **credit** (deposit, payment, financial aid) increases the balance; a **debit** (withdrawal, charge, fee) decreases it.

The UI uses these neutral names throughout.

### Base models

Every model inherits from one abstract base class in `core/models.py`: **`BaseModel`**, which adds a UUID primary key plus `created_at` and `updated_at`.

Deleting is not supported. The ledger is immutable and accounts are closed rather than deleted.

### Data model

```
Account (BaseModel)
  account_number    str                # unique, read-only after create; generated (10 random digits) when left blank
  holder_name       str
  email             str, optional
  status            enum: OPEN | CLOSED
Transaction (BaseModel)
  account           FK -> Account (PROTECT)
  direction         enum: DEBIT | CREDIT
  amount            Decimal(12,2), > 0 # sign comes from direction
  transaction_date  date
  reference_id      str                # source-system ID, used for idempotency; generated ("TXN-" + 8 chars) when left blank
  description       str, optional
  import_batch      FK -> ImportBatch, nullable   # added in Milestone 5, with ImportBatch
  UNIQUE (account, reference_id)

ImportBatch (BaseModel)
  original_filename str
  status            enum: PROCESSING | COMPLETED | FAILED
  row_count         int
  error_count       int
  completed_at      datetime, nullable

ImportFile (BaseModel)                 # the uploaded file, byte for byte, for auditing; its own table so
  batch             1:1 -> ImportBatch # listing imports never loads file contents
  content           binary             # at most 5 MB

ImportRowError (BaseModel)
  batch             FK -> ImportBatch
  row_number        int
  raw_data          JSON
  errors            JSON               # field -> [messages]
```

The account **balance** is computed (credits minus debits: positive is money held, negative means the account is overdrawn or owes), not stored. `Transaction.account_id` is indexed: Django indexes FK columns by default. Postgres doesn't, so check that the index appears in the migration.

### Delete rules

- **Account:** the API offers no delete. An account can be edited (except `account_number`), and it's retired by setting its status to CLOSED. An account can be closed with a nonzero balance. CLOSED is final: the API rejects setting the status back to OPEN, and a closed account can't be edited or receive new transactions.
- **Transaction:** the API offers no delete or edit. You correct a transaction by posting one with the same amount in the opposite direction, as real ledgers do.
- **ImportBatch:** an import is never deleted. Its transactions are the audit trail.

---

## 2. Features

### CRUD

- Accounts: list (search, filter by status, paginate), create, view, edit, close.
- Transactions: listed and posted per account (drill down from the account; filter by direction and date range), view one.
- Account detail page: header, computed balance, transaction history.

### Bulk upload (all-or-nothing)

- Upload a CSV of transactions with the columns `account_number, direction, amount, transaction_date, reference_id, description`. Unlike the form, imports require `reference_id`: re-importing the same file must not post anything twice.
- Problems with the file itself (over 5 MB or 10,000 rows, not UTF-8, malformed, empty, missing a required column) are a 400 with a clear message, and no batch is created. Unknown columns are ignored; header names are case-insensitive, CSVs saved from Excel read correctly, and blank rows (including the comma-only rows spreadsheets export) are skipped. Errors report each row's real line in the file.
- The pipeline has four steps:
  1. **Parse** the file. It fails fast if the file is malformed or headers are missing.
  2. **Validate every row** and collect all errors, rather than stopping at the first one. Validation reuses the same DRF serializer as single-record create, so there's one source of truth.
     - Checks: the account exists and is not CLOSED, the direction is DEBIT or CREDIT, the amount is a positive decimal with at most 2 decimal places (anything more is rejected, never rounded), the date is valid, and the reference_id is not a duplicate within the file or in the DB.
     - Accounts and existing reference_ids are each prefetched in a single query, so validation doesn't query the DB once per row.
  3. **If any row fails**, the batch is marked FAILED, the row errors are saved, and **nothing is inserted**.
  4. **If every row passes**, a short `transaction.atomic()` block re-checks and inserts. Validation runs before it, with no transaction or locks, so slow validation never blocks other requests. Inside the block, the file's still-open accounts are locked (`SELECT … FOR UPDATE`, in a fixed order) and their references are checked again. If an account closed or a reference was taken since validation, those rows fail the import as usual. Otherwise all rows are inserted with `bulk_create` and the batch is marked COMPLETED. Concurrent imports and posts to the same accounts take turns only during this short block. Measured on 10,000 rows: about 1.5 seconds of validation without locks, then locks held for about 0.45 seconds.
- Results page: a download of the original file exactly as uploaded (`GET /api/imports/{id}/file/`), summary counts, a table of row errors (by line in the file; the header is line 1), and a download of the error rows as CSV, with the original columns plus an `errors` column, so the user can fix them in place and re-upload the same file.

### Download sample file

- An **"Download sample file"** button on the upload page.
- The file is generated on the fly by `GET /api/imports/sample.csv?rows=25` (1 to 1,000 rows). It uses real account numbers from the DB, a mix of debits and credits, plus fresh unique `reference_id`s. That way the file passes validation and uploads successfully as-is, which makes the demo work end to end.
- `?invalid=true` produces a file with a few deliberate errors (an unknown account, a negative amount, a bad date, a duplicate reference), to demo the failure path.
- If there are no open accounts, the endpoint returns a clear 400 telling the user to open one first.

### Sync vs. async (Celery)

Imports are processed **synchronously** in the request, with no Celery.

- With all-or-nothing validation, prefetched lookups, and a single `bulk_create`, files of up to ~10k rows finish in well under a few seconds.
- Celery would add Redis and a worker container. That makes local setup and later hosting harder, and it shows less than it costs.
- The `ImportBatch` status model is built so a worker could take over later without changing the API: the frontend already reads a batch's status from its own endpoint.

---

## 3. API (DRF)

```
GET                /api/health/               (200 ok; standard 500 error if the database is down)
GET                /api/schema/               (OpenAPI schema; Redoc at /api/docs/)
GET/POST           /api/accounts/
GET/PATCH          /api/accounts/{id}/
GET/POST           /api/accounts/{id}/transactions/   (list or post; the account comes from the URL)
GET                /api/transactions/{id}/
GET/POST           /api/imports/              (list, or upload a CSV as multipart `file`)
GET                /api/imports/{id}/
GET                /api/imports/{id}/errors/  (paginated row errors)
GET                /api/imports/{id}/errors.csv
GET                /api/imports/{id}/file/    (the original upload, byte for byte)
GET                /api/imports/sample.csv    (?rows=N&invalid=true)
```

- OpenAPI schema with drf-spectacular, Redoc at `/api/docs/`.
- Pagination and filtering with django-filter.
- **Errors:** every error returns `{"error": {"type", "message", "detail"?, "fields"?}}`. Business logic raises `core.exceptions.ApiError` (a 400) or `ConflictError` (a 409); unknown ids are DRF's own 404s. The exception handler reshapes DRF's own errors, and turns anything unexpected into a generic, logged 500. `core.schema.ApiAutoSchema` documents the defaults on every endpoint: 500 everywhere, 400 on writes, and 404 on single-object paths. Views only declare unusual codes, such as a 409.
- No authentication for now.

---

## 4. Frontend (Vue 3)

- Vite, Vue 3 Composition API with `<script setup>`, TypeScript, Vue Router. In this simple app, no need for central store with shared state.
- UI kit: PrimeVue 4 (Aura theme), because its DataTable suits this kind of app.
- Views: Accounts list, Account detail (with the account's transactions), Account form (open and edit), Transaction form, Transaction detail, Import upload (with the "Download sample file" button), Import results, Import history.
- Money is never a JavaScript number: amounts stay decimal strings from the API to the screen (`Intl.NumberFormat` formats the string exactly), and typed amounts become 2-decimal strings before they're sent.
- A typed API client: `openapi-typescript` generates TypeScript types from the drf-spectacular schema (`make api-types`), and a thin fetch wrapper uses them.

---

## 5. Repo layout

```
/
├── backend/
│   ├── config/            # settings, urls, wsgi
│   ├── core/              # shared: BaseModel, error handling, API schema defaults
│   ├── health/            # health check endpoint
│   ├── ledger/            # accounts, transactions
│   ├── imports/           # upload pipeline, sample file generator
│   ├── .python-version    # 3.13, read by uv
│   ├── pyproject.toml     # deps (uv), ruff, pytest, coverage config
│   ├── uv.lock
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json       # Node version pinned with Volta
│   └── Dockerfile
├── plans/PLAN.md
├── .env.example           # DATABASE_URL etc.; copied to .env by make init
├── .gitignore
├── .pre-commit-config.yaml
├── docker-compose.yml     # postgres, backend, frontend
├── Makefile               # one entry point for both halves
├── CLAUDE.md
└── README.md
```

Note: each django app keeps its tests in `<app>/tests/`

---

## 6. Local dev and tooling

**Decisions:** uv for Python (it also installs Python 3.13, replacing pyenv), Volta for Node (pinned to Node 24, which the current Vue tooling requires), pytest-django as the test runner. In day-to-day development, Postgres runs in Docker and Django and Vite run locally for hot reload and fast tests. `make up` runs everything in Docker for a one-command demo.

### Makefile (repo root)

A single root Makefile drives both halves. Backend commands run via `uv run --directory backend ...` and frontend commands via `cd frontend && npm ...` (so Volta picks up the pinned Node), so nobody has to activate a venv.

Local ports avoid clashing with other projects: Postgres on 5433, the API on 8001, Vite on 5173.

| Target                                         | What it does                                                                                             |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `init`                                         | First-time setup: install and initialize dependencies, copy `.env.example` to `.env`, then run `install` |
| `install`                                      | `uv sync`, `npm ci`, `pre-commit install`. Rerun after pulling                                           |
| `upgrade`                                      | `uv lock --upgrade`, `npm update`, `pre-commit autoupdate`                                               |
| `db` / `up` / `down`                           | Start Postgres only / start the full stack / stop everything                                             |
| `backend` / `frontend`                         | Run the Django dev server / the Vite dev server locally                                                  |
| `migrate`, `makemigrations`, `lint-migrations` | Run locally against Docker Postgres; `lint-migrations` uses django-migration-linter                      |
| `seed`                                         | `manage.py seed_demo`                                                                                    |
| `test`                                         | `pytest -n auto --reuse-db --cov` + coverage report, then `test-fe`                                      |
| `test-be`, `test-fe`                           | Backend only / Vitest only                                                                               |
| `test-nc`, `test-serial`, `test-new-db`        | Same as your current targets, mapped to pytest flags (no `--cov` / no `-n` / `--create-db`)              |
| `lint`                                         | `pre-commit run --all-files`                                                                             |
| `api-types`                                    | Export the OpenAPI schema and regenerate the frontend's TypeScript types                                 |
| `clean-coverage`                               | Delete coverage artifacts                                                                                |

### Pre-commit (`.pre-commit-config.yaml` at the repo root)

This is your config with these changes:

- `ruff-check` and `ruff-format` are scoped to `files: ^backend/`.
- Ruff's `I` rules sort imports, replacing the separate isort hook; ruff detects the project's own apps as first-party automatically.
- Local hooks run the frontend's ESLint and Prettier on `^frontend/` files, plus a whole-project `vue-tsc` type check whenever frontend TypeScript, Vue or tsconfig files change.
- `pre-commit` is a backend dev dependency, so `make install` sets it up.
- `no-commit-to-branch` is removed. It isn't needed for this project.

### README.md

The README is written in Milestone 1 so setup instructions exist from day one. It covers what the app is, prerequisites (Homebrew, Docker, Volta), a quick start (`make init && make db && make migrate && make seed`, then `make backend` and `make frontend`, or just `make up`), the table of make targets, and the repo layout. The "Design decisions" section is filled in during Milestone 7 (Polish).

---

## 7. Quality bar

- **Backend tests:** pytest-django + factory_boy. Cover:
  - Unique constraints on `account_number` and `(account, reference_id)`.
  - Serializers and API endpoints.
  - The import pipeline: happy path, every validation failure, duplicates within the file and in the DB, and a check that nothing is inserted on failure.
  - The sample file generator, including a test that its output imports cleanly.
- **Frontend tests:** Vitest + Vue Test Utils for components. One Playwright end-to-end test of the upload flow is a stretch goal.
- **Lint/format:** ruff (Python, including import sorting), ESLint + Prettier (frontend), all run through pre-commit (see section 6).
- **Seed data:** a management command (`seed_demo`) that generates fake accounts and transactions with Faker.
- **README:** one-command startup, architecture notes, and design decisions (immutable ledger, why there's no deletes, why balances are calculated on demand rather than stored and kept in sync (fine at this scale), all-or-nothing imports, decimal handling, why imports are synchronous, using USD everywhere for currency).

---

## 8. Milestones

1. **Scaffold** (done): Docker Compose with Postgres, Django project (uv), Vite app (Volta), Makefile, pre-commit, `.env.example`, `.gitignore`, and README (setup part). Done when a fresh clone runs `make init && make db && make migrate && make test && make lint` cleanly.
2. **Core** (done): abstract `BaseModel` (UUID primary key, timestamps) with tests.
3. **Domain + API** (done): `ledger` app with Account and Transaction models, migration, services, DRF endpoints and tests. Transactions are listed and posted under their account (`/api/accounts/{id}/transactions/`); there's no all-transactions list. Posting to or editing a closed account is a 400; reposting a `reference_id` (a genuine clash) is a 409. Services lock the account row, so concurrent requests can't bypass the closed-account rule.
4. **Frontend CRUD** (done): accounts list (server-side paging, search, status filter, sorting), account detail with its transactions (direction and date filters) and close-with-confirmation, account form (open and edit), transaction form, transaction detail. API field errors show next to their fields; tests sit beside each view. Search, filters, sort and page live in the URL (e.g. `/accounts?status=CLOSED&ordering=-balance&page=2`, `/accounts/{id}?direction=DEBIT&from=2026-09-01`), so refresh, shared links and Back restore them; invalid values are ignored, and a page that no longer exists falls back to page 1.
5. **Bulk upload backend** (done): `imports` app with ImportBatch and ImportRowError, `Transaction.import_batch`, parser, all-or-nothing validation reusing the transaction serializer, lock-free validation then a short locked re-check and bulk insert, error CSV, sample file generator, tests.
6. **Bulk upload frontend** (done): upload (drop zone, column guide, sample downloads), results (summary, row errors, error CSV), history; header nav for Accounts and Imports.
7. **Polish** (done): `seed_demo` command (`make seed`), README with design decisions, a frontend container that reinstalls dependencies when `package-lock.json` changes, and a pass over the code for the CLAUDE.md conventions.

---

## 9. Deferred

- **Hosting**: a live demo, maybe on Render or Fly.io. Synchronous imports keep this to a web service plus Postgres. Serve with gunicorn (`gunicorn config.wsgi`, `gthread` workers, bound to the host's `$PORT`, logs to stdout); `runserver` stays for local dev.
- **Authentication**: a Django session login with a demo user, if it's needed later.
- **Async imports**: a Celery or RQ worker, if file sizes ever justify it.
- **XLSX upload support.**
