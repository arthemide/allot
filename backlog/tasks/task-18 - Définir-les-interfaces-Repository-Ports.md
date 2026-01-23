---
id: TASK-18
title: Définir les interfaces Repository (Ports)
status: To Do
assignee: []
created_date: '2026-01-23 09:45'
labels:
  - ddd
  - architecture
  - hexagonal
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Créer des interfaces abstraites pour les repositories suivant le pattern Ports & Adapters:
- `IFundRepository` - interface abstraite
- `SQLAlchemyFundRepository` - implémentation concrète

Avantages:
- Découplage domaine/infrastructure
- Testabilité (mocks faciles)
- Possibilité de changer d'ORM

Structure:
```
backend/domain/repositories/       # Interfaces (ports)
backend/infrastructure/persistence/ # Implémentations (adapters)
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Interfaces définies avec ABC
- [ ] #2 Repositories retournent des entités de domaine
- [ ] #3 Implémentations SQLAlchemy séparées
- [ ] #4 Injection de dépendances configurée
- [ ] #5 Tests avec mocks fonctionnels
<!-- AC:END -->
