SHELL:=/bin/bash
.SHELLFLAGS = -ec
.ONESHELL:
.SILENT:


.PHONY: help
help:
	echo "❓ Use \`make <target>'"
	grep -E '^\.PHONY: [a-zA-Z0-9_-]+ .*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = "(: |##)"}; {printf "\033[36m%-30s\033[0m %s\n", $$2, $$3}'

.PHONY: install ## 💁 install dependencies
install:
	uv sync

.PHONY: run ## 🏃 run the application
run:
	uv run python -m src.server

# .PHONY: lint ## 🕵 run lint
# lint:
# 	uv run autoflake -i --remove-all-unused-imports -r --ignore-init-module-imports . --exclude venv
# 	uv run isort . --gitignore
# 	uv run black .
# 	uv run flake8 .

.PHONY: lint ## 🕵 run lint
lint:
	uv run ruff check . --fix
	uv run ruff format .

.PHONY: check ## 🕵 run check
check:
	uv run ruff check .

.PHONY: tests ## 🕵 run tests
tests:
	uv run pytest ./tests --disable-warnings --cov=./src --cov-fail-under 99 --junitxml=coverage/junit-report.xml --cov-report=xml:coverage/coverage.xml --cov-report=html:coverage/htmlcov

.PHONY: docker-build ## 🐳 build docker image
docker-build:
	docker build -t stock-alerting:latest .

.PHONY: docker-run ## 🐳 run docker container
docker-run:
	docker run -v "$${PWD}/config.json:/app/config.json:ro" stock-alerting:latest
