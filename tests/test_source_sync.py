"""A source snapshot, from the choices it needs to the positions it sets.

Afer is the source here: no ISIN, a quantity and what was paid in per line,
so every line is mapped to a ticker by hand.
"""

from __future__ import annotations

import pytest

from src.databases import sqlite as db
from src.models.schema import (
    AccountPlacement,
    LineMapping,
    PositionRow,
    SourceSnapshot,
)
from src.services import source_sync

SNAPSHOT = {
    "source": "afer",
    "version": 1,
    "read_on": "2026-10-14",
    "accounts": [
        {
            "label": "Afer Multisupport",
            "product": "Assurance vie",
            "balance": 12345.67,
            "lines": [
                {
                    "label": "Afer Actions Monde C/D",
                    "quantity": 4,
                    "unit_value": 50,
                    "valuation": 200,
                    "invested": 160,
                },
                # The euro fund: no quantity, never a position.
                {"label": "Fonds Garanti en Euros", "valuation": 12000},
            ],
        }
    ],
}

ACCOUNT = "Afer Multisupport"
FUND = "Afer Actions Monde C/D"


@pytest.fixture
def rows():
    return source_sync.rows_from_snapshot(SourceSnapshot.model_validate(SNAPSHOT))


class TestPending:
    def test_a_new_account_and_its_lines_need_a_choice(self, database, rows):
        # Given an envelope named like nothing the source reports
        db.upsert_envelope("Assurance vie", 0.0)
        # When the first reading comes in
        choices = source_sync.pending("afer", rows)
        # Then the account waits for an envelope, and the one fund for a ticker
        assert [(a.account, a.lines) for a in choices.accounts] == [(ACCOUNT, 1)]
        assert [line.label for line in choices.lines] == [FUND]

    def test_nothing_is_asked_twice(self, database, rows):
        # Given choices already made
        db.upsert_envelope("AV", 0.0)
        db.set_source_account("afer", ACCOUNT, "AV")
        db.set_source_line("afer", FUND, "AFERMONDE")
        # Then the next reading needs none
        choices = source_sync.pending("afer", rows)
        assert choices.accounts == [] and choices.lines == []


class TestPlace:
    def test_an_account_without_an_envelope_is_refused_and_nothing_written(
        self, database, rows
    ):
        # When only the line is answered
        with pytest.raises(ValueError, match=ACCOUNT):
            source_sync.place(
                "afer", [], [LineMapping(label=FUND, symbol="AFERMONDE")], rows
            )
        # Then not even the line was remembered
        assert db.source_lines("afer") == {}

    def test_a_blank_choice_leaves_the_account_out(self, database, rows):
        source_sync.place(
            "afer", [AccountPlacement(account=ACCOUNT, envelope="  ")], [], rows
        )
        assert db.source_accounts("afer") == {ACCOUNT: None}


class TestApply:
    def test_a_line_mapped_to_a_new_ticker_becomes_its_asset(
        self, database, offline, rows
    ):
        # Given the account placed and the fund mapped to a ticker not tracked yet
        source_sync.place(
            "afer",
            [AccountPlacement(account=ACCOUNT, envelope="AV")],
            [LineMapping(label=FUND, symbol="AFERMONDE")],
            rows,
        )
        # When the reading is applied
        report = source_sync.apply("afer", rows)
        # Then the asset exists, bought by amount, at what was paid in per unit
        assert [line["symbol"] for line in report["imported"]] == ["AFERMONDE"]
        asset = db.get_asset("AFERMONDE")
        assert asset["envelope"] == "AV"
        assert asset["by_amount"] == 1
        assert asset["base_quantity"] == 4
        assert asset["base_prum"] == pytest.approx(40.0)


class TestRoutes:
    def test_the_preview_lists_the_choices(self, client):
        response = client.post("/assets/imports/preview", json=SNAPSHOT)
        assert response.status_code == 200
        assert response.json()["accounts"][0]["account"] == ACCOUNT

    def test_an_import_with_its_choices_goes_through(self, client):
        response = client.post(
            "/assets/imports",
            json={
                "snapshot": SNAPSHOT,
                "placements": [{"account": ACCOUNT, "envelope": "AV"}],
                "mappings": [{"label": FUND, "symbol": "AFERMONDE"}],
            },
        )
        assert response.status_code == 200
        assert response.json()["imported"][0]["symbol"] == "AFERMONDE"

    def test_a_missing_envelope_is_a_422(self, client):
        response = client.post("/assets/imports", json={"snapshot": SNAPSHOT})
        assert response.status_code == 422
        assert ACCOUNT in response.json()["detail"]

    def test_an_unknown_source_is_a_404(self, client):
        response = client.post(
            "/assets/imports/preview", json={**SNAPSHOT, "source": "nowhere"}
        )
        assert response.status_code == 404


def _place_and_apply(rows, symbol="AFERMONDE"):
    source_sync.place(
        "afer",
        [AccountPlacement(account=ACCOUNT, envelope="AV")],
        [LineMapping(label=FUND, symbol=symbol)],
        rows,
    )
    return source_sync.apply("afer", rows)


class TestScope:
    def test_an_asset_of_the_envelope_tracked_by_hand_is_left_alone(
        self, database, offline, rows
    ):
        # Given the envelope already holds an asset bought by hand
        db.upsert_envelope("AV", 0.0)
        db.add_asset("CW8.PA", "Amundi World", "AV", "EUR")
        db.set_opening_position("CW8.PA", 3.0, 1500.0)
        # When the Afer account is imported into it
        _place_and_apply(rows)
        # Then the source only spoke for its own line
        assert db.get_asset("CW8.PA")["base_quantity"] == 3.0

    def test_a_fund_the_source_no_longer_reports_is_zeroed(
        self, database, offline, rows
    ):
        # Given a first import, then a reading where only the euro fund is left
        _place_and_apply(rows)
        account = SNAPSHOT["accounts"][0]
        gone = SourceSnapshot.model_validate(
            {**SNAPSHOT, "accounts": [{**account, "lines": account["lines"][1:]}]}
        )
        # When it is applied
        source_sync.apply("afer", source_sync.rows_from_snapshot(gone))
        # Then the fund the source mapped is sold off
        assert db.get_asset("AFERMONDE")["base_quantity"] == 0

    def test_an_account_read_without_any_line_zeroes_nothing(
        self, database, offline, rows
    ):
        # Given a first import, then a reading that found no line at all, as
        # when the site changed its tables
        _place_and_apply(rows)
        empty = SourceSnapshot.model_validate(
            {**SNAPSHOT, "accounts": [{**SNAPSHOT["accounts"][0], "lines": []}]}
        )
        # When it is applied
        source_sync.apply("afer", source_sync.rows_from_snapshot(empty))
        # Then nothing is taken for sold
        assert db.get_asset("AFERMONDE")["base_quantity"] == 4

    def test_a_bank_sync_still_zeroes_what_it_no_longer_reports(
        self, database, offline
    ):
        # Given an asset of the envelope nobody mapped, tracked by hand
        db.upsert_envelope("PEA", 0.0)
        db.add_asset("CW8.PA", "Amundi World", "PEA", "EUR")
        db.set_opening_position("CW8.PA", 3.0, 1500.0)
        db.set_source_account("bourso", "PEA", "PEA")
        cash = PositionRow(
            source="bourso", account="PEA", support_type="cash", label="Cash", value=5
        )
        # When the bank no longer reports it
        source_sync.apply("bourso", [cash])
        # Then it was sold, as a bank sync has always said
        assert db.get_asset("CW8.PA")["base_quantity"] == 0


class TestOneSourcePerEnvelope:
    def test_an_envelope_a_bank_account_syncs_into_is_refused(self, database, rows):
        # Given a BoursoBank account syncing into AV
        db.upsert_envelope("AV", 0.0)
        db.set_source_account("bourso", "BOURSO VIE", "AV")
        # When the Afer contract is placed there too
        with pytest.raises(ValueError, match="BoursoBank's account BOURSO VIE"):
            source_sync.place(
                "afer",
                [AccountPlacement(account=ACCOUNT, envelope="AV")],
                [LineMapping(label=FUND, symbol="AFERMONDE")],
                rows,
            )
        # Then nothing was written, not even the line's ticker
        assert db.source_accounts("afer") == {}
        assert db.source_lines("afer") == {}

    def test_it_is_not_even_offered(self, database, rows):
        # Given an envelope named like the Afer account, already Bourso's
        db.upsert_envelope(ACCOUNT, 0.0)
        db.set_source_account("bourso", "PEA", ACCOUNT)
        # Then the preview does not offer it as the default
        assert source_sync.pending("afer", rows).accounts[0].envelope is None

    def test_two_accounts_of_the_same_source_may_share_one(self, database, rows):
        # A PEA and a PEA-PME at the bank, both in one envelope: one source
        db.upsert_envelope("AV", 0.0)
        db.set_source_account("afer", "Another contract", "AV")
        source_sync.place(
            "afer", [AccountPlacement(account=ACCOUNT, envelope="AV")], [], rows
        )
        assert db.source_accounts("afer")[ACCOUNT] == "AV"


class TestResolution:
    def test_the_chosen_ticker_wins_over_the_search_ranking(
        self, database, offline, mocker, rows
    ):
        # Given a search that ranks another listing first
        mocker.patch(
            "src.services.prices.search",
            return_value=[
                {"symbol": "AFERMONDE.X", "currency": "USD"},
                {"symbol": "AFERMONDE", "currency": "EUR"},
            ],
        )
        # When the line mapped to AFERMONDE is applied
        report = _place_and_apply(rows)
        # Then it is AFERMONDE, in the currency of its own listing
        assert [line["symbol"] for line in report["imported"]] == ["AFERMONDE"]
        assert db.get_asset("AFERMONDE")["currency"] == "EUR"

    def test_a_line_the_source_buys_by_the_share_stays_so(self, database, offline):
        snapshot = {**SNAPSHOT}
        snapshot["accounts"] = [
            {
                **SNAPSHOT["accounts"][0],
                "lines": [{**SNAPSHOT["accounts"][0]["lines"][0], "by_amount": False}],
            }
        ]
        rows = source_sync.rows_from_snapshot(SourceSnapshot.model_validate(snapshot))
        _place_and_apply(rows)
        assert db.get_asset("AFERMONDE")["by_amount"] == 0


class TestAvailable:
    def test_the_euro_fund_is_reported_not_written(self, database, offline, rows):
        # When the contract is imported
        report = _place_and_apply(rows)
        # Then its euro fund is shown with its envelope, and no asset holds it
        assert report["available"] == [
            {
                "account": ACCOUNT,
                "envelope": "AV",
                "label": "Fonds Garanti en Euros",
                "value": 12000.0,
                "currency": "EUR",
            }
        ]
        assert [a["symbol"] for a in db.all_assets()] == ["AFERMONDE"]

    def test_an_account_left_out_shows_nothing(self, database, offline, rows):
        source_sync.place(
            "afer", [AccountPlacement(account=ACCOUNT, envelope=None)], [], rows
        )
        assert source_sync.apply("afer", rows)["available"] == []


class TestPendingLines:
    def test_a_line_with_an_isin_is_resolved_by_the_search_not_by_hand(self, database):
        tagged = {**SNAPSHOT["accounts"][0]["lines"][0], "isin": "FR0010821470"}
        snapshot = {
            **SNAPSHOT,
            "accounts": [{**SNAPSHOT["accounts"][0], "lines": [tagged]}],
        }
        rows = source_sync.rows_from_snapshot(SourceSnapshot.model_validate(snapshot))
        assert source_sync.pending("afer", rows).lines == []

    def test_the_lines_of_an_account_left_out_are_not_asked(self, database, rows):
        db.set_source_account("afer", ACCOUNT, None)
        assert source_sync.pending("afer", rows).lines == []
