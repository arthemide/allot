---
id: TASK-22
title: Séparer les Bounded Contexts (Portfolio vs Trading)
status: To Do
assignee: []
created_date: '2026-01-23 09:45'
labels:
  - ddd
  - architecture
  - bounded-context
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Définir explicitement deux bounded contexts avec leurs propres modèles:

**Portfolio Context** (API):
- Gestion des fonds et actifs
- Suivi des répartitions
- Calcul des performances

**Trading Context** (Bot DCA):
- Exécution des achats
- Calcul PRUM
- Historique transactions

Chaque contexte aura ses propres entités, même si elles partagent des données en BDD. Un Anti-Corruption Layer (ACL) traduira entre les deux.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Contextes clairement séparés dans le code
- [ ] #2 Chaque contexte a ses propres entités
- [ ] #3 ACL implémenté pour la communication
- [ ] #4 shared/ réduit au strict minimum
- [ ] #5 Documentation des context maps
<!-- AC:END -->
