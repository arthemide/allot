"""The entry point: startup, health, and what is mounted alongside the API."""

from __future__ import annotations

from fastapi.testclient import TestClient

import app as application
from src.databases import sqlite as db


class TestHealth:
    def test_health_answers_without_touching_anything(self, client):
        # Given a running app
        # When the health endpoint is called
        response = client.get("/health")
        # Then it answers on its own
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStartup:
    def test_startup_lays_out_the_schema(self, client):
        # Given a database whose schema the lifespan just replayed
        # When a table is written to
        db.upsert_envelope("PEA", 0.0)
        # Then it was there
        assert db.get_envelope("PEA") is not None

    def test_startup_prunes_the_envelopes_nothing_points_at(
        self, database, offline, caplog
    ):
        # Given an envelope left behind by its last asset
        db.upsert_envelope("CTO", 100.0)
        # When the app starts
        with caplog.at_level("INFO"):
            with TestClient(application.app):
                pass
        # Then it was pruned, and said so
        assert db.all_envelopes() == []
        assert "removed empty envelopes: CTO" in caplog.text

    def test_a_ticker_that_does_not_answer_is_reported(
        self, database, offline, mocker, caplog
    ):
        # Given an asset whose ticker is silent
        db.upsert_envelope("PEA", 0.0)
        db.add_asset("GHOST.PA", "Delisted", "PEA", "EUR")
        mocker.patch("src.services.prices.check_tickers", return_value=["GHOST.PA"])
        # When the startup check runs
        with caplog.at_level("INFO"):
            application._check_tickers()
        # Then the symbol is named in the warning
        assert "tickers not answering: GHOST.PA" in caplog.text

    def test_the_startup_check_stays_quiet_when_every_ticker_answers(
        self, portfolio_data, offline, caplog
    ):
        # Given tickers that all answer
        # When the startup check runs
        with caplog.at_level("INFO"):
            application._check_tickers()
        # Then it only says how many were checked
        assert "all 2 tickers answered" in caplog.text


class TestExposedSurface:
    def test_the_interactive_docs_are_off(self, client):
        # Given the default configuration
        # When the docs are asked for
        # Then they are not published, and neither is the schema behind them
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/redoc").status_code == 404

    def test_cors_is_not_wired_in_by_default(self):
        # Given the default configuration
        # When the middleware stack is inspected
        names = [
            middleware.cls.__name__ for middleware in application.app.user_middleware
        ]
        # Then no permissive policy sits next to the session cookie
        assert "CORSMiddleware" not in names
