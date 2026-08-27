# Allot

> Per-asset PRUM tracking and a monthly allocation note.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

## Overview

Allot tracks what you hold, what it cost you, and tells you where this month's
money should go.

Positions are never stored. Quantity and PRUM (*prix de revient unitaire
moyen*, the weighted average price paid) are recomputed on every read from the
transactions plus an optional opening position — the holding that predates
tracking. There is no state to keep in sync and no reconciliation step.

Assets are grouped into **envelopes** (PEA, CTO, CRYPTO…). Each envelope
carries its own monthly amount and stands on its own: one envelope never draws
from another. Inside an envelope the amount is split across assets by their
relative weight, modulated by how far the current price sits from the PRUM —
1.5x when the price is more than 10% below it, 0.5x when it is more than 10%
above, 1x in between. The envelope total stays invariant.

## Features

- Per-asset position, PRUM, gain and gain percentage, recomputed from history
- Envelopes with a monthly amount and a per-asset split
- Ticker search, so the exchange suffix (`WPEA.PA`, `VWCE.DE`, `ETH-USD`) does
  not have to be guessed
- Price chart with transaction markers and the step PRUM curve
- A plain-text monthly note, ready to paste into a reminder

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) and Python 3.12+
- Node 22+

No configuration file, no environment variable, no external service: the whole
state lives in a SQLite file at `data/allot.db`, created on first run.

### Installation

```bash
git clone https://github.com/arthemide/stock-alerting.git
cd stock-alerting
make install
```

### Usage

Build the front and serve everything on <http://127.0.0.1:8000>:

```bash
make start
```

For development, run the API and the front dev server side by side:

```bash
make dev-api      # :8000, auto-reload
make dev-front    # :5173, calls the API on :8000 directly
```

Print the monthly note while the app is running:

```bash
make note
```

Run `make` on its own to list every target.

## HTTP API

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/assets` | Every tracked asset with its recomputed position |
| `POST` | `/assets` | Track a new asset, normally picked from the search |
| `GET` | `/assets/search?q=` | Ticker search |
| `GET` | `/assets/summary` | Totals per envelope, converted to EUR |
| `GET`/`PUT`/`DELETE` | `/assets/{symbol}` | Read, edit, or stop tracking |
| `PUT` | `/assets/{symbol}/opening` | Set the holding that predates tracking |
| `GET` | `/assets/{symbol}/chart` | Prices, transactions and the step PRUM |
| `GET`/`PUT`/`DELETE` | `/envelopes` | Envelopes and their monthly amount |
| `GET`/`POST`/`DELETE` | `/transactions` | Buys and sells |
| `GET` | `/note` | The monthly note, as plain text |

Interactive docs are served at `/docs`.

## Layout

```
app.py              entry point: the API, and the built front alongside it
schema.sql          the whole database schema
src/calc.py         pure calculations — no I/O, the only module worth unit-testing
src/services/       positions, allocation, prices, note rendering
src/databases/      SQLite access, plain dicts, no ORM
src/routes/         HTTP surface
front/              SvelteKit front, built statically into front/dist
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
