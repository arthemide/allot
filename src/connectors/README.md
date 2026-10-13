# Bank connectors

BoursoBank can be synced from Allot itself, with [woob](https://woob.dev) doing the login. Everything the connector writes lives under `data/connectors/` (git-ignored): the snapshot database and woob's saved state.

## Credentials

The sync runs where the app runs (the Pi), so your credentials travel from the browser to the app over the LAN: turn `ALLOT_PASSWORD_HASH` on, and put HTTPS in front of a non-local instance. The password is used once and never written or logged.

woob receives a full bank session. Allot only calls the account and investment listings, but the woob module itself also knows transfers and documents: treat the host as one that can reach your bank account.

## Local run

```sh
make woob-install
make woob-vendor    # downloads the module once, then vendors it with Allot
```

The app loads the module with woob's `WoobBase`, from `vendor/woob-modules/` only: no repository, no `woob update`, nothing fetched at runtime.

## Image

In the on-premise image, woob is controlled by the `INSTALL_WOOB` build argument (it pulls lxml, which compiles from source on the 32-bit Pi):

```sh
docker compose -f docker-compose.yml -f docker-compose.build.yml build \
    --build-arg INSTALL_WOOB=1
```

The connector's state (snapshot database and the woob trusted-device cookie) then lives under `/data/connectors` on the same volume as the app database.

## Sync

In the app, "Sync BoursoBank" asks for your login and password. If the bank wants a second factor, the dialog shows a code field, or asks you to validate in your bank app and confirm once done. The device is trusted for 90 days through woob's saved state (`data/connectors/woob-state/`, a secret, git-ignored), so the second factor is not asked again until it lapses.

The bank is authoritative: each sync replaces the account's opening positions with what BoursoBank reports, clears the manual trades of those assets, and zeroes any asset the bank no longer lists. The cash balance is read but left for you to reconcile.

Each sync appends a snapshot to `data/connectors/connectors.db` and never overwrites one:

```sh
sqlite3 data/connectors/connectors.db 'SELECT * FROM positions WHERE snapshot_id = (SELECT max(id) FROM snapshots)'
```

## Limits

woob performs the automated login internally. That is the fragile part: if BoursoBank changes its login screen, the vendored module has to be refreshed with `make woob-vendor`. It does not support BoursoBank's QR-code validation; when the bank requires one, import the BoursoBank CSV export instead.
