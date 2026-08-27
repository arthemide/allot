# Contributing to Allot

Thanks for your interest in contributing! This document explains how to set up the project and the workflow we follow.

## Setup

```bash
git clone https://github.com/arthemide/allot.git
cd allot
make install
```

You need [uv](https://docs.astral.sh/uv/) for the Python side and Node 22 for the front. `make install` runs `uv sync` and `npm ci`.

## Running

```bash
make start        # build the front, serve everything on :8000
make dev-api      # API alone, auto-reload, :8000
make dev-front    # front dev server on :5173 (needs dev-api)
```

## Checks

```bash
make test         # pytest
make lint         # ruff check + svelte-check
make format       # ruff format, then ruff check --fix
```

Run `make lint` and `make test` before pushing; CI runs the same commands.

## Workflow

1. Branch from `main` using a descriptive name:
   - `feat/short-description` — new feature
   - `fix/short-description` — bug fix
   - `docs/short-description` — documentation
   - `refactor/short-description` — refactoring
2. Make your changes and add tests.
3. Run the linter and test suite locally before pushing.
4. Open a pull request against `main` — never push directly to `main`.

## Code conventions

- Keep changes focused and small; one logical change per pull request.
- Follow the existing style of the surrounding code.
- Add or update tests for any behavior change. `src/calc.py` is pure and must stay covered; anything doing I/O belongs in `src/services` or `src/databases`.
- Update documentation when you change user-facing behavior.
- Everything in the repository — code, comments, commits, branches — is written in English. The monthly note rendered by `src/services/note.py` is the one exception: its output is French on purpose.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.

## Pull requests

- Describe what the change does and why.
- Link any related issues (e.g. `Closes #123`).
- Make sure CI passes before requesting review.

## Reporting bugs and requesting features

Open an issue. Please search existing issues first to avoid duplicates.
