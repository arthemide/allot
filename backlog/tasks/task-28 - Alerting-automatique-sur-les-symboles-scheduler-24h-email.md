---
id: TASK-28
title: Alerting automatique sur les symboles (scheduler 24h + email)
status: In Progress
assignee:
  - '@claude'
created_date: '2026-02-15 22:09'
updated_date: '2026-05-18 09:54'
labels:
  - feature
  - frontend
  - backend
  - alerting
  - scheduler
dependencies: []
references:
  - front/src/lib/components/ConfigManager.svelte
  - front/src/lib/services/api-calls.ts
  - front/src/lib/types/config.ts
  - backend/api/src/routes/funds.py
  - backend/api/src/services/utils.py
  - backend/bot/dca/email_notifier.py
  - backend/api/src/models/pydantic/schema.py
  - backend/api/src/main.py
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ajouter un système d'alerting **automatique** qui vérifie toutes les 24h si un stock dépasse ses seuils configurés (Arbitration Threshold et Alert Threshold), dans les deux directions (positif et négatif), et envoie un email automatiquement si des alertes sont détectées. Aucune intervention manuelle nécessaire.

## Règles d'alertes

**Arbitration Threshold** : alerte quand `|current_repartition - target_repartition| > arbitration_threshold`
- Positif → sur-pondéré (over-weight)
- Négatif → sous-pondéré (under-weight)

**Alert Threshold (threshold_to_alert)** : alerte quand `|gain_loss_percentage| > threshold_to_alert`
- Positif → gain significatif
- Négatif → perte significative

## Implémentation

### Backend

1. **Extraire EmailNotifier dans `shared`**
   - Créer `backend/shared/src/shared/email_notifier.py` avec la classe générique
   - Modifier `backend/bot/dca/email_notifier.py` pour importer depuis shared et créer `DCAEmailNotifier` en sous-classe

2. **Créer le service d'alertes** (`backend/api/src/services/alerts.py`)
   - `check_stock_alerts(stock)` : calcule les alertes pour un stock
   - `check_fund_alerts(fund)` : boucle sur tous les stocks
   - `check_all_funds_alerts()` : parcourt TOUS les fonds et collecte les alertes
   - `send_alert_email(fund, alerts)` : formate et envoie l'email récapitulatif

3. **Scheduler automatique (toutes les 24h)**
   - Utiliser `APScheduler` intégré à FastAPI pour lancer un job périodique
   - Le job parcourt tous les fonds, vérifie les seuils de chaque stock, et envoie un email récapitulatif automatiquement si des alertes sont détectées
   - Configurable via env var `ALERT_CHECK_INTERVAL_HOURS` (défaut: 24)
   - Log chaque exécution du scheduler
   - Démarrage automatique au lancement de l'API

4. **Endpoint manuel (optionnel, pour debug/test)**
   - `POST /funds/{fund_id}/check-alerts` pour déclencher une vérification manuelle
   - Retourne `{ fund_id, fund_name, alerts_count, alerts: [...], email_sent: bool }`

### Frontend

5. **Indicateurs visuels dans ConfigManager.svelte**
   - Fonction helper `getAlertStatus(stock)` → `{ arbitration: 'over'|'under'|null, gainLoss: 'positive'|'negative'|null }`
   - Colonne "Alerts" dans le tableau avec badges Tailwind (orange/bleu pour arbitration, vert/rouge pour gain/loss)
   - Dans la ligne expanded, marquer les seuils dépassés avec couleur + "(BREACHED)"

## Pas de migration DB nécessaire
Toutes les données sont déjà présentes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Un scheduler tourne automatiquement toutes les 24h et vérifie les seuils de tous les fonds sans intervention
- [x] #2 Un email récapitulatif est envoyé automatiquement quand des alertes sont détectées
- [x] #3 L'intervalle est configurable via env var ALERT_CHECK_INTERVAL_HOURS (défaut 24)
- [x] #4 Les badges visuels s'affichent dans le tableau quand un stock dépasse son arbitration_threshold (over-weight orange / under-weight bleu)
- [x] #5 Les badges visuels s'affichent quand gain_loss_percentage dépasse threshold_to_alert (gain vert / loss rouge)
- [x] #6 La ligne expanded montre les seuils dépassés avec (BREACHED)
- [x] #7 Le scheduler démarre automatiquement au lancement de l'API
- [x] #8 L'endpoint POST /funds/{id}/check-alerts permet une vérification manuelle à la demande
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Plan

1. **Shared EmailNotifier**: extract generic `EmailNotifier(subject_prefix)` to `backend/shared/src/shared/email_notifier.py`. Refactor `backend/bot/dca/email_notifier.py` so `EmailNotifier` becomes a subclass that fixes prefix to `[DCA Bot]` (preserves existing imports + tests).
2. **Alert service** (`backend/api/src/services/alerts.py`): `Alert` pydantic model + `check_stock_alerts`, `check_fund_alerts`, `check_all_funds_alerts`, `send_alert_email`, `run_alert_check` orchestrator. Rules:
   - arbitration: `abs(current - target) > arbitration_threshold` → over (diff>0) / under (diff<0)
   - gain/loss: `abs(gain_loss_percentage) > threshold_to_alert` → gain (positive) / loss (negative)
3. **API EmailNotifier** (`backend/api/src/services/email_notifier.py`): `AlertEmailNotifier` subclass with prefix `[Stock Alerting]` + singleton.
4. **Scheduler**: add `apscheduler` to `backend/api/pyproject.toml`; wire `AsyncIOScheduler` via FastAPI lifespan in `main.py`; `ALERT_CHECK_INTERVAL_HOURS` env var (default 24); run job in `asyncio.to_thread`.
5. **Manual endpoint**: `POST /funds/{fund_id}/check-alerts` returns `{fund_id, fund_name, alerts_count, alerts, email_sent}`.
6. **Frontend** (`ConfigManager.svelte`): `getAlertStatus(stock)` helper, new "Alerts" column with Tailwind badges (orange over / blue under / green gain / red loss), and `(BREACHED)` markers + colored values in the expanded row. Update colspan 7→8.

No DB migration needed.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation complete. Generic EmailNotifier(subject_prefix) extracted to backend/shared/src/shared/email_notifier.py; dca.email_notifier.EmailNotifier is now a subclass (existing imports/tests preserved; SMTP patch path updated to shared.email_notifier.smtplib.SMTP). AlertEmailNotifier singleton in backend/api/src/services/email_notifier.py. Alert service in backend/api/src/services/alerts.py (Alert pydantic model + check_stock_alerts/check_fund_alerts/check_all_funds_alerts/send_alert_email/run_alert_check). APScheduler AsyncIOScheduler wired via FastAPI lifespan in main.py; ALERT_CHECK_INTERVAL_HOURS env var (default 24); job runs run_alert_check via asyncio.to_thread. Manual endpoint POST /funds/{fund_id}/check-alerts returns {fund_id, fund_name, alerts_count, alerts, email_sent} (verified registered). apscheduler>=3.10.4 added to api/pyproject.toml. ConfigManager.svelte: getAlertStatus() helper, new Alerts column with orange/blue/green/red badges, expanded row marks breached fields with (BREACHED) + colored values, colspan 7->8. Tests: bot email_notifier 11/11, api 77/77, shared 38/38 all pass. One pre-existing unrelated test_config env leak failure remains.
<!-- SECTION:NOTES:END -->
