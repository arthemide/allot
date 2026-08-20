"""Unit tests for the pure calculation module. No database, no network."""

import pytest

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
        trades = [Trade("buy", 1.0, 100.0, fees=6.0), Trade("buy", 1.0, 200.0, fees=4.0)]
        # When the position is recomputed
        result = position(trades)
        # Then the fees are spread over the bought quantity
        assert result.quantity == 2.0
        assert result.prum == pytest.approx((100.0 + 200.0 + 10.0) / 2.0)

    def test_sell_reduces_quantity_but_not_prum(self):
        # Given two buys followed by a sell at a very different price
        trades = [
            Trade("buy", 1.0, 100.0),
            Trade("buy", 1.0, 200.0),
            Trade("sell", 0.5, 900.0),
        ]
        # When the position is recomputed
        result = position(trades)
        # Then only the quantity moves
        assert result.quantity == pytest.approx(1.5)
        assert result.prum == pytest.approx(150.0)

    def test_opening_position_behaves_like_a_first_buy(self):
        # Given an opening position of 2 at 50 and one buy of 2 at 150
        result = position([Trade("buy", 2.0, 150.0)], base_quantity=2.0, base_prum=50.0)
        # Then both are averaged together
        assert result.quantity == pytest.approx(4.0)
        assert result.prum == pytest.approx(100.0)

    def test_invested_follows_quantity_and_prum(self):
        result = position([Trade("buy", 2.0, 100.0)])
        assert result.invested == pytest.approx(200.0)

    def test_empty_history_is_flat(self):
        assert position([]) == position([], 0.0, None)
        assert position([]).quantity == 0.0

    def test_unknown_side_is_rejected(self):
        with pytest.raises(ValueError):
            position([Trade("swap", 1.0, 100.0)])


class TestPrumAfterBuy:
    def test_buying_below_prum_lowers_it(self):
        # Given 1 unit held at 200, buying 100 worth at 100
        bought, new_prum = prum_after_buy(quantity=1.0, prum=200.0, price=100.0, amount=100.0)
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
        result = quantity_for_target_prum(quantity=1.0, prum=100.0, price=80.0, target=90.0)
        assert result is not None
        needed, amount = result
        assert needed == pytest.approx(1.0)
        assert amount == pytest.approx(80.0)

    def test_reaching_the_target_actually_reaches_it(self):
        needed, amount = quantity_for_target_prum(3.0, 120.0, 60.0, 90.0)
        after = position(
            [Trade("buy", needed, 60.0)], base_quantity=3.0, base_prum=120.0
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
