"""The /envelopes surface. An envelope is a name and a monthly amount."""

from __future__ import annotations

from src.databases import sqlite as db


class TestListing:
    def test_envelopes_come_back_in_alphabetical_order(self, client, portfolio_data):
        # Given a second envelope created after the first
        db.upsert_envelope("CTO", 100.0)
        # When they are listed
        body = client.get("/envelopes").json()
        # Then the name orders them
        assert body == [
            {"name": "CTO", "monthly_amount": 100.0},
            {"name": "PEA", "monthly_amount": 300.0},
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
        assert response.json() == {"name": "PEA", "monthly_amount": 300.0}

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
