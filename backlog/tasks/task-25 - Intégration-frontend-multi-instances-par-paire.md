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
Relier le bot DCA au frontend existant et aux paires déjà configurées. Permettre de lancer/configurer une nouvelle instance de bot DCA depuis le frontend (bouton "Setup DCA" sur une paire).

- Chaque paire aurait sa propre config (montant, jours, stratégie)
- Le backend expose une API REST pour créer/démarrer/arrêter des instances de bot
- Le frontend affiche l'état de chaque instance (actif, en pause, dernière exécution)
- Stockage des configs d'instances en DB
<!-- SECTION:DESCRIPTION:END -->
