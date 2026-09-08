"""POST /assets/import: a portfolio export becomes opening positions."""

from __future__ import annotations

import pytest

from src.databases import sqlite as db
from src.services import prices
from tests.test_broker_csv import BOURSO, MOVEMENTS

HITS = {
    "IE000BI8OT95": {"symbol": "CW8.PA", "label": "Amundi World", "currency": "EUR"},
    "FR0000000001": {"symbol": "0P0001.F", "label": "Europe", "currency": "EUR"},
}


@pytest.fixture
def resolver(mocker):
    """A ticker search that knows the two ISINs of the fixture and nothing else."""

    def search(query, limit=10):
        hit = HITS.get(query)
        return [hit] if hit else []

    return mocker.patch.object(prices, "search", side_effect=search)


def post(client, csv=BOURSO, envelope="PEA"):
    return client.post(f"/assets/import?envelope={envelope}", json={"csv": csv})


class TestImport:
    def test_each_row_becomes_an_opening_position(self, client, resolver):
        # Given an export of two lines whose ISINs resolve
        # When it is imported into an envelope that does not exist yet
        response = post(client)
        # Then the envelope was created, and each asset carries the broker's
        # quantity and PRUM as its opening position
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert body["unresolved"] == []
        assert [line["symbol"] for line in body["imported"]] == ["CW8.PA", "0P0001.F"]
        assert db.get_envelope("PEA") == {"name": "PEA", "monthly_amount": 0.0}
        etf = db.get_asset("CW8.PA")
        assert etf["envelope"] == "PEA"
        assert etf["label"] == "AMUNDI MSCI WORLD UCITS ETF"
        assert etf["base_quantity"] == 10.0
        assert etf["base_prum"] == pytest.approx(100.0)

    def test_importing_again_replaces_rather_than_adds(self, client, resolver):
        # Given an export already imported once
        post(client)
        # When the same export comes in again
        post(client)
        # Then the position is what the broker says, not twice it
        assert db.get_asset("CW8.PA")["base_quantity"] == 10.0

    def test_an_asset_already_tracked_keeps_its_envelope_and_weight(
        self, client, resolver
    ):
        # Given an asset the user filed under another envelope with a weight
        db.upsert_envelope("CTO", 100.0)
        db.add_asset("CW8.PA", "My world ETF", "CTO", "EUR", 3.0)
        # When an export lands it in PEA
        post(client, envelope="PEA")
        # Then only its opening position moved
        asset = db.get_asset("CW8.PA")
        assert asset["envelope"] == "CTO"
        assert asset["weight"] == 3.0
        assert asset["label"] == "My world ETF"
        assert asset["base_quantity"] == 10.0

    def test_a_row_no_ticker_answers_to_is_reported_not_written(self, client, mocker):
        # Given a search that resolves the ETF and nothing else
        mocker.patch.object(
            prices,
            "search",
            side_effect=lambda q, limit=10: [HITS[q]] if q == "IE000BI8OT95" else [],
        )
        # When the export is imported
        body = post(client).json()
        # Then the fund is listed as unresolved, and nothing exists for it
        assert body["unresolved"] == [
            {"isin": "FR0000000001", "name": "FONDS EUROPE CROISSANCE"}
        ]
        assert len(body["imported"]) == 1
        assert db.get_asset("0P0001.F") is None

    def test_the_hit_currency_is_kept(self, client, mocker):
        mocker.patch.object(
            prices,
            "search",
            return_value=[{"symbol": "VTI", "label": "Vanguard", "currency": "USD"}],
        )
        post(client, csv="isin;quantity;pru\nUS0000000001;2;50\n")
        assert db.get_asset("VTI")["currency"] == "USD"


class TestRefusals:
    def test_a_movements_export_is_a_422_with_the_reason(self, client, resolver):
        response = post(client, csv=MOVEMENTS)
        assert response.status_code == 422
        assert "portfolio" in response.json()["detail"]
        assert db.all_assets() == []

    def test_an_empty_body_is_rejected_by_validation(self, client, resolver):
        assert post(client, csv="").status_code == 422

    def test_the_envelope_is_required(self, client, resolver):
        response = client.post("/assets/import", json={"csv": BOURSO})
        assert response.status_code == 422

    def test_the_route_is_behind_the_session(self, guarded_client):
        response = guarded_client.post(
            "/assets/import?envelope=PEA", json={"csv": BOURSO}
        )
        assert response.status_code == 401
