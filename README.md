# Allot

> Per-asset PRUM tracking and a monthly allocation note.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

## Overview

Allot tracks what you hold, what it cost you, and tells you where this month's money should go.

Positions are never stored. Quantity and PRUM (*prix de revient unitaire moyen*, the weighted average price paid) are recomputed on every read from the transactions plus an optional opening position - the holding that predates tracking. There is no state to keep in sync and no reconciliation step.

Assets are grouped into **envelopes** (PEA, CTO, CRYPTO…). Each envelope carries its own monthly amount and stands on its own: one envelope never draws from another. Inside an envelope the amount is split across assets by their relative weight, modulated by how far the current price sits from the PRUM - 1.5x when the price is more than 10% below it, 0.5x when it is more than 10% above, 1x in between. The envelope total stays invariant.

## Features

- Per-asset position, PRUM, gain and gain percentage, recomputed from history
- Envelopes with a monthly amount and a per-asset split
- Ticker search, so the exchange suffix (`WPEA.PA`, `VWCE.DE`, `ETH-USD`) does not have to be guessed
- Price chart with transaction markers and the step PRUM curve
- A plain-text monthly note, ready to paste into a reminder

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) and Python 3.12+
- Node 22+

Only for developing on it. To just run it, see [Self-hosting](#self-hosting) - Docker is the single requirement there.

No configuration file and no external service: the whole state lives in a SQLite file at `data/allot.db`, created on first run. Three environment variables exist for the container, all optional - `ALLOT_HOST`, `ALLOT_PORT`, `ALLOT_DB_PATH`.

### Installation

```bash
git clone https://github.com/arthemide/allot.git
cd allot
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

## Self-hosting

To run Allot on a machine of your own - a Raspberry Pi, a NAS, a spare box - without installing Python or Node:

```bash
git clone https://github.com/arthemide/allot.git
cd allot
cp .env.example .env
make up
```

`make up` pulls the image published by CI rather than building it, so the machine compiles nothing. The image is built for `linux/amd64`, `linux/arm64` and `linux/arm/v7`.

> A GHCR package is private until it is made public, even on a public repository. If the pull fails with `denied`, open the package's settings on GitHub and switch its visibility once.

It listens on `:8000` and is reachable from the LAN. There is **no authentication**: keep it on a network you trust, or put a reverse proxy with a password in front of it.

The database lives in the `allot-data` Docker volume, so `docker compose down` and an upgrade lose nothing. To build from the checkout instead, for development, use `make up-local`.

### Staying up to date

`ALLOT_VERSION` in `.env` pins what runs, so the running version is readable in a file:

```bash
make update    # pull the pinned version and restart
```

To move to a newer release, set `ALLOT_VERSION` to its tag and run `make update` again; to roll back, set it to the previous tag and do the same. Automating that is deliberately left out of this repository — it depends on your machine, your secrets and your appetite for unattended updates.

### Off-site replication

Set `LITESTREAM_BUCKET` in `.env` and the container replicates the SQLite write-ahead log to S3-compatible object storage continuously, so a lost disk costs seconds of data rather than a day. Leave it empty and the app runs on its own.

[Litestream](https://litestream.io) ships inside the image and supervises the application process, which is the arrangement its documentation recommends: replication is running before the first write, and it stops cleanly with the app. There is no sidecar to start and nothing to install on the host.

`.env.example` targets Scaleway Object Storage; any S3-compatible provider works by changing `LITESTREAM_ENDPOINT` and `LITESTREAM_REGION`.

1. In the Scaleway console, create a bucket (Object Storage) and an API key. The secret key is shown once, at creation.
2. Fill the `LITESTREAM_*` lines in `.env`, then `make up`.
3. `make replication` lists what has been replicated.

Recovery needs no command at all: the entrypoint passes `-restore-if-db-not-exists`, so a container started against an empty volume rebuilds the database from the replica. Moving to a new machine is installing Docker, cloning, writing the same `.env`, and `make up`.

To restore by hand over an existing volume:

```bash
docker compose stop
docker compose run --rm --entrypoint litestream app \
  restore -config /etc/litestream.yml /data/allot.db
docker compose up -d
```

Replication requires WAL mode, which `schema.sql` turns on. It is stored in the database header, so an existing database picks it up on the next start.

## Releases

The version in `pyproject.toml` is the source of truth. Bumping it and merging to `main` is the whole release process: CI writes `CHANGELOG.md`, tags `vX.Y.Z`, publishes `ghcr.io/arthemide/allot` with a provenance attestation, and opens a GitHub Release. See [CONTRIBUTING.md](CONTRIBUTING.md).

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
src/calc.py         pure calculations - no I/O, the only module worth unit-testing
src/services/       positions, allocation, prices, note rendering
src/databases/      SQLite access, plain dicts, no ORM
src/routes/         HTTP surface
front/              SvelteKit front, built statically into front/dist
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

Apache 2.0 - see [LICENSE](LICENSE).
