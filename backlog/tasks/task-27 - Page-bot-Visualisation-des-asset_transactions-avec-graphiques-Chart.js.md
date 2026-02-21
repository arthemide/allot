---
id: TASK-27
title: 'Page /bot : Visualisation des asset_transactions avec graphiques Chart.js'
status: Done
assignee: []
created_date: '2026-02-14 17:58'
labels:
  - feature
  - frontend
  - backend
  - charts
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## What was built

Page `/bot` in the SvelteKit frontend displaying DCA bot transactions from `asset_transactions` via two Chart.js charts and a detail table.

## Backend

### `GET /transactions?fund_id=&asset_id=&limit=`
Returns `List[TransactionSchema]` (id, asset_id, asset_symbol, asset_name, transaction_type, timestamp, quantity, price, total_cost, order_id, created_at). Joins `AssetTransactionTable` + `AssetTable`, filters by fund_id/asset_id, ordered by timestamp desc.

### `GET /stocks/price-history?symbol=&start=&end=`
Returns `List[PricePoint]` (date, price) fetched via yfinance daily close. Returns `[]` silently for unrecognised symbols (crypto pairs, etc.).

## Frontend

### `CumulativeInvestment.svelte`
Line chart (Chart.js). Single line across all assets. Transactions grouped by ISO date, sorted chronologically. buy → `+= total_cost`, sell → `-= total_cost`. Indigo area fill. Dark mode aware.

### `TransactionTimeline.svelte`
Mixed scatter + line chart (Chart.js, no extra adapter needed). Three datasets:
- **Scatter** — one point per day (average price if multiple tx same day). Green = buy, red = sell.
- **AVCO line** — running average cost basis, recomputed in the frontend from sorted buy transactions, forward-filled, orange dashed.
- **Historical price line** *(optional)* — loaded from `/stocks/price-history`, indigo semi-transparent. Omitted silently if API returns `[]`.

Dates: all timestamps converted to ISO `YYYY-MM-DD`, merged and sorted before building the category axis, formatted with 2-digit year to avoid cross-year collisions.

### Page `/bot`
- Fund selector (top) — filters all data
- **Chart 1**: Cumulative Investment (all assets)
- **Chart 2**: Purchase Price per Transaction & AVCO — with per-pair selector in card header (dropdown only shown when multiple symbols exist, auto-selects first symbol)
- Transaction history table: Date, Asset, Type (coloured badge), Quantity, Price, Total
- States: loading, empty, error — all in English
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GET /transactions works with fund_id, asset_id, limit filters and returns enriched transactions (symbol, name)
- [x] #2 Chart.js installed in the frontend
- [x] #3 TransactionTimeline: scatter points per day + AVCO dashed line + optional historical price line
- [x] #4 CumulativeInvestment: single cumulative line across all assets with area fill
- [x] #5 Page /bot with fund selector, 2 charts, transaction table
- [x] #6 Navigation in layout (Portfolio and Bot links)
- [x] #7 Charts responsive and readable in dark mode
- [x] #8 Loading, empty and error states handled (in English)
- [x] #9 Per-pair filter on the price/AVCO chart
- [x] #10 Historical price fetched from /stocks/price-history, silently omitted if unavailable
<!-- AC:END -->
