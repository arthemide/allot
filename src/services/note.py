"""Render the monthly note as plain text.

Plain text with bullet points, no Markdown, 78 columns maximum, so it stays
readable once pasted into a reminder description field. The app has no notion
of recurrence or event: it just renders the note as of now.

Only ASCII punctuation is used for dashes and signs, so nothing turns into a
mojibake box depending on where the text is pasted. The note itself is written
in French, matching the specified format; the code around it is not.
"""

from __future__ import annotations

from datetime import date, datetime

from src.databases import sqlite as db
from src.services import allocation, prices

WIDTH = 78
STALE_DAYS = 45

MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _money(value: float, currency: str = "EUR", decimals: int = 0) -> str:
    symbol = "$" if currency == "USD" else "€"
    formatted = f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return f"{formatted} {symbol}"


def _asset_line(asset: dict) -> str:
    """One bullet per asset: how much to put in, and why."""
    cell = f"  - {asset['symbol']:<9} {_money(asset['amount'], decimals=2):>10}"

    price = asset["price"]
    prum = asset["prum"]
    if price is None:
        return f"{cell}   cours indisponible"

    if prum:
        gap = (price - prum) / prum * 100
        multiplier = f"{asset['multiplier']:g}".replace(".", ",")
        return (
            f"{cell}   {_money(price, asset['currency'])} vs PRUM "
            f"{_money(prum, asset['currency'])} "
            f"({gap:+.0f} %) x{multiplier}"
        )

    return f"{cell}   cours {_money(price, asset['currency'], decimals=2)}"


def _stale_warning(today: date) -> str | None:
    last = db.last_transaction_date()
    if last is None:
        return "- Aucune transaction saisie."
    last_date = datetime.fromisoformat(last).date()
    if (today - last_date).days <= STALE_DAYS:
        return None
    return (
        f"- Aucune transaction saisie depuis le {last_date.day} "
        f"{MONTHS[last_date.month - 1]}."
    )


def render(today: date | None = None) -> str:
    today = today or date.today()
    envelopes = allocation.plan()
    rate = prices.eur_usd_rate()

    total = sum(e["amount"] for e in envelopes)
    lines = [
        f"Point patrimoine - {MONTHS[today.month - 1]} {today.year}",
        f"À placer ce mois : {_money(total)}",
        "",
    ]

    for envelope in envelopes:
        lines.append(f"{envelope['envelope']} - {_money(envelope['amount'])}")
        for asset in envelope["assets"]:
            lines.append(_asset_line(asset))

    lines.append("")
    warning = _stale_warning(today)
    if warning:
        lines.append(warning)

    excel = ", ".join(
        f"{e['envelope']} {_money(_to_eur(e['market_value'], e, rate))}"
        for e in envelopes
        if e["market_value"]
    )
    lines.append(f"- À recopier dans l'Excel : {excel or 'rien'}")

    return "\n".join(line[:WIDTH] for line in lines) + "\n"


def _to_eur(value: float, envelope: dict, rate: float | None) -> float:
    """Convert an envelope's market value to EUR, at the very last moment."""
    if not value:
        return 0.0
    currencies = {a["currency"] for a in envelope["assets"]}
    if currencies == {"USD"} and rate:
        return value / rate
    return value
