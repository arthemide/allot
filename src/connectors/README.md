# Bank connectors

BoursoBank can be synced from Allot itself, with [woob](https://woob.dev) doing the login. The only thing the connector writes outside the app database is woob's saved state, under `data/connectors/` (git-ignored).

## Credentials

The sync runs where the app runs (the Pi), so your credentials travel from the browser to the app over the LAN: turn `ALLOT_PASSWORD_HASH` on, and put HTTPS in front of a non-local instance. The password is used once and never written or logged.

woob receives a full bank session. Allot only calls the account and investment listings, but the woob module itself also knows transfers and documents: treat the host as one that can reach your bank account.

## Local run

```sh
make woob-install
```

The app loads the module with woob's `WoobBase`, from `vendor/woob-modules/` only: no repository, no `woob update`, nothing fetched at runtime. The module is committed; see [its README](../../vendor/woob-modules/README.md) for where it comes from and how it is refreshed.

## Image

In the on-premise image, woob is controlled by the `INSTALL_WOOB` build argument (it pulls lxml, which compiles from source on the 32-bit Pi):

```sh
docker compose -f docker-compose.yml -f docker-compose.build.yml build \
    --build-arg INSTALL_WOOB=1
```

The woob trusted-device cookie then lives under `/data/connectors`, on the same volume as the app database.

## Sync

In the app, "Sync BoursoBank" asks for your login and password. If the bank wants a second factor, the dialog shows a code field, or asks you to validate in your bank app and confirm once done. The device is trusted for 90 days through woob's saved state (`data/connectors/woob-state/`, a secret, git-ignored), so the second factor is not asked again until it lapses.

The bank is authoritative: each sync replaces the account's opening positions with what BoursoBank reports, clears the manual trades of those assets, and zeroes any asset the bank no longer lists. The cash balance is read but left for you to reconcile.

A line is reported unresolved, and nothing is written for it, when it has no ISIN (a CEFP line by parts), no cost price, or no Yahoo listing in BoursoBank's currency: add it by hand. While any line is unresolved, nothing in that account is zeroed.

## Limits

woob performs the automated login internally. That is the fragile part: if BoursoBank changes its login screen, the vendored module has to be refreshed with `make woob-update`. It does not support BoursoBank's QR-code validation; when the bank requires one, import the BoursoBank CSV export instead.
