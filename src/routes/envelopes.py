"""Envelope endpoints. An envelope is a name and a monthly amount, nothing else."""

from fastapi import APIRouter, HTTPException, status

from src.databases import sqlite as db
from src.models.schema import Envelope

router = APIRouter(prefix="/envelopes", tags=["envelopes"])


@router.get("", response_model=list[Envelope])
def list_envelopes():
    return db.all_envelopes()


@router.put("/{name}", response_model=Envelope)
def upsert_envelope(name: str, payload: Envelope):
    """Create the envelope or set its monthly amount."""
    db.upsert_envelope(name, payload.monthly_amount)
    return db.get_envelope(name)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_envelope(name: str):
    """Refused while assets still point at it, to avoid orphaning them."""
    if db.get_envelope(name) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown envelope")
    if db.envelope_asset_count(name):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Envelope still holds assets"
        )
    db.delete_envelope(name)
