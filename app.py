"""Single entry point: the API, and the built front served alongside it.

    uv run app.py

Nothing else needs to run.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.databases import sqlite as db
from src.routes import router
from src.services import prices

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")

FRONT_DIST = Path(__file__).parent / "front" / "dist"
DEV_ORIGIN = "http://localhost:5173"


def _check_tickers() -> None:
    """List tickers that do not answer. Never blocks startup."""
    symbols = [a["symbol"] for a in db.all_assets()]
    failing = prices.check_tickers(symbols)
    if failing:
        logger.warning("tickers not answering: %s", ", ".join(failing))
    else:
        logger.info("all %d tickers answered", len(symbols))


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    _check_tickers()
    yield


app = FastAPI(title="Allot", lifespan=lifespan)
app.include_router(router)

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
    uvicorn.run(app, host="127.0.0.1", port=8000)
