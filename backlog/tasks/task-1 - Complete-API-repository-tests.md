---
id: TASK-1
title: Complete API repository tests
status: Done
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
Create comprehensive tests for FundRepository and StockRepository in the API layer. Currently 0% coverage of new architecture.

**Current State:**
- All existing tests are obsolete: 24 tests covering old Fund and Stock classes
- 0% coverage of new architecture: repositories, services, API endpoints
- Only shared package has modern tests (TransactionRepository)

**Plan:**
1. Create conftest.py with database fixtures
2. Write test_repositories.py
3. Test all CRUD operations for both repositories
4. Verify selectinload behavior
5. Verify cascade deletes

**Test both FundRepository and StockRepository:**
- FundRepository.get_all() - retrieve all funds with stocks
- FundRepository.get_by_id() - retrieve single fund
- FundRepository.create() - create new fund
- FundRepository.update() - update fund name
- FundRepository.delete() - delete fund (cascade to stocks)
- StockRepository.add() - add stock to fund
- StockRepository.update() - update stock in fund
- StockRepository.remove() - remove stock from fund

**Test Strategy:**
- Use in-memory SQLite (like shared package tests)
- Create conftest.py with database fixtures
- Test proper selectinload behavior
- Verify cascade deletes
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 FundRepository: test all 5 methods (get_all, get_by_id, create, update, delete)
- [ ] #2 StockRepository: test all 3 methods (add, update, remove)
- [ ] #3 Database fixtures properly isolate tests
- [ ] #4 All tests passing
- [ ] #5 Remove old tests
<!-- AC:END -->
