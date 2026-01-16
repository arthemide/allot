---
id: TASK-9
title: Create DATABASE.md
status: To Do
assignee: []
created_date: '2026-01-16 10:16'
labels:
  - documentation
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Complete database schema documentation.

**Location:** `/workspace/projects/stock-alerting/DATABASE.md`

**Content to include:**
- Complete database schema
- Tables:
  - funds - Portfolio funds
  - stocks (AssetTable) - Unified assets (stocks, crypto, bonds)
  - asset_transactions - Transaction history for PRUM
- Relationships and foreign keys
- PRUM calculation algorithm
- Migration strategy
- How to create migrations (alembic revision)
- How to run migrations (alembic upgrade head)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Complete database schema documented
- [ ] #2 All tables described with columns
- [ ] #3 Relationships and foreign keys explained
- [ ] #4 PRUM calculation algorithm detailed
- [ ] #5 Migration instructions included
<!-- AC:END -->
