---
id: TASK-2
title: Extract yfinance utilities from old code
status: To Do
assignee: []
created_date: '2026-01-16 10:15'
labels:
  - refactoring
  - api
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract Stock.get_stock_price(), get_long_name(), and search_symbol() from src/old/stock.py into a new yfinance_utils.py module to remove legacy code dependencies.

**Current Dependencies in src/old/:**
1. Stock.get_stock_price(symbol) - used in services/utils.py for live prices
2. Stock.get_long_name(symbol) - used in services/stock.py, migration.py
3. Stock.search_symbol(query) - used in routes/stocks.py for /stocks/search endpoint
4. Fund class - only used in archived tests

**Create:** `/workspace/projects/stock-alerting/backend/api/src/services/yfinance_utils.py`

Extract these functions:
- get_stock_price(symbol: str) -> Optional[float]
- get_long_name(symbol: str) -> Optional[str]
- search_symbol(query: str, max_results: int = 5) -> List[Dict]
- _get_history_metadata(symbol: str) -> Optional[Dict]

**Files to update imports:**
- routes/stocks.py (line 5)
- services/stock.py (line 7)
- services/utils.py (line 6)
- migration.py (line 3)

**Add tests** in `tests/services/test_yfinance_utils.py` to cover all 4 functions.

<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 New yfinance_utils.py created with 4 functions
- [ ] #2 All imports updated in 4 files
- [ ] #3 Tests pass after refactoring
- [ ] #4 Stock search endpoint works correctly
- [ ] #5 src/old/ folder deleted
<!-- AC:END -->
