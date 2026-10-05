"""Trigger a bank sync from the app itself.

The login is interactive: the first call hands over the credentials, and if
the bank asks for a second factor the caller answers it on a follow-up call
carrying the session id. Once through, the account's positions are read and
written as opening positions, the bank being authoritative.

Credentials reach this process in the request body and never leave it; woob
does the actual login. See src/connectors/woob_bourso.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, status

from src.connectors import login_session, store
from src.connectors.errors import (
    AuthFailed,
    ConnectorUnavailable,
    LayoutChanged,
    SessionExpired,
)
from src.models.schema import ConnectorAnswer, ConnectorLogin, ConnectorStatus

router = APIRouter(prefix="/connectors", tags=["connectors"])

SOURCE = "bourso"


@dataclass
class _Line:
    """A security row as the import service wants it (isin, name, qty, prum)."""

    isin: str
    name: str
    quantity: float
    prum: float


@router.post("/bourso/login", response_model=ConnectorStatus)
def login(payload: ConnectorLogin):
    try:
        session_id, attempt = login_session.begin(payload.login, payload.password)
    except ConnectorUnavailable as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error))
    except AuthFailed as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error))
    except (SessionExpired, LayoutChanged) as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error))
    return _advance(session_id, attempt)


@router.post("/bourso/login/{session_id}", response_model=ConnectorStatus)
def answer(session_id: str, payload: ConnectorAnswer):
    try:
        attempt = login_session.answer(session_id, payload.answer)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such login in progress.")
    except AuthFailed as error:
        login_session.finish(session_id)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error))
    except (SessionExpired, LayoutChanged) as error:
        login_session.finish(session_id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error))
    return _advance(session_id, attempt)


def _advance(session_id: str, attempt) -> ConnectorStatus:
    """Return the pending challenge, or run the sync once the login is through."""
    if attempt.status in ("otp", "app_validation"):
        return ConnectorStatus(
            session_id=session_id, status=attempt.status, prompt=attempt.prompt
        )
    try:
        report = _sync(attempt)
    finally:
        login_session.finish(session_id)
    return ConnectorStatus(session_id=session_id, status="done", report=report)


def _sync(attempt) -> dict:
    from src.services import portfolio_import

    rows = attempt.investments()
    store.save_snapshot(store.DEFAULT_DB, SOURCE, rows)

    by_account: dict[str, list[_Line]] = {}
    for row in rows:
        if row.support_type == "cash" or row.isin is None:
            continue
        by_account.setdefault(row.account, []).append(
            _Line(
                isin=row.isin,
                name=row.label,
                quantity=row.quantity or 0.0,
                prum=row.unit_cost or 0.0,
            )
        )

    merged = {"imported": [], "unresolved": [], "elsewhere": [], "total": 0}
    for account, lines in by_account.items():
        report = portfolio_import.apply_snapshot(account, lines, authoritative=True)
        for key in ("imported", "unresolved", "elsewhere"):
            merged[key].extend(report[key])
        merged["total"] += report["total"]
    return merged
