"""Bank connectors: read the positions a broker holds into Allot.

BoursoBank is the only one, through woob (`woob_bourso.py`, the only file that
imports it). The rules it keeps:

- Nothing fetched at runtime: woob loads its module from vendor/woob-modules/,
  never from a remote repository.
- Credentials used once: the login and password reach woob in memory for one
  attempt and are never written or logged.
- Reading only: Allot calls the account and investment listings and nothing
  else, even though the woob module itself can do more (transfers, documents).

Local state (snapshots, the trusted-device cookie) lives under
data/connectors/, which git ignores.
"""
