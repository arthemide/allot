"""Logging in, and telling the front whether it has to."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from src.models.schema import Login, Session
from src.services import auth

router = APIRouter(tags=["auth"])


def set_session_cookie(response: Response) -> None:
    """Put a fresh session cookie on a response.

    Also called by the middleware on every authenticated request, which is
    what makes the window slide.
    """
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.issue(),
        max_age=auth.session_days() * 24 * 3600,
        httponly=True,
        secure=auth.cookie_secure(),
        samesite="lax",
        path="/",
    )


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(payload: Login, response: Response):
    """Exchange the password for a session cookie."""
    if not auth.enabled():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "This instance has no password configured."
        )
    if not auth.verify_password(payload.password, auth.password_hash()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password.")
    # On the injected response, whose headers FastAPI keeps when the handler
    # returns nothing.
    set_session_cookie(response)


@router.get("/session", response_model=Session)
def read_session(request: Request):
    """Whether a password is needed here, and whether this browser has one."""
    if not auth.enabled():
        return Session(required=False, authenticated=True)
    token = request.cookies.get(auth.COOKIE_NAME, "")
    return Session(required=True, authenticated=bool(token) and auth.verify(token))
