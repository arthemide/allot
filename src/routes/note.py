"""The monthly note, as plain text and as a calendar feed."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse

from src.models.schema import FeedUrl
from src.services import auth, note

router = APIRouter(tags=["note"])


def _base_url(request: Request) -> str:
    """Whatever host the caller used: there is no configured public URL."""
    return str(request.base_url)


@router.get("/note", response_class=PlainTextResponse)
def get_note(request: Request) -> str:
    """Recomputed from current prices on every request."""
    return note.render(_base_url(request))


@router.get("/note/feed-url", response_model=FeedUrl)
def get_feed_url(request: Request) -> FeedUrl:
    """The address to hand to a calendar, token included.

    Behind the session: this URL is a credential.
    """
    token = auth.feed_token()
    url = f"{_base_url(request).rstrip('/')}/note.ics"
    return FeedUrl(url=f"{url}?feed={token}" if token else url, token=bool(token))


@router.get("/note.ics")
def get_feed(request: Request) -> Response:
    """Twelve months of events, for a calendar to subscribe to.

    A file imported once would quietly go stale; each fetch rebuilds the
    whole series.
    """
    return Response(
        content=note.feed(_base_url(request)),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="allot.ics"'},
    )
