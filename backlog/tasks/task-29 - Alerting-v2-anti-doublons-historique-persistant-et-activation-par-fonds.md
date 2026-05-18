---
id: TASK-29
title: 'Alerting v2: anti-doublons, historique persistant, et activation par fonds'
status: To Do
assignee: []
created_date: '2026-05-18 10:18'
labels:
  - feature
  - backend
  - frontend
  - alerting
  - follow-up
dependencies:
  - TASK-28
references:
  - backend/api/src/services/alerts.py
  - backend/api/src/services/email_notifier.py
  - backend/api/src/main.py
  - backend/shared/src/shared/db/models/fund.py
  - front/src/lib/components/ConfigManager.svelte
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Suite de TASK-28. Une fois l'alerting de base en place, trois manques importants à adresser ensemble car ils touchent le même modèle de données.

## Contexte / problèmes

1. **Anti-doublons** : aujourd'hui le scheduler envoie un email à chaque exécution tant qu'une alerte est active. Sur un seuil dépassé pendant 3 jours = 3 emails identiques. Il faut un état "déjà notifié" par alerte logique (clé : fund_id + stock_id + kind + direction).
2. **Historique** : aucune trace persistante des alertes émises (juste loguru + l'email envoyé). Empêche de répondre à "depuis quand AAPL est en gain ?" ou de tracer une régression.
3. **Activation par fonds (ou global)** : un utilisateur qui ne veut pas spammer pour un fonds expérimental ne peut pas le désactiver. Besoin d'un flag `alerting_enabled` sur `FundTable` (et idéalement `ALERTING_ENABLED` global comme kill switch).

## Implémentation suggérée

### Backend

- **Migration** : 
  - `FundTable.alerting_enabled: bool = True` (default true pour compat)
  - Nouvelle table `AlertEventTable` : `id`, `fund_id`, `asset_id`, `kind` (arbitration|gain_loss), `direction`, `value`, `threshold`, `triggered_at`, `resolved_at: datetime | None`, `notified_at: datetime | None`.
- **Anti-doublons** : dans `run_alert_check`, avant d'envoyer, chercher une `AlertEventTable` active (resolved_at IS NULL) avec la même clé logique. Si elle existe et a déjà été notifiée dans les < N heures (ex: 24h, configurable), skip. Sinon insert / update `notified_at`.
- **Résolution automatique** : si une alerte précédemment active n'est plus détectée, marquer `resolved_at = now`. Optionnel : email "résolu".
- **Filtre activation** : `check_all_funds_alerts()` skip les fonds avec `alerting_enabled=False`. Kill switch global via env var `ALERTING_ENABLED=false`.
- **Endpoints** :
  - `PATCH /funds/{id}` (existant) accepte `alerting_enabled`.
  - `GET /funds/{id}/alert-history?limit=50` pour consulter l'historique.

### Frontend

- Toggle "Enable alerts" dans le header du fond dans `ConfigManager.svelte`.
- Onglet ou modal "Alert history" listant les `AlertEventTable` (triggered_at, resolved_at, kind, direction, valeur).
- Petit indicateur visuel quand l'alerting est désactivé sur un fonds (badge gris dans la sidebar).

## Dépendances
- Bloquée par TASK-28 (qui pose les bases du scheduler et de la détection).

## Notes
- L'antidoublons doit être configurable : env var `ALERT_RENOTIFY_AFTER_HOURS` (défaut 24).
- Veiller à ce que `run_alert_check` reste idempotent et résilient aux exceptions DB (try/except par fonds).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Un flag `alerting_enabled` par fonds permet de désactiver l'alerting pour un fonds donné sans affecter les autres
- [ ] #2 Un kill switch global ALERTING_ENABLED=false désactive le scheduler entièrement
- [ ] #3 Une alerte qui reste active ne déclenche pas d'email à chaque cycle: re-notification configurable via ALERT_RENOTIFY_AFTER_HOURS (défaut 24h)
- [ ] #4 Les alertes émises sont persistées dans une table AlertEventTable avec triggered_at / resolved_at / notified_at
- [ ] #5 Quand une alerte précédemment active n'est plus détectée, son resolved_at est rempli automatiquement
- [ ] #6 Endpoint GET /funds/{id}/alert-history retourne l'historique paginé
- [ ] #7 Toggle visuel dans ConfigManager pour activer/désactiver l'alerting d'un fonds
- [ ] #8 Une vue (modal ou onglet) affiche l'historique d'alertes d'un fonds
- [ ] #9 Migration DB ajoutée et testée (alembic ou équivalent)
<!-- AC:END -->
