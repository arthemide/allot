"""Why a sync stops. Each ends the run before anything is stored."""

from __future__ import annotations


class SessionExpired(RuntimeError):
    """The second-factor validation lapsed, or was refused in the bank app."""

    def __init__(self, bank: str):
        super().__init__(
            f"{bank} validation expired or was refused: start the sync again."
        )


class AuthFailed(RuntimeError):
    """The bank refused the credentials, or locked the account."""


class AuthenticationInterrupted(RuntimeError):
    """The bank stopped an interactive authentication before it completed."""


class AuthenticationMethodUnsupported(RuntimeError):
    """The bank requires a login method the connector cannot complete."""


class ConnectorUnavailable(RuntimeError):
    """The optional connector dependency (woob) is not installed here."""


class BankUnavailable(RuntimeError):
    """The bank failed or answered something woob could not read."""
