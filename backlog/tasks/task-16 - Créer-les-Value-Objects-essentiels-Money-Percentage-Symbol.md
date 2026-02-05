---
id: TASK-16
title: 'Créer les Value Objects essentiels (Money, Percentage, Symbol)'
status: To Do
assignee: []
created_date: '2026-01-23 09:45'
labels:
  - ddd
  - architecture
  - refactoring
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Créer des Value Objects immutables pour encapsuler les concepts métier:
- `Money`: montants avec validation (pas de valeurs négatives), opérations arithmétiques
- `Percentage`: répartition/seuils avec validation [0-100]
- `Symbol`: ticker avec validation de format
- `PRUM`: prix de revient unitaire moyen avec calcul intégré

Ces VOs remplaceront les float/str bruts dans tout le code et garantiront l'intégrité des données.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Value Objects créés dans backend/domain/value_objects/
- [ ] #2 Tests unitaires pour chaque VO
- [ ] #3 Immutabilité garantie (frozen dataclass ou __slots__)
- [ ] #4 Validation dans constructeur
- [ ] #5 Opérations métier implémentées (ex: Money.add())
<!-- AC:END -->
