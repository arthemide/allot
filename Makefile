.PHONY: tests
.SILENT:
.DEFAULT_GOAL: help
help:
	echo "GLOBAL"
	grep -E '^\.PHONY: (up|up-debug|up-debug-no-mig) .*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = "(: |##)"}; {printf "  \033[36m%-45s\033[0m %s\n", $$2, $$3}'
	echo ""
	echo "BOT"
	grep -E '^\.PHONY: (dca-start|dca-logs|dca-stop) .*?## .*$$' $(MAKEFILE_LIST) \
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

.PHONY: down ## 🛑 down
down:
	docker-compose -f docker-compose.yaml -f docker-compose.with-migrations.yaml down

.PHONY: dca-start ## 🤖 start DCA bot detached
dca-start:
	docker-compose -f docker-compose.yaml --profile dca up --build -d dca-bot

.PHONY: dca-logs ## 📋 view DCA bot logs
dca-logs:
	docker-compose -f docker-compose.yaml --profile dca logs -f dca-bot

.PHONY: dca-stop ## 🛑 stop DCA bot
dca-stop:
	docker-compose -f docker-compose.yaml --profile dca stop dca-bot

.PHONY: db-backup ## 💾 backup postgres to ./backups
db-backup:
	mkdir -p ./backups
	docker exec stock-alerting-db pg_dump -U romeo stock_alerting > ./backups/db-export-$$(date +%Y%m%d-%H%M%S).sql
	docker run --rm -v stock_alerting_postgres_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/postgres-backup-$$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@echo "✅ Backups saved to ./backups/"
	@ls -lh ./backups/

.PHONY: db-restore ## 💾 restore from ./backups/postgres-backup-*.tar.gz
db-restore:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Usage: make db-restore FILE=./backups/postgres-backup-YYYYMMDD-HHMMSS.tar.gz"; \
		echo ""; \
		echo "Available backups:"; \
		ls -lh ./backups/*.tar.gz 2>/dev/null || echo "No backups found"; \
		exit 1; \
	fi
	@echo "⚠️  This will REPLACE all current database data!"
	@echo "Backup file: $(FILE)"
	@read -p "Continue? (yes/no): " confirm && [ "$$confirm" = "yes" ] || (echo "Cancelled" && exit 1)
	docker-compose down
	docker volume rm stock_alerting_postgres_data 2>/dev/null || true
	docker volume create stock_alerting_postgres_data
	docker run --rm -v stock_alerting_postgres_data:/data -v $(PWD)/backups:/backup alpine tar xzf /backup/$$(basename $(FILE)) -C /data
	docker-compose up -d db
	@echo "✅ Database restored from $(FILE)"
