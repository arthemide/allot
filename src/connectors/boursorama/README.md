# Bank connectors

BoursoBank can be synced from Allot itself, with [woob](https://woob.dev) doing the login. The only thing the connector writes outside the app database is woob's saved state, under `data/connectors/` (git-ignored).

## Credentials

The sync runs where the app runs (the Pi), so your credentials travel from the browser to the app over the LAN. The `/connectors` routes therefore answer 403 until the app password is on (`ALLOT_PASSWORD_HASH`, see `make password`); put HTTPS in front of a non-local instance too. Bank logins are capped at 5 per 10 minutes, since the bank locks an account after a few failures. The password is used once and never written or logged.

woob receives a full bank session. Allot only calls the account and investment listings, but the woob module itself also knows transfers and documents: treat the host as one that can reach your bank account.

## Local run

```sh
make woob-install
```

The app loads the module with woob's `WoobBase`, from `vendor/woob-modules/` only: no repository, no `woob update`, nothing fetched at runtime. The module is committed; see [its README](../../../vendor/woob-modules/README.md) for where it comes from and how it is refreshed.

## Image

The on-premise image leaves woob out by default: on the 32-bit Pi, pillow (a woob dependency) has no wheel and compiles from source. Build it in explicitly:

```sh
docker compose -f docker-compose.yml -f docker-compose.build.yml build \
    --build-arg INSTALL_WOOB=1
```

The woob trusted-device cookie then lives under `/data/connectors`, on the same volume as the app database.

## Sync

In the app, "Sync BoursoBank" asks for your login and password. If the bank wants a second factor, the dialog shows a code field, or asks you to validate in your bank app and confirm once done. The device is trusted for 90 days through woob's saved state (`data/connectors/woob-state/`, a secret, git-ignored), so the second factor is not asked again until it lapses.

The first time an account shows up (PEA, CTO...), the dialog asks which envelope it syncs into, offering an envelope of the same name when there is one; leaving it empty keeps the account out of Allot. The choice is remembered (`source_account` table, under the `bourso` source). Deleting the envelope forgets it, so the account is asked about again.

The bank is authoritative on what is held: after a sync, each asset it reports holds exactly its quantity and PRUM, and an asset of the envelope it no longer lists holds nothing. The trades you recorded are never deleted, because the envelope's cash is derived from them; the opening position absorbs the difference instead. When it cannot, because the trades already hold more than the bank reports (a sell not recorded yet), the line is reported as a conflict and left as it was: record the sell, then sync again. The cash balance is read but left for you to reconcile.

A line is reported unresolved, and nothing is written for it, when it has no ISIN, no cost price, or no Yahoo listing in BoursoBank's currency: add it by hand. While any line is unresolved, nothing in that account is zeroed.

## Limits

woob performs the automated login internally. That is the fragile part: if BoursoBank changes its login screen, the vendored module has to be refreshed with `make woob-update`. It does not support BoursoBank's QR-code validation; when the bank requires one, import the BoursoBank CSV export instead.
