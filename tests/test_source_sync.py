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
