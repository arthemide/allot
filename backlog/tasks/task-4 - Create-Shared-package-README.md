---
id: TASK-4
title: Create Shared package README.md
status: To Do
assignee: []
created_date: '2026-01-16 10:15'
labels:
  - documentation
  - shared
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Document the shared package including unified asset model, PRUM system, and repository pattern.

**Location:** `/workspace/projects/stock-alerting/backend/shared/README.md`

**Content to include:**
- Shared package purpose
- Database schema documentation
  - Unified asset model (stocks, crypto, bonds)
  - Assets table structure
  - Transactions table structure
  - Funds table structure
- Repository pattern explanation
- PRUM calculation system with formula
- How to use TransactionRepository with examples
- Installation as editable package (uv pip install -e .)
- Running tests (uv run pytest)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Database schema documented with all tables
- [ ] #2 Unified asset model explained
- [ ] #3 PRUM calculation detailed with formula
- [ ] #4 Repository usage examples provided
- [ ] #5 Installation instructions included
<!-- AC:END -->
