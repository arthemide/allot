"""The monthly note as plain text, and the calendar feed around it.

The note is a checklist: one line per thing to do this month, and under each
the link that opens the app on that asset. Plain text, no Markdown, 78 columns
maximum so it survives a reminder field - links excepted, a cut URL being a
dead one. ASCII punctuation only, so nothing turns into a mojibake box
wherever it is pasted.

The feed is the same thing twelve months at a time, rebuilt on every request,
so a subscribed calendar never holds a copy that quietly went stale.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from src import calc
from src.databases import sqlite as db
from src.models.schema import PlanAsset, PlanEntry, ProjectionEntry
from src.services import allocation

WIDTH = 78
STALE_DAYS = 45
FEED_MONTHS = 12

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _money(value: float, currency: str = "EUR", decimals: int = 0) -> str:
    symbol = "$" if currency == "USD" else "€"
    formatted = f"{value:,.{decimals}f}"
    return f"{formatted} {symbol}"


def title(today: date) -> str:
    return f"Portfolio check - {MONTHS[today.month - 1]} {today.year}"


def _link(base_url: str | None, symbol: str) -> str | None:
    """The app, opened on one asset. Nothing when no base URL is known."""
    if not base_url:
        return None
    return f"    {base_url.rstrip('/')}/?asset={symbol}"


def _asset_line(asset: PlanAsset, box: str = "[ ] ") -> str:
    """What to buy, and nothing else: the reasoning is not a to-do."""
    if asset.units:
        units = "unit" if asset.units == 1 else "units"
        return (
            f"{box}{asset.symbol:<9} {asset.units} {units}"
            f"  {_money(asset.amount)}"
        )
    line = f"{box}{asset.symbol:<9} {_money(asset.amount, decimals=2)}"
    # Without a quote the amount is still the plan, but it was not checked
    # against a price and cannot be turned into a number of shares.
    return line if asset.price else f"{line}  no quote"


def _waiting_lines(envelope: PlanEntry, today: date) -> list[str]:
    """Why an envelope does nothing this month, and when it will.

    The cheapest of the assets it is saving for: that is what the wait is
    about, and naming a month makes it bearable.
    """
    lines = [
        f"{envelope.envelope} - nothing this month. {_money(envelope.budget)} in cash."
    ]

    target = min(envelope.waiting, key=lambda m: m.price_eur or 0.0)
    if target.missing <= 0:
        return lines

    when = target.months_left
    tail = ""
    if when:
        month = calc.add_months(today.replace(day=1), when)
        tail = f" ({MONTHS[month.month - 1]})"
    lines.append(
        f"{_money(target.missing)} short for 1 {target.symbol}{tail}."
    )
    return lines


def _stale_warning(today: date) -> str | None:
    last = db.last_transaction_date()
    if last is None:
        return "No transaction recorded."
    last_date = datetime.fromisoformat(last).date()
    if (today - last_date).days <= STALE_DAYS:
        return None
    return f"Nothing recorded since {MONTHS[last_date.month - 1]} {last_date.day}."


def _spendable(asset: PlanAsset) -> bool:
    """Held but never topped up, or owed nothing: no line in a to-do list."""
    return bool(asset.weight) and asset.amount > 0


def render(base_url: str | None = None, today: date | None = None) -> str:
    today = today or date.today()
    envelopes = allocation.plan(today)

    lines = [title(today)]
    total = sum(
        asset.amount
        for envelope in envelopes
        for asset in envelope.assets
        if _spendable(asset)
    )
    lines.append(f"{_money(total)} to invest this month.")

    for envelope in envelopes:
        buying = [a for a in envelope.assets if _spendable(a)]
        # A dormant envelope is noise: no cash to follow, nothing to place.
        if not buying and not envelope.cash and not envelope.budget:
            continue
        lines.append("")

        if not buying:
            if envelope.waiting:
                lines += _waiting_lines(envelope, today)
            elif envelope.budget:
                # Funded, but every asset sits at weight 0: the money has
                # nowhere to go, which is worth saying out loud.
                lines.append(
                    f"{envelope.envelope} - {_money(envelope.budget)} with "
                    f"no destination, no asset to fund."
                )
            else:
                lines.append(f"{envelope.envelope} - nothing this month.")
            continue

        if envelope.cash:
            lines.append(
                f"{envelope.envelope} - {_money(envelope.budget)} in cash"
            )
        else:
            lines.append(f"{envelope.envelope} - {_money(envelope.amount)}")

        for asset in buying:
            lines.append(_asset_line(asset))
            link = _link(base_url, asset.symbol)
            if link:
                lines.append(link)

        if envelope.carry >= 1:
            lines.append(f"{_money(envelope.carry)} left in cash.")

    warning = _stale_warning(today)
    if warning:
        lines.append("")
        lines.append(warning)

    return "\n".join(_clip(line) for line in lines) + "\n"


def _clip(line: str) -> str:
    """Keep the note within its columns, links excepted: a cut URL is dead."""
    return line if "://" in line else line[:WIDTH]


def _projected(month: date, entries: list[ProjectionEntry], base_url: str | None) -> str:
    """A month that has not happened yet, at today's prices."""
    lines = ["Projected at current pace, at today's prices."]
    for entry in entries:
        buying = [a for a in entry.assets if _spendable(a)]
        if not buying:
            continue
        lines.append("")
        label = " in cash" if entry.tracked else ""
        lines.append(f"{entry.envelope} - {_money(entry.budget)}{label}")
        for asset in buying:
            lines.append(_asset_line(asset, box="  "))
    if len(lines) == 1:
        lines.append("")
        lines.append("Nothing affordable that month: the cash keeps growing.")
    if base_url:
        lines.append("")
        lines.append(base_url)
    return "\n".join(_clip(line) for line in lines) + "\n"


def _escape(text: str) -> str:
    """RFC 5545 escaping for a TEXT value."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> list[str]:
    """Split a content line on 75 octets, continuations starting with a space."""
    octets = line.encode()
    if len(octets) <= 75:
        return [line]
    chunks, start = [], 0
    while start < len(octets):
        limit = 75 if not chunks else 74
        end = min(start + limit, len(octets))
        # Never cut inside a UTF-8 sequence.
        while end < len(octets) and octets[end] & 0xC0 == 0x80:
            end -= 1
        chunk = octets[start:end].decode()
        chunks.append(chunk if not chunks else f" {chunk}")
        start = end
    return chunks


def _event(day: date, summary: str, description: str, stamp: str) -> list[str]:
    return [
        "BEGIN:VEVENT",
        # Stable, so a refetch updates the occurrence instead of duplicating it.
        f"UID:allot-{day:%Y-%m}@allot",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
        # DTEND is exclusive: a one-day event ends the morning after.
        f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "TRIGGER:PT9H",
        f"DESCRIPTION:{_escape(summary)}",
        "END:VALARM",
        "END:VEVENT",
    ]


def feed(
    base_url: str | None = None,
    today: date | None = None,
    now: datetime | None = None,
) -> str:
    """Twelve months of events, rebuilt from scratch on every request.

    A calendar subscribes to this rather than importing a file once: the
    amounts move with the prices and with what has been bought, so every
    refetch corrects the previous one.
    """
    today = today or date.today()
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    # Every occurrence sits on the 1st, this month's included: with a stable
    # UID, dating it on the day it was fetched would walk the event across the
    # month at every refetch.
    first = today.replace(day=1)
    events = _event(first, title(today), render(base_url, today), stamp)
    for step in allocation.projection(today, FEED_MONTHS - 1):
        events += _event(
            step.month, title(step.month), _projected(step.month, step.envelopes, base_url), stamp
        )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Allot//Monthly note//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Allot",
        *events,
        "END:VCALENDAR",
    ]
    folded = [part for line in lines for part in _fold(line)]
    return "\r\n".join(folded) + "\r\n"
