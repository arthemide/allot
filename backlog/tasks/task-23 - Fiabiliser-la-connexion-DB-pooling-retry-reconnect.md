---
id: TASK-23
title: Fiabiliser la connexion DB (pooling, retry, reconnect)
status: To Do
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
