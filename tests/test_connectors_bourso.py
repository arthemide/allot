"""Reading BoursoBank's PEA pages: no browser, no network."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.connectors.bourso import (
    account_name,
    find_pea_paths,
    is_login_url,
    parse_french_number,
    parse_positions,
    to_rows,
)
from src.connectors.errors import LayoutChanged, SessionExpired

FIXTURE = Path(__file__).parent / "fixtures" / "connectors" / "bourso_positions.html"


@pytest.fixture(scope="module")
def page() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def table(header: str, row: str) -> str:
    return (
        "<h3>Gestion Libre</h3><table data-table-trading-operations>"
        f"<thead><tr>{header}</tr></thead><tbody><tr>{row}</tr></tbody></table>"
    )


def th(column: str | None, caption: str = "") -> str:
    if column is None:
        return f"<th>{caption}</th>"
    return f'<th><a href="/compte/pea/x/positions?colonne={column}">{caption}</a></th>'


class TestFrenchNumbers:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("4,7445", 4.7445),
            ("1 234,56 €", 1234.56),
            ("1 020,04 €", 1020.04),
            ("- 2,14 %", -2.14),
            ("+ 42,96 €", 42.96),
            ("-15,25 €", -15.25),
            ("150 000 €", 150000.0),
            ("1.234,5", 1234.5),
            ("12", 12.0),
        ],
    )
    def test_a_figure_as_the_page_prints_it(self, text, expected):
        assert parse_french_number(text) == expected

    @pytest.mark.parametrize("text", [None, "", "  ", "-", "+", "n/a"])
    def test_an_empty_or_unreadable_cell_is_none(self, text):
        assert parse_french_number(text) is None


class TestPositions:
    def test_every_line_of_both_sections_is_read(self, page):
        # Given the positions page, with a profiled and a free section
        # When it is parsed
        portfolio = parse_positions(page)
        # Then each line carries what the page shows, by section
        assert [(line.section, line.isin) for line in portfolio.lines] == [
            ("managed", "FR0010315770"),
            ("free", "IE00B4L5Y983"),
            ("free", "LU0274208692"),
            ("free", None),
        ]
        managed = portfolio.lines[0]
        assert managed.label == "PROFIL OFFENSIF TEST C"
        assert managed.quantity == 5.1234
        assert managed.unit_cost == 150.0
        # The intraday change beside the price is left out
        assert managed.unit_price == 147.0
        assert managed.value == 753.14
        assert managed.gain == -15.37

    def test_the_buy_and_sell_column_does_not_shift_anything(self, page):
        etf = parse_positions(page).lines[2]
        assert (etf.label, etf.quantity, etf.value, etf.gain) == (
            "ETF MONDE TEST",
            12.0,
            1188.96,
            42.96,
        )

    def test_the_cash_balance_comes_from_the_summary_box(self, page):
        assert parse_positions(page).cash == 1020.04

    def test_the_securities_add_up_to_the_page_total(self, page):
        total = sum(line.value for line in parse_positions(page).lines)
        assert round(total, 2) == 13523.10

    def test_columns_are_found_by_sort_link_whatever_their_order(self):
        html = table(
            th("amount") + th("quantity") + th("name"),
            "<td>1 000,00 €</td><td>3</td>"
            '<td><span class="c-link__label">X</span></td>',
        )
        line = parse_positions(html).lines[0]
        assert (line.label, line.quantity, line.value) == ("X", 3.0, 1000.0)
        assert line.unit_cost is None and line.isin is None

    def test_a_header_without_sort_link_falls_back_on_its_caption(self):
        html = table(
            th(None, "Valeur") + th(None, "Quantité") + th(None, "Montant"),
            "<td>Y</td><td>2</td><td>10,00 €</td>",
        )
        line = parse_positions(html).lines[0]
        assert (line.label, line.quantity, line.value) == ("Y", 2.0, 10.0)

    def test_rows_without_a_label_or_an_amount_are_skipped(self):
        html = table(
            th("quantity") + th("amount") + th("name"),
            "<td>1</td><td>5,00</td><td></td></tr><tr><td>1</td><td>-</td><td>Z</td>"
            "</tr><tr><td>1</td>",
        )
        assert parse_positions(html).lines == []

    def test_an_invalid_isin_is_dropped(self):
        html = table(
            th("name") + th("amount"),
            '<td>W<span class="c-table__mention">FR0010315771</span></td><td>1,00</td>',
        )
        assert parse_positions(html).lines[0].isin is None

    def test_pending_liquidation_orders_are_not_positions(self):
        html = (
            "<h3>Engagements en liquidation</h3><table data-table-trading-operations>"
            "<thead><tr><th>nothing</th></tr></thead></table>"
        )
        assert parse_positions(html).lines == []

    def test_no_table_means_the_layout_changed(self):
        with pytest.raises(LayoutChanged, match="no positions table"):
            parse_positions("<html><body>Bienvenue</body></html>")

    def test_a_missing_column_means_the_layout_changed(self):
        html = table(th("name") + th("quantity"), "<td>A</td><td>1</td>")
        with pytest.raises(LayoutChanged, match="column\\(s\\): amount"):
            parse_positions(html)

    def test_no_cash_item_gives_no_cash(self):
        html = table(th("name") + th("amount"), "<td>A</td><td>1,00</td>")
        assert parse_positions(html).cash is None


class TestRows:
    def test_lines_become_rows_and_cash_comes_last(self, page):
        rows = to_rows("PEA", parse_positions(page))
        assert [r.support_type for r in rows] == [
            "managed",
            "security",
            "security",
            "security",
            "cash",
        ]
        cash = rows[-1]
        assert (cash.isin, cash.quantity, cash.value) == (None, None, 1020.04)
        assert all(r.account == "PEA" and r.currency == "EUR" for r in rows)

    def test_no_cash_no_cash_row(self):
        html = table(th("name") + th("amount"), "<td>A</td><td>1,00</td>")
        assert [r.support_type for r in to_rows("PEA", parse_positions(html))] == [
            "security"
        ]


class TestNavigation:
    def test_pea_links_are_found_once_each_in_order(self):
        html = (
            '<a href="/compte/cav/abc/">current</a>'
            '<a href="/compte/pea/k1/positions">pea</a>'
            '<a href="https://clients.boursobank.com/compte/pea/k1/">again</a>'
            '<a href="/compte/pea-pme/k2/mouvements">pme</a>'
        )
        paths = find_pea_paths(html)
        assert paths == ["/compte/pea/k1/", "/compte/pea-pme/k2/"]
        assert [account_name(p) for p in paths] == ["PEA", "PEA-PME"]
        assert account_name("/elsewhere/") == "PEA"

    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://clients.boursobank.com/connexion/", True),
            ("https://clients.boursobank.com/connexion/?expire=1", True),
            ("https://clients.boursobank.com/connexion/saisie-mot-de-passe", True),
            ("https://clients.boursobank.com/compte/pea/k/positions", False),
            ("https://clients.boursobank.com/connexions-utiles", False),
        ],
    )
    def test_the_login_page_is_recognised(self, url, expected):
        assert is_login_url(url) is expected

    def test_an_expired_session_says_how_to_recover(self):
        assert "make discover BANK=bourso" in str(
            SessionExpired("BoursoBank", "bourso")
        )
