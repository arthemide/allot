"""Single entry point: the API, and the built front served alongside it.

    uv run app.py

Nothing else needs to run.
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.databases import sqlite as db
from src.routes import router
from src.routes.auth import set_session_cookie
from src.services import auth, prices

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")

FRONT_DIST = Path(__file__).parent / "front" / "dist"
DEV_ORIGIN = "http://localhost:5173"

# 127.0.0.1 by default: nothing is exposed unless it is asked for. The
# container sets 0.0.0.0 so the app is reachable from the LAN.
HOST = os.getenv("ALLOT_HOST", "127.0.0.1")
PORT = int(os.getenv("ALLOT_PORT", "8000"))

# The rate limit keys on the client address; behind an untrusted proxy every
# caller would look like the same one.
FORWARDED_ALLOW_IPS = os.getenv("ALLOT_FORWARDED_ALLOW_IPS", "127.0.0.1")

# The static front is deliberately not guarded: it carries no data, and
# guarding it would make the login screen itself unreachable.
GUARDED_PREFIXES = ("/assets", "/transactions", "/envelopes", "/note")

DOCS = bool(os.getenv("ALLOT_DOCS"))


def _check_tickers() -> None:
    """List tickers that do not answer, and warm the quote cache on the way.

    One network round-trip per asset, so it runs off the startup path.
    """
    symbols = [a["symbol"] for a in db.all_assets()]
    failing = prices.check_tickers(symbols)
    if failing:
        logger.warning("tickers not answering: %s", ", ".join(failing))
    else:
        logger.info("all %d tickers answered", len(symbols))


@asynccontextmanager
async def lifespan(_: FastAPI):
    if auth.enabled():
        # Fail here rather than at the first login attempt.
        auth.secret_key()
        logger.info("authentication is on")
    else:
        logger.warning(
            "no ALLOT_PASSWORD_HASH: the API is open to anyone who can reach it"
        )
    db.init()
    pruned = db.prune_empty_envelopes()
    if pruned:
        logger.info("removed empty envelopes: %s", ", ".join(pruned))
    threading.Thread(target=_check_tickers, daemon=True).start()
    yield


app = FastAPI(
    title="Allot",
    lifespan=lifespan,
    docs_url="/docs" if DOCS else None,
    redoc_url="/redoc" if DOCS else None,
    openapi_url="/openapi.json" if DOCS else None,
)
app.include_router(router)


# A calendar client cannot log in, so this one route also opens with a token
# in the query string when ALLOT_FEED_TOKEN is set.
FEED_PATH = "/note.ics"


@app.middleware("http")
async def require_session(request: Request, call_next):
    """Guard the API when a password is configured.

    /health stays open: the container health check and the deployment wait on
    it, and it says nothing about the portfolio.
    """
    if not auth.enabled() or not request.url.path.startswith(GUARDED_PREFIXES):
        return await call_next(request)

    if request.url.path == FEED_PATH and auth.feed_token_valid(
        request.query_params.get("feed", "")
    ):
        return await call_next(request)

    token = request.cookies.get(auth.COOKIE_NAME, "")
    if not token or not auth.verify(token):
        return JSONResponse({"detail": "Not authenticated."}, status_code=401)

    response = await call_next(request)
    # Reissued on every call, so the window slides.
    set_session_cookie(response)
    return response


# The front is same-origin in production: CORS is for `make dev-front` only,
# and a permissive policy next to a session cookie is not worth leaving behind.
if os.getenv("ALLOT_DEV_CORS"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[DEV_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if FRONT_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONT_DIST, html=True), name="front")
else:
    logger.warning("front build not found at %s; API only", FRONT_DIST)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        proxy_headers=True,
        forwarded_allow_ips=FORWARDED_ALLOW_IPS,
    )
