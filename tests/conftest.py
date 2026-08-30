"""Shared fixtures: a throwaway database, an offline app, and a small dataset.

Two things have to be neutralised before any test touches the app.

The database path is a module constant read at import time, and it is also
bound as the default argument of `connect()` and `init()`. Rebinding
`db.DB_PATH` is therefore not enough on its own: `connect()` is wrapped as
well, so a call aimed at the real database lands on the temporary one instead.

The lifespan of `app.py` goes to Yahoo. The session that would carry a request
out is therefore refused for every test, and the `offline` fixture stubs each
price entry point on top of that. No test in this suite may open a socket or
touch data/allot.db.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app
from src.databases import sqlite as db
from src.services import prices

# The real database, captured before anything rebinds it: it is what the
# bound defaults of connect() and init() still point at.
REAL_DB_PATH = db.DB_PATH

EUR_USD = 1.1
PRICE = 12.0


@pytest.fixture(autouse=True)
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every connection at a fresh database, and lay out the schema."""
    path = tmp_path / "allot.db"
    real_connect = db.connect

    def connect(target: Path = path):
        return real_connect(path if target == REAL_DB_PATH else target)

    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "connect", connect)
    db.init(path)
    return path


@pytest.fixture(autouse=True)
def no_network(mocker):
    """The one door out. Tests that want a real payload patch it themselves."""

    def refuse(*args, **kwargs):
        raise AssertionError("a test tried to reach the network")

    mocker.patch.object(prices, "_session", side_effect=refuse)


@pytest.fixture
def offline(mocker):
    """Every price entry point, stubbed with something deterministic."""
    mocker.patch.object(prices, "check_tickers", return_value=[])
    mocker.patch.object(prices, "current_price", return_value=PRICE)
    mocker.patch.object(prices, "eur_usd_rate", return_value=EUR_USD)
    mocker.patch.object(prices, "price_history", return_value=[])
    mocker.patch.object(prices, "search", return_value=[])


@pytest.fixture
def client(database, offline):
    """The app with its lifespan run, so startup is covered too."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def portfolio_data(database):
    """One envelope, two assets, one of them with a buy and a sell."""
    db.upsert_envelope("PEA", 300.0)
    db.add_asset("WPEA.PA", "Amundi PEA Monde", "PEA", "EUR", 2.0)
    db.add_asset("ESE.PA", "BNP S&P 500", "PEA", "EUR", 1.0)
    db.add_transaction("WPEA.PA", "2026-01-10", "buy", 10.0, 5.0, 1.0)
    db.add_transaction("WPEA.PA", "2026-02-10", "sell", 4.0, 6.0)
