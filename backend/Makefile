.PHONY: tests
.SILENT:
.DEFAULT_GOAL: help

help:
	echo "Please use \`make \033[36m<target>\033[0m\`"
	echo "\t where \033[36m<target>\033[0m is one of"
	grep -E '^\.PHONY: [a-zA-Z_-]+ .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "• \033[36m%-30s\033[0m %s\n", $$2, $$3}'

.PHONY: dca-install ## 🤖 Install DCA bot dependencies
dca-install:
	cd bot && uv sync --group dca

.PHONY: dca-test ## 🧪 Test DCA bot configuration (no real purchase)
dca-test:
	cd bot && uv run python -m dca.main --test

.PHONY: dca-debug ## 🔍 Run API debug tests (read-only, no trades)
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

.PHONY: dca-bot-install ## 🍎 Install macOS service (starts automatically)
dca-bot-install:
	./scripts/install-macos-service.sh

.PHONY: dca-bot-uninstall ## 🗑️  Uninstall macOS service
dca-bot-uninstall:
	./scripts/uninstall-macos-service.sh

.PHONY: dca-bot-status ## 📊 View macOS service status
dca-bot-status:
	@launchctl list | grep dca-bot || echo "Service not active"
