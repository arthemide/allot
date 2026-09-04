"""Envelope endpoints: a name, a monthly amount, and where its strategy starts."""

from datetime import date

from fastapi import APIRouter, HTTPException, status

from src import calc
from src.databases import sqlite as db
from src.models.schema import Envelope, EnvelopeStart
from src.services import cash

router = APIRouter(prefix="/envelopes", tags=["envelopes"])


def _with_cash(row: dict) -> Envelope:
    """The envelope as the API returns it: the row, plus its derived cash."""
    envelope = Envelope(**row)
    balance = cash.available(row)
    if balance is None:
        return envelope
    return envelope.model_copy(
        update={
            "started_on": balance.started_on,
            "opening_cash": balance.opening_cash,
            "available": balance.available,
        }
    )


@router.get("", response_model=list[Envelope])
def list_envelopes():
    return [_with_cash(envelope) for envelope in db.all_envelopes()]


@router.put("/{name}", response_model=Envelope)
def upsert_envelope(name: str, payload: Envelope):
    """Create the envelope or set its monthly amount.

    Changing the amount freezes today's cash into a new start, dated the 1st of
    next month since this month was already paid in at the old amount. Without
    that, the new amount would apply retroactively to every month since the
    start and the cash would jump for no reason.
    """
    existing = db.get_envelope(name)
    if (
        existing is not None
        and existing["monthly_amount"] != payload.monthly_amount
        and db.get_envelope_start(name) is not None
    ):
        balance = cash.available(existing)
        next_month = calc.add_months(date.today().replace(day=1), 1)
        db.set_envelope_start(name, next_month.isoformat(), balance.available)

    db.upsert_envelope(name, payload.monthly_amount)
    return _with_cash(db.get_envelope(name))


@router.put("/{name}/start", response_model=Envelope)
def set_start(name: str, payload: EnvelopeStart):
    """Start tracking the envelope's cash, or recalibrate it against a statement."""
    envelope = db.get_envelope(name)
    if envelope is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No envelope named {name}")
    db.set_envelope_start(name, payload.started_on, payload.opening_cash)
    return _with_cash(db.get_envelope(name))


@router.delete("/{name}/start", response_model=Envelope)
def clear_start(name: str):
    """Stop tracking cash: the monthly amount is split in euros again."""
    envelope = db.get_envelope(name)
    if envelope is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No envelope named {name}")
    db.clear_envelope_start(name)
    return _with_cash(db.get_envelope(name))


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_envelope(name: str):
    """Refused while assets still point at it, to avoid orphaning them."""
    if db.get_envelope(name) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No envelope named {name}")
    count = db.envelope_asset_count(name)
    if count:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{name} still holds {count} asset(s). Move or delete them first.",
        )
    db.delete_envelope(name)
