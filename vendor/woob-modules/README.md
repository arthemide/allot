# Vendored woob modules

The in-app BoursoBank sync runs woob's `boursorama` module. It is vendored here so the app loads it with woob's `WoobBase`, from this folder only: no repository, no `woob update`, nothing fetched at runtime.

## Where it comes from

woob's last core release is 3.7 (PyPI), but its modules are still built from woob's main branch and published to `https://updates.woob.tech/3/main/`, the repository `woob update` itself reads. That repository keeps only the latest build of each module, so a build cannot be fetched again later: vendoring it is what makes the image reproducible, and each refresh a diff to review.

| File | What it is |
|---|---|
| `boursorama/` | The module, as published, minus its own `test.py` |
| `boursorama.lock` | Version, sha256 of the signed archive, woob spec, fetch date |
| `trusted.gpg` | woob's public keyring, the trust anchor, pinned by sha256 in `scripts/woob_update.py` |
| `COPYING`, `COPYING.LESSER` | The module's licence, LGPL-3.0-or-later, which builds on the GPL-3.0 |

## Refreshing it

```sh
make woob-update    # needs gpgv: `brew install gnupg` on macOS, `gpgv` on Debian
```

`scripts/woob_update.py` downloads the repository index and the module archive, refuses either unless `gpgv` finds a good signature from `trusted.gpg`, checks that the module accepts the woob version in `uv.lock` and depends on no other module, refuses any archive entry outside `boursorama/` or that is not a plain file, then swaps the folder and rewrites `boursorama.lock`. Any failed check leaves this folder untouched. `--force` vendors the same version again.

A weekly workflow (`.github/workflows/woob-update.yaml`) runs the same target and opens a PR when the module changed. That code receives the bank login and password: read the diff before merging.

## When woob rotates its key

The script stops with "woob rotated its keyring". Do not just copy the new `trusted.gpg`: check the new key with the woob maintainers, then replace the file and bump `KEYRING_SHA256` and `KEY_UPDATE` in `scripts/woob_update.py` in a commit of their own.

## Licence

Allot is Apache-2.0. The `boursorama` module is LGPL-3.0-or-later, copyright its authors (see the file headers); it is kept unmodified (only its test file is left out) in its own folder, loaded at runtime by woob, and ships with its licence texts.
