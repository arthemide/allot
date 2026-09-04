# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [0.5.1] - 2026-09-04

### Changed

- move the allocation off dictionaries (#35)

### Fixed

- asset selection and dialog widths (#36)
- truncate long asset labels (#39)

## [0.5.0] - 2026-09-04

### Added

- update favicon and enhance layout with title and navigation link
- envelope cash and calendar feed (#34)

## [0.4.0] - 2026-09-01

### Other

- bump the actions group across 1 directory with 10 updates (#23)
- bump ruff from 0.16.3 to 0.16.4 in the python group across 1 directory (#22)
- bump node from 22-alpine to 26-alpine (#21)
- bump the front group in /front with 8 updates (#24)
- bump @lucide/svelte from 0.561.0 to 1.35.0 in /front (#25)
- bump python from 3.12-slim to 3.14-slim (#20)
- bump vite to 8.2.2 and vite-plugin-svelte to 7.3.0 (#32)

## [0.3.0] - 2026-08-30

### Added

- close the app down enough to put it on a domain (#31)

## [0.2.2] - 2026-08-30

### Other

- cover the routes and the SQLite layer (#30)

## [0.2.0] - 2026-08-29

### Added

- bundle Litestream in the image and fix the healthcheck budget (#28)

## [0.1.0] - 2026-08-29

### Added

- initialize front-end project
- add Docker support and improve logging configuration
- add configuration files for sandbox environment and update Docker setup
- add ui components
- add API calls and db
- change parts to shares in stock model and update related components
- update stock table and related services
- implement stock search functionality with autocomplete feature
- update Dockerfiles and docker-compose for shared package integration
- add documentation and task files for project setup, testing, and architecture
- add claude flow context
- add task descriptions for Value Objects, validation, repository interfaces, domain entities, domain events, Unit of Work, and bounded contexts
- update Dockerfile for DCA bot, add auto-start commands, and enhance Makefile help output
- enhance DCA bot with crash and misfire notifications, add grace period for missed executions, and update Docker configurations
- update task priorities and add implementation notes for various tasks
- implement database health check and retry mechanism across repositories
- make DCA strategy parameters configurable via environment variables
- Enhance API and bot tests with new fixtures and coverage
- add regression tests for transaction accessibility after session closure
- move test cov to more than 80 everywhere
- new tasks
- update Makefile for database backup and restore, add API README, and modify docker-compose for image builds
- make sure a bot visualization page exists (#13)
- add currency handling and unique constraints for stock symbols (#16)
- implement automated stock alerting system with email notifications (#17)
- implement position reconciliation and commission handling in DCA bot
- on-premise deployment with tagged releases and GHCR images (#19)

### Changed

- remove ConfigManager from config page and update layout in main page

### Fixed

- remove popover component and add dark mode
- update Makefile to include migrations in up command
- correct volume name for front-end node modules in shared volumes configuration
- update workflow to use backend directory for caching and dependencies
- ci (#15)
- update repository links in CONTRIBUTING and README files
- lint code

### Other

- update with Python version and switch from poetry to uv
- remove .gitignore file from backups directory

### Refacto

- code structure for improved readability and maintainability
- continue refactoring
- remove old files

