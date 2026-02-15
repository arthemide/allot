---
id: TASK-27
title: 'Page /bot : Visualisation des asset_transactions avec graphiques Chart.js'
status: To Do
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
## Objectif

Creer une page `/bot` dans le frontend SvelteKit pour afficher les transactions (table `asset_transactions`) via graphiques Chart.js et tableau. Transactions enregistrees par le bot DCA dans PostgreSQL, actuellement invisibles dans l'interface.

## Contexte technique

### Modele `asset_transactions` (PostgreSQL)
Defini dans `backend/shared/src/shared/db/models/transaction.py` (AssetTransactionTable) :
- `id` (PK), `asset_id` (FK→stocks.id), `transaction_type` ('buy'/'sell'/'dividend')
- `timestamp`, `quantity` (Numeric 20,10), `price` (Numeric 20,10), `total_cost` (Numeric 20,10)
- `order_id` (nullable, ref externe Binance), `created_at`
- Index `idx_asset_timestamp` sur (asset_id, timestamp)

### Relations
- `AssetTable` (stocks) → `transactions` (one-to-many), chaque asset a symbol/name/asset_type
- Assets appartiennent a un `FundTable` via fund_id

### Repository existant (`backend/shared/src/shared/db/repositories/transaction.py`)
- `get_recent_transactions(symbol, asset_type, limit)`, `get_asset_statistics()`, `calculate_prum()`

### Stack frontend
SvelteKit 2.48/Svelte 5, Bits UI, TailwindCSS 4, Lucide. Pas de lib graphique installee.

### API existante (FastAPI sur :8000)
Routes : `/funds`, `/stocks/search`. Aucune route transactions.

---

## PARTIE 1 : Backend

### 1.1 Schema Pydantic (`backend/api/src/models/pydantic/schema.py`)
Ajouter `TransactionSchema(BaseModel)` avec : id, asset_id, asset_symbol, asset_name, transaction_type, timestamp, quantity, price, total_cost, order_id, created_at.

### 1.2 Service (`backend/api/src/services/transaction.py` - CREER)
`TransactionService.get_all(fund_id?, asset_id?, limit=100)` :
- Join AssetTransactionTable + AssetTable
- Filtres optionnels fund_id et asset_id
- Tri par timestamp desc, limit
- Enrichir avec asset_symbol/name

### 1.3 Route (`backend/api/src/routes/transactions.py` - CREER)
`GET /transactions?fund_id=X&asset_id=Y&limit=100` → List[TransactionSchema]
Enregistrer dans `routes/__init__.py`.

## PARTIE 2 : Frontend

### 2.1 Installer `chart.js` (npm install)

### 2.2 Type (`front/src/lib/types/config.ts`)
Ajouter interface `AssetTransaction` (id, asset_id, asset_symbol, asset_name, transaction_type, timestamp, quantity, price, total_cost, order_id).

### 2.3 API call (`front/src/lib/services/api-calls.ts`)
Ajouter `getTransactions(params?)` avec URLSearchParams pour fund_id/asset_id/limit.

### 2.4 TransactionTimeline.svelte (CREER)
Bar chart : axe X=temps, Y=total_cost. Barres vertes (buy), rouges (sell). Tooltip avec details. $effect pour lifecycle Chart.js.

### 2.5 CumulativeInvestment.svelte (CREER)
Line chart : axe X=temps, Y=cumul progressif. buy→cumul+=total_cost, sell→cumul-=total_cost. Une ligne/couleur par asset_symbol. Area fill gradient.

### 2.6 Page /bot (`front/src/routes/bot/+page.svelte` - CREER)
- Selecteur de fonds en haut
- Graphique investissement cumule (line)
- Graphique timeline transactions (bar)
- Tableau : Date, Asset, Type (badge colore), Qty, Prix, Total
- Etats : loading, vide, erreur
- Composants UI existants : Card, Table

### 2.7 Navigation (`front/src/routes/+layout.svelte`)
Barre nav minimaliste : lien "Portfolio" (/) + "Bot" (/bot). Toggle dark mode a droite.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GET /transactions fonctionne avec filtres fund_id, asset_id, limit et retourne transactions enrichies (symbol, name)
- [ ] #2 Chart.js installe dans le frontend
- [ ] #3 Composant TransactionTimeline : bar chart barres vertes (buy) / rouges (sell) sur axe temporel
- [ ] #4 Composant CumulativeInvestment : line chart courbe cumulative par asset
- [ ] #5 Page /bot avec selecteur de fonds, 2 graphiques, tableau de transactions
- [ ] #6 Navigation dans le layout (liens Portfolio et Bot)
- [ ] #7 Graphiques responsives et lisibles en dark mode
- [ ] #8 Etats loading, vide et erreur geres
<!-- AC:END -->
