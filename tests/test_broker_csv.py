"""Reading a portfolio export: no database, no network."""

from __future__ import annotations

import pytest

from src.services import broker_csv
from src.services.broker_csv import CsvError, parse

# BoursoBank's portfolio columns, with made-up holdings.
BOURSO = (
    "name;isin;quantity;buyingPrice;lastPrice;intradayVariation;amount;"
    "amountVariation;variation;lastMovementDate;compensation\n"
    '"AMUNDI MSCI WORLD UCITS ETF";IE000BI8OT95;10,00;100,00;108,40;0,21;'
    "1084,00;84,00;8,40;2026-02-11;\n"
    '"FONDS EUROPE CROISSANCE";FR0000000001;0,50;"2 000,00";"1 900,00";0,10;'
    "950,00;-50,00;-5,00;2025-06-03;\n"
)

MOVEMENTS = (
    "dateOp;dateVal;label;category;categoryParent;supplierFound;amount;"
    "accountNum;accountLabel;accountBalance\n"
    '2026-03-01;2026-03-01;"ACHAT COMPTANT ETF";Bourse;Epargne;;-500,00;'
    "0001;PEA;1000,00\n"
)


class TestBoursoBankPortfolio:
    def test_each_line_held_becomes_a_row(self):
        # Given the export as BoursoBank writes it
        # When it is read
        parsed = parse(BOURSO)
        # Then it is recognised and every row carries what a position needs
        assert parsed.broker == "BoursoBank portfolio"
        assert parsed.delimiter == ";"
        assert len(parsed.rows) == 2
        etf = parsed.rows[0]
        assert etf.isin == "IE000BI8OT95"
        assert etf.name == "AMUNDI MSCI WORLD UCITS ETF"
        assert etf.quantity == 10.0
        assert etf.prum == 100.0
        assert etf.price == 108.4

    def test_french_thousands_and_decimals_are_read(self):
        # Given "2 000,00" quoted, space for thousands and comma for decimals
        fund = parse(BOURSO).rows[1]
        # Then both are understood
        assert fund.prum == 2000.0
        assert fund.price == 1900.0
        assert fund.quantity == 0.5

    def test_columns_are_mapped_by_role(self):
        roles = parse(BOURSO).roles
        assert roles["isin"] == "identifier"
        assert roles["quantity"] == "quantity"
        assert roles["buyingPrice"] == "cost"
        assert roles["lastPrice"] == "valuation"
        assert roles["name"] == "name"

    def test_a_byte_order_mark_is_ignored(self):
        assert len(parse("﻿" + BOURSO).rows) == 2


class TestOtherShapes:
    def test_english_headers_with_commas_read_the_same(self):
        # Given a generic export, comma-separated, English headers, no price
        text = "ISIN,Quantity,Average price\nFR0000000001,3,50.5\n"
        parsed = parse(text)
        assert parsed.delimiter == ","
        assert parsed.broker == "unknown"
        row = parsed.rows[0]
        assert (row.quantity, row.prum, row.price) == (3.0, 50.5, None)
        # And the name falls back to the identifier
        assert row.name == "FR0000000001"

    def test_accented_french_headers_are_recognised(self):
        text = "Libellé;Code ISIN;Quantité;Prix de revient\nX;FR0000000001;1;10\n"
        assert parse(text).rows[0].prum == 10.0

    def test_blank_lines_are_skipped(self):
        text = "isin;quantity;pru\n\nFR0000000001;1;10\n  \n"
        assert len(parse(text).rows) == 1


class TestRefusals:
    def test_a_movements_export_is_named_as_such(self):
        # Given the export people reach for first
        # When it is read
        with pytest.raises(CsvError) as error:
            parse(MOVEMENTS)
        # Then the message says what to export instead
        assert "movements" in str(error.value)
        assert "portfolio" in str(error.value)

    def test_a_missing_required_column_is_named(self):
        with pytest.raises(CsvError, match="cost"):
            parse("isin;quantity\nFR0000000001;1\n")

    def test_an_empty_file_is_refused(self):
        with pytest.raises(CsvError, match="empty"):
            parse("   \n")

    def test_a_bad_quantity_points_at_its_line(self):
        with pytest.raises(CsvError, match="line 3") as error:
            parse("isin;quantity;pru\nFR0000000001;1;10\nFR0000000002;abc;10\n")
        assert error.value.line == 3

    def test_a_zero_cost_is_refused(self):
        with pytest.raises(CsvError, match="cost"):
            parse("isin;quantity;pru\nFR0000000001;1;0\n")

    def test_an_empty_identifier_is_refused(self):
        with pytest.raises(CsvError, match="identifier"):
            parse("isin;quantity;pru\n;1;10\n")

    def test_too_many_rows_are_refused(self, monkeypatch):
        monkeypatch.setattr(broker_csv, "MAX_ROWS", 2)
        text = "isin;quantity;pru\n" + "FR0000000001;1;10\n" * 3
        with pytest.raises(CsvError, match="too many rows"):
            parse(text)

    def test_too_large_a_file_is_refused(self, monkeypatch):
        monkeypatch.setattr(broker_csv, "MAX_BYTES", 10)
        with pytest.raises(CsvError, match="too large"):
            parse(BOURSO)
