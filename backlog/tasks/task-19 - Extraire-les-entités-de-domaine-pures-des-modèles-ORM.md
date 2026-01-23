---
id: TASK-19
title: Extraire les entités de domaine pures des modèles ORM
status: To Do
assignee: []
created_date: '2026-01-23 09:45'
labels:
  - ddd
  - architecture
  - refactoring
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Séparer la couche domaine de l'infrastructure en créant des entités de domaine pures:
- Créer `Fund`, `Asset`, `Transaction` comme classes Python pures (pas SQLAlchemy)
- Ajouter comportements métier (Fund.add_asset(), Fund.rebalance(), Asset.calculate_gain())
- Définir `Fund` comme Aggregate Root
- Les repositories retourneront ces entités au lieu des *Table

Structure cible:
```
backend/domain/
├── entities/
│   ├── fund.py
│   ├── asset.py
│   └── transaction.py
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Entités créées sans dépendance SQLAlchemy
- [ ] #2 Fund défini comme Aggregate Root
- [ ] #3 Comportements métier dans les entités
- [ ] #4 Tests unitaires pour logique métier
- [ ] #5 Mappers ORM ↔ Domain créés
<!-- AC:END -->
