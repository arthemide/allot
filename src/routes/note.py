"""The monthly note, as plain text."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from src.services import note

router = APIRouter(tags=["note"])


@router.get("/note", response_class=PlainTextResponse)
def get_note() -> str:
    """Recomputed from current prices on every request."""
    return note.render()
