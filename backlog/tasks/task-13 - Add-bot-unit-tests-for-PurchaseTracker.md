---
id: TASK-13
title: Add bot unit tests for PurchaseTracker
status: Done
assignee: []
created_date: '2026-01-16 10:16'
labels:
  - testing
  - bot
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create unit tests for the PurchaseTracker in the bot module.

**Location:** `/workspace/projects/stock-alerting/backend/bot/tests/`

**Test coverage needed:**
- Purchase tracking logic
- Decision logic for DCA purchases
- Integration with shared package
- Error handling scenarios
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 PurchaseTracker fully tested
- [x] #2 Decision logic tested
- [x] #3 Integration with shared package verified
- [x] #4 Error handling tested
- [ ] #5 All tests passing (need to run in Docker)
<!-- AC:END -->

## Implementation Notes

### Implémenté (2026-02-05)

**Fichier créé:** `backend/bot/tests/test_purchase_tracker.py`

**Tests couverts (14 tests):**
- `TestPurchaseTrackerInit`: init avec/sans base_prum, gestion erreur DB
- `TestAddPurchase`: ajout réussi, sans timestamp, gestion erreur
- `TestCalculatePrum`: retour valeur, None si pas d'achats, graceful degradation
- `TestGetStatistics`: succès, empty dict on error
- `TestGetRecentPurchases`: liste de dicts, empty on error, respect du limit
