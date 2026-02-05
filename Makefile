.PHONY: tests
.SILENT:
.DEFAULT_GOAL: help
help:
	echo "GLOBAL"
	grep -E '^\.PHONY: (up|up-debug|up-debug-no-mig) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "BOT"
	grep -E '^\.PHONY: (dca-start|dca-start-d|dca-logs|dca-stop) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "DATABASE"
	grep -E '^\.PHONY: (db-backup|db-restore) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
.PHONY: up ## 🚀 up
up:
	docker-compose -f docker-compose.yaml -f docker-compose.with-migrations.yaml up --build --force-recreate -d

.PHONY: up-debug ## 🚀 up-debug
up-debug:
	docker-compose -f docker-compose.yaml -f docker-compose.with-migrations.yaml -f shared-volumes.yaml up --build --force-recreate

.PHONY: up-debug-no-mig ## 🚀 up-debug-no-mig (no migrations)
up-debug-no-mig:
	docker-compose -f docker-compose.yaml -f shared-volumes.yaml up --build --force-recreate db api front

.PHONY: dca-start ## 🤖 dca-start (start DCA bot with db dependency)
dca-start:
	docker-compose -f docker-compose.yaml --profile dca up --build dca-bot

.PHONY: dca-start-d ## 🤖 dca-start-d (start DCA bot detached)
dca-start-d:
	docker-compose -f docker-compose.yaml --profile dca up --build -d dca-bot

.PHONY: dca-logs ## 📋 dca-logs (view DCA bot logs)
dca-logs:
	docker-compose -f docker-compose.yaml --profile dca logs -f dca-bot

.PHONY: dca-stop ## 🛑 dca-stop (stop DCA bot)
dca-stop:
	docker-compose -f docker-compose.yaml --profile dca stop dca-bot

.PHONY: db-backup ## 💾 db-backup (backup postgres data to ./data/db-backup)
db-backup:
	mkdir -p ./data/db-backup
	docker run --rm -v stock_postgres_data:/data -v $(PWD)/data/db-backup:/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
	echo "✅ Backup saved to ./data/db-backup/postgres_backup.tar.gz"

.PHONY: db-restore ## 💾 db-restore (restore postgres data from ./data/db-backup)
db-restore:
	docker volume create stock_postgres_data 2>/dev/null || true
	docker run --rm -v stock_postgres_data:/data -v $(PWD)/data/db-backup:/backup alpine sh -c "rm -rf /data/* && tar xzf /backup/postgres_backup.tar.gz -C /data"
	echo "✅ Database restored from ./data/db-backup/postgres_backup.tar.gz"
