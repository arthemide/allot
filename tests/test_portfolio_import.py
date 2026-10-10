"""apply_snapshot: the shared path from a broker snapshot to opening positions.

The CSV import keeps its old behaviour (authoritative=False); a connector sync
speaks for the whole account (authoritative=True).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.databases import sqlite as db
from src.services import portfolio_import, prices

HITS = {
    "IE000BI8OT95": {"symbol": "CW8.PA", "label": "World", "currency": "EUR"},
    "FR0000000001": {"symbol": "0P0001.F", "label": "Europe", "currency": "EUR"},
}


@dataclass
class Line:
    isin: str
    name: str
    quantity: float
    prum: float
    currency: str | None = None


@pytest.fixture
def resolver(mocker):
    def search(query, limit=10):
        hit = HITS.get(query)
        return [hit] if hit else []

    return mocker.patch.object(prices, "search", side_effect=search)


WORLD = Line("IE000BI8OT95", "World", 10.0, 100.0)
EUROPE = Line("FR0000000001", "Europe", 2.0, 50.0)


class TestNonAuthoritative:
    def test_rows_become_opening_positions_and_the_envelope_is_created(
        self, database, resolver
    ):
        report = portfolio_import.apply_snapshot("PEA", [WORLD, EUROPE])
        assert report["total"] == 2
        assert {line["symbol"] for line in report["imported"]} == {"CW8.PA", "0P0001.F"}
        asset = db.get_asset("CW8.PA")
        assert asset["base_quantity"] == 10.0 and asset["base_prum"] == 100.0

    def test_an_unresolved_isin_is_reported_and_nothing_is_written(
        self, database, resolver
    ):
        report = portfolio_import.apply_snapshot("PEA", [Line("XX", "Mystery", 1, 1)])
        assert report["unresolved"] == [{"isin": "XX", "name": "Mystery"}]
        assert db.get_asset("XX") is None

    def test_manual_trades_and_untouched_assets_are_left_alone(
        self, database, resolver
    ):
        portfolio_import.apply_snapshot("PEA", [WORLD])
        db.add_transaction("CW8.PA", "2026-01-01", "buy", 1.0, 100.0)
        portfolio_import.apply_snapshot("PEA", [EUROPE])
        # The trade on the asset not in this snapshot survives
        assert len(db.transactions_of("CW8.PA")) == 1
        assert db.get_asset("CW8.PA")["base_quantity"] == 10.0

    def test_a_broker_currency_selects_the_matching_yahoo_listing(
        self, database, mocker
    ):
        mocker.patch.object(
            prices,
            "search",
            return_value=[
                {"symbol": "WORLD", "label": "World USD", "currency": "USD"},
                {"symbol": "WORLD.PA", "label": "World EUR", "currency": "EUR"},
            ],
        )

        portfolio_import.apply_snapshot(
            "PEA", [Line("IE000BI8OT95", "World", 10.0, 100.0, "EUR")]
        )

        assert db.get_asset("WORLD") is None
        assert db.get_asset("WORLD.PA")["currency"] == "EUR"

    def test_a_confirmed_ticker_corrects_an_existing_asset_currency(
        self, database, mocker
    ):
        db.upsert_envelope("PEA", 0.0)
        db.add_asset("WORLD.PA", "World", "PEA", "USD")
        mocker.patch.object(
            prices,
            "search",
            return_value=[{"symbol": "WORLD.PA", "label": "World EUR", "currency": "EUR"}],
        )

        portfolio_import.apply_snapshot(
            "PEA", [Line("IE000BI8OT95", "World", 10.0, 100.0, "EUR")]
        )

        assert db.get_asset("WORLD.PA")["currency"] == "EUR"

    def test_a_later_sync_reuses_the_asset_linked_to_the_broker_isin(
        self, database, mocker
    ):
        db.upsert_envelope("CTO", 0.0)
        db.add_asset("AMD.F", "AMD", "CTO", "EUR")
        db.set_asset_isin("AMD.F", "US0079031078")

        portfolio_import.apply_snapshot(
            "CTO", [Line("US0079031078", "AMD", 2.0, 100.0, "EUR")]
        )

        mocker.patch.object(prices, "search", side_effect=AssertionError("not searched"))
        portfolio_import.apply_snapshot(
            "CTO", [Line("US0079031078", "AMD", 3.0, 110.0, "EUR")]
        )

        assert db.get_asset("AMD.F")["base_quantity"] == 3.0
        assert db.get_asset("AMD.DE") is None

    def test_a_different_currency_leaves_the_broker_line_unresolved(
        self, database, mocker
    ):
        mocker.patch.object(
            prices,
            "search",
            return_value=[{"symbol": "WORLD", "label": "World USD", "currency": "USD"}],
        )

        report = portfolio_import.apply_snapshot(
            "PEA", [Line("IE000BI8OT95", "World", 10.0, 100.0, "EUR")]
        )

        assert report["imported"] == []
        assert report["unresolved"] == [{"isin": "IE000BI8OT95", "name": "World"}]

    def test_an_explicit_ticker_cannot_bypass_the_currency_check(self, database, mocker):
        mocker.patch.object(
            prices,
            "search",
            return_value=[{"symbol": "WORLD", "label": "World USD", "currency": "USD"}],
        )

        report = portfolio_import.apply_snapshot(
            "PEA",
            [Line("IE000BI8OT95", "World", 10.0, 100.0, "EUR")],
            symbols={"IE000BI8OT95": "WORLD"},
        )

        assert report["imported"] == []
        assert db.get_asset("WORLD") is None


class TestAuthoritative:
    def test_manual_trades_of_touched_assets_are_cleared(self, database, resolver):
        portfolio_import.apply_snapshot("PEA", [WORLD])
        db.add_transaction("CW8.PA", "2026-01-01", "buy", 1.0, 100.0)
        portfolio_import.apply_snapshot("PEA", [WORLD], authoritative=True)
        assert db.transactions_of("CW8.PA") == []

    def test_an_asset_no_longer_reported_is_zeroed(self, database, resolver):
        # Given two assets imported, one of them traded
        portfolio_import.apply_snapshot("PEA", [WORLD, EUROPE])
        db.add_transaction("0P0001.F", "2026-01-01", "buy", 1.0, 50.0)
        # When a later authoritative snapshot reports only the first
        portfolio_import.apply_snapshot("PEA", [WORLD], authoritative=True)
        # Then the missing one is zeroed and its trades dropped, asset kept
        sold = db.get_asset("0P0001.F")
        assert sold is not None
        assert sold["base_quantity"] == 0.0 and sold["base_prum"] is None
        assert db.transactions_of("0P0001.F") == []

    def test_an_unresolved_line_prevents_a_partial_snapshot_from_zeroing_assets(
        self, database, mocker
    ):
        portfolio_import.apply_snapshot("PEA", [WORLD])
        mocker.patch.object(prices, "search", return_value=[])

        portfolio_import.apply_snapshot(
            "PEA", [Line("XX", "Unresolved", 1.0, 1.0, "EUR")], authoritative=True
        )

        assert db.get_asset("CW8.PA")["base_quantity"] == 10.0

    def test_an_asset_in_another_envelope_is_not_zeroed(self, database, resolver):
        portfolio_import.apply_snapshot("OTHER", [EUROPE])
        portfolio_import.apply_snapshot("PEA", [WORLD], authoritative=True)
        assert db.get_asset("0P0001.F")["base_quantity"] == 2.0

    def test_a_reported_asset_is_moved_to_its_account_keeping_weight(
        self, database, resolver
    ):
        # Given an asset the user had filed under PEA with a custom weight
        portfolio_import.apply_snapshot("PEA", [WORLD])
        db.update_asset("CW8.PA", "World", "PEA", 3.0)
        # When the bank reports it under CTO
        portfolio_import.apply_snapshot("CTO", [WORLD], authoritative=True)
        moved = db.get_asset("CW8.PA")
        # Then it moves, keeps its weight, and a later PEA sync cannot zero it
        assert moved["envelope"] == "CTO" and moved["weight"] == 3.0
        portfolio_import.apply_snapshot("PEA", [EUROPE], authoritative=True)
        assert db.get_asset("CW8.PA")["base_quantity"] == 10.0
