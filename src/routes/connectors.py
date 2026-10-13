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
    AuthenticationInterrupted,
    AuthenticationMethodUnsupported,
    AuthFailed,
    ConnectorUnavailable,
    SessionExpired,
)
from src.models.schema import (
    ConnectorAnswer,
    ConnectorLogin,
    ConnectorResolution,
    ConnectorStatus,
    ImportReport,
)

router = APIRouter(prefix="/connectors", tags=["connectors"])

SOURCE = "bourso"


@dataclass
class _Line:
    """A security row as the import service wants it."""

    account: str
    broker_key: str
    isin: str | None
    name: str
    quantity: float
    # None when the bank shows no cost basis (a CEFP page lists parts and
    # their value only): the user supplies what was invested.
    prum: float | None
    currency: str


@router.post("/bourso/login", response_model=ConnectorStatus)
def login(payload: ConnectorLogin):
    try:
        session_id, attempt = login_session.begin(payload.login, payload.password)
    except ConnectorUnavailable as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error))
    except AuthFailed as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error))
    except AuthenticationMethodUnsupported as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    except (AuthenticationInterrupted, SessionExpired) as error:
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
    except AuthenticationMethodUnsupported as error:
        login_session.finish(session_id)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))
    except (AuthenticationInterrupted, SessionExpired) as error:
        login_session.finish(session_id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error))
    return _advance(session_id, attempt)


@router.post("/bourso/resolve", response_model=ImportReport)
def resolve(payload: ConnectorResolution):
    """Apply a manually selected ticker to the latest unresolved Bourso row.

    The row is found by its `broker_key`, which works for an ISIN line and for
    a part-based line the broker does not tag (a CEFP line without ISIN). Once
    the choice is made it is remembered, so the next sync updates in place.
    """
    from src.services import portfolio_import

    row = next(
        (
            row
            for row in store.latest(store.DEFAULT_DB, SOURCE)
            if row["account"] == payload.account
            and row["broker_key"] == payload.broker_key
            and row["support_type"] != "cash"
        ),
        None,
    )
    if row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "This BoursoBank position is no longer in the latest snapshot.",
        )
    quantity = row["quantity"] or 0.0
    prum = row["unit_cost"]
    if prum is None:
        # The bank gives no cost basis for this line: the user's figure is the
        # only source, and the PRUM follows from it.
        if not payload.invested or quantity <= 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "BoursoBank shows no cost basis for this line: give the amount "
                "invested.",
            )
        prum = payload.invested / quantity
    line = _Line(
        account=row["account"],
        broker_key=row["broker_key"],
        isin=row["isin"],
        name=row["label"],
        quantity=quantity,
        prum=prum,
        currency=row["currency"],
    )
    report = portfolio_import.apply_snapshot(
        payload.account,
        [line],
        authoritative=True,
        reconcile_missing=False,
        symbols={payload.broker_key: payload.symbol},
    )
    if report["unresolved"]:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"{payload.symbol} is not a Yahoo listing in {line.currency}.",
        )
    return report


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
        # A cash balance is not an asset, and a line without a quantity cannot
        # hold a position. Everything else is kept, even without an ISIN or a
        # cost basis (a CEFP line has neither): those are offered to the user
        # rather than dropped.
        if row.support_type == "cash" or not row.quantity:
            continue
        by_account.setdefault(row.account, []).append(
            _Line(
                account=row.account,
                broker_key=row.broker_key,
                isin=row.isin,
                name=row.label,
                quantity=row.quantity or 0.0,
                prum=row.unit_cost,
                currency=row.currency,
            )
        )

    merged = {"imported": [], "unresolved": [], "elsewhere": [], "total": 0}
    for account, lines in by_account.items():
        report = portfolio_import.apply_snapshot(account, lines, authoritative=True)
        for key in ("imported", "unresolved", "elsewhere"):
            merged[key].extend(report[key])
        merged["total"] += report["total"]
    return merged
