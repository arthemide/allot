.PHONY: tests
.SILENT:
.DEFAULT_GOAL: help
help:
	echo "GLOBAL"
	grep -E '^\.PHONY: (install|lint|check|tests) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "API"
	grep -E '^\.PHONY: (api-install|api-test|api-dev) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "DATABASE"
	grep -E '^\.PHONY: (db-migrate|db-revision|db-downgrade|db-test) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "BOT"
	echo ""
	echo "TERMINAL AUTO-START"
	
# =============================================================================
# Global commands
# =============================================================================

.PHONY: install ## 💁 Install all dependencies
install:
	uv sync --all-packages

.PHONY: lint ## 🕵 Run lint and format on all packages
lint:
	uv run ruff check . --fix
	uv run ruff format .

.PHONY: check ## 🕵 Run lint check without fixing
check: install
	uv run ruff check .
	uv run ty check

.PHONY: tests ## 🧪 Run all tests
tests:
	$(MAKE) api-test
	$(MAKE) db-test

# =============================================================================
# API commands
# =============================================================================

.PHONY: api-install ## 💁 Install API dependencies only
api-install:
	uv sync --package stock-alerting-api

.PHONY: api-test ## 🧪 Run API tests
api-test:
	PYTHONPATH=api uv run pytest api/tests --disable-warnings --cov=api/src --cov-fail-under 80 --junitxml=api/coverage/junit-report.xml --cov-report=xml:api/coverage/coverage.xml --cov-report=html:api/coverage/htmlcov

.PHONY: api-dev ## 🚀 Run API development server
api-dev:
	uv run uvicorn src.main:app --reload --app-dir api


# =============================================================================
# Database commands
# =============================================================================

.PHONY: db-migrate ## 🗄️  Run database migrations
db-migrate:
	cd shared && uv run alembic upgrade head

.PHONY: db-revision ## 📝 Create new migration revision
db-revision:
	@read -p "Revision message: " msg && \
	cd shared && uv run alembic revision --autogenerate -m "$$msg"

.PHONY: db-downgrade ## ⬇️  Downgrade database by one revision
db-downgrade:
	cd shared && uv run alembic downgrade -1

db-test:
	uv run pytest shared/tests --disable-warnings --cov=shared/src --cov-fail-under 80 --junitxml=shared/coverage/junit-report.xml --cov-report=xml:shared/coverage/coverage.xml --cov-report=html:shared/coverage/htmlcov

# =============================================================================
# Bot commands
# =============================================================================
