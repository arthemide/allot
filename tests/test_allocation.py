"""The monthly split, and the one place envelope market values are converted.

An envelope amount is invariant: multipliers only move money between the
assets of a single envelope, never across envelopes.
"""

import pytest

from src.services import allocation

ASSETS = [
    {"symbol": "WPEA.PA", "envelope": "PEA", "currency": "EUR", "weight": 1.0},
    {"symbol": "ETH-USD", "envelope": "CRYPTO", "currency": "USD", "weight": 3.0},
    {"symbol": "CW8.PA", "envelope": "CRYPTO", "currency": "EUR", "weight": 1.0},
]

ENVELOPES = [
    {"name": "CRYPTO", "monthly_amount": 100.0},
    {"name": "PEA", "monthly_amount": 400.0},
]

POSITIONS = [
    {"symbol": "WPEA.PA", "price": 6.0, "prum": 6.0, "market_value": 600.0},
    {"symbol": "ETH-USD", "price": 2000.0, "prum": 2000.0, "market_value": 1080.0},
    {"symbol": "CW8.PA", "price": 50.0, "prum": 50.0, "market_value": 500.0},
]


@pytest.fixture
def offline(mocker):
    mocker.patch.object(allocation.db, "all_assets", return_value=ASSETS)
    mocker.patch.object(allocation.db, "all_envelopes", return_value=ENVELOPES)
    mocker.patch.object(allocation.portfolio, "all_positions", return_value=POSITIONS)
    mocker.patch.object(allocation.prices, "eur_usd_rate", return_value=1.08)


def _by_name(plan):
    return {envelope["envelope"]: envelope for envelope in plan}


class TestPlan:
    def test_envelope_total_is_split_across_its_assets(self, offline):
        # Given a 100 EUR envelope holding two assets weighted 3 and 1
        crypto = _by_name(allocation.plan())["CRYPTO"]
        # When the plan is computed, prices sitting exactly on the PRUM
        # Then the split follows the weights and adds back up to the envelope
        amounts = {a["symbol"]: a["amount"] for a in crypto["assets"]}
        assert amounts["ETH-USD"] == pytest.approx(75.0)
        assert amounts["CW8.PA"] == pytest.approx(25.0)
        assert sum(amounts.values()) == pytest.approx(crypto["amount"])

    def test_a_price_below_the_prum_pulls_money_from_the_same_envelope(
        self, offline, mocker
    ):
        # Given one asset trading 20% under its PRUM
        positions = [dict(p) for p in POSITIONS]
        positions[1] = {**positions[1], "price": 1600.0}
        mocker.patch.object(
            allocation.portfolio, "all_positions", return_value=positions
        )
        # When the plan is computed
        crypto = _by_name(allocation.plan())["CRYPTO"]
        amounts = {a["symbol"]: a["amount"] for a in crypto["assets"]}
        # Then it gets more, its neighbour gets less, and the envelope is
        # unchanged: nothing was taken from the PEA
        assert amounts["ETH-USD"] > 75.0
        assert amounts["CW8.PA"] < 25.0
        assert sum(amounts.values()) == pytest.approx(100.0)

    def test_market_value_is_converted_asset_by_asset(self, offline):
        # Given a CRYPTO envelope holding 1080 USD and 500 EUR
        crypto = _by_name(allocation.plan())["CRYPTO"]
        # When the plan is computed at 1.08 USD per EUR
        # Then only the USD line is converted: 1080 / 1.08 + 500
        assert crypto["market_value"] == pytest.approx(1500.0)

    def test_an_asset_with_no_price_falls_back_to_a_neutral_multiplier(
        self, offline, mocker
    ):
        # Given an asset whose ticker does not answer
        positions = [dict(p) for p in POSITIONS]
        positions[1] = {**positions[1], "price": None, "market_value": None}
        mocker.patch.object(
            allocation.portfolio, "all_positions", return_value=positions
        )
        # When the plan is computed
        crypto = _by_name(allocation.plan())["CRYPTO"]
        multipliers = {a["symbol"]: a["multiplier"] for a in crypto["assets"]}
        # Then it is neither favoured nor penalised, and it counts for nothing
        # in the envelope's market value
        assert multipliers["ETH-USD"] == 1.0
        assert crypto["market_value"] == pytest.approx(500.0)
