---
id: TASK-7
title: Add API endpoint tests
status: Done
assignee: []
created_date: '2026-01-16 10:16'
labels:
  - testing
  - api
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Test all FastAPI endpoints with TestClient for funds and stocks.

**Note:** This task depends on "Complete API repository tests" being done first.

**Create:** `/workspace/projects/stock-alerting/backend/api/tests/test_endpoints.py`

**Test actual HTTP endpoints with FastAPI TestClient:**
- GET /funds - list all funds
- GET /funds/{id} - get single fund with stocks
- POST /funds - create fund with stocks
- PUT /funds/{id} - update fund
- DELETE /funds/{id} - delete fund
- POST /funds/{id}/stocks - add stock
- PUT /funds/{id}/stocks/{stock_id} - update stock
- DELETE /funds/{id}/stocks/{stock_id} - remove stock
- GET /stocks/search?q=... - stock search
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All 8 fund endpoints tested
- [ ] #2 Stock search endpoint tested
- [ ] #3 HTTP status codes verified
- [ ] #4 Response schemas validated
<!-- AC:END -->
