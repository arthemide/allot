---
id: TASK-2
title: Extract yfinance utilities from old code
status: Done
assignee: []
created_date: '2026-01-16 10:15'
updated_date: '2026-01-23 19:05'
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
- [x] #1 New yfinance_utils.py created with 4 functions
- [x] #2 All imports updated in 4 files
- [x] #3 Tests pass after refactoring
- [x] #4 Stock search endpoint works correctly
- [x] #5 src/old/ folder deleted
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Terminé le 23/01/2026:

- Créé api/src/services/yfinance_utils.py avec get_stock_price(), get_long_name(), search_symbol()

- Mis à jour imports dans routes/stocks.py, services/stock.py, services/utils.py, migration.py

- Supprimé api/src/old/ (classes Fund et Stock legacy)

- Supprimé tests legacy: test_fund.py, test_stock.py, test_utils.py, test_server.py, server.py, utils.py
<!-- SECTION:NOTES:END -->
