# Bank connectors

Read-only, local-only access to BoursoBank (PEA) and Afer (life insurance). You log in yourself in a visible browser, 2FA included; nothing here asks for or stores a password. The browser refuses every host outside the bank's domains, and the code never clicks or types.

Everything it writes lives under `data/connectors/`, which git ignores: the browser profile (`profiles/<bank>/`, it holds a live session), the masked network dumps (`dumps/<bank>/<timestamp>/`) and, later, the snapshot database.

## Install

```sh
make connectors-install   # Playwright and its Chromium, outside the default install
```

## First connection: discovery

```sh
make discover BANK=bourso   # or BANK=afer
```

A Chromium window opens on the bank's site. Log in, open the target page (PEA portfolio, or the Afer membership detail with its split across funds), wait for it to load, then press Enter in the terminal. Every JSON response and every page is masked (tokens, IBANs, account and membership numbers, personal details) and written to the dump folder, followed by `summary.txt`: which endpoints carry amounts, quantities, ISINs or labels, and whether the figures arrive as JSON or as server-rendered HTML. Hosts the browser refused are listed too; if the login page breaks, one of them is probably needed.

Read the dumps before reusing any of them as a test fixture: masking leans towards too much, but it is a regex, not a guarantee.

To print the summary of a past run again:

```sh
uv run python -m src.connectors summary data/connectors/dumps/bourso/<timestamp>
```

## Sync

```sh
make sync BANK=bourso
```

Reuses the session the profile kept, in a hidden browser (`uv run --group connectors python -m src.connectors sync bourso --visible` to watch it). It loads the account list, then the positions page of each PEA, by address only, with a random pause of 2 to 6 seconds between pages. BoursoBank renders those pages server-side, so the figures are read from the HTML: per line the ISIN, label, quantity, cost price, last price, value and unrealised gain, plus the available cash.

Each sync appends a snapshot to `data/connectors/connectors.db` and never overwrites one:

```sh
sqlite3 data/connectors/connectors.db 'SELECT * FROM positions WHERE snapshot_id = (SELECT max(id) FROM snapshots)'
```

If the page no longer looks like what the parser expects, the sync stops without storing anything and says what is missing. Afer has no sync yet: it waits for its own discovery.

## Session expired

The profile keeps the session between runs. When the bank has logged it out, sync stops with a message and stores nothing. Run `make discover BANK=<bank>` again, log in in the window, press Enter, then sync. To start from scratch, delete `data/connectors/profiles/<bank>/`.

## One run at a time

A lock file, `data/connectors/run.lock`, refuses a second run. If a run crashed and left it behind, delete it.


## Sync from the app, with woob

The sync above drives a browser on your machine. BoursoBank can instead be
synced from Allot itself, with [woob](https://woob.dev) doing the login. This
runs where the app runs (the Pi), so your credentials travel from the browser
to the app over the LAN: turn `ALLOT_PASSWORD_HASH` on, and put HTTPS in front
of a non-local instance. The password is used once and never written or logged.

For a local run (`make start`):

```sh
make woob-install   # woob and the vendored modules, nothing fetched later
```

In the on-premise image, woob is left out by default (it pulls lxml, which
compiles from source on the 32-bit Pi). Build it in explicitly:

```sh
docker compose -f docker-compose.yml -f docker-compose.build.yml build \
    --build-arg INSTALL_WOOB=1
```

The connectors' state (snapshot database and the woob trusted-device cookie)
then lives under `/data/connectors` on the same volume as the app database.

In the app, "Sync BoursoBank" asks for your login and password. If the bank
wants a second factor, the dialog shows a code field or asks you to validate
in your bank app, then finishes on its own. The device is trusted for 90 days
through woob's saved state (`data/connectors/woob-state/`, a secret, git-
ignored), so the second factor is not asked again until it lapses.

The bank is authoritative: each sync replaces the PEA's opening positions with
what BoursoBank reports, clears the manual trades of those assets, and zeroes
any asset the bank no longer lists. The cash balance is read but left for you
to reconcile.

woob performs the automated login internally. That is the fragile part: if
BoursoBank changes its login screen, woob has to catch up. Modules are
vendored under `vendor/woob-modules/` so nothing is fetched at runtime; see
that folder's README to populate it.
