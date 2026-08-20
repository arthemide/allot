"""Render the monthly note as plain text.

Plain text aligned with spaces, no Markdown, 78 columns maximum, so it stays
readable once pasted into a reminder description field. The app has no notion
of recurrence or event: it just renders the note as of now.

The note itself is written in French, matching the specified format; the code
around it is not.
"""

from __future__ import annotations

from datetime import date, datetime

from src.databases import sqlite as db
from src.services import allocation, prices

WIDTH = 78
PREFIX_WIDTH = 17
STALE_DAYS = 45

MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _money(value: float, currency: str = "EUR", decimals: int = 2) -> str:
    symbol = "$" if currency == "USD" else "€"
    formatted = f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return f"{formatted} {symbol}"


def _round_money(value: float, currency: str = "EUR") -> str:
    return _money(value, currency, decimals=0)


def _envelope_label(name: str, amount: float) -> str:
    return f"{name} — {_round_money(amount)}"


def _asset_line(asset: dict) -> str:
    """The right-hand part of an asset line, after the envelope prefix."""
    amount = _money(asset["amount"])
    cell = f"{asset['symbol']:<9} {amount:>10}"

    price = asset["price"]
    prum = asset["prum"]
    if price is None:
        return f"{cell}   cours indisponible"

    if prum:
        gap = (price - prum) / prum * 100
        sign = "+" if gap >= 0 else "−"
        multiplier = f"{asset['multiplier']:g}".replace(".", ",")
        return (
            f"{cell}  {_round_money(price, asset['currency'])} vs PRUM "
            f"{_round_money(prum, asset['currency'])} "
            f"({sign}{abs(gap):.0f} %) ×{multiplier}"
        )

    shares = asset["amount"] / price
    unit = "part" if shares < 2 else "parts"
    count = f"{shares:,.2f}".replace(",", " ").replace(".", ",")
    return f"{cell}  {_money(price, asset['currency'])}     ≈ {count} {unit}"


def _stale_warning(today: date) -> str | None:
    last = db.last_transaction_date()
    if last is None:
        return "⚠ Aucune transaction saisie."
    last_date = datetime.fromisoformat(last).date()
    if (today - last_date).days <= STALE_DAYS:
        return None
    day = last_date.day
    return (
        f"⚠ Aucune transaction saisie depuis le {day} "
        f"{MONTHS[last_date.month - 1]}."
    )


def render(today: date | None = None) -> str:
    today = today or date.today()
    envelopes = allocation.plan()
    rate = prices.eur_usd_rate()

    header_left = f"Point patrimoine — {MONTHS[today.month - 1]} {today.year}"
    total = sum(e["amount"] for e in envelopes)
    header_right = f"Épargne à placer : {_round_money(total)}"
    padding = max(1, WIDTH - len(header_left) - len(header_right))
    lines = [header_left + " " * padding + header_right, ""]

    # Envelopes holding priced assets get a block; the others are collapsed
    # onto a single line of bare amounts, as in the reference format.
    bare = []
    for envelope in envelopes:
        priced = [a for a in envelope["assets"] if a["price_source"] != "manual"]
        if not priced:
            bare.append(_envelope_label(envelope["envelope"], envelope["amount"]))
            continue
        prefix = _envelope_label(envelope["envelope"], envelope["amount"])
        for index, asset in enumerate(priced):
            left = prefix if index == 0 else ""
            lines.append(f"{left:<{PREFIX_WIDTH}}{_asset_line(asset)}".rstrip())

    if bare:
        lines.append("     ".join(bare))

    lines.append("")
    warning = _stale_warning(today)
    if warning:
        lines.append(warning)

    excel = ", ".join(
        f"{e['envelope']} {_round_money(_to_eur(e['market_value'], e, rate))}"
        for e in envelopes
        if e["market_value"]
    )
    lines.append(f"À recopier dans l'Excel : {excel or '—'}")

    return "\n".join(line[:WIDTH] for line in lines) + "\n"


def _to_eur(value: float, envelope: dict, rate: float | None) -> float:
    """Convert an envelope's market value to EUR, at the very last moment."""
    if not value:
        return 0.0
    currencies = {a["currency"] for a in envelope["assets"]}
    if currencies == {"USD"} and rate:
        return value / rate
    return value
