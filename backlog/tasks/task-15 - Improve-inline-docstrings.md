---
id: TASK-15
title: Improve inline docstrings
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
Update docstrings in key files to improve code documentation.

**Files needing better docstrings:**
- `/workspace/projects/stock-alerting/backend/shared/src/shared/db/models/asset.py`
  - Document asset_type field values
  - Explain base_prum and historical tracking
  - Document backward compatibility properties
- `/workspace/projects/stock-alerting/backend/shared/src/shared/db/repositories/transaction.py`
  - Document PRUM calculation formula in detail
  - Add usage examples in docstrings
- `/workspace/projects/stock-alerting/backend/api/src/services/utils.py`
  - Document fund_table_to_pydantic() transformation logic
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 asset.py docstrings improved with asset_type values
- [ ] #2 transaction.py has PRUM formula documented
- [ ] #3 utils.py transformation logic documented
- [ ] #4 Usage examples added where appropriate
<!-- AC:END -->
