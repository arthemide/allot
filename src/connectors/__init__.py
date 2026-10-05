"""Read-only connectors to the banks that hold the positions.

Three rules hold for everything in this package:

- Local only: the browser talks to the bank it was opened for and nothing
  else. Every other host is refused before the request leaves.
- Read only: the code navigates and listens. It never clicks, never types,
  never submits a form. Logging in is done by hand, 2FA included.
- No credentials anywhere: no password is asked for or stored. The session
  lives in a persistent browser profile under data/connectors/, which git
  ignores along with the dumps and the database.

The browser lives in `browser.py`; everything else is pure and tested.
"""
