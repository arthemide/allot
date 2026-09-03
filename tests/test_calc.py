"""Unit tests for the pure calculation module. No database, no network."""

from datetime import date

import pytest

from src import calc
from src.calc import (
    Trade,
    multiplier,
    position,
    prum_after_buy,
    quantity_for_target_prum,
    renormalize,
)


class TestPosition:
    def test_prum_includes_fees(self):
        # Given two buys carrying 10 of fees between them
        trades = [
            Trade(side="buy", quantity=1.0, unit_price=100.0, fees=6.0),
            Trade(side="buy", quantity=1.0, unit_price=200.0, fees=4.0),
        ]
        # When the position is recomputed
        result = position(trades)
        # Then the fees are spread over the bought quantity
        assert result.quantity == 2.0
        assert result.prum == pytest.approx((100.0 + 200.0 + 10.0) / 2.0)

    def test_sell_reduces_quantity_but_not_prum(self):
        # Given two buys followed by a sell at a very different price
        trades = [
            Trade(side="buy", quantity=1.0, unit_price=100.0),
            Trade(side="buy", quantity=1.0, unit_price=200.0),
            Trade(side="sell", quantity=0.5, unit_price=900.0),
        ]
        # When the position is recomputed
        result = position(trades)
        # Then only the quantity moves
        assert result.quantity == pytest.approx(1.5)
        assert result.prum == pytest.approx(150.0)

    def test_opening_position_behaves_like_a_first_buy(self):
        # Given an opening position of 2 at 50 and one buy of 2 at 150
        result = position(
            [Trade(side="buy", quantity=2.0, unit_price=150.0)],
            base_quantity=2.0,
            base_prum=50.0,
        )
        # Then both are averaged together
        assert result.quantity == pytest.approx(4.0)
        assert result.prum == pytest.approx(100.0)

    def test_invested_follows_quantity_and_prum(self):
        result = position([Trade(side="buy", quantity=2.0, unit_price=100.0)])
        assert result.invested == pytest.approx(200.0)

    def test_empty_history_is_flat(self):
        assert position([]) == position([], 0.0, None)
        assert position([]).quantity == 0.0

    def test_unknown_side_is_rejected(self):
        with pytest.raises(ValueError):
            position([Trade(side="swap", quantity=1.0, unit_price=100.0)])


class TestPrumAfterBuy:
    def test_buying_below_prum_lowers_it(self):
        # Given 1 unit held at 200, buying 100 worth at 100
        bought, new_prum = prum_after_buy(
            quantity=1.0, prum=200.0, price=100.0, amount=100.0
        )
        assert bought == pytest.approx(1.0)
        assert new_prum == pytest.approx(150.0)

    def test_fees_are_included_in_the_amount(self):
        # Given 10 of fees inside a 110 order, only 100 buys shares
        bought, new_prum = prum_after_buy(1.0, 200.0, 100.0, amount=110.0, fees=10.0)
        assert bought == pytest.approx(1.0)
        assert new_prum == pytest.approx((200.0 + 110.0) / 2.0)

    def test_zero_price_is_rejected(self):
        with pytest.raises(ValueError):
            prum_after_buy(1.0, 200.0, 0.0, 100.0)


class TestQuantityForTargetPrum:
    def test_reachable_target(self):
        # Given 1 unit at a PRUM of 100 and a price of 80, targeting 90
        result = quantity_for_target_prum(
            quantity=1.0, prum=100.0, price=80.0, target=90.0
        )
        assert result is not None
        needed, amount = result
        assert needed == pytest.approx(1.0)
        assert amount == pytest.approx(80.0)

    def test_reaching_the_target_actually_reaches_it(self):
        needed, amount = quantity_for_target_prum(3.0, 120.0, 60.0, 90.0)
        after = position(
            [Trade(side="buy", quantity=needed, unit_price=60.0)],
            base_quantity=3.0,
            base_prum=120.0,
        )
        assert after.prum == pytest.approx(90.0)

    def test_target_above_price_is_unreachable(self):
        # When the price is at or above the target, buying can never get there
        assert quantity_for_target_prum(1.0, 100.0, 95.0, 90.0) is None
        assert quantity_for_target_prum(1.0, 100.0, 90.0, 90.0) is None

    def test_target_above_current_prum_is_unreachable(self):
        assert quantity_for_target_prum(1.0, 100.0, 80.0, 110.0) is None


class TestMultiplier:
    def test_more_than_ten_percent_below_prum_buys_more(self):
        assert multiplier(price=85.0, prum=100.0) == 1.5

    def test_more_than_ten_percent_above_prum_buys_less(self):
        assert multiplier(price=115.0, prum=100.0) == 0.5

    def test_inside_the_band_is_neutral(self):
        assert multiplier(100.0, 100.0) == 1.0
        assert multiplier(90.0, 100.0) == 1.0
        assert multiplier(110.0, 100.0) == 1.0

    def test_no_prum_is_neutral(self):
        assert multiplier(100.0, 0.0) == 1.0


class TestRenormalize:
    def test_single_asset_envelope_ignores_the_multiplier(self):
        # This is intended: an envelope never draws from another one
        assert renormalize(440.0, [(1.0, 1.5)]) == [pytest.approx(440.0)]
        assert renormalize(440.0, [(1.0, 0.5)]) == [pytest.approx(440.0)]

    def test_two_asset_envelope_shifts_between_them(self):
        # Given equal weights, one boosted and one damped
        amounts = renormalize(165.0, [(0.5, 1.5), (0.5, 0.5)])
        # Then the split moves but the envelope total is unchanged
        assert amounts[0] == pytest.approx(123.75)
        assert amounts[1] == pytest.approx(41.25)
        assert sum(amounts) == pytest.approx(165.0)

    def test_uneven_weights_are_respected(self):
        amounts = renormalize(220.0, [(0.75, 1.0), (0.25, 1.0)])
        assert amounts == [pytest.approx(165.0), pytest.approx(55.0)]

    def test_all_weights_zero_yields_nothing(self):
        assert renormalize(100.0, [(0.0, 1.0), (0.0, 1.5)]) == [0.0, 0.0]


class TestMonthsElapsed:
    def test_the_month_a_strategy_starts_counts(self):
        # Given a strategy started on the 1st
        # When the month is read halfway through
        # Then its contribution has landed: one month, not zero
        assert calc.months_elapsed(date(2026, 9, 1), date(2026, 9, 15)) == 1

    def test_it_counts_calendar_months_not_days(self):
        # The 25th to the 2nd of the next month is a new contribution, even
        # though barely a week went by
        assert calc.months_elapsed(date(2026, 9, 25), date(2026, 10, 2)) == 2

    def test_it_crosses_years(self):
        assert calc.months_elapsed(date(2026, 9, 1), date(2027, 2, 3)) == 6

    def test_a_start_in_the_future_counts_for_nothing(self):
        # Rather than for a negative number of months
        assert calc.months_elapsed(date(2027, 1, 1), date(2026, 9, 15)) == 0


class TestAddMonths:
    def test_it_walks_forward(self):
        assert calc.add_months(date(2026, 9, 1), 2) == date(2026, 11, 1)

    def test_it_crosses_the_year(self):
        assert calc.add_months(date(2026, 12, 1), 1) == date(2027, 1, 1)


def _candidate(symbol, price, weight=1.0, held=0.0):
    return calc.Candidate(symbol=symbol, price=price, weight=weight, held_value=held)


class TestBuyLots:
    def test_a_budget_below_the_cheapest_share_buys_nothing(self):
        # Given 300 EUR and a share at 600
        lots, carry = calc.buy_lots(300.0, [_candidate("MC.PA", 600.0)])
        # Then nothing is bought and everything is carried: a third of a share
        # cannot be ordered, and saying so is the whole point
        assert lots == []
        assert carry == 300.0

    def test_it_buys_what_it_can_and_carries_the_rest(self):
        lots, carry = calc.buy_lots(650.0, [_candidate("MC.PA", 600.0)])
        assert [(lot.symbol, lot.units, lot.amount) for lot in lots] == [
            ("MC.PA", 1, 600.0)
        ]
        assert carry == 50.0

    def test_the_dearer_share_goes_first_when_nothing_separates_them(self):
        # Given equal weights, one share at 600 and one at 55
        lots, carry = calc.buy_lots(
            650.0, [_candidate("MC.PA", 600.0), _candidate("TTE.PA", 55.0)]
        )
        # Then the expensive one is taken: the cheap one can still be bought
        # later with what is left, the reverse starves it for another month
        assert [lot.symbol for lot in lots] == ["MC.PA"]
        assert carry == 50.0

    def test_the_most_under_weighted_asset_is_served_first(self):
        # Given two equally weighted shares, one already held in quantity
        lots, _ = calc.buy_lots(
            100.0,
            [
                _candidate("A.PA", 50.0, held=1000.0),
                _candidate("B.PA", 50.0, held=0.0),
            ],
        )
        # Then the one lagging behind gets the first share
        assert lots[0].symbol == "B.PA"

    def test_several_shares_of_the_same_asset_when_the_budget_allows(self):
        lots, carry = calc.buy_lots(260.0, [_candidate("TTE.PA", 50.0)])
        assert (lots[0].units, lots[0].amount) == (5, 250.0)
        assert carry == 10.0

    def test_an_asset_without_a_price_is_left_out(self):
        # A quote that did not come back cannot be turned into an order
        lots, carry = calc.buy_lots(500.0, [_candidate("GHOST.PA", 0.0)])
        assert lots == []
        assert carry == 500.0

    def test_a_weightless_asset_is_left_out(self):
        # Held but never topped up: no money goes its way
        lots, carry = calc.buy_lots(500.0, [_candidate("MC.PA", 100.0, weight=0.0)])
        assert lots == []
        assert carry == 500.0

    def test_the_loop_is_bounded(self):
        # Given a budget that would buy thousands of one-euro shares
        lots, _ = calc.buy_lots(10_000.0, [_candidate("CENT.PA", 1.0)])
        # Then it stops at the cap rather than spinning
        assert lots[0].units == calc.MAX_LOTS

    def test_the_same_portfolio_always_gives_the_same_plan(self):
        candidates = [_candidate("A.PA", 100.0), _candidate("B.PA", 100.0)]
        first = calc.buy_lots(300.0, candidates)
        second = calc.buy_lots(300.0, candidates)
        assert first == second


class TestIsFractional:
    def test_a_crypto_pair_is_bought_by_the_amount(self):
        assert calc.is_fractional("ETH-USD")
        assert calc.is_fractional("BTC-EUR")

    def test_a_share_is_bought_whole_until_proven_otherwise(self):
        # The careful default: it makes an envelope save up rather than
        # produce an order the broker would refuse
        assert not calc.is_fractional("MC.PA")

    def test_a_fraction_already_traded_settles_it(self):
        # Whatever the ticker looks like: a quantity of 0.4 is proof
        assert calc.is_fractional("MC.PA", traded_in_fractions=True)
