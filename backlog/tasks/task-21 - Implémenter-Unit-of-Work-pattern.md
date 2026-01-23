---
id: TASK-21
title: Implémenter Unit of Work pattern
status: To Do
assignee: []
created_date: '2026-01-23 09:45'
labels:
  - ddd
  - architecture
  - persistence
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Actuellement chaque méthode de repository crée sa propre session SQLAlchemy. Implémenter Unit of Work pour:
- Gérer les transactions de manière cohérente
- Permettre plusieurs opérations dans une même transaction
- Faciliter le rollback en cas d'erreur

Pattern cible:
```python
with uow:
    fund = uow.funds.get_by_id(1)
    fund.add_asset(asset)
    uow.commit()
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 UnitOfWork class créée
- [ ] #2 Tous les repos utilisent UoW
- [ ] #3 Transactions atomiques garanties
- [ ] #4 Rollback automatique sur exception
- [ ] #5 Tests d'intégration
<!-- AC:END -->
