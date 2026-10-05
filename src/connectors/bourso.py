"""Read BoursoBank's PEA from the pages the server renders.

Nothing on these pages comes as JSON: the positions table and the cash
balance are server-rendered HTML. Columns are found through the sort link in
each header (`?colonne=quantity`), which names what the column holds whatever
its position or caption; the caption is only a fallback. The table under
"Gestion Libre" has an extra leading column of buy/sell buttons, which is why
nothing here counts cells.

No browser, no network: HTML in, normalised rows out.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ConfigDict

from src.connectors.errors import LayoutChanged
from src.connectors.mask import ISIN, valid_isin
from src.connectors.store import PositionRow

ORIGIN = "https://clients.boursobank.com"
# Where the account links are, tried in order until one lists a PEA. The
# dashboard comes last and is read once its scripts have run: it loads the
# account list after the page (its `/dashboard/comptes` fragment answers 404
# when asked for directly).
ACCOUNT_LISTS = ("/produits/mes-produits", "/compte/", "/")
POSITIONS = "positions"

PEA_PATH = re.compile(r"^/compte/(pea|pea-pme)/([^/?#]+)/")
LOGIN_PATH = re.compile(r"^/connexion(/|$)")

# Header captions, normalised, for a header that lost its sort link.
CAPTIONS = {
    "valeur": "name",
    "quantite": "quantity",
    "pxrevient": "buyingPrice",
    "cours": "lastPrice",
    "montant": "amount",
    "latentes": "amountVariation",
}
REQUIRED = ("name", "amount")


class Line(BaseModel):
    model_config = ConfigDict(frozen=True)

    # "managed" under Gestion Profilée, "free" for what is held directly.
    section: Literal["managed", "free"]
    isin: str | None
    label: str
    quantity: float | None
    unit_cost: float | None
    unit_price: float | None
    value: float
    gain: float | None


class Portfolio(BaseModel):
    model_config = ConfigDict(frozen=True)

    lines: list[Line]
    cash: float | None


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())


def parse_french_number(text: str | None) -> float | None:
    """`- 1 234,56 €` -> -1234.56. None for an empty cell or a dash."""
    if text is None:
        return None
    cleaned = re.sub(r"[\s  €%]|EUR", "", text)
    if not cleaned or cleaned in ("-", "+"):
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def is_login_url(url: str) -> bool:
    return bool(LOGIN_PATH.match(urlsplit(url).path))


def find_pea_paths(html: str) -> list[str]:
    """Every PEA and PEA-PME account linked from a page, in order, once each."""
    paths: list[str] = []
    for link in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        match = PEA_PATH.match(urlsplit(link["href"]).path)
        if match and match.group(0) not in paths:
            paths.append(match.group(0))
    return paths


def account_name(path: str) -> str:
    """ "PEA" or "PEA-PME": the key in the path is an identifier, never stored."""
    match = PEA_PATH.match(path)
    return match.group(1).upper() if match else "PEA"


def _text(node: Tag | None) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _columns(table: Tag) -> dict[str, int]:
    columns: dict[str, int] = {}
    for index, th in enumerate(table.select("thead th")):
        link = th.find("a", href=True)
        name = None
        if link:
            name = parse_qs(urlsplit(link["href"]).query).get("colonne", [None])[0]
        if not name:
            caption = _normalise(_text(th))
            name = next((c for k, c in CAPTIONS.items() if caption.endswith(k)), None)
        if name:
            columns.setdefault(name, index)
    missing = [name for name in REQUIRED if name not in columns]
    if missing:
        raise LayoutChanged(f"positions table without column(s): {', '.join(missing)}")
    return columns


def _value(cells: list[Tag], columns: dict[str, int], name: str) -> float | None:
    """The figure of a cell, leaving out what sits beside it (intraday change)."""
    index = columns.get(name)
    if index is None or index >= len(cells):
        return None
    cell = cells[index]
    return parse_french_number(
        _text(cell.select_one(".c-table__cell-content-wrapper") or cell)
    )


def _section(table: Tag) -> str | None:
    heading = table.find_previous("h3")
    return _text(heading) if heading else None


def parse_positions(html: str) -> Portfolio:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table[data-table-trading-operations]")
    if not tables:
        raise LayoutChanged("no positions table on the page")

    lines: list[Line] = []
    for table in tables:
        heading = _normalise(_section(table) or "")
        if "liquidation" in heading:  # pending deferred-settlement orders
            continue
        section = "managed" if "profilee" in heading else "free"
        columns = _columns(table)
        for row in table.select("tbody tr"):
            cells = row.find_all("td", recursive=False)
            if columns["name"] >= len(cells):
                continue
            name_cell = cells[columns["name"]]
            mention = _text(name_cell.select_one(".c-table__mention"))
            label = (
                _text(
                    name_cell.select_one(".c-link__label")
                    or name_cell.select_one(".c-table__cell-content-wrapper")
                )
                or _text(name_cell).removesuffix(mention).strip()
            )
            value = _value(cells, columns, "amount")
            if not label or value is None:
                continue
            isin = mention if ISIN.fullmatch(mention) and valid_isin(mention) else None
            lines.append(
                Line(
                    section=section,
                    isin=isin,
                    label=label,
                    quantity=_value(cells, columns, "quantity"),
                    unit_cost=_value(cells, columns, "buyingPrice"),
                    unit_price=_value(cells, columns, "lastPrice"),
                    value=value,
                    gain=_value(cells, columns, "amountVariation"),
                )
            )
    return Portfolio(lines=lines, cash=_cash(soup))


def _cash(soup: BeautifulSoup) -> float | None:
    for item in soup.select("li.c-databox-list__item"):
        name = _normalise(_text(item.select_one(".c-databox__name")))
        if name.startswith("soldeespeces"):
            return parse_french_number(_text(item.select_one(".c-databox__value")))
    return None


def to_rows(account: str, portfolio: Portfolio) -> list[PositionRow]:
    rows = [
        PositionRow(
            account=account,
            support_type="managed" if line.section == "managed" else "security",
            isin=line.isin,
            label=line.label,
            quantity=line.quantity,
            value=line.value,
            unit_cost=line.unit_cost,
            unit_price=line.unit_price,
            gain=line.gain,
        )
        for line in portfolio.lines
    ]
    if portfolio.cash is not None:
        rows.append(
            PositionRow(
                account=account, support_type="cash", label="Cash", value=portfolio.cash
            )
        )
    return rows
