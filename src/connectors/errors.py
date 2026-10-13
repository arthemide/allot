"""Why a sync stops. Each ends the run before anything is stored."""

from __future__ import annotations


class SessionExpired(RuntimeError):
    """The bank let the second-factor validation lapse before it was given."""

    def __init__(self, bank: str):
        super().__init__(f"{bank} validation expired: start the sync again.")


class AuthFailed(RuntimeError):
    """The bank refused the credentials, or locked the account."""


class AuthenticationInterrupted(RuntimeError):
    """The bank stopped an interactive authentication before it completed."""


class AuthenticationMethodUnsupported(RuntimeError):
    """The bank requires a login method the connector cannot complete."""


class ConnectorUnavailable(RuntimeError):
    """The optional connector dependency (woob) is not installed here."""
