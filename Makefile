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
	poetry install -v --no-root

.PHONY: lint ## 🕵 run lint
lint:
	echo running black...
	black .
	echo running isort...
	isort . --gitignore
	echo running autoflake...
	autoflake -i --remove-all-unused-imports -r --ignore-init-module-imports . --exclude venv
	echo running flake8...
	flake8 .

.PHONY: check ## 📑 Check code format
check:
	poetry run black . --check
	poetry run isort . --gitignore --check
	poetry run flake8 src

.PHONY: tests ## 🕵 run tests
tests:
	echo running tests...
	poetry run pytest ./tests --disable-warnings --cov=./src --cov-fail-under 86 --junitxml=coverage/junit-report.xml --cov-report=xml:coverage/coverage.xml --cov-report=html:coverage/htmlcov
