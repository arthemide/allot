"""Why a sync stops. Both end the run before anything is stored."""

from __future__ import annotations


class SessionExpired(RuntimeError):
    """The bank sent the browser back to its login page."""

    def __init__(self, bank: str, key: str):
        super().__init__(
            f"{bank} session expired: run `make discover BANK={key}`, log in in "
            "the window, then sync again."
        )


class LayoutChanged(RuntimeError):
    """The page no longer looks like what the parser was written against."""


class AuthFailed(RuntimeError):
    """The bank refused the credentials, or locked the account."""


class AuthenticationInterrupted(RuntimeError):
    """The bank stopped an interactive authentication before it completed."""


class AuthenticationMethodUnsupported(RuntimeError):
    """The bank requires a login method the connector cannot complete."""


class ConnectorUnavailable(RuntimeError):
    """The optional connector dependency (woob) is not installed here."""
