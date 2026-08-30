"""The /transactions surface."""

from __future__ import annotations

from src.databases import sqlite as db


class TestListing:
    def test_every_transaction_comes_back_oldest_first(self, client, portfolio_data):
        # Given a buy and a later sell
        # When the transactions are listed
        body = client.get("/transactions").json()
        # Then the date orders them, and the symbol is not part of the payload
        assert [t["date"] for t in body] == ["2026-01-10", "2026-02-10"]
        assert [t["side"] for t in body] == ["buy", "sell"]
        assert "symbol" not in body[0]

    def test_the_listing_can_be_narrowed_to_one_asset(self, client, portfolio_data):
        # Given transactions on one asset out of two
        # When the other one is asked for
        response = client.get("/transactions", params={"symbol": "ESE.PA"})
        # Then nothing comes back, rather than the whole history
        assert response.json() == []

    def test_an_unknown_symbol_simply_has_no_transactions(self, client, portfolio_data):
        # Given a symbol nobody tracks
        # When its transactions are listed
        # Then it is an empty list, not a 404: there is nothing to find
        assert client.get("/transactions", params={"symbol": "GHOST"}).json() == []


class TestCreation:
    def test_a_recorded_buy_comes_back_with_the_identifier_it_was_given(
        self, client, portfolio_data
    ):
        # Given a tracked asset
        # When a buy is posted
        response = client.post(
            "/transactions",
            json={
                "symbol": "ESE.PA",
                "date": "2026-03-10",
                "side": "buy",
                "quantity": 2.0,
                "unit_price": 30.0,
                "fees": 1.5,
            },
        )
        # Then the stored row carries the same id
        assert response.status_code == 201
        body = response.json()
        assert body["fees"] == 1.5
        assert [t["id"] for t in db.transactions_of("ESE.PA")] == [body["id"]]

    def test_a_transaction_needs_an_asset_to_hang_on(self, client, portfolio_data):
        # Given a symbol nobody tracks
        # When a buy is posted on it
        response = client.post(
            "/transactions",
            json={
                "symbol": "GHOST",
                "date": "2026-03-10",
                "side": "buy",
                "quantity": 1.0,
                "unit_price": 5.0,
            },
        )
        # Then it is refused before any SQL runs
        assert response.status_code == 404
        assert len(db.all_transactions()) == 2

    def test_recording_a_buy_moves_the_position_it_belongs_to(
        self, client, portfolio_data
    ):
        # Given an asset holding nothing yet
        # When a buy is recorded on it
        client.post(
            "/transactions",
            json={
                "symbol": "ESE.PA",
                "date": "2026-03-10",
                "side": "buy",
                "quantity": 2.0,
                "unit_price": 30.0,
            },
        )
        # Then the position is recomputed from it, not stored alongside it
        position = client.get("/assets/ESE.PA").json()
        assert (position["quantity"], position["prum"]) == (2.0, 30.0)

    def test_a_payload_the_schema_refuses_never_reaches_the_database(
        self, client, portfolio_data
    ):
        # Given a side that is neither a buy nor a sell, and a null quantity
        payloads = [
            {"side": "hold", "quantity": 1.0, "unit_price": 5.0},
            {"side": "buy", "quantity": 0.0, "unit_price": 5.0},
            {"side": "buy", "quantity": 1.0, "unit_price": 0.0},
            {"side": "buy", "quantity": 1.0, "unit_price": 5.0, "fees": -1.0},
        ]
        # When each of them is posted
        answers = [
            client.post(
                "/transactions",
                json={"symbol": "WPEA.PA", "date": "2026-03-10", **payload},
            )
            for payload in payloads
        ]
        # Then the model refused them all, and nothing was written
        assert [answer.status_code for answer in answers] == [422] * 4
        assert len(db.all_transactions()) == 2


class TestDeletion:
    def test_deleting_a_transaction_changes_the_position_it_backed(
        self, client, portfolio_data
    ):
        # Given a position derived from a buy and a sell
        sell = db.all_transactions()[1]
        # When the sell is deleted
        response = client.delete(f"/transactions/{sell['id']}")
        # Then the quantity follows, because nothing was stored
        assert response.status_code == 204
        assert client.get("/assets/WPEA.PA").json()["quantity"] == 10.0

    def test_deleting_a_transaction_nobody_has_is_still_no_content(
        self, client, portfolio_data
    ):
        # Given an id that does not exist
        # When it is deleted
        response = client.delete("/transactions/999")
        # Then the endpoint is idempotent rather than a 404
        assert response.status_code == 204
        assert len(db.all_transactions()) == 2

    def test_an_identifier_that_is_not_a_number_is_refused(self, client):
        # Given a path parameter that cannot be an id
        # When it is deleted
        assert client.delete("/transactions/abc").status_code == 422
