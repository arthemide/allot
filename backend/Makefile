.PHONY: tests
.SILENT:
.DEFAULT_GOAL: help
help:
	echo "GLOBAL"
	grep -E '^\.PHONY: (install|lint|check|tests) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "API"
	grep -E '^\.PHONY: (api-install|api-test|api-dev|api-docker-build|api-docker-run) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "BOT"
	grep -E '^\.PHONY: (bot-install|bot-test|dca-test|dca-debug|dca-once|dca-now|dca-start|dca-bot-logs) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "DATABASE"
	grep -E '^\.PHONY: (db-migrate|db-revision|db-downgrade) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "macOS SERVICE"
	grep -E '^\.PHONY: (dca-bot-install|dca-bot-uninstall|dca-bot-status) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	
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
check:
	uv run ruff check .

.PHONY: tests ## 🧪 Run all tests
tests:
	PYTHONPATH=bot uv run pytest bot/tests --disable-warnings --cov=bot/dca --cov-report=term-missing
	PYTHONPATH=shared/src uv run pytest shared/tests --disable-warnings --cov=shared/src/shared --cov-report=term-missing

# =============================================================================
# API commands
# =============================================================================

.PHONY: api-install ## 💁 Install API dependencies only
api-install:
	uv sync --package stock-alerting-api

.PHONY: api-test ## 🧪 Run API tests
api-test:
	PYTHONPATH=api uv run pytest api/tests --disable-warnings --cov=api/src --cov-fail-under 99 --junitxml=api/coverage/junit-report.xml --cov-report=xml:api/coverage/coverage.xml --cov-report=html:api/coverage/htmlcov

.PHONY: api-dev ## 🚀 Run API development server
api-dev:
	uv run uvicorn src.main:app --reload --app-dir api

.PHONY: api-docker-build ## 🐳 Build API Docker image
api-docker-build:
	docker build -t stock-alerting:latest api/

.PHONY: api-docker-run ## 🐳 Run API Docker container
api-docker-run:
	docker run -v "$${PWD}/api/config.json:/app/config.json:ro" stock-alerting:latest

# =============================================================================
# Bot commands
# =============================================================================

.PHONY: bot-install ## 💁 Install Bot dependencies only
bot-install:
	uv sync --package stock-alerting-bot

.PHONY: bot-test ## 🧪 Run Bot tests
bot-test:
	PYTHONPATH=bot uv run pytest bot/tests --disable-warnings --cov=bot/dca --junitxml=bot/coverage/junit-report.xml --cov-report=xml:bot/coverage/coverage.xml --cov-report=html:bot/coverage/htmlcov

.PHONY: dca-test ## 🧪 Test DCA bot configuration (no real purchase)
dca-test:
	cd bot && uv run python -m dca.main --test

.PHONY: dca-debug ## 🔍 Run DCA API debug tests (read-only, no trades)
dca-debug:
	cd bot && uv run python -m dca.test_debug

.PHONY: dca-once ## ▶️  Execute a single DCA purchase
dca-once:
	cd bot && uv run python -m dca.main --once

.PHONY: dca-now ## ⚡ Execute immediately then start the scheduler
dca-now:
	cd bot && uv run python -m dca.main --now

.PHONY: dca-start ## 🚀 Start the DCA bot in scheduler mode
dca-start:
	cd bot && uv run python -m dca.main

.PHONY: dca-bot-logs ## 📋 View DCA bot logs
dca-bot-logs:
	tail -f bot/dca/logs/launchd-dca-bot.log

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

# =============================================================================
# macOS Service commands
# =============================================================================

.PHONY: dca-bot-install ## 🍎 Install macOS service (starts automatically)
dca-bot-install:
	./scripts/install-macos-service.sh

.PHONY: dca-bot-uninstall ## 🗑️  Uninstall macOS service
dca-bot-uninstall:
	./scripts/uninstall-macos-service.sh

.PHONY: dca-bot-status ## 📊 View macOS service status
dca-bot-status:
	@launchctl list | grep dca-bot || echo "Service not active"
