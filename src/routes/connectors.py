"""Trigger a bank sync from the app itself.

The login is interactive: the first call hands over the credentials, and if
the bank asks for a second factor the caller answers it on a follow-up call
carrying the session id. Once through, the accounts are read; an account
seen for the first time waits for the user to pick its envelope, then every
placed account is synced (src/services/bank_sync.py).

Credentials reach this process in the request body and never leave it; woob
does the actual login (src/connectors/boursorama/connector.py). Because they are bank
credentials, these routes refuse to run on an instance without a password.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.connectors import login_session
from src.connectors.errors import (
    AuthenticationInterrupted,
    AuthenticationMethodUnsupported,
    AuthFailed,
    BankUnavailable,
    ConnectorUnavailable,
    SessionExpired,
)
from src.models.schema import (
    ConnectorAccounts,
    ConnectorAnswer,
    ConnectorLogin,
    ConnectorStatus,
)
from src.services import auth, bank_sync, ratelimit

# A login reaches the bank, which locks an account after a few failures: far
# fewer tries than the Yahoo endpoints get.
LOGIN_LIMIT = 5
LOGIN_WINDOW = 600.0


def password_required() -> None:
    """Bank credentials only travel to an instance that asks for a password."""
    if not auth.enabled():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "The bank sync sends your bank credentials to this server, so it "
            "needs the app password on: set ALLOT_PASSWORD_HASH (make password).",
        )


def login_rate_limited(request: Request) -> None:
    key = "bank-login:" + (request.client.host if request.client else "unknown")
    if not ratelimit.allow(key, LOGIN_LIMIT, LOGIN_WINDOW):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many bank logins. The bank locks an account after a few "
            "failures, so they are capped.",
            headers={"Retry-After": str(ratelimit.retry_after(key, LOGIN_WINDOW))},
        )


router = APIRouter(
    prefix="/connectors",
    tags=["connectors"],
    dependencies=[Depends(password_required)],
)

# How each failure reads over HTTP. A failed attempt is dropped: the bank
# invalidates it on its side too.
_STATUS = (
    (ConnectorUnavailable, status.HTTP_503_SERVICE_UNAVAILABLE),
    (AuthFailed, status.HTTP_401_UNAUTHORIZED),
    (AuthenticationMethodUnsupported, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (AuthenticationInterrupted, status.HTTP_502_BAD_GATEWAY),
    (SessionExpired, status.HTTP_502_BAD_GATEWAY),
    (BankUnavailable, status.HTTP_502_BAD_GATEWAY),
)
_FAILURES = tuple(kind for kind, _ in _STATUS)


def _http(error: Exception) -> HTTPException:
    code = next(code for kind, code in _STATUS if isinstance(error, kind))
    return HTTPException(code, str(error))


@router.post(
    "/bourso/login",
    response_model=ConnectorStatus,
    dependencies=[Depends(login_rate_limited)],
)
def login(payload: ConnectorLogin):
    try:
        session_id, attempt = login_session.begin(payload.login, payload.password)
    except _FAILURES as error:
        raise _http(error)
    return _advance(session_id, attempt)


@router.post("/bourso/login/{session_id}", response_model=ConnectorStatus)
def answer(session_id: str, payload: ConnectorAnswer):
    if login_session.held(session_id) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This sync is waiting for its accounts."
        )
    try:
        attempt = login_session.answer(session_id, payload.answer)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such login in progress.")
    except _FAILURES as error:
        login_session.finish(session_id)
        raise _http(error)
    return _advance(session_id, attempt)


@router.post("/bourso/login/{session_id}/accounts", response_model=ConnectorStatus)
def place_accounts(session_id: str, payload: ConnectorAccounts):
    """Pick the envelope of each new account, then finish the sync."""
    rows = login_session.held(session_id)
    if rows is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No sync is waiting for its accounts."
        )
    try:
        bank_sync.place(payload.envelopes, rows)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    return _done(session_id, rows)


def _advance(session_id: str, attempt) -> ConnectorStatus:
    """Return the pending challenge, or read the accounts once the login is through."""
    if attempt.status in ("otp", "app_validation"):
        return ConnectorStatus(
            session_id=session_id, status=attempt.status, prompt=attempt.prompt
        )
    try:
        rows = attempt.investments()
    except BankUnavailable as error:
        login_session.finish(session_id)
        raise _http(error)
    # Everything needed is read: let go of the bank session now rather than
    # while the user picks envelopes.
    attempt.deinit()
    login_session.hold(session_id, rows)
    pending = bank_sync.new_accounts(rows)
    if pending:
        return ConnectorStatus(
            session_id=session_id, status="accounts", accounts=pending
        )
    return _done(session_id, rows)


def _done(session_id: str, rows: list) -> ConnectorStatus:
    try:
        report = bank_sync.apply(rows)
    finally:
        login_session.finish(session_id)
    return ConnectorStatus(session_id=session_id, status="done", report=report)
