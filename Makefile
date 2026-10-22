OS := $(shell uname)

ifeq ($(OS),Linux)
	SHELL:=/bin/bash
endif

# uv manages the backend venv itself; an activated pyenv/virtualenv would only
# trigger "VIRTUAL_ENV does not match" warnings.
unexport VIRTUAL_ENV

# Backend commands run inside backend/ with its uv-managed venv. Frontend
# commands cd into frontend/ so Volta picks up the Node version pinned there.
UV := uv run --directory backend
MANAGE := $(UV) python manage.py
NPM := cd frontend && npm

# Volta's shims, so a Volta installed by `make init` works before the shell
# profile change from `volta setup` takes effect.
export VOLTA_HOME ?= $(HOME)/.volta
export PATH := $(VOLTA_HOME)/bin:$(PATH)

BACKEND_PORT ?= 8001

PYTEST_COV := --cov --cov-report=term-missing

# run this the first time you pull down the repo to ensure you have pre-reqs
.PHONY: init
init:
	@command -v brew >/dev/null || { echo "Homebrew is required: https://brew.sh"; exit 1; }
	command -v uv >/dev/null || brew install uv
	command -v volta >/dev/null || { brew install volta && volta setup; }
	command -v docker >/dev/null || brew install --cask docker-desktop
	@docker info >/dev/null 2>&1 || { \
		echo "Starting Docker Desktop (first launch asks you to accept the license)..."; \
		open -a Docker; \
		until docker info >/dev/null 2>&1; do sleep 2; done; \
	}
	cd backend && uv python install
	[ -f .env ] || cp .env.example .env
	$(MAKE) install

.PHONY: install
install:
	cd backend && uv sync
	$(NPM) ci
	$(UV) pre-commit install

.PHONY: upgrade
upgrade:
	cd backend && uv lock --upgrade && uv sync
	$(NPM) update
	$(UV) pre-commit autoupdate

# --- Docker ---------------------------------------------------------------

.PHONY: db
db:
	docker compose up -d --wait db

.PHONY: up
up:
	docker compose up --build --renew-anon-volumes

.PHONY: down
down:
	docker compose down

# --- Local dev servers ----------------------------------------------------

.PHONY: backend
backend:
	$(MANAGE) runserver $(BACKEND_PORT)

.PHONY: frontend
frontend:
	cd frontend && API_PROXY_TARGET=http://localhost:$(BACKEND_PORT) npm run dev

# --- Database -------------------------------------------------------------

.PHONY: migrate
migrate:
	$(MANAGE) migrate

.PHONY: makemigrations
makemigrations:
	$(MANAGE) makemigrations

.PHONY: lint-migrations
lint-migrations:
	$(MANAGE) lintmigrations --unapplied-migrations --quiet ignore

.PHONY: seed
seed:
	$(MANAGE) seed_demo

# --- Tests ----------------------------------------------------------------

.PHONY: test
test: test-be test-fe

.PHONY: test-be
test-be:
	$(UV) pytest -n auto --reuse-db $(PYTEST_COV)
	date

# run the tests without coverage tracking for quicker execution
.PHONY: test-nc
test-nc:
	$(UV) pytest -n auto --reuse-db

.PHONY: test-serial
test-serial:
	$(UV) pytest --reuse-db $(PYTEST_COV)
	date

.PHONY: test-new-db
test-new-db:
	$(UV) pytest -n auto --create-db $(PYTEST_COV)
	date

.PHONY: test-fe
test-fe:
	$(NPM) test

.PHONY: clean-coverage
clean-coverage:
	find backend -name '.coverage*' -delete

# --- Lint and generated code ----------------------------------------------

.PHONY: lint
lint:
	$(UV) pre-commit run --all-files

# Export the OpenAPI schema and regenerate the frontend's TypeScript types.
.PHONY: api-types
api-types:
	$(MANAGE) spectacular --validate --file openapi.yml
	$(NPM) run api-types
