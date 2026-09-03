"""The monthly note: a checklist, its links, and the calendar feed around it.

`allocation.plan()` and `allocation.projection()` are stubbed here: they
already hand the note everything in EUR, so nothing in this module converts
anything. What is tested is the shape of what a calendar and a reminder
receive.
"""

from datetime import date, datetime, timezone

import pytest

from src.services import note

BASE = "https://allot.example.com/"


def _line(symbol, amount, units=None, weight=1.0, fractional=True, price=None):
    return {
        "symbol": symbol,
        "weight": weight,
        "amount": amount,
        "units": units,
        "fractional": fractional,
        "currency": "EUR",
        "price": price,
        "price_eur": price,
        "prum": None,
        "multiplier": 1.0,
        "held_eur": 0.0,
    }


# CTO tracks its cash and buys one whole share; CRYPTO splits its monthly
# amount in euros, the way an envelope without a start always did.
PLAN = [
    {
        "envelope": "CTO",
        "amount": 100.0,
        "budget": 650.0,
        "cash": {"available": 650.0, "started_on": "2026-03-01"},
        "carry": 50.0,
        "market_value": 0.0,
        "assets": [_line("MC.PA", 600.0, units=1, fractional=False, price=600.0)],
        "waiting": [],
    },
    {
        "envelope": "CRYPTO",
        "amount": 165.0,
        "budget": 165.0,
        "cash": None,
        "carry": 0.0,
        "market_value": 0.0,
        "assets": [
            _line("ETH-USD", 123.75, price=1890.0),
            _line("BTC-USD", 41.25, price=64300.0),
        ],
        "waiting": [],
    },
]

WAITING = {
    "envelope": "PEA",
    "amount": 100.0,
    "budget": 340.0,
    "cash": {"available": 340.0, "started_on": "2026-03-01"},
    "carry": 340.0,
    "market_value": 0.0,
    "assets": [],
    "waiting": [
        {
            "symbol": "CW8.PA",
            "price_eur": 500.0,
            "missing": 160.0,
            "months_left": 2,
        }
    ],
}


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: PLAN)
    monkeypatch.setattr(note.allocation, "projection", lambda *a, **k: [])
    monkeypatch.setattr(note.db, "last_transaction_date", lambda: "2026-09-01")


class TestNote:
    def test_never_exceeds_78_columns_except_on_links(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        for line in text.splitlines():
            assert len(line) <= note.WIDTH or "://" in line

    def test_is_plain_text_without_markdown(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        for marker in ("**", "##", "|---", "```"):
            assert marker not in text

    def test_header_names_the_month_and_what_is_going_out(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        lines = text.splitlines()
        assert lines[0] == "Point patrimoine - septembre 2026"
        # 600 + 123,75 + 41,25: what actually leaves, not what is available
        assert lines[1] == "765 € à placer ce mois."

    def test_a_whole_share_is_counted_in_shares(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        assert "[ ] MC.PA     1 part  600 €" in text

    def test_a_fractional_asset_is_counted_in_euros(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        assert "[ ] ETH-USD   123,75 €" in text

    def test_a_line_without_a_quote_says_so(self, offline, monkeypatch):
        # Given an asset whose quote did not come back
        plan = [{**PLAN[1], "assets": [_line("ETH-USD", 165.0, price=None)]}]
        monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: plan)
        # When the note is rendered
        text = note.render(BASE, date(2026, 9, 15))
        # Then the amount is still the plan, but it is not passed off as
        # checked against a price
        assert "[ ] ETH-USD   165,00 €  cours indisponible" in text

    def test_every_line_carries_the_link_to_its_asset(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        assert "    https://allot.example.com/?asset=MC.PA" in text
        assert "    https://allot.example.com/?asset=ETH-USD" in text

    def test_a_link_is_never_truncated(self, offline):
        symbol = "A" * 90
        plan = [{**PLAN[0], "assets": [_line(symbol, 600.0, units=1, price=600.0)]}]
        note.allocation.plan = lambda *a, **k: plan
        text = note.render(BASE, date(2026, 9, 15))
        assert f"?asset={symbol}" in text

    def test_no_link_at_all_when_the_app_has_no_address(self, offline):
        text = note.render(None, date(2026, 9, 15))
        assert "://" not in text
        assert "[ ] MC.PA" in text

    def test_an_envelope_tracking_cash_shows_it(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        assert "CTO - 650 € en cagnotte" in text
        assert "Reste 50 € en cagnotte." in text

    def test_an_envelope_without_cash_shows_its_monthly_amount(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        assert "CRYPTO - 165 €" in text

    def test_an_envelope_that_buys_nothing_says_what_it_waits_for(
        self, offline, monkeypatch
    ):
        # Given an envelope saving up for a share it cannot afford yet
        monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: [WAITING])
        # When the note is rendered
        text = note.render(BASE, date(2026, 9, 15))
        # Then it says so, with what is missing and when it lands
        assert "PEA - rien ce mois. 340 € en cagnotte." in text
        assert "Il manque 160 € pour 1 CW8.PA (novembre)." in text

    def test_it_says_nothing_more_when_nothing_is_out_of_reach(
        self, offline, monkeypatch
    ):
        # Given an envelope waiting on an asset it could in fact afford
        plan = [{**WAITING, "waiting": [{**WAITING["waiting"][0], "missing": 0.0}]}]
        monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: plan)
        # When the note is rendered
        text = note.render(BASE, date(2026, 9, 15))
        # Then it does not announce that 0 EUR is missing
        assert "PEA - rien ce mois. 340 € en cagnotte." in text
        assert "Il manque" not in text

    def test_a_dormant_envelope_is_left_out(self, offline, monkeypatch):
        # Given an envelope with no cash tracked and nothing to place
        dormant = {**PLAN[1], "envelope": "AFER", "amount": 0.0, "budget": 0.0}
        dormant["assets"] = [_line("AFER-FUND", 0.0)]
        monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: [dormant])
        # When the note is rendered
        text = note.render(BASE, date(2026, 9, 15))
        # Then it is not mentioned at all
        assert "AFER" not in text

    def test_an_envelope_with_money_and_nowhere_to_put_it_still_speaks(
        self, offline, monkeypatch
    ):
        # Given a funded envelope whose assets all sit at weight 0
        stuck = {
            **PLAN[1],
            "budget": 165.0,
            "assets": [_line("SOL-USD", 0.0, price=88.0)],
        }
        monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: [stuck])
        # When the note is rendered
        text = note.render(BASE, date(2026, 9, 15))
        # Then it says why, rather than just "nothing this month"
        assert "CRYPTO - 165 € sans destination, aucun actif à alimenter." in text

    def test_the_reasoning_stays_out_of_the_note(self, offline):
        # The gap to the PRUM and the multiplier explain the amounts; the
        # note is a to-do list, and they are not to-dos
        text = note.render(BASE, date(2026, 9, 15))
        assert "PRUM" not in text
        assert "x1" not in text

    def test_zero_weight_and_zero_amount_lines_are_left_out(self, offline, monkeypatch):
        plan = [
            {
                **PLAN[1],
                "assets": [
                    _line("SOL-USD", 0.0, price=88.0),
                    _line("DOT-USD", 10.0, weight=0.0, price=4.0),
                ],
            }
        ]
        monkeypatch.setattr(note.allocation, "plan", lambda *a, **k: plan)
        text = note.render(BASE, date(2026, 9, 15))
        assert "SOL-USD" not in text
        assert "DOT-USD" not in text

    def test_uses_plain_ascii_dashes(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        for character in ("—", "−", "×"):
            assert character not in text

    def test_warns_when_nothing_was_entered_for_45_days(self, offline, monkeypatch):
        monkeypatch.setattr(note.db, "last_transaction_date", lambda: "2026-07-12")
        text = note.render(BASE, date(2026, 9, 15))
        assert "Rien de saisi depuis le 12 juillet." in text

    def test_stays_quiet_when_entries_are_recent(self, offline):
        text = note.render(BASE, date(2026, 9, 15))
        assert "Rien de saisi" not in text


PROJECTION = [
    {
        "month": date(2026, 10, 1),
        "envelopes": [
            {
                "envelope": "CTO",
                "tracked": True,
                "budget": 150.0,
                "assets": [],
                "carry": 150.0,
            },
            {
                "envelope": "CRYPTO",
                "tracked": False,
                "budget": 165.0,
                "assets": [_line("ETH-USD", 165.0, price=1890.0)],
                "carry": 0.0,
            },
        ],
    },
    {
        "month": date(2026, 11, 1),
        "envelopes": [
            {
                "envelope": "CTO",
                "tracked": True,
                "budget": 620.0,
                "assets": [
                    _line("MC.PA", 600.0, units=1, fractional=False, price=600.0)
                ],
                "carry": 20.0,
            }
        ],
    },
]


@pytest.fixture
def feed(offline, monkeypatch):
    monkeypatch.setattr(note.allocation, "projection", lambda *a, **k: PROJECTION)
    return note.feed(
        BASE, date(2026, 9, 15), datetime(2026, 9, 15, 8, 30, tzinfo=timezone.utc)
    )


class TestFeed:
    def test_one_event_per_month(self, feed):
        assert feed.startswith("BEGIN:VCALENDAR\r\n")
        assert feed.count("BEGIN:VEVENT") == 3
        assert feed.rstrip().endswith("END:VCALENDAR")

    def test_events_are_all_day_and_dated_by_month(self, feed):
        assert "DTSTART;VALUE=DATE:20260901" in feed
        assert "DTSTART;VALUE=DATE:20261001" in feed
        assert "DTSTART;VALUE=DATE:20261101" in feed
        # A subscription, not a recurrence: every month is computed
        assert "RRULE" not in feed

    def test_uids_are_stable_so_a_refetch_updates_in_place(self, feed):
        assert "UID:allot-2026-09@allot" in feed
        assert "UID:allot-2026-11@allot" in feed

    def test_this_months_event_does_not_move_between_fetches(
        self, offline, monkeypatch
    ):
        # Given the feed fetched on two different days of the same month
        monkeypatch.setattr(note.allocation, "projection", lambda *a, **k: [])
        first = note.feed(BASE, date(2026, 9, 3))
        later = note.feed(BASE, date(2026, 9, 27))
        # Then the occurrence stays on the 1st: the UID is stable, so a moving
        # date would drag the event across the month at every refetch
        assert "DTSTART;VALUE=DATE:20260901" in first
        assert "DTSTART;VALUE=DATE:20260901" in later

    def test_the_current_month_carries_the_checklist(self, feed):
        unfolded = feed.replace("\r\n ", "")
        assert "[ ] MC.PA" in unfolded
        assert "?asset=MC.PA" in unfolded

    def test_a_future_month_carries_the_projection_without_boxes(self, feed):
        unfolded = feed.replace("\r\n ", "")
        november = unfolded.split("UID:allot-2026-11@allot")[1]
        assert "Prévu au rythme actuel" in november
        assert "CTO - 620 € en cagnotte" in november
        assert "MC.PA" in november
        assert "[ ]" not in november

    def test_an_envelope_buying_nothing_that_month_is_simply_absent(self, feed):
        unfolded = feed.replace("\r\n ", "")
        october = unfolded.split("UID:allot-2026-10@allot")[1].split("END:VEVENT")[0]
        # CTO cannot afford anything in October: it says nothing rather than
        # showing a line worth zero
        assert "CTO" not in october
        assert "CRYPTO" in october

    def test_a_month_with_nothing_to_buy_at_all_says_the_cash_keeps_growing(
        self, offline, monkeypatch
    ):
        empty = [{**PROJECTION[1], "envelopes": [PROJECTION[0]["envelopes"][0]]}]
        monkeypatch.setattr(note.allocation, "projection", lambda *a, **k: empty)
        text = note.feed(BASE, date(2026, 9, 15)).replace("\r\n ", "")
        assert "cagnotte continue de monter" in text

    def test_every_line_fits_75_octets(self, feed):
        for line in feed.split("\r\n"):
            assert len(line.encode()) <= 75

    def test_folding_keeps_the_accents(self, feed):
        assert "à placer" in feed.replace("\r\n ", "")

    def test_special_characters_are_escaped(self, offline, monkeypatch):
        monkeypatch.setattr(note, "render", lambda *a, **k: "a,b;c\n")
        monkeypatch.setattr(note.allocation, "projection", lambda *a, **k: [])
        assert "DESCRIPTION:a\\,b\\;c\\n" in note.feed(BASE, date(2026, 9, 15))
