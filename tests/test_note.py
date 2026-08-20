"""The monthly note must stay pasteable into a reminder description field."""

from datetime import date

import pytest

from src.services import note

PLAN = [
    {
        "envelope": "PEA",
        "amount": 440.0,
        "market_value": 1000.0,
        "assets": [
            {
                "symbol": "WPEA.PA",
                "amount": 440.0,
                "multiplier": 1.0,
                "currency": "EUR",
                "price_source": "yfinance",
                "price": 6.21,
                "prum": None,
            }
        ],
    },
    {
        "envelope": "CRYPTO",
        "amount": 165.0,
        "market_value": 2000.0,
        "assets": [
            {
                "symbol": "ETH-USD",
                "amount": 123.75,
                "multiplier": 1.5,
                "currency": "USD",
                "price_source": "yfinance",
                "price": 1890.0,
                "prum": 2150.0,
            },
            {
                "symbol": "BTC-USD",
                "amount": 41.25,
                "multiplier": 0.5,
                "currency": "USD",
                "price_source": "yfinance",
                "price": 64300.0,
                "prum": 58000.0,
            },
        ],
    },
    {
        "envelope": "AFER",
        "amount": 110.0,
        "market_value": 0.0,
        "assets": [
            {
                "symbol": "AFER",
                "amount": 110.0,
                "multiplier": 1.0,
                "currency": "EUR",
                "price_source": "manual",
                "price": None,
                "prum": None,
            }
        ],
    },
]


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: PLAN)
    monkeypatch.setattr(note.prices, "eur_usd_rate", lambda: 1.08)
    monkeypatch.setattr(note.db, "last_transaction_date", lambda: "2026-07-12")


class TestNote:
    def test_never_exceeds_78_columns(self, offline):
        text = note.render(date(2026, 9, 15))
        assert max(len(line) for line in text.splitlines()) <= note.WIDTH

    def test_is_plain_text_without_markdown(self, offline):
        text = note.render(date(2026, 9, 15))
        for marker in ("**", "##", "|---", "```"):
            assert marker not in text

    def test_header_names_the_month_and_the_amount(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "Point patrimoine — septembre 2026" in text
        assert "715 €" in text.splitlines()[0]

    def test_priced_asset_with_a_prum_shows_the_multiplier(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "ETH-USD" in text
        assert "×1,5" in text
        assert "×0,5" in text

    def test_asset_without_a_prum_shows_share_count(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "parts" in text

    def test_manual_envelope_is_collapsed_to_a_bare_amount(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "AFER — 110 €" in text

    def test_warns_when_nothing_was_entered_for_45_days(self, offline):
        # Given the last transaction is 12 July and we are in September
        text = note.render(date(2026, 9, 15))
        assert "⚠ Aucune transaction saisie depuis le 12 juillet." in text

    def test_stays_quiet_when_entries_are_recent(self, offline):
        # Given the last transaction is only a few days old
        text = note.render(date(2026, 7, 20))
        assert "⚠" not in text

    def test_excel_block_converts_usd_envelopes_to_eur(self, offline):
        text = note.render(date(2026, 9, 15))
        # 2000 USD at 1.08 USD per EUR is about 1852 EUR
        assert "CRYPTO 1 852 €" in text
        assert "PEA 1 000 €" in text
