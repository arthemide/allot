---
id: TASK-17
title: Ajouter validation d'entrée avec Pydantic dans les entités
status: To Do
assignee: []
created_date: '2026-01-23 09:45'
labels:
  - validation
  - quality
  - security
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Renforcer la validation des données à l'entrée du domaine:
- Utiliser Pydantic pour les DTOs API (déjà fait partiellement)
- Ajouter validation dans les constructeurs d'entités
- Créer des factory methods pour la création d'entités valides

Exemples de validations manquantes:
- shares_number >= 0
- current_repartition entre 0 et 100
- symbol format valide (majuscules, longueur)
- prix et coûts positifs
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Validation exhaustive dans entités
- [ ] #2 Messages d'erreur clairs
- [ ] #3 Tests pour tous les cas limites
- [ ] #4 Impossible de créer une entité invalide
<!-- AC:END -->
