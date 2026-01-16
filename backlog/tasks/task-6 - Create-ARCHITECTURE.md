---
id: TASK-6
title: Create ARCHITECTURE.md
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
Comprehensive architectural documentation covering system design, layer separation, and data flow.

**Location:** `/workspace/projects/stock-alerting/ARCHITECTURE.md`

**Do it using Mermaid diagrams where applicable.**

**Content to include:**
- Overall system design diagram
- Three-tier architecture:
  - Frontend (Svelte) → API (FastAPI) → Database (PostgreSQL)
  - Bot (Python) → Shared Package → Database
- Backend structure:
  - API Layer: Routes → Services → Repositories
  - Shared Layer: Models, Repositories, Config
  - Bot Layer: DCA executor, Purchase tracker
- Data flow diagrams
- Unified asset model explanation
- Backward compatibility layer (stocks → assets)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 System design diagram included
- [ ] #2 Three-tier architecture explained
- [ ] #3 Backend layer structure documented
- [ ] #4 Data flow diagrams provided
- [ ] #5 Unified asset model explained
<!-- AC:END -->
