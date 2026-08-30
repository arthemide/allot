"""The /assets surface: validate, delegate, translate errors into status codes."""

from __future__ import annotations

import pytest

from src.databases import sqlite as db
from tests.conftest import PRICE


class TestListing:
    def test_an_empty_portfolio_answers_an_empty_list(self, client):
        # Given nothing tracked
        # When the assets are listed
        response = client.get("/assets")
        # Then the answer is empty rather than an error
        assert response.status_code == 200
        assert response.json() == []

    def test_each_asset_comes_back_with_its_recomputed_position(
        self, client, portfolio_data
    ):
        # Given an asset bought 10 at 5 with 1 of fees, then sold 4
        # When the assets are listed
        body = client.get("/assets").json()
        # Then the position was derived, never read from a stored figure
        position = next(p for p in body if p["symbol"] == "WPEA.PA")
        assert position["quantity"] == 6.0
        assert position["prum"] == 5.1
        assert position["invested"] == pytest.approx(30.6)
        assert position["price"] == PRICE
        assert position["market_value"] == 72.0

    def test_an_asset_whose_ticker_is_silent_has_no_market_value(
        self, client, portfolio_data, mocker
    ):
        # Given a provider that does not answer for this symbol
        mocker.patch("src.services.prices.current_price", return_value=None)
        # When the asset is read
        body = client.get("/assets/WPEA.PA").json()
        # Then the position is still there, without the figures a price carries
        assert body["quantity"] == 6.0
        assert body["price"] is None
        assert body["market_value"] is None
        assert body["gain"] is None
        assert body["gain_percent"] is None


class TestCreation:
    def test_adding_an_asset_creates_the_envelope_it_names(self, client):
        # Given no envelope yet
        # When an asset is added into one
        response = client.post(
            "/assets",
            json={
                "symbol": "WPEA.PA",
                "label": "Amundi PEA Monde",
                "envelope": "PEA",
                "currency": "EUR",
                "weight": 2.0,
            },
        )
        # Then the envelope was created on the way, with no monthly amount
        assert response.status_code == 201
        assert response.json()["symbol"] == "WPEA.PA"
        assert db.get_envelope("PEA") == {"name": "PEA", "monthly_amount": 0.0}

    def test_adding_an_asset_into_a_known_envelope_leaves_its_amount_alone(
        self, client, portfolio_data
    ):
        # Given an envelope funded with 300 a month
        # When another asset joins it
        client.post(
            "/assets",
            json={
                "symbol": "BTC-EUR",
                "label": "Bitcoin",
                "envelope": "PEA",
                "currency": "EUR",
            },
        )
        # Then the monthly amount was not reset
        assert db.get_envelope("PEA")["monthly_amount"] == 300.0

    def test_a_tracked_asset_cannot_be_added_twice(self, client, portfolio_data):
        # Given an asset already tracked in PEA
        # When it is added again, in another envelope
        response = client.post(
            "/assets",
            json={
                "symbol": "WPEA.PA",
                "label": "Amundi PEA Monde",
                "envelope": "CTO",
                "currency": "EUR",
            },
        )
        # Then it is refused, and the answer says where it already lives
        assert response.status_code == 409
        assert "PEA" in response.json()["detail"]
        assert db.get_asset("WPEA.PA")["envelope"] == "PEA"

    def test_a_negative_weight_is_refused_before_reaching_the_database(self, client):
        # Given a payload with a weight that makes no sense
        # When it is posted
        response = client.post(
            "/assets",
            json={
                "symbol": "WPEA.PA",
                "label": "Amundi PEA Monde",
                "envelope": "PEA",
                "currency": "EUR",
                "weight": -1.0,
            },
        )
        # Then the model rejected it
        assert response.status_code == 422
        assert db.all_assets() == []


class TestReadUpdateDelete:
    def test_an_unknown_symbol_is_a_404_everywhere(self, client, portfolio_data):
        # Given a symbol nobody tracks
        # When each of the per-asset endpoints is called on it
        answers = [
            client.get("/assets/GHOST"),
            client.put(
                "/assets/GHOST", json={"label": "x", "envelope": "PEA", "weight": 1.0}
            ),
            client.delete("/assets/GHOST"),
            client.put("/assets/GHOST/opening", json={"quantity": 0.0}),
            client.get("/assets/GHOST/chart"),
        ]
        # Then all of them say the same thing
        assert [answer.status_code for answer in answers] == [404] * 5

    def test_updating_an_asset_can_move_it_to_a_new_envelope(
        self, client, portfolio_data
    ):
        # Given an asset in PEA
        # When it is moved to an envelope that does not exist yet
        response = client.put(
            "/assets/WPEA.PA",
            json={"label": "Amundi World", "envelope": "CTO", "weight": 3.0},
        )
        # Then the envelope was created and the asset carries the new values
        assert response.status_code == 200
        body = response.json()
        assert (body["envelope"], body["label"], body["weight"]) == (
            "CTO",
            "Amundi World",
            3.0,
        )
        assert db.get_envelope("CTO") is not None

    def test_moving_the_last_asset_out_of_an_envelope_prunes_it(self, client):
        # Given an envelope holding a single asset
        client.post(
            "/assets",
            json={
                "symbol": "WPEA.PA",
                "label": "Amundi PEA Monde",
                "envelope": "PEA",
                "currency": "EUR",
            },
        )
        # When that asset moves elsewhere
        client.put(
            "/assets/WPEA.PA",
            json={"label": "Amundi PEA Monde", "envelope": "CTO", "weight": 1.0},
        )
        # Then the envelope it left behind is gone
        assert [e["name"] for e in db.all_envelopes()] == ["CTO"]

    def test_deleting_an_asset_takes_its_transactions_with_it(
        self, client, portfolio_data
    ):
        # Given an asset with a history
        # When it is deleted
        response = client.delete("/assets/WPEA.PA")
        # Then it answers no content, and nothing of it is left
        assert response.status_code == 204
        assert client.get("/assets/WPEA.PA").status_code == 404
        assert db.all_transactions() == []

    def test_deleting_the_last_asset_of_an_envelope_prunes_it(
        self, client, portfolio_data
    ):
        # Given an envelope holding two assets
        # When both are deleted
        client.delete("/assets/WPEA.PA")
        client.delete("/assets/ESE.PA")
        # Then the envelope went with the last one
        assert db.all_envelopes() == []


class TestOpeningPosition:
    def test_an_opening_position_is_stored_as_a_quantity_and_a_derived_prum(
        self, client, portfolio_data
    ):
        # Given a holding that predates tracking: 20 units for 100 EUR
        # When it is recorded
        response = client.put(
            "/assets/WPEA.PA/opening", json={"quantity": 20.0, "invested": 100.0}
        )
        # Then it behaves like an initial buy in the recomputed position
        body = response.json()
        assert body["base_quantity"] == 20.0
        assert body["base_prum"] == 5.0
        assert body["quantity"] == 26.0
        assert body["prum"] == pytest.approx(151 / 30)

    def test_a_quantity_without_an_amount_has_no_prum_to_compute(
        self, client, portfolio_data
    ):
        # Given a quantity given on its own
        # When it is sent
        response = client.put("/assets/WPEA.PA/opening", json={"quantity": 20.0})
        # Then it is refused, and the answer says how to clear it instead
        assert response.status_code == 400
        assert "quantity at 0" in response.json()["detail"]
        assert db.get_asset("WPEA.PA")["base_quantity"] == 0.0

    def test_a_quantity_of_zero_clears_the_opening_position(
        self, client, portfolio_data
    ):
        # Given an opening position already recorded
        client.put(
            "/assets/WPEA.PA/opening", json={"quantity": 20.0, "invested": 100.0}
        )
        # When it is cleared
        body = client.put("/assets/WPEA.PA/opening", json={"quantity": 0.0}).json()
        # Then only the transactions are left to derive the position from
        assert body["base_quantity"] == 0.0
        assert body["base_prum"] is None
        assert body["quantity"] == 6.0


class TestSearch:
    def test_the_search_is_handed_straight_to_the_provider(self, client, mocker):
        # Given a provider answering one hit
        search = mocker.patch(
            "src.services.prices.search",
            return_value=[
                {
                    "symbol": "WPEA.PA",
                    "label": "Amundi PEA Monde",
                    "exchange": "PAR",
                    "type": "ETF",
                    "currency": "EUR",
                    "price": 5.68,
                }
            ],
        )
        # When a ticker is searched with an explicit limit
        response = client.get("/assets/search", params={"q": "amundi", "limit": 3})
        # Then the query and the limit went through untouched
        assert response.status_code == 200
        assert response.json()[0]["symbol"] == "WPEA.PA"
        search.assert_called_once_with("amundi", 3)

    def test_the_search_needs_a_query(self, client):
        # Given no query at all
        # When the endpoint is called
        # Then it is the model that says so
        assert client.get("/assets/search").status_code == 422

    def test_search_comes_before_the_symbol_route(self, client, portfolio_data):
        # Given an asset tracked alongside the search endpoint
        # When /assets/search is called
        response = client.get("/assets/search", params={"q": "whatever"})
        # Then it is the search that answered, not a lookup for a symbol
        assert response.status_code == 200
        assert response.json() == []


class TestSummary:
    def test_everything_is_totalled_in_eur_by_envelope(self, client, portfolio_data):
        # Given a EUR asset with a position and one with nothing in it
        # When the summary is read
        body = client.get("/assets/summary").json()
        # Then the totals are grouped by envelope, in EUR
        assert body["currency"] == "EUR"
        assert body["eur_usd_rate"] == 1.1
        assert body["invested"] == pytest.approx(30.6)
        assert body["market_value"] == 72.0
        assert body["gain"] == pytest.approx(41.4)
        assert [e["envelope"] for e in body["envelopes"]] == ["PEA"]
        assert len(body["envelopes"][0]["assets"]) == 2

    def test_a_dollar_line_is_converted_before_it_is_added_up(self, client):
        # Given a USD asset worth 12 a unit, at 1.1 dollars per euro
        db.upsert_envelope("CTO", 0.0)
        db.add_asset("VOO", "Vanguard S&P 500", "CTO", "USD")
        db.set_opening_position("VOO", 1.0, 11.0)
        # When the summary is read
        body = client.get("/assets/summary").json()
        # Then both figures went through the rate before being totalled
        assert body["invested"] == 10.0
        assert body["market_value"] == pytest.approx(12.0 / 1.1)

    def test_a_portfolio_with_nothing_invested_has_no_rate_of_return(self, client):
        # Given no asset at all
        # When the summary is read
        body = client.get("/assets/summary").json()
        # Then there is no percentage to show rather than a zero
        assert body["invested"] == 0.0
        assert body["gain_percent"] is None
        assert body["envelopes"] == []


class TestChart:
    def test_the_chart_carries_prices_markers_and_the_step_prum(
        self, client, portfolio_data, mocker
    ):
        # Given a price history for the asset
        mocker.patch(
            "src.services.prices.price_history",
            return_value=[{"date": "2026-01-10", "price": 5.0}],
        )
        # When the chart is read
        body = client.get("/assets/WPEA.PA/chart").json()
        # Then it holds one PRUM step per transaction, the sell included
        assert body["symbol"] == "WPEA.PA"
        assert body["currency"] == "EUR"
        assert body["prices"] == [{"date": "2026-01-10", "price": 5.0}]
        assert [t["date"] for t in body["transactions"]] == ["2026-01-10", "2026-02-10"]
        assert [p["prum"] for p in body["prum"]] == [5.1, 5.1]

    def test_a_named_window_decides_how_far_back_the_history_goes(
        self, client, portfolio_data, mocker
    ):
        # Given a provider recording the window it was asked for
        history = mocker.patch("src.services.prices.price_history", return_value=[])
        # When a five-year chart is asked for
        client.get("/assets/WPEA.PA/chart", params={"window": "5y"})
        # Then the start is five years back, not a quarter before the first buy
        _, start, end = history.call_args.args
        assert (end - start).days == 5 * 365

    def test_by_default_the_window_opens_before_the_first_transaction(
        self, client, portfolio_data, mocker
    ):
        # Given a provider recording the window it was asked for
        history = mocker.patch("src.services.prices.price_history", return_value=[])
        # When the chart is asked for with no window
        client.get("/assets/WPEA.PA/chart")
        # Then it starts a quarter before the first buy, so it is not glued left
        _, start, _ = history.call_args.args
        assert start.isoformat() == "2025-10-12"

    def test_an_asset_with_no_history_still_draws_a_chart(self, client, portfolio_data):
        # Given an asset with no transaction
        # When its chart is read
        body = client.get("/assets/ESE.PA/chart").json()
        # Then the chart is empty rather than absent
        assert body["transactions"] == []
        assert body["prum"] == []

    def test_the_opening_prum_opens_the_step_curve(self, client, portfolio_data):
        # Given an asset whose only position predates tracking
        db.set_opening_position("ESE.PA", 10.0, 300.0)
        # When its chart is read
        body = client.get("/assets/ESE.PA/chart").json()
        # Then the curve starts at the opening PRUM, from the window's first day
        assert [p["prum"] for p in body["prum"]] == [30.0]
