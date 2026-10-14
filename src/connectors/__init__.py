"""Bank connectors: read the positions a broker holds into Allot.

Each bank lives in its own subpackage (`boursorama/` for now) and hands the
sync a list of `src.models.schema.PositionRow`; what is shared - errors, the parked
logins, where local state lives - sits at this level. The rules every
connector keeps:

- Nothing fetched at runtime: a connector's code is vendored, never pulled
  from a remote repository.
- Credentials used once: the login and password stay in memory for one
  attempt and are never written or logged.
- Reading only: Allot calls the account and investment listings and nothing
  else, even when the library behind it can do more (transfers, documents).

Local state (a bank's trusted-device cookie, say) lives under
data/connectors/, which git ignores.
"""
