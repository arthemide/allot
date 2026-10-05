"""What a discovery run caught, reduced to the endpoints worth reading.

An endpoint is worth reading when it carries amounts, quantities, ISINs or
fund labels. The verdict says where the figures actually come from: JSON the
page fetches, or HTML the server renders - in which case the extractor parses
the page, and the selector hints say where to start.

Pure except for `load`, which reads back what `browser.py` wrote.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict

from src.connectors.mask import valid_isin

# Key fragments, normalised like the masking does, by what the value holds.
AMOUNT_KEYS = (
    "amount",
    "montant",
    "valuation",
    "valorisation",
    "value",
    "valeur",
    "balance",
    "solde",
    "price",
    "prix",
    "cours",
    "pru",
    "gain",
    "plusvalue",
    "encours",
    "capital",
    "total",
)
QUANTITY_KEYS = (
    "quantity",
    "quantite",
    "qty",
    "nbparts",
    "nombredeparts",
    "shares",
    "units",
)
LABEL_KEYS = (
    "label",
    "libelle",
    "name",
    "designation",
    "intitule",
    "support",
    "fund",
    "fonds",
)

ISIN = re.compile(r"(?<![A-Z0-9])[A-Z]{2}[A-Z0-9]{9}\d(?![A-Z0-9])")
NUMERIC = re.compile(r"^-?\d{1,3}(?:[   .]?\d{3})*(?:[.,]\d+)?$")
# "1 234,56 €" as a French page prints it.
HTML_AMOUNT = re.compile(r"\d{1,3}(?:[   ]\d{3})*,\d{2}\s*(?:€|&euro;|EUR)")
OPENING_TAG = re.compile(r"<([a-zA-Z][\w-]*)\b[^>]*\bclass=[\"']([^\"']+)[\"'][^>]*>")


class Capture(BaseModel):
    """One response, as written to the dump: already masked."""

    model_config = ConfigDict(frozen=True)

    seq: int
    kind: Literal["json", "html"]
    method: str
    url: str
    status: int
    content_type: str
    file: str
    body: Any = None


class Signals(BaseModel):
    amounts: int = 0
    quantities: int = 0
    labels: int = 0
    isins: set[str] = set()
    keys: set[str] = set()

    def merge(self, other: Signals) -> None:
        self.amounts += other.amounts
        self.quantities += other.quantities
        self.labels += other.labels
        self.isins |= other.isins
        self.keys |= other.keys

    @property
    def relevant(self) -> bool:
        return bool(self.amounts or self.quantities or self.isins)


class Endpoint(BaseModel):
    kind: Literal["json", "html"]
    method: str
    url: str
    hits: int
    statuses: set[int]
    files: list[str]
    signals: Signals


class Summary(BaseModel):
    verdict: Literal["json", "html", "none"]
    reason: str
    endpoints: list[Endpoint]
    ignored: int
    blocked: dict[str, int]
    selectors: list[tuple[str, int]]


def _normalise(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def find_isins(text: str) -> set[str]:
    return {code for code in ISIN.findall(text) if valid_isin(code)}


def _numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return isinstance(value, str) and bool(NUMERIC.match(value.strip()))


def scan_json(body: Any) -> Signals:
    signals = Signals()

    def walk(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for k, item in value.items():
                walk(item, k)
            return
        if isinstance(value, list):
            for item in value:
                walk(item, key)
            return
        norm = _normalise(key)
        if isinstance(value, str):
            signals.isins |= find_isins(value)
        if _numeric(value) and any(f in norm for f in QUANTITY_KEYS):
            signals.quantities += 1
            signals.keys.add(key)
        elif _numeric(value) and any(f in norm for f in AMOUNT_KEYS):
            signals.amounts += 1
            signals.keys.add(key)
        elif isinstance(value, str) and any(f in norm for f in LABEL_KEYS):
            signals.labels += 1
            signals.keys.add(key)

    walk(body)
    return signals


def scan_html(html: str) -> Signals:
    return Signals(amounts=len(HTML_AMOUNT.findall(html)), isins=find_isins(html))


def selector_hints(html: str, window: int = 600) -> Counter[str]:
    """The nearest classed element before each ISIN: where a parser would look."""
    hints: Counter[str] = Counter()
    for match in ISIN.finditer(html):
        if not valid_isin(match.group(0)):
            continue
        before = html[max(0, match.start() - window) : match.start()]
        tags = OPENING_TAG.findall(before)
        if tags:
            tag, classes = tags[-1]
            hints[f"{tag}.{'.'.join(classes.split())}"] += 1
    return hints


def _endpoint_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def summarise(captures: list[Capture], blocked: dict[str, int]) -> Summary:
    endpoints: dict[tuple[str, str, str], Endpoint] = {}
    selectors: Counter[str] = Counter()
    for capture in captures:
        if capture.kind == "json":
            signals = scan_json(capture.body)
        else:
            signals = scan_html(capture.body or "")
            selectors += selector_hints(capture.body or "")
        key = (capture.kind, capture.method, _endpoint_url(capture.url))
        endpoint = endpoints.setdefault(
            key,
            Endpoint(
                kind=capture.kind,
                method=capture.method,
                url=key[2],
                hits=0,
                statuses=set(),
                files=[],
                signals=Signals(),
            ),
        )
        endpoint.hits += 1
        endpoint.statuses.add(capture.status)
        endpoint.files.append(capture.file)
        endpoint.signals.merge(signals)

    relevant = sorted(
        (e for e in endpoints.values() if e.signals.relevant),
        key=lambda e: (
            -len(e.signals.isins),
            -e.signals.quantities,
            -e.signals.amounts,
            e.url,
        ),
    )
    json_isins = set().union(*(e.signals.isins for e in relevant if e.kind == "json"))
    html_isins = set().union(*(e.signals.isins for e in relevant if e.kind == "html"))
    json_figures = any(e.kind == "json" for e in relevant)
    html_figures = any(e.kind == "html" for e in relevant)

    if html_isins - json_isins:
        verdict, reason = (
            "html",
            f"{len(html_isins - json_isins)} ISIN(s) appear in server-rendered HTML "
            "that no JSON response carries",
        )
    elif json_figures:
        verdict, reason = "json", "the figures arrive in JSON responses"
    elif html_figures:
        verdict, reason = "html", "amounts only appear in server-rendered HTML"
    else:
        verdict, reason = (
            "none",
            "no amount, quantity or ISIN was seen - was the target page open?",
        )

    return Summary(
        verdict=verdict,
        reason=reason,
        endpoints=relevant,
        ignored=len(endpoints) - len(relevant),
        blocked=dict(sorted(blocked.items(), key=lambda item: -item[1])),
        selectors=selectors.most_common(8),
    )


def render(summary: Summary) -> str:
    lines = [f"Verdict: {summary.verdict.upper()} - {summary.reason}", ""]
    if summary.endpoints:
        lines.append("Endpoints carrying figures:")
    for e in summary.endpoints:
        s = e.signals
        statuses = ",".join(str(code) for code in sorted(e.statuses))
        lines.append(f"  [{e.kind}] {e.method} {e.url}  (x{e.hits}, {statuses})")
        lines.append(
            f"      amounts={s.amounts} quantities={s.quantities} "
            f"labels={s.labels} isins={len(s.isins)}"
        )
        if s.keys:
            lines.append(f"      keys: {', '.join(sorted(s.keys)[:12])}")
        lines.append(f"      files: {', '.join(e.files[:5])}")
    lines.append(f"Endpoints with nothing relevant: {summary.ignored}")
    if summary.selectors:
        lines += ["", "HTML elements right before an ISIN:"]
        lines += [f"  {selector}  x{count}" for selector, count in summary.selectors]
    if summary.blocked:
        lines += ["", "Hosts refused (outside the bank's domains):"]
        lines += [f"  {host}  x{count}" for host, count in summary.blocked.items()]
    return "\n".join(lines)


def load(dump_dir: Path) -> tuple[list[Capture], dict[str, int]]:
    """Read a run back from its index, bodies included."""
    index = json.loads((dump_dir / "index.json").read_text(encoding="utf-8"))
    captures = []
    for entry in index["captures"]:
        text = (dump_dir / entry["file"]).read_text(encoding="utf-8")
        body = json.loads(text)["body"] if entry["kind"] == "json" else text
        captures.append(Capture(**entry, body=body))
    return captures, index["blocked"]
