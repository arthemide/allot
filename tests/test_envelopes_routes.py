"""The /envelopes surface: a name, a monthly amount, and an optional start."""

from __future__ import annotations

from datetime import date, timedelta

from src import calc
from src.databases import sqlite as db

# What an envelope that tracks no cash reads back as.
NO_CASH = {"started_on": None, "opening_cash": None, "available": None}


class TestListing:
    def test_envelopes_come_back_in_alphabetical_order(self, client, portfolio_data):
        # Given a second envelope created after the first
        db.upsert_envelope("CTO", 100.0)
        # When they are listed
        body = client.get("/envelopes").json()
        # Then the name orders them
        assert body == [
            {"name": "CTO", "monthly_amount": 100.0, **NO_CASH},
            {"name": "PEA", "monthly_amount": 300.0, **NO_CASH},
        ]

    def test_an_empty_database_has_no_envelope(self, client):
        # Given nothing tracked
        # When the envelopes are listed
        assert client.get("/envelopes").json() == []


class TestUpsert:
    def test_an_unknown_envelope_is_created_by_the_put(self, client):
        # Given no envelope
        # When one is written
        response = client.put(
            "/envelopes/PEA", json={"name": "PEA", "monthly_amount": 300.0}
        )
        # Then it exists, with the amount that was sent
        assert response.status_code == 200
        assert response.json() == {"name": "PEA", "monthly_amount": 300.0, **NO_CASH}

    def test_the_path_names_the_envelope_not_the_payload(self, client):
        # Given a payload whose name disagrees with the path
        # When it is written
        client.put("/envelopes/PEA", json={"name": "CTO", "monthly_amount": 50.0})
        # Then the path won, and no second envelope appeared
        assert [e["name"] for e in db.all_envelopes()] == ["PEA"]

    def test_writing_a_known_envelope_only_moves_its_amount(
        self, client, portfolio_data
    ):
        # Given an envelope funded with 300 a month
        # When it is written again
        body = client.put(
            "/envelopes/PEA", json={"name": "PEA", "monthly_amount": 450.0}
        ).json()
        # Then the amount changed and the assets stayed where they were
        assert body["monthly_amount"] == 450.0
        assert db.envelope_asset_count("PEA") == 2

    def test_a_negative_monthly_amount_is_refused(self, client):
        # Given an amount that makes no sense
        # When it is written
        response = client.put(
            "/envelopes/PEA", json={"name": "PEA", "monthly_amount": -1.0}
        )
        # Then the model rejected it before the CHECK had to
        assert response.status_code == 422
        assert db.all_envelopes() == []


class TestDeletion:
    def test_an_unknown_envelope_cannot_be_deleted(self, client):
        # Given no envelope
        # When one is deleted
        assert client.delete("/envelopes/GHOST").status_code == 404

    def test_an_envelope_still_holding_assets_is_not_deleted(
        self, client, portfolio_data
    ):
        # Given an envelope holding two assets
        # When it is deleted
        response = client.delete("/envelopes/PEA")
        # Then it is refused, and the answer says how many are in the way
        assert response.status_code == 409
        assert "2 asset(s)" in response.json()["detail"]
        assert db.get_envelope("PEA") is not None

    def test_an_empty_envelope_is_deleted(self, client, portfolio_data):
        # Given an envelope nothing points at
        db.upsert_envelope("CTO", 100.0)
        # When it is deleted
        response = client.delete("/envelopes/CTO")
        # Then it is gone
        assert response.status_code == 204
        assert db.get_envelope("CTO") is None


class TestStart:
    def test_an_envelope_tracks_no_cash_until_a_start_is_posed(
        self, client, portfolio_data
    ):
        # Given an envelope that never declared where its strategy starts
        # When it is read
        body = client.get("/envelopes").json()[0]
        # Then it says nothing about cash, and behaves as it always did
        assert body["available"] is None

    def test_posing_a_start_derives_the_cash_from_it(self, client, portfolio_data):
        # Given a 300 EUR/month envelope started five months ago with 250 EUR
        started = date.today().replace(day=1) - timedelta(days=31 * 4)
        response = client.put(
            "/envelopes/PEA/start",
            json={"started_on": started.isoformat(), "opening_cash": 250.0},
        )
        # When it is read back
        assert response.status_code == 200
        body = response.json()
        # Then the cash is the opening plus the contributions, less the buy
        # and plus the sell already recorded on that envelope
        assert body["started_on"] == started.isoformat()
        assert body["available"] > 250.0

    def test_a_start_on_an_unknown_envelope_is_refused(self, client):
        response = client.put(
            "/envelopes/GHOST/start", json={"started_on": "2026-01-01"}
        )
        assert response.status_code == 404

    def test_clearing_the_start_stops_the_tracking(self, client, portfolio_data):
        # Given an envelope that tracks its cash
        client.put("/envelopes/PEA/start", json={"started_on": "2026-01-01"})
        # When the start is removed
        body = client.delete("/envelopes/PEA/start").json()
        # Then it is back to splitting its monthly amount, and knows no cash
        assert body["available"] is None
        assert db.get_envelope_start("PEA") is None

    def test_clearing_on_an_unknown_envelope_is_refused(self, client):
        assert client.delete("/envelopes/GHOST/start").status_code == 404

    def test_changing_the_monthly_amount_freezes_the_cash(self, client, portfolio_data):
        # Given an envelope started a year ago, so many contributions in
        started = (date.today() - timedelta(days=365)).isoformat()
        client.put("/envelopes/PEA/start", json={"started_on": started})
        before = client.get("/envelopes").json()[0]["available"]
        # When the monthly amount is raised
        after = client.put(
            "/envelopes/PEA", json={"name": "PEA", "monthly_amount": 500.0}
        ).json()
        # Then the cash did not jump: the past keeps the amount it was lived
        # with, and the new one only counts from today
        assert after["available"] == before
        # Dated next month: this month was already paid in at the old amount
        assert (
            after["started_on"]
            == calc.add_months(date.today().replace(day=1), 1).isoformat()
        )

    def test_an_unchanged_amount_leaves_the_start_alone(self, client, portfolio_data):
        # Given an envelope started long ago
        client.put("/envelopes/PEA/start", json={"started_on": "2026-01-01"})
        # When the same amount is written again
        body = client.put(
            "/envelopes/PEA", json={"name": "PEA", "monthly_amount": 300.0}
        ).json()
        # Then nothing was frozen: there was nothing to protect against
        assert body["started_on"] == "2026-01-01"
