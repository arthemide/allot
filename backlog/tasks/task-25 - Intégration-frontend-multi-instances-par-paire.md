---
id: TASK-25
title: Intégration frontend + multi-instances par paire
status: To Do
assignee: []
created_date: '2026-02-02 13:43'
labels:
  - frontend
  - backend
  - api
  - multi-instance
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Relier le bot DCA au frontend et permettre de gerer plusieurs instances de bot (une par paire de trading) depuis l'interface. Actuellement le bot est configure via variables d'environnement et ne supporte qu'une seule paire.
<!-- SECTION:DESCRIPTION:END -->

## Contexte technique actuel

### Architecture du bot (`backend/bot/dca/`)
- **config.py** : Config via env vars (`DCAConfig` Pydantic model) - une seule instance
- **main.py** : Entry point CLI (`--test`, `--once`, `--now`)
- **scheduler.py** : `DCAScheduler` avec APScheduler `BlockingScheduler` + `CronTrigger`
- **dca_executor.py** : Logique metier (momentum analysis, PRUM, balance check, market order Binance)
- **purchase_tracker.py** : Enregistre les transactions via `TransactionRepository` (package shared)
- **binance_client.py** : Client API Binance REST (spot trading, earn, klines)

### Points cles
- Le bot tourne en Docker (`docker-compose.yaml`, profile `dca`, image `dca-bot`)
- Config actuelle : 1 seule paire (ETHUSDC), 1 montant, 1 schedule via `.env`
- Transactions deja stockees en DB (table `asset_transactions`, modele `AssetTransactionTable`)
- Le `DCAConfig` Pydantic contient tous les champs parametrables : `symbol`, `base_asset`, `quote_asset`, `amount_usdc`, `days_of_month`, `execution_hour`/`minute`, `prum_buffer`, `momentum_periods`, `kline_interval`, `base_prum`, `base_quantity`
- Le scheduler utilise `BlockingScheduler` (un seul job, bloquant)

### Limites actuelles
- Pas de table DB pour stocker les configs d'instances
- Pas d'API REST pour piloter le bot
- Pas de support multi-instances (1 fichier .env = 1 paire = 1 process Docker)
- Pas d'UI frontend pour le bot

---

## PARTIE 1 : Modele DB — Table `bot_instances`

**Fichier a creer** : `backend/shared/src/shared/db/models/bot_instance.py`

### Schema de la table

| Colonne | Type | Contrainte | Description |
|---------|------|-----------|-------------|
| `id` | Integer | PK, index | Identifiant unique |
| `asset_id` | Integer | FK→stocks.id, nullable | Lien vers l'asset (cree automatiquement) |
| `symbol` | String(20) | NOT NULL | Paire de trading, ex: `ETHUSDC` |
| `base_asset` | String(20) | NOT NULL | Asset achete, ex: `ETH` |
| `quote_asset` | String(20) | NOT NULL | Asset depense, ex: `USDC` |
| `amount` | Numeric(20,10) | NOT NULL | Montant par achat en quote_asset |
| `days_of_month` | String(100) | NOT NULL | Jours d'execution, ex: `1,15` |
| `execution_hour` | Integer | default 10 | Heure d'execution (0-23) |
| `execution_minute` | Integer | default 0 | Minute d'execution (0-59) |
| `prum_buffer` | Float | default 0.03 | Seuil au-dessus du PRUM pour skip (3%) |
| `momentum_periods` | Integer | default 2 | Periodes historiques pour analyse momentum |
| `kline_interval` | String(10) | default `1w` | Intervalle klines (`1d`, `3d`, `1w`, `1M`) |
| `base_prum` | Numeric(20,10) | nullable | Prix moyen historique (pre-bot) |
| `base_quantity` | Numeric(20,10) | default 0 | Quantite historique (pre-bot) |
| `status` | String(20) | default `active` | `active` / `paused` / `stopped` |
| `last_execution_at` | DateTime(tz) | nullable | Date de derniere execution |
| `last_result` | String(50) | nullable | `success` / `skipped` / `error` |
| `last_error` | Text | nullable | Message d'erreur si echec |
| `created_at` | DateTime(tz) | server_default now | Date de creation |
| `updated_at` | DateTime(tz) | onupdate now | Date de derniere modification |

Relation : `asset = relationship("AssetTable")`.

**Migration Alembic** a generer avec `alembic revision --autogenerate -m "add_bot_instances"`.

---

## PARTIE 2 : Backend API

### 2.1 Schemas Pydantic

**Fichier a modifier** : `backend/api/src/models/pydantic/schema.py`

3 schemas a ajouter :

**`BotInstanceSchema`** (reponse API) : tous les champs de la table.

**`BotInstanceCreate`** (creation) : `symbol` (req), `base_asset` (req), `quote_asset` (req), `amount` (req), `days_of_month` (def `"1,15"`), `execution_hour` (def 10), `execution_minute` (def 0), `prum_buffer` (def 0.03), `momentum_periods` (def 2), `kline_interval` (def `"1w"`), `base_prum` (opt), `base_quantity` (def 0).

**`BotInstanceUpdate`** (mise a jour partielle) : tous les champs optionnels sauf symbol/base_asset/quote_asset (la paire ne change pas apres creation).

### 2.2 Service

**Fichier a creer** : `backend/api/src/services/bot_instance.py`

Suivre le meme pattern que `FundService` (`backend/api/src/services/fund.py`) :

| Methode | Description |
|---------|-------------|
| `get_all()` | Liste toutes les instances, retourne `List[BotInstanceSchema]` |
| `get_by_id(id: int)` | Detail d'une instance, 404 si non trouvee |
| `create(data: BotInstanceCreate)` | Cree l'instance + cree/lie l'asset via `TransactionRepository.get_or_create_asset()` |
| `update(id: int, data: BotInstanceUpdate)` | Met a jour les champs fournis |
| `delete(id: int)` | Supprime l'instance (ne supprime PAS les transactions liees) |
| `set_status(id: int, status: str)` | Change le statut (`active` ou `paused`) |

### 2.3 Routes API

**Fichier a creer** : `backend/api/src/routes/bot.py`

```
router = APIRouter(prefix="/bot", tags=["bot"])
```

| Endpoint | Methode | Corps/Params | Reponse | Description |
|----------|---------|-------------|---------|-------------|
| `/bot/instances` | GET | - | `List[BotInstanceSchema]` | Liste toutes les instances |
| `/bot/instances` | POST | `BotInstanceCreate` | `BotInstanceSchema` (201) | Cree une instance |
| `/bot/instances/{id}` | GET | - | `BotInstanceSchema` | Detail d'une instance |
| `/bot/instances/{id}` | PUT | `BotInstanceUpdate` | `BotInstanceSchema` | Met a jour la config |
| `/bot/instances/{id}` | DELETE | - | `{"deleted": true}` | Supprime l'instance |
| `/bot/instances/{id}/pause` | POST | - | `BotInstanceSchema` | Passe en `paused` |
| `/bot/instances/{id}/resume` | POST | - | `BotInstanceSchema` | Passe en `active` |

**Fichier a modifier** : `backend/api/src/routes/__init__.py` — importer et enregistrer `bot_router`.

---

## PARTIE 3 : Adaptation du bot pour multi-instances

### 3.1 Chargement config depuis DB

**Fichier a modifier** : `backend/bot/dca/config.py`

Ajouter une methode de classe :
```python
@classmethod
def from_bot_instance(cls, instance: BotInstanceTable) -> "DCAConfig":
    """Cree un DCAConfig depuis une ligne de la table bot_instances."""
    return DCAConfig(
        amount_usdc=float(instance.amount),
        symbol=instance.symbol,
        base_asset=instance.base_asset,
        quote_asset=instance.quote_asset,
        base_prum=float(instance.base_prum) if instance.base_prum else None,
        base_quantity=float(instance.base_quantity) if instance.base_quantity else 0.0,
        days_of_month=instance.days_of_month,
        execution_hour=instance.execution_hour,
        execution_minute=instance.execution_minute,
        prum_buffer=instance.prum_buffer,
        momentum_periods=instance.momentum_periods,
        kline_interval=instance.kline_interval,
    )
```

**Logique de fallback** : si aucune instance en DB → utiliser les env vars (comportement actuel).

### 3.2 Multi-instance scheduler

**Fichier a modifier** : `backend/bot/dca/scheduler.py`

Changements :
1. Remplacer `BlockingScheduler` par `BackgroundScheduler` (non-bloquant)
2. Au demarrage :
   - Lire toutes les instances `status='active'` depuis la table `bot_instances`
   - Pour chaque instance : creer un `DCAConfig` + `DCAExecutor` + job APScheduler
   - Job ID = `f"dca_instance_{instance.id}"`
3. Ajouter un **job de synchronisation** (toutes les 60 secondes) :
   - Re-lire les instances depuis la DB
   - Comparer avec les jobs actuels
   - Ajouter les jobs pour les nouvelles instances actives
   - Retirer les jobs pour les instances pausees/supprimees
   - Re-creer les jobs dont la config a change (schedule different)
4. Garder le main thread vivant avec `signal.pause()` ou boucle `while True: sleep(1)`

### 3.3 Mise a jour du statut apres execution

**Fichier a modifier** : `backend/bot/dca/dca_executor.py`

Apres chaque execution (`execute_dca_purchase`), mettre a jour la table `bot_instances` :
- `last_execution_at` = maintenant
- `last_result` = `"success"` / `"skipped"` / `"error"`
- `last_error` = message d'erreur (ou NULL si succes)

Ajouter un champ `instance_id: Optional[int]` au constructeur `DCAExecutor` pour identifier l'instance.

---

## PARTIE 4 : Frontend

### 4.1 Types TypeScript

**Fichier a modifier** : `front/src/lib/types/config.ts`

```typescript
export interface BotInstance {
    id: number;
    symbol: string;
    base_asset: string;
    quote_asset: string;
    amount: number;
    days_of_month: string;
    execution_hour: number;
    execution_minute: number;
    prum_buffer: number;
    momentum_periods: number;
    kline_interval: string;
    base_prum: number | null;
    base_quantity: number;
    status: 'active' | 'paused' | 'stopped';
    last_execution_at: string | null;
    last_result: 'success' | 'skipped' | 'error' | null;
    last_error: string | null;
    created_at: string | null;
}

export interface BotInstanceCreate {
    symbol: string;
    base_asset: string;
    quote_asset: string;
    amount: number;
    days_of_month?: string;
    execution_hour?: number;
    execution_minute?: number;
    prum_buffer?: number;
    momentum_periods?: number;
    kline_interval?: string;
    base_prum?: number;
    base_quantity?: number;
}
```

### 4.2 API calls

**Fichier a modifier** : `front/src/lib/services/api-calls.ts`

Ajouter un objet `botApi` (separe de `configApi`) :

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `getInstances()` | GET `/bot/instances` | Liste les instances |
| `getInstance(id)` | GET `/bot/instances/{id}` | Detail |
| `createInstance(data)` | POST `/bot/instances` | Creation |
| `updateInstance(id, data)` | PUT `/bot/instances/{id}` | Mise a jour |
| `deleteInstance(id)` | DELETE `/bot/instances/{id}` | Suppression |
| `pauseInstance(id)` | POST `/bot/instances/{id}/pause` | Pause |
| `resumeInstance(id)` | POST `/bot/instances/{id}/resume` | Resume |

### 4.3 UI — Section instances sur page `/bot`

**Fichier a modifier/creer** : `front/src/routes/bot/+page.svelte`

La page `/bot` (creee par TASK-27 pour les graphiques) integre une section de gestion des instances :

**Layout de la section :**
```
┌─────────────────────────────────────────────────────────┐
│ DCA Instances                    [+ New Instance]       │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🟢 ETHUSDC        30 USDC      1er & 15 @ 10:02   │ │
│ │ Derniere exec: 2026-02-01 ✅   PRUM: 2450.00      │ │
│ │                     [Pause] [Edit] [Delete]        │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ 🟡 BTCUSDC        50 USDC      1er @ 09:00        │ │
│ │ Derniere exec: 2026-01-15 ⏸️   Status: paused     │ │
│ │                     [Resume] [Edit] [Delete]       │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Composants a utiliser** : Card, Button, Table (existants dans `ui/`). Dialog pour le formulaire de creation/edition (pattern StockForm existant).

**Formulaire de creation** (champs) :
- Symbol (ex: ETHUSDC) — input text requis
- Base asset (ex: ETH) — input text requis
- Quote asset (ex: USDC) — input text requis
- Montant par achat — input number requis
- Jours d'execution — input text (ex: "1,15")
- Heure/minute — 2 inputs number
- Section "Strategie avancee" (collapse) : prum_buffer, momentum_periods, kline_interval
- Section "Historique" (collapse) : base_prum, base_quantity

**Etats a gerer** : loading, empty (aucune instance), error.

---

## Fichiers impactes (resume)

| Fichier | Action |
|---------|--------|
| `backend/shared/src/shared/db/models/bot_instance.py` | CREER |
| `backend/api/alembic/versions/xxx_add_bot_instances.py` | CREER (migration) |
| `backend/api/src/models/pydantic/schema.py` | MODIFIER (3 schemas) |
| `backend/api/src/services/bot_instance.py` | CREER |
| `backend/api/src/routes/bot.py` | CREER |
| `backend/api/src/routes/__init__.py` | MODIFIER (import bot_router) |
| `backend/bot/dca/config.py` | MODIFIER (from_bot_instance) |
| `backend/bot/dca/scheduler.py` | MODIFIER (BackgroundScheduler + sync) |
| `backend/bot/dca/dca_executor.py` | MODIFIER (update status + instance_id) |
| `front/src/lib/types/config.ts` | MODIFIER (BotInstance types) |
| `front/src/lib/services/api-calls.ts` | MODIFIER (botApi) |
| `front/src/routes/bot/+page.svelte` | MODIFIER (section instances) |

## Verification

1. **Migration** : `alembic upgrade head` — la table `bot_instances` existe
2. **API** : `curl POST /bot/instances` pour creer une instance, verifier en `GET`
3. **Pause/Resume** : `POST /bot/instances/1/pause`, verifier que le statut change
4. **Bot** : lancer le bot, verifier qu'il cree des jobs pour les instances actives
5. **Frontend** : naviguer vers `/bot`, creer/editer/pause une instance
6. **Integration** : creer une instance, attendre une execution, verifier `last_execution_at` dans l'UI
