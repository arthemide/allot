"""Read a broker's portfolio export.

The one format guaranteed is BoursoBank's "portefeuille" CSV, but nothing here
is keyed on it: columns are recognised by what they hold (an identifier, a
quantity, a cost basis...) from their header, in French or English, so another
broker exporting the same three things reads the same way.

What comes out is a snapshot, one row per line held - never a transaction
stream. A cash-movements export (date, label, amount) is refused by name, since
it is the file people reach for first and it cannot give a position.

No database, no network: text in, rows out.
"""

from __future__ import annotations

import csv
import io
import unicodedata
from dataclasses import dataclass

MAX_BYTES = 256 * 1024
MAX_ROWS = 500

# Header keys, normalised (lowercase, unaccented, alphanumeric only), by the
# role the column plays. Exact matches win; a substring only counts for keys
# long enough not to fire on everything ("nb" alone would).
ROLES = {
    "identifier": ("isin", "codeisin", "symbol", "symbole", "ticker", "mnemo", "code"),
    "quantity": (
        "quantity",
        "quantite",
        "qte",
        "qty",
        "nombredeparts",
        "parts",
        "shares",
    ),
    "cost": (
        "buyingprice",
        "pru",
        "prixderevient",
        "prixdachat",
        "prixmoyen",
        "averageprice",
        "prixunitairemoyen",
    ),
    "valuation": (
        "lastprice",
        "amount",
        "valuation",
        "valorisation",
        "cours",
        "derniercours",
    ),
    "name": ("name", "nom", "label", "libelle", "designation", "intitule"),
}
REQUIRED = ("identifier", "quantity", "cost")
DELIMITERS = ";,\t|"

# The cash-movements export, so it can be named in the error.
MOVEMENTS_SIGNATURE = ("dateop", "label", "amount")


class CsvError(ValueError):
    """The file cannot be read as a portfolio; the message says why."""

    def __init__(self, message: str, line: int | None = None):
        super().__init__(f"line {line}: {message}" if line else message)
        self.line = line


@dataclass(frozen=True)
class Row:
    isin: str
    name: str
    quantity: float
    prum: float
    # Optional: the import resolves prices itself, the simulator needs it.
    price: float | None


@dataclass(frozen=True)
class Parsed:
    rows: list[Row]
    delimiter: str
    broker: str
    roles: dict[str, str]


def _normalise(header: str) -> str:
    decomposed = unicodedata.normalize("NFD", header.lower())
    return "".join(
        c for c in decomposed if c.isalnum() and not unicodedata.combining(c)
    )


def _role(header: str) -> str | None:
    key = _normalise(header)
    if not key:
        return None
    for role, names in ROLES.items():
        if key in names:
            return role
    for role, names in ROLES.items():
        if any(len(name) >= 4 and name in key for name in names):
            return role
    return None


def _delimiter(first_line: str) -> str:
    counts = dict.fromkeys(DELIMITERS, 0)
    quoted = False
    for char in first_line:
        if char == '"':
            quoted = not quoted
        elif not quoted and char in counts:
            counts[char] += 1
    best = max(counts, key=counts.get)
    return best if counts[best] else ";"


def _number(text: str | None) -> float | None:
    """A French or English decimal; None when the cell is empty."""
    if text is None:
        return None
    cleaned = text.replace(" ", "").replace(" ", "").replace(" ", "")
    cleaned = "".join(c for c in cleaned if c.isdigit() or c in ",.-")
    if not cleaned:
        return None
    if "," in cleaned:
        # 1.234,56 or 1234,56: the comma is the decimal mark either way.
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _broker(keys: set[str]) -> str:
    if {"isin", "quantity", "buyingprice"} <= keys:
        return "BoursoBank portfolio"
    if set(MOVEMENTS_SIGNATURE) <= keys:
        return "BoursoBank movements"
    return "unknown"


def parse(text: str) -> Parsed:
    if len(text.encode()) > MAX_BYTES:
        raise CsvError(f"file too large: {MAX_BYTES // 1024} KiB at most")
    text = text.lstrip("﻿")
    first_line = text.split("\n", 1)[0]
    if not first_line.strip():
        raise CsvError("empty file")

    delimiter = _delimiter(first_line)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter, quotechar='"')
    headers = [h.strip() for h in next(reader)]
    keys = {_normalise(h) for h in headers}
    broker = _broker(keys)

    columns: dict[str, int] = {}
    roles: dict[str, str] = {}
    for index, header in enumerate(headers):
        role = _role(header)
        if role and role not in columns:
            columns[role] = index
            roles[header] = role

    missing = [role for role in REQUIRED if role not in columns]
    if missing:
        if broker == "BoursoBank movements":
            raise CsvError(
                "this is an account movements export (date, label, amount); "
                "export the portfolio instead, it carries quantity and cost"
            )
        raise CsvError(f"no column for: {', '.join(missing)}")

    rows: list[Row] = []
    for number, cells in enumerate(reader, start=2):
        if not any(cell.strip() for cell in cells):
            continue
        if len(rows) >= MAX_ROWS:
            raise CsvError(f"too many rows: {MAX_ROWS} at most")

        def cell(role: str) -> str | None:
            index = columns.get(role)
            return (
                cells[index].strip()
                if index is not None and index < len(cells)
                else None
            )

        isin = (cell("identifier") or "").upper()
        if not isin:
            raise CsvError("empty identifier", number)
        quantity = _number(cell("quantity"))
        if quantity is None or quantity <= 0:
            raise CsvError("quantity must be a positive number", number)
        prum = _number(cell("cost"))
        if prum is None or prum <= 0:
            raise CsvError("cost basis must be a positive number", number)
        price = _number(cell("valuation"))
        rows.append(
            Row(
                isin=isin,
                name=cell("name") or isin,
                quantity=quantity,
                prum=prum,
                price=price if price and price > 0 else None,
            )
        )

    return Parsed(rows=rows, delimiter=delimiter, broker=broker, roles=roles)
