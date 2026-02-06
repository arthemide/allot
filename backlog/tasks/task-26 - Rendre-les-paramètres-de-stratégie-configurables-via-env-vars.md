---
id: TASK-26
title: Rendre les paramètres de stratégie configurables via env vars
status: Done
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

## Implementation Notes

### Implémenté (2026-02-05)

**Nouvelles variables d'environnement:**
- `DCA_PRUM_BUFFER` (default: 0.03) - Buffer au-dessus du PRUM
- `DCA_MOMENTUM_PERIODS` (default: 2) - Nombre de périodes à analyser
- `DCA_KLINE_INTERVAL` (default: 1w) - Intervalle des klines (1d, 3d, 1w, 1M)

**Fichiers modifiés:**
- `config.py`: Ajout des paramètres dans DCAConfig + validation
- `dca_executor.py`: Utilisation des paramètres config au lieu de valeurs hardcodées
- `.env.template`: Documentation des nouvelles variables
