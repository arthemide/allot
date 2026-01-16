---
id: TASK-5
title: Add service layer tests
status: To Do
assignee: []
created_date: '2026-01-16 10:15'
labels:
  - testing
  - api
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Test FundService and StockService with mocked repositories.

**Create:** `/workspace/projects/stock-alerting/backend/api/tests/test_services.py`

**Test strategy:**
- Mock repository responses
- Test business logic without database
- Verify correct repository method calls
- Test error handling

**Services to test:**
- FundService: business logic for fund operations
- StockService: business logic for stock operations
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 FundService fully tested with mocked repository
- [ ] #2 StockService fully tested with mocked repository
- [ ] #3 Business logic verified without database dependency
- [ ] #4 Error handling tested
- [ ] #5 All tests passing
<!-- AC:END -->
