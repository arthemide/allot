---
id: TASK-28
title: Alerting automatique sur les symboles (scheduler 24h + email)
status: To Do
assignee: []
created_date: '2026-02-15 22:09'
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
- [ ] #1 Un scheduler tourne automatiquement toutes les 24h et vérifie les seuils de tous les fonds sans intervention
- [ ] #2 Un email récapitulatif est envoyé automatiquement quand des alertes sont détectées
- [ ] #3 L'intervalle est configurable via env var ALERT_CHECK_INTERVAL_HOURS (défaut 24)
- [ ] #4 Les badges visuels s'affichent dans le tableau quand un stock dépasse son arbitration_threshold (over-weight orange / under-weight bleu)
- [ ] #5 Les badges visuels s'affichent quand gain_loss_percentage dépasse threshold_to_alert (gain vert / loss rouge)
- [ ] #6 La ligne expanded montre les seuils dépassés avec (BREACHED)
- [ ] #7 Le scheduler démarre automatiquement au lancement de l'API
- [ ] #8 L'endpoint POST /funds/{id}/check-alerts permet une vérification manuelle à la demande
<!-- AC:END -->
