"""The SQL layer and the constraints the schema is supposed to enforce.

Nothing derived is ever stored, so what is worth pinning here is what the
database does on its own: cascades, checks, foreign keys, and the handful of
writes that carry a rule of their own.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.databases import sqlite as db


class TestSchema:
    def test_the_schema_can_be_replayed_on_an_existing_database(self, database):
        # Given a database that already holds data
        db.upsert_envelope("PEA", 300.0)
        # When the schema is laid out again, as every boot does
        db.init(database)
        # Then nothing was dropped
        assert db.get_envelope("PEA") == {"name": "PEA", "monthly_amount": 300.0}

    def test_the_write_ahead_log_is_on(self, database):
        # Given a database created by init()
        connection = db.connect()
        # When the journal mode is read back
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        connection.close()
        # Then it is the persistent WAL mode Litestream replicates
        assert mode == "wal"

    def test_an_asset_cannot_point_at_a_missing_envelope(self, database):
        # Given no envelope at all
        # When an asset claims one anyway
        with pytest.raises(sqlite3.IntegrityError):
            db.add_asset("WPEA.PA", "Amundi PEA Monde", "GHOST", "EUR")

    def test_a_transaction_cannot_point_at_a_missing_asset(self, database):
        # Given no asset
        # When a transaction claims one
        with pytest.raises(sqlite3.IntegrityError):
            db.add_transaction("GHOST", "2026-01-10", "buy", 1.0, 5.0)

    @pytest.mark.parametrize(
        "side, quantity, unit_price, fees",
        [
            ("hold", 1.0, 5.0, 0.0),
            ("buy", 0.0, 5.0, 0.0),
            ("buy", 1.0, 0.0, 0.0),
            ("buy", 1.0, 5.0, -1.0),
        ],
    )
    def test_a_transaction_has_to_make_sense(
        self, portfolio_data, side, quantity, unit_price, fees
    ):
        # Given a tracked asset
        # When a transaction breaks one of the checks
        with pytest.raises(sqlite3.IntegrityError):
            db.add_transaction(
                "WPEA.PA", "2026-01-10", side, quantity, unit_price, fees
            )

    def test_an_envelope_cannot_owe_a_negative_amount(self, database):
        # Given nothing
        # When an envelope is given a negative monthly amount
        with pytest.raises(sqlite3.IntegrityError):
            db.upsert_envelope("PEA", -1.0)

    def test_an_opening_quantity_without_a_prum_is_refused(self, portfolio_data):
        # Given a tracked asset
        # When a base quantity is written with no base PRUM behind it
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "UPDATE asset SET base_quantity = 5 WHERE symbol = ?", ("WPEA.PA",)
            )

    def test_the_same_order_cannot_be_inserted_twice(self, portfolio_data):
        # Given an order carrying its broker reference
        db.execute(
            'INSERT INTO "transaction" '
            "(symbol, date, side, quantity, unit_price, external_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("WPEA.PA", "2026-01-10", "buy", 1.0, 5.0, "broker-1"),
        )
        # When the same reference comes back, as a replayed migration would
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                'INSERT INTO "transaction" '
                "(symbol, date, side, quantity, unit_price, external_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("WPEA.PA", "2026-02-10", "buy", 2.0, 6.0, "broker-1"),
            )


class TestAssets:
    def test_assets_come_back_grouped_by_envelope_then_symbol(self, database):
        # Given assets added in no particular order
        db.upsert_envelope("PEA", 0.0)
        db.upsert_envelope("CTO", 0.0)
        db.add_asset("ESE.PA", "BNP S&P 500", "PEA", "EUR")
        db.add_asset("BTC-EUR", "Bitcoin", "CTO", "EUR")
        db.add_asset("WPEA.PA", "Amundi PEA Monde", "PEA", "EUR")
        # When they are listed
        symbols = [asset["symbol"] for asset in db.all_assets()]
        # Then the order is the envelope first, the symbol second
        assert symbols == ["BTC-EUR", "ESE.PA", "WPEA.PA"]

    def test_adding_a_known_asset_updates_it_rather_than_failing(self, portfolio_data):
        # Given an asset already tracked in PEA
        db.upsert_envelope("CTO", 0.0)
        # When it is added again, elsewhere and with another weight
        db.add_asset("WPEA.PA", "Amundi World", "CTO", "USD", 3.0)
        # Then the row was updated in place
        asset = db.get_asset("WPEA.PA")
        assert asset["label"] == "Amundi World"
        assert asset["envelope"] == "CTO"
        assert asset["currency"] == "USD"
        assert asset["weight"] == 3.0

    def test_updating_an_asset_leaves_its_currency_alone(self, portfolio_data):
        # Given a tracked asset
        # When its label, envelope and weight are changed
        db.update_asset("WPEA.PA", "Renamed", "PEA", 5.0)
        # Then the currency is not part of what an update touches
        asset = db.get_asset("WPEA.PA")
        assert (asset["label"], asset["weight"]) == ("Renamed", 5.0)
        assert asset["currency"] == "EUR"

    def test_an_unknown_asset_reads_back_as_nothing(self, database):
        # Given an empty database
        # When an asset is looked up
        # Then there is no row rather than an error
        assert db.get_asset("GHOST") is None

    def test_deleting_an_asset_takes_its_transactions_with_it(self, portfolio_data):
        # Given an asset with two transactions
        assert len(db.transactions_of("WPEA.PA")) == 2
        # When the asset is deleted
        db.delete_asset("WPEA.PA")
        # Then the cascade removed its history too
        assert db.get_asset("WPEA.PA") is None
        assert db.all_transactions() == []


class TestOpeningPosition:
    def test_the_prum_is_derived_from_what_the_statement_says(self, portfolio_data):
        # Given a holding that predates tracking: 20 units for 100 EUR
        db.set_opening_position("WPEA.PA", 20.0, 100.0)
        # When the asset is read back
        asset = db.get_asset("WPEA.PA")
        # Then only the quantity and the derived PRUM are stored
        assert asset["base_quantity"] == 20.0
        assert asset["base_prum"] == 5.0

    @pytest.mark.parametrize(
        "quantity, invested", [(0.0, 100.0), (-1.0, 100.0), (20.0, None), (20.0, 0.0)]
    )
    def test_an_opening_position_that_says_nothing_clears_it(
        self, portfolio_data, quantity, invested
    ):
        # Given an opening position already recorded
        db.set_opening_position("WPEA.PA", 20.0, 100.0)
        # When it is set to something that carries no PRUM
        db.set_opening_position("WPEA.PA", quantity, invested)
        # Then the line is back to having no history behind it
        asset = db.get_asset("WPEA.PA")
        assert asset["base_quantity"] == 0.0
        assert asset["base_prum"] is None


class TestEnvelopes:
    def test_envelopes_come_back_in_alphabetical_order(self, database):
        # Given envelopes created in reverse
        db.upsert_envelope("PEA", 300.0)
        db.upsert_envelope("CTO", 100.0)
        # When they are listed
        # Then the name orders them
        assert [e["name"] for e in db.all_envelopes()] == ["CTO", "PEA"]

    def test_upserting_a_known_envelope_only_moves_its_amount(self, database):
        # Given an envelope
        db.upsert_envelope("PEA", 300.0)
        # When it is written again with another amount
        db.upsert_envelope("PEA", 450.0)
        # Then there is still one envelope, with the new amount
        assert db.all_envelopes() == [{"name": "PEA", "monthly_amount": 450.0}]

    def test_an_unknown_envelope_reads_back_as_nothing(self, database):
        # Given an empty database
        # When an envelope is looked up
        assert db.get_envelope("GHOST") is None

    def test_the_asset_count_is_what_gates_a_deletion(self, portfolio_data):
        # Given an envelope holding two assets
        assert db.envelope_asset_count("PEA") == 2
        # When one of them leaves
        db.delete_asset("ESE.PA")
        # Then the count follows
        assert db.envelope_asset_count("PEA") == 1
        assert db.envelope_asset_count("GHOST") == 0

    def test_pruning_only_removes_the_envelopes_nothing_points_at(self, portfolio_data):
        # Given an envelope left behind by its last asset
        db.upsert_envelope("CTO", 100.0)
        # When empty envelopes are pruned
        pruned = db.prune_empty_envelopes()
        # Then the leftover is gone and the one still holding assets stayed
        assert pruned == ["CTO"]
        assert [e["name"] for e in db.all_envelopes()] == ["PEA"]

    def test_pruning_says_so_when_there_is_nothing_to_remove(self, portfolio_data):
        # Given every envelope still holding an asset
        # When empty envelopes are pruned
        # Then nothing is reported, so startup stays quiet
        assert db.prune_empty_envelopes() == []


class TestTransactions:
    def test_transactions_come_back_oldest_first(self, portfolio_data):
        # Given a buy and a later sell
        # When the asset's history is read
        rows = db.transactions_of("WPEA.PA")
        # Then the date orders it
        assert [row["date"] for row in rows] == ["2026-01-10", "2026-02-10"]
        assert rows[0]["fees"] == 1.0

    def test_a_transaction_is_read_back_under_its_own_symbol_only(self, portfolio_data):
        # Given transactions on one asset out of two
        # When the other asset's history is read
        assert db.transactions_of("ESE.PA") == []
        # Then the global listing still shows them
        assert len(db.all_transactions()) == 2

    def test_adding_a_transaction_hands_back_its_identifier(self, portfolio_data):
        # Given a tracked asset
        # When a buy is recorded
        transaction_id = db.add_transaction("ESE.PA", "2026-03-10", "buy", 2.0, 30.0)
        # Then the row can be found again by that id
        assert transaction_id > 0
        assert [row["id"] for row in db.transactions_of("ESE.PA")] == [transaction_id]

    def test_deleting_a_transaction_leaves_the_others_alone(self, portfolio_data):
        # Given two transactions
        first, second = db.all_transactions()
        # When one is deleted
        db.delete_transaction(first["id"])
        # Then only the other one remains
        assert [row["id"] for row in db.all_transactions()] == [second["id"]]

    def test_deleting_an_unknown_transaction_is_not_an_error(self, portfolio_data):
        # Given two transactions
        # When an id nobody knows is deleted
        db.delete_transaction(999)
        # Then nothing happened
        assert len(db.all_transactions()) == 2

    def test_the_last_transaction_date_is_the_most_recent_one(self, portfolio_data):
        # Given a history
        # When the freshness of the data is asked for
        assert db.last_transaction_date() == "2026-02-10"

    def test_an_empty_history_has_no_last_date(self, database):
        # Given no transaction at all
        # When the last date is asked for
        # Then it is None, which the note turns into its own warning
        assert db.last_transaction_date() is None


class TestPriceCache:
    def test_cached_points_come_back_in_date_order(self, database):
        # Given points cached out of order
        db.cache_prices("WPEA.PA", iter([("2026-02-10", 11.0), ("2026-01-10", 10.0)]))
        # When they are read back
        assert db.cached_prices("WPEA.PA") == [
            {"date": "2026-01-10", "price": 10.0},
            {"date": "2026-02-10", "price": 11.0},
        ]

    def test_caching_the_same_day_again_overwrites_the_price(self, database):
        # Given a day already cached
        db.cache_prices("WPEA.PA", iter([("2026-01-10", 10.0)]))
        # When the provider answers a corrected close for it
        db.cache_prices("WPEA.PA", iter([("2026-01-10", 10.5)]))
        # Then the day is stored once, at the new price
        assert db.cached_prices("WPEA.PA") == [{"date": "2026-01-10", "price": 10.5}]

    def test_the_cache_is_per_symbol(self, database):
        # Given two symbols cached
        db.cache_prices("WPEA.PA", iter([("2026-01-10", 10.0)]))
        db.cache_prices("ESE.PA", iter([("2026-01-10", 30.0)]))
        # When one is read
        # Then the other one is not in it
        assert db.cached_prices("ESE.PA") == [{"date": "2026-01-10", "price": 30.0}]

    def test_caching_nothing_is_a_no_op(self, database):
        # Given no points to store
        db.cache_prices("WPEA.PA", iter([]))
        # When the cache is read
        assert db.cached_prices("WPEA.PA") == []
