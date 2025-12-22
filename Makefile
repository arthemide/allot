.PHONY: tests
.SILENT:
.DEFAULT_GOAL: help

help:
	echo "Please use \`make \033[36m<target>\033[0m\`"
	echo "\t where \033[36m<target>\033[0m is one of"
	grep -E '^\.PHONY: [a-zA-Z_-]+ .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "• \033[36m%-30s\033[0m %s\n", $$2, $$3}'

.PHONY: up ## 🚀 up
up:
	docker-compose -f docker-compose.yaml up --build --force-recreate -d

.PHONY: up-debug ## 🚀 up-debug
up-debug:
	docker-compose -f docker-compose.yaml -f docker-compose.with-migrations.yaml -f shared-volumes.yaml up --build --force-recreate

.PHONY: up-debug-no-mig ## 🚀 up-debug-no-mig (no migrations)
up-debug-no-mig:
	docker-compose -f docker-compose.yaml -f shared-volumes.yaml up --build --force-recreate db api front
