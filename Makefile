.SILENT:
.DEFAULT_GOAL := help

FRONT_DIR := front

help:
	echo "Please use \`make \033[36m<target>\033[0m\`"
	echo "\t where \033[36m<target>\033[0m is one of"
	grep -E '^\.PHONY: [a-zA-Z_-]+ .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "• \033[36m%-30s\033[0m %s\n", $$2, $$3}'

.PHONY: install ## 📦 Install backend and front dependencies
install:
	uv sync
	cd $(FRONT_DIR) && npm ci

.PHONY: start ## 🚀 Build the front and serve everything on :8000
start: build
	uv run app.py

.PHONY: dev-api ## 🚀 Run the API alone with auto-reload on :8000
dev-api:
	uv run uvicorn app:app --reload --port 8000

.PHONY: dev-front ## 🚀 Run the front dev server on :5173 (needs dev-api)
dev-front:
	cd $(FRONT_DIR) && npm run dev

.PHONY: build ## 🏗️ Build the static front into front/dist
build:
	cd $(FRONT_DIR) && npm run build

.PHONY: preview ## 👁️ Preview the built front on its own
preview:
	cd $(FRONT_DIR) && npm run preview

.PHONY: test ## 🧪 Run the unit tests
test:
	uv run pytest -q

.PHONY: lint ## 🔍 Check Python and Svelte
lint:
	uv run ruff check .
	cd $(FRONT_DIR) && npm run check

.PHONY: format ## 🔍 Format Python and fix what can be fixed
format:
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: note ## 📚 Print the monthly note (needs the app running)
note:
	curl -s http://127.0.0.1:8000/note

.PHONY: up ## 🐳 Start the on-premise stack from the published image
up:
	docker compose up -d

.PHONY: up-local ## 🐳 Same, but build the image from this checkout
up-local:
	docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build

.PHONY: down ## 🐳 Stop the on-premise stack
down:
	docker compose down

.PHONY: update ## 🚀 Pull the pinned version and restart
update:
	docker compose pull
	docker compose up -d

.PHONY: logs ## 🐳 Follow the container logs
logs:
	docker compose logs -f

.PHONY: replication ## 💾 Show what Litestream has replicated off-site
replication:
	docker compose exec app litestream ltx -level all -config /etc/litestream.yml /data/allot.db

.PHONY: clean ## 🧹 Remove build output and caches
clean:
	rm -rf $(FRONT_DIR)/dist $(FRONT_DIR)/.svelte-kit
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -not -path "./.venv/*" -exec rm -rf {} +
