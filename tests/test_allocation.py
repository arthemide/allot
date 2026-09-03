"""The monthly split, and the one place envelope market values are converted.

An envelope amount is invariant: multipliers only move money between the
assets of a single envelope, never across envelopes.
"""

from datetime import date

import pytest

from src.services import allocation


def _asset(symbol, envelope, currency, weight):
    return {
        "symbol": symbol,
        "envelope": envelope,
        "currency": currency,
        "weight": weight,
    }


ASSETS = [
    _asset("WPEA.PA", "PEA", "EUR", 1.0),
    _asset("ETH-USD", "CRYPTO", "USD", 3.0),
    _asset("CW8.PA", "CRYPTO", "EUR", 1.0),
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


class TestCashRegime:
    """An envelope that declares a start buys whole shares out of its cash."""

    @pytest.fixture
    def cto(self, mocker):
        # A 100 EUR/month CTO holding one 600 EUR share, nothing fractional
        mocker.patch.object(
            allocation.db,
            "all_assets",
            return_value=[_asset("MC.PA", "CTO", "EUR", 1.0)],
        )
        mocker.patch.object(
            allocation.db,
            "all_envelopes",
            return_value=[{"name": "CTO", "monthly_amount": 100.0}],
        )
        mocker.patch.object(
            allocation.portfolio,
            "all_positions",
            return_value=[
                {"symbol": "MC.PA", "price": 600.0, "prum": 600.0, "market_value": 0.0}
            ],
        )
        mocker.patch.object(allocation.prices, "eur_usd_rate", return_value=1.08)

    def _with_cash(self, mocker, amount):
        mocker.patch.object(
            allocation.cash,
            "available",
            return_value={"available": amount, "started_on": "2026-01-01"},
        )

    def test_a_cagnotte_too_small_buys_nothing_and_waits(self, cto, mocker):
        # Given 320 EUR saved against a 600 EUR share
        self._with_cash(mocker, 320.0)
        # When the month is planned
        envelope = _by_name(allocation.plan())["CTO"]
        # Then no order is produced, and the whole cagnotte is carried over
        assert envelope["assets"] == []
        assert envelope["carry"] == 320.0
        assert envelope["waiting"][0]["symbol"] == "MC.PA"

    def test_it_says_what_is_missing_and_when(self, cto, mocker):
        self._with_cash(mocker, 320.0)
        waiting = _by_name(allocation.plan())["CTO"]["waiting"][0]
        # 280 missing at 100 a month
        assert waiting["missing"] == pytest.approx(280.0)
        assert waiting["months_left"] == 3

    def test_a_full_cagnotte_buys_the_share_and_carries_the_change(self, cto, mocker):
        # Given six months of saving
        self._with_cash(mocker, 650.0)
        envelope = _by_name(allocation.plan())["CTO"]
        # Then one share is bought, and the rest waits for next month
        assert (envelope["assets"][0]["symbol"], envelope["assets"][0]["units"]) == (
            "MC.PA",
            1,
        )
        assert envelope["assets"][0]["amount"] == 600.0
        assert envelope["carry"] == 50.0
        assert envelope["waiting"] == []

    def test_a_weightless_asset_waits_for_nothing(self, cto, mocker):
        # Given a second asset held but never topped up
        mocker.patch.object(
            allocation.db,
            "all_assets",
            return_value=[
                _asset("MC.PA", "CTO", "EUR", 1.0),
                _asset("OLD.PA", "CTO", "EUR", 0.0),
            ],
        )
        mocker.patch.object(
            allocation.portfolio,
            "all_positions",
            return_value=[
                {"symbol": "MC.PA", "price": 600.0, "prum": 600.0, "market_value": 0.0},
                {"symbol": "OLD.PA", "price": 20.0, "prum": 20.0, "market_value": 0.0},
            ],
        )
        self._with_cash(mocker, 320.0)
        envelope = _by_name(allocation.plan())["CTO"]
        # Then it is not listed as something the envelope is saving up for:
        # no money was ever going its way
        assert [m["symbol"] for m in envelope["waiting"]] == ["MC.PA"]

    def test_what_is_missing_counts_the_money_left_for_shares(self, cto, mocker):
        # Given an envelope whose cash is shared with a fractional line
        mocker.patch.object(
            allocation.db,
            "all_assets",
            return_value=[
                _asset("MC.PA", "CTO", "EUR", 1.0),
                _asset("ETH-USD", "CTO", "USD", 1.0),
            ],
        )
        mocker.patch.object(
            allocation.portfolio,
            "all_positions",
            return_value=[
                {"symbol": "MC.PA", "price": 600.0, "prum": 600.0, "market_value": 0.0},
                {
                    "symbol": "ETH-USD",
                    "price": 100.0,
                    "prum": 100.0,
                    "market_value": 0.0,
                },
            ],
        )
        self._with_cash(mocker, 400.0)
        envelope = _by_name(allocation.plan())["CTO"]
        # Then the 200 that went to the crypto line are not counted as
        # available for the share: 600 - 200 left, not 600 - 400
        assert envelope["waiting"][0]["missing"] == pytest.approx(400.0)

    def test_a_fractional_asset_keeps_its_euro_amount(self, cto, mocker):
        # Given a line already traded by the tenth: the broker has settled it
        mocker.patch.object(
            allocation.db, "symbols_traded_in_fractions", return_value={"MC.PA"}
        )
        self._with_cash(mocker, 320.0)
        envelope = _by_name(allocation.plan())["CTO"]
        # Then the whole cagnotte goes in, no rounding involved
        assert envelope["assets"][0]["amount"] == 320.0
        assert envelope["assets"][0]["units"] is None

    def test_without_a_start_the_monthly_amount_is_split_as_before(self, cto, mocker):
        # Given an envelope that tracks no cash, holding a 600 EUR share
        mocker.patch.object(allocation.cash, "available", return_value=None)
        envelope = _by_name(allocation.plan())["CTO"]
        # Then nothing changed: the euro split, and no notion of shares
        assert envelope["assets"][0]["amount"] == 100.0
        assert envelope["assets"][0]["units"] is None
        assert envelope["waiting"] == []


class TestProjection:
    @pytest.fixture
    def cto(self, mocker):
        mocker.patch.object(
            allocation.db,
            "all_assets",
            return_value=[_asset("MC.PA", "CTO", "EUR", 1.0)],
        )
        mocker.patch.object(
            allocation.db,
            "all_envelopes",
            return_value=[{"name": "CTO", "monthly_amount": 100.0}],
        )
        mocker.patch.object(
            allocation.portfolio,
            "all_positions",
            return_value=[
                {"symbol": "MC.PA", "price": 600.0, "prum": 600.0, "market_value": 0.0}
            ],
        )
        mocker.patch.object(allocation.prices, "eur_usd_rate", return_value=1.08)
        mocker.patch.object(
            allocation.cash,
            "available",
            return_value={"available": 320.0, "started_on": "2026-01-01"},
        )

    def test_it_walks_the_months_forward(self, cto):
        months = allocation.projection(date(2026, 9, 15), 4)
        assert [m["month"] for m in months] == [
            date(2026, 10, 1),
            date(2026, 11, 1),
            date(2026, 12, 1),
            date(2027, 1, 1),
        ]

    def test_the_cagnotte_keeps_growing_until_it_can_buy(self, cto):
        months = allocation.projection(date(2026, 9, 15), 4)
        bought = {
            month["month"].month: month["envelopes"][0]["assets"] for month in months
        }
        # 320 now, then 420, 520, 620: the share lands in the third month
        assert bought[10] == [] and bought[11] == []
        assert bought[12][0]["units"] == 1
        # And what is left starts over from the change
        assert months[3]["envelopes"][0]["budget"] == pytest.approx(120.0)

    def test_an_envelope_without_cash_repeats_the_same_split(self, cto, mocker):
        mocker.patch.object(allocation.cash, "available", return_value=None)
        months = allocation.projection(date(2026, 9, 15), 2)
        # It has nothing to accumulate, but it still has something to do
        for month in months:
            assert month["envelopes"][0]["assets"][0]["amount"] == 100.0
            assert month["envelopes"][0]["carry"] == 0.0
