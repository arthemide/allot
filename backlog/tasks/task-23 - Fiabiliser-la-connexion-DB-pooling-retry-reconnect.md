---
id: TASK-23
title: Fiabiliser la connexion DB (pooling, retry, reconnect)
status: Done
assignee: []
created_date: '2026-02-02 13:43'
labels:
  - database
  - reliability
  - backend
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Actuellement le bot suppose que la DB PostgreSQL est toujours disponible. Améliorer la résilience :

- Connection pooling (ex: via SQLAlchemy pool ou asyncpg pool)
- Retry automatique sur les requêtes DB en cas d'erreur transitoire
- Gestion propre des déconnexions et reconnexions
- Logging des erreurs DB pour diagnostic
- Health check DB avant chaque cycle d'achat
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

### Implémenté (2026-02-05)

**shared/db/config.py :**
- ✅ Pool amélioré : `pool_recycle=1800`, `pool_timeout=30`
- ✅ Timeouts PostgreSQL : `connect_timeout=10`, `statement_timeout=30s`
- ✅ `check_db_health()` : vérifie la connectivité DB
- ✅ `@with_db_retry(max_retries=3)` : décorateur retry avec backoff exponentiel

**shared/db/repositories/transaction.py :**
- ✅ `@with_db_retry` sur `get_or_create_asset`, `add_transaction`, `get_recent_transactions`

**bot/dca/scheduler.py :**
- ✅ Health check DB avant chaque cycle d'achat
- ✅ Notification d'erreur si DB indisponible
