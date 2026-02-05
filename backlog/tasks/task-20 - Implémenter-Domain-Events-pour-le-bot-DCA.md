---
id: TASK-20
title: Implémenter Domain Events pour le bot DCA
status: To Do
assignee: []
created_date: '2026-01-23 09:45'
updated_date: '2026-01-23 18:59'
labels:
  - ddd
  - architecture
  - event-driven
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remplacer les notifications directes par un système d'événements de domaine:
- `AssetPurchased` - émis après un achat DCA réussi
- `PurchaseSkipped` - émis quand les conditions ne sont pas remplies
- `ThresholdExceeded` - émis quand un seuil d'alerte est dépassé

Le bot émet les événements, des handlers les consomment (email, logging, webhook).

Avantages:
- Découplage notification/logique métier
- Extensibilité (ajouter Slack, webhook sans toucher au bot)
- Traçabilité
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Events définis dans domain/events/
- [ ] #2 Event dispatcher implémenté
- [ ] #3 EmailNotifier converti en event handler
- [ ] #4 Tests d'intégration pour le flux complet
- [ ] #5 Documentation du pattern
<!-- AC:END -->
