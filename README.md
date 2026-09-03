# Allot

> Per-asset PRUM tracking and a monthly allocation note.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

## Overview

Allot tracks what you hold, what it cost you, and tells you where this month's money should go.

Positions are never stored. Quantity and PRUM (*prix de revient unitaire moyen*, the weighted average price paid) are recomputed on every read from the transactions plus an optional opening position - the holding that predates tracking. There is no state to keep in sync and no reconciliation step.

Assets are grouped into **envelopes** (PEA, CTO, CRYPTO…). Each envelope carries its own monthly amount and stands on its own: one envelope never draws from another. Inside an envelope the amount is split across assets by their relative weight, modulated by how far the current price sits from the PRUM - 1.5x when the price is more than 10% below it, 0.5x when it is more than 10% above, 1x in between. The envelope total stays invariant.

An envelope can also **track its cash**, which is what makes a 600 € share reachable from an envelope funded with 100 € a month. Tell it where the strategy starts - a date, and the cash already there - and the balance is derived from then on: the monthly amount, month after month, minus what was bought. Nothing is stored, exactly as with the PRUM. Assets that only trade in whole units are then bought by the share, most under-weighted first, and what cannot be spent waits for next month. There is nothing to declare about that: a fractional quantity already recorded settles it, and until then the ticker is the clue (`ETH-USD` is bought by the amount, `MC.PA` by the share). When the figure drifts from the statement - a fee, a dividend, a month skipped - record what is really there today and the derivation restarts from that point.

## Features

- Per-asset position, PRUM, gain and gain percentage, recomputed from history
- Envelopes with a monthly amount and a per-asset split
- Ticker search, so the exchange suffix (`WPEA.PA`, `VWCE.DE`, `ETH-USD`) does not have to be guessed
- Price chart with transaction markers and the step PRUM curve
- Envelope cash: an envelope can save up month after month and be told to buy whole shares when it can afford them, rather than to place an amount that no broker will take
- A monthly note, as a checklist with a link per line, and a calendar feed to subscribe to

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

It listens on `:8000` and is reachable from the LAN.

### Authentication

Out of the box there is **no authentication**: anyone who can reach the port can read and delete everything. That is the LAN arrangement, and it stays the default.

Before putting Allot on a domain, give it a password:

```bash
docker compose run --rm --entrypoint python app -m src.services.auth
docker compose run --rm --entrypoint python app -c \
    'import secrets; print("ALLOT_SECRET_KEY=" + secrets.token_urlsafe(32))'
```

Put both lines in `.env` and restart. The API then answers only a browser that has logged in; `/health` stays open, because the container health check and the deployment wait on it. The session is a signed, `HttpOnly` cookie reissued on every request, so it lasts 30 days from the last visit rather than from the login: the password is typed once per browser and effectively not again. Changing `ALLOT_SECRET_KEY` logs every browser out.

Behind a proxy, set `ALLOT_COOKIE_SECURE=0` only if the instance is reached over plain HTTP, and `ALLOT_FORWARDED_ALLOW_IPS` to the proxy's address so the rate limit on the Yahoo-facing endpoints counts real callers rather than the proxy.

TLS, the domain and the tunnel are not this repository's business - they belong to whatever runs in front.

### The calendar feed

`/note.ics` is a rolling twelve months of events, rebuilt on every fetch: the current month carries the checklist, the ones after it carry what today's prices say is coming. A calendar subscribes to it once - it is plain ICS, so Google, Apple, Thunderbird and the rest all take it - and nothing ever goes stale, since nothing is copied.

A calendar client cannot log in. Set `ALLOT_FEED_TOKEN` to a long random string and that one route answers a request carrying `?feed=<token>`, while everything else stays behind the session:

```bash
docker compose run --rm --entrypoint python app -c \
    'import secrets; print("ALLOT_FEED_TOKEN=" + secrets.token_urlsafe(32))'
```

The dialog behind **Monthly note** hands you the full address to paste. **That URL is a credential**: whoever holds it reads the tickers and the amounts. Leave `ALLOT_FEED_TOKEN` empty and the feed stays behind the session like every other route - which also means no calendar can reach it.

Note that a hosted calendar fetches from its own servers, not from the phone: Google Calendar can only subscribe to an address reachable from the internet. On a LAN-only instance, a client that fetches from the device - Apple Calendar, Thunderbird - works without exposing anything.

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
3. `make replication` lists the LTX files held off-site; snapshots are level 9.

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
| `PUT`/`DELETE` | `/envelopes/{name}/start` | Start tracking an envelope's cash, or stop |
| `GET` | `/note` | The monthly note, as plain text |
| `GET` | `/note.ics` | Twelve months of events, for a calendar to subscribe to |
| `GET` | `/note/feed-url` | The address to hand to a calendar, token included |

`GET /session` says whether a password is required, and `POST /login` exchanges one for a session cookie.

Interactive docs are off - they publish the whole surface. `make dev-api` turns them back on at `/docs`.

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
