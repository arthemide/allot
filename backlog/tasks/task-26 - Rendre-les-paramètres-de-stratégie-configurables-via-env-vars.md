---
id: TASK-26
title: Rendre les paramètres de stratégie configurables via env vars
status: To Do
assignee: []
created_date: '2026-02-02 13:43'
labels:
  - configuration
  - strategy
  - backend
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Plusieurs paramètres de la stratégie DCA sont actuellement en dur dans le code :

- Buffer PRUM de 3%
- Nombre de périodes analysées (actuellement 2)

Les rendre configurables via variables d'environnement avec des valeurs par défaut sensées. Valider les valeurs au démarrage du bot.
<!-- SECTION:DESCRIPTION:END -->
