"""The monthly note must stay pasteable into a reminder description field.

`allocation.plan()` is stubbed out here: it already hands the note its
market values in EUR, so nothing in this module converts anything.
"""

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
                "weight": 1.0,
                "amount": 440.0,
                "multiplier": 1.0,
                "currency": "EUR",
                "price": 6.21,
                "prum": None,
            }
        ],
    },
    {
        "envelope": "CRYPTO",
        "amount": 165.0,
        # 2000 USD at 1.08 USD per EUR, converted by allocation.plan()
        "market_value": 1851.85,
        "assets": [
            {
                "symbol": "ETH-USD",
                "weight": 1.0,
                "amount": 123.75,
                "multiplier": 1.5,
                "currency": "USD",
                "price": 1890.0,
                "prum": 2150.0,
            },
            {
                "symbol": "BTC-USD",
                "weight": 1.0,
                "amount": 41.25,
                "multiplier": 0.5,
                "currency": "USD",
                "price": 64300.0,
                "prum": 58000.0,
            },
        ],
    },
    {
        "envelope": "CTO",
        "amount": 80.0,
        "market_value": 0.0,
        "assets": [],
    },
]


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: PLAN)
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
        lines = text.splitlines()
        assert lines[0] == "Point patrimoine - septembre 2026"
        assert lines[1] == "À placer ce mois : 685 €"

    def test_priced_asset_with_a_prum_shows_the_multiplier(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "ETH-USD" in text
        assert "x1,5" in text
        assert "x0,5" in text

    def test_assets_are_listed_as_bullets(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "  - WPEA.PA" in text
        assert "  - ETH-USD" in text

    def test_asset_without_a_prum_shows_its_price(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "cours 6,21 €" in text

    def test_envelope_without_assets_shows_its_amount_alone(self, offline):
        # An envelope with nothing in it yet still states what goes into it
        text = note.render(date(2026, 9, 15))
        assert "CTO - 80 €" in text

    def test_zero_weight_asset_is_left_out(self, offline, monkeypatch):
        # Given a held asset that is never topped up
        plan = [dict(e) for e in PLAN]
        plan[1] = dict(plan[1])
        plan[1]["assets"] = plan[1]["assets"] + [
            {
                "symbol": "SOL-USD",
                "weight": 0.0,
                "amount": 0.0,
                "multiplier": 1.0,
                "currency": "USD",
                "price": 88.0,
                "prum": 90.0,
            }
        ]
        monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: plan)
        # When the note is rendered
        text = note.render(date(2026, 9, 15))
        # Then it says nothing about it: there is no money going its way
        assert "SOL-USD" not in text

    def test_uses_plain_ascii_dashes(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "—" not in text
        assert "−" not in text
        assert "×" not in text

    def test_warns_when_nothing_was_entered_for_45_days(self, offline):
        # Given the last transaction is 12 July and we are in September
        text = note.render(date(2026, 9, 15))
        assert "- Aucune transaction saisie depuis le 12 juillet." in text

    def test_stays_quiet_when_entries_are_recent(self, offline):
        # Given the last transaction is only a few days old
        text = note.render(date(2026, 7, 20))
        assert "Aucune transaction saisie" not in text

    def test_excel_block_lists_envelope_values(self, offline):
        text = note.render(date(2026, 9, 15))
        assert "CRYPTO 1 852 €" in text
        assert "PEA 1 000 €" in text

    def test_excel_block_says_so_when_nothing_is_held(self, offline, monkeypatch):
        # Given envelopes that hold nothing yet
        plan = [{**e, "market_value": 0.0} for e in PLAN]
        monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: plan)
        # When the note is rendered
        text = note.render(date(2026, 9, 15))
        # Then the line is still there, saying there is nothing to copy
        assert "- À recopier dans l'Excel : rien" in text
