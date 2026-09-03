"""The envelope cash: derived from the strategy, never stored.

An envelope declares where its strategy starts; everything else follows from
the monthly amount and the transactions. These tests use the real database, so
what is checked is the derivation itself, not a stubbed version of it.
"""

from datetime import date

import pytest

from src.databases import sqlite as db
from src.services import cash


@pytest.fixture
def envelope(database):
    """A 100 EUR/month envelope holding one asset, and nothing bought yet."""
    db.upsert_envelope("CTO", 100.0)
    db.add_asset("MC.PA", "LVMH", "CTO", "EUR", 1.0)
    return db.get_envelope("CTO")


class TestAvailable:
    def test_an_envelope_without_a_start_tracks_no_cash(self, envelope):
        # Given an envelope that never declared a start
        # When its cash is asked for
        # Then there is none to speak of, and the caller falls back to the
        # plain monthly split
        assert cash.available(envelope, date(2026, 9, 15)) is None

    def test_the_current_month_counts(self, envelope):
        # Given a strategy started on the 1st of this month with nothing
        db.set_envelope_start("CTO", "2026-09-01", 0.0)
        # When the cash is read mid-month
        balance = cash.available(envelope, date(2026, 9, 15))
        # Then this month's contribution is already in: it is what the note
        # is about to tell us to place
        assert balance.months == 1
        assert balance.available == 100.0

    def test_contributions_add_up_month_after_month(self, envelope):
        # Given a strategy started six months ago with 250 EUR already there
        db.set_envelope_start("CTO", "2026-09-01", 250.0)
        # When the cash is read
        balance = cash.available(envelope, date(2027, 2, 3))
        # Then it is the opening plus one contribution per month since
        assert balance.months == 6
        assert balance.paid_in == 600.0
        assert balance.available == 850.0

    def test_buying_spends_it_fees_included(self, envelope):
        db.set_envelope_start("CTO", "2026-09-01", 0.0)
        db.add_transaction("MC.PA", "2026-10-05", "buy", 1.0, 500.0, 5.0)
        balance = cash.available(envelope, date(2027, 2, 3))
        assert balance.spent == 505.0
        assert balance.available == 600.0 - 505.0

    def test_selling_credits_it_back_fees_deducted(self, envelope):
        db.set_envelope_start("CTO", "2026-09-01", 0.0)
        db.add_transaction("MC.PA", "2026-10-05", "sell", 1.0, 500.0, 5.0)
        balance = cash.available(envelope, date(2027, 2, 3))
        assert balance.returned == 495.0
        assert balance.available == 600.0 + 495.0

    def test_what_happened_before_the_start_is_none_of_its_business(self, envelope):
        # Given a buy predating the start, and a recalibration after it
        db.add_transaction("MC.PA", "2026-08-05", "buy", 1.0, 500.0)
        db.set_envelope_start("CTO", "2026-09-01", 0.0)
        # When the cash is read
        balance = cash.available(envelope, date(2026, 9, 15))
        # Then the old buy is not deducted twice: the start already accounts
        # for everything that came before it
        assert balance.spent == 0.0
        assert balance.available == 100.0

    def test_a_usd_line_is_spent_in_euros(self, envelope, mocker):
        # Given a dollar asset in the envelope
        mocker.patch.object(cash.prices, "eur_usd_rate", return_value=1.1)
        db.add_asset("ETH-USD", "Ethereum", "CTO", "USD", 1.0)
        db.set_envelope_start("CTO", "2026-09-01", 0.0)
        db.add_transaction("ETH-USD", "2026-09-05", "buy", 1.0, 110.0)
        # When the cash is read
        balance = cash.available(envelope, date(2026, 9, 15))
        # Then the dollars were converted: cash is counted in euros
        assert balance.spent == pytest.approx(100.0)

    def test_it_never_goes_negative(self, envelope):
        # Given more spent than the strategy ever paid in
        db.set_envelope_start("CTO", "2026-09-01", 0.0)
        db.add_transaction("MC.PA", "2026-09-05", "buy", 1.0, 900.0)
        # When the cash is read
        balance = cash.available(envelope, date(2026, 9, 15))
        # Then it reads as empty rather than as a debt: a negative figure
        # would only propagate an error that a recalibration should fix
        assert balance.available == 0.0

    def test_a_start_in_the_future_has_paid_in_nothing_yet(self, envelope):
        db.set_envelope_start("CTO", "2026-12-01", 40.0)
        balance = cash.available(envelope, date(2026, 9, 15))
        assert balance.months == 0
        assert balance.available == 40.0

    def test_the_terms_of_the_calculation_come_back_with_it(self, envelope):
        # So the figure can be argued with against a statement
        db.set_envelope_start("CTO", "2026-09-01", 250.0)
        balance = cash.available(envelope, date(2026, 11, 15))
        assert balance.opening_cash == 250.0
        assert balance.months == 3
        assert balance.started_on == "2026-09-01"


class TestMonthsToAfford:
    def test_nothing_to_wait_for_when_the_cash_is_there(self):
        assert cash.months_to_afford(600.0, 700.0, 100.0) == 0

    def test_it_rounds_up_to_the_next_full_month(self):
        # 280 missing at 100 a month is three months, not two and a bit
        assert cash.months_to_afford(600.0, 320.0, 100.0) == 3

    def test_an_envelope_that_receives_nothing_never_gets_there(self):
        assert cash.months_to_afford(600.0, 320.0, 0.0) is None
