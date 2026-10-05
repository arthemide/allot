"""Summarising a discovery run: which endpoints carry figures, JSON or HTML."""

from __future__ import annotations

import json
from pathlib import Path

from src.connectors.mask import valid_isin
from src.connectors.summary import (
    Capture,
    find_isins,
    load,
    render,
    scan_json,
    selector_hints,
    summarise,
)

ISIN = "FR0010315770"
OTHER = "IE00B4L5Y983"


def capture(seq: int, kind: str, url: str, body, method: str = "GET") -> Capture:
    return Capture(
        seq=seq,
        kind=kind,
        method=method,
        url=url,
        status=200,
        content_type="application/json" if kind == "json" else "text/html",
        file=f"{seq:03d}.{kind}",
        body=body,
    )


POSITIONS = {
    "positions": [
        {"isin": ISIN, "label": "LYXOR", "quantity": 3, "amount": "1 234,56"},
        {"isin": OTHER, "libelle": "ISHARES", "nbParts": 1.5, "valuation": 99.0},
    ],
    "cashBalance": 12.0,
    "flag": True,
}
HTML = (
    '<table><tr class="c-table__row"><td>'
    f'<span class="c-name">{ISIN}</span></td><td>1 234,56 €</td></tr>'
    f'<tr class="c-table__row"><td><span class="c-name">{OTHER}</span>'
    "</td><td>99,00 €</td></tr></table>"
)


class TestIsin:
    def test_the_check_digit_tells_an_isin_from_lookalikes(self):
        assert valid_isin(ISIN) and valid_isin(OTHER)
        assert not valid_isin("FR0010315771")
        assert find_isins(f"{ISIN} FR0010315771 ABCDEFGHIJKL") == {ISIN}


class TestScanJson:
    def test_amounts_quantities_labels_and_isins_are_counted(self):
        signals = scan_json(POSITIONS)
        assert signals.isins == {ISIN, OTHER}
        assert signals.quantities == 2
        assert signals.amounts == 3
        assert signals.labels == 2
        assert {"quantity", "nbParts", "cashBalance", "libelle"} <= signals.keys


class TestSummarise:
    def test_json_wins_when_it_carries_every_isin(self):
        # Given a positions call fetched twice, a noise call and the page itself
        captures = [
            capture(1, "json", "https://x.boursobank.com/api/positions?p=1", POSITIONS),
            capture(2, "json", "https://x.boursobank.com/api/positions?p=2", POSITIONS),
            capture(3, "json", "https://x.boursobank.com/api/menu", {"items": []}),
            capture(4, "html", "https://x.boursobank.com/pea", HTML),
        ]
        # When the run is summarised
        summary = summarise(captures, {"tracker.example": 3})
        # Then the positions endpoint comes first, grouped across its queries
        assert summary.verdict == "json"
        assert summary.ignored == 1
        top = summary.endpoints[0]
        assert top.url == "https://x.boursobank.com/api/positions"
        assert top.hits == 2 and top.files == ["001.json", "002.json"]
        assert summary.blocked == {"tracker.example": 3}

    def test_html_wins_when_isins_only_appear_in_the_page(self):
        captures = [
            capture(1, "json", "https://x/api/menu", {"items": []}),
            capture(2, "html", "https://x/pea", HTML),
        ]
        summary = summarise(captures, {})
        assert summary.verdict == "html"
        assert summary.selectors == [("span.c-name", 2)]
        assert summary.endpoints[0].signals.amounts == 2

    def test_html_amounts_alone_still_point_at_the_page(self):
        captures = [capture(1, "html", "https://x/av", "<p>Solde 10 000,00 €</p>")]
        assert summarise(captures, {}).verdict == "html"

    def test_nothing_relevant_says_so(self):
        summary = summarise([capture(1, "json", "https://x/api", {"ok": True})], {})
        assert summary.verdict == "none"
        assert "target page" in render(summary)

    def test_the_report_names_endpoints_selectors_and_blocked_hosts(self):
        captures = [
            capture(1, "json", "https://x/api/positions", POSITIONS),
            capture(2, "html", "https://x/pea", HTML),
        ]
        report = render(summarise(captures, {"tracker.example": 3}))
        assert "[json] GET https://x/api/positions" in report
        assert "isins=2" in report
        assert "span.c-name" in report
        assert "tracker.example  x3" in report


class TestSelectorHints:
    def test_an_isin_without_a_classed_parent_gives_no_hint(self):
        assert selector_hints(f"<td>{ISIN}</td>") == {}


class TestLoad:
    def test_a_run_reads_back_as_written(self, tmp_path: Path):
        (tmp_path / "001.json").write_text(
            json.dumps({"url": "u", "method": "GET", "body": POSITIONS})
        )
        (tmp_path / "002.html").write_text(HTML)
        entries = [
            capture(1, "json", "https://x/api", None).model_dump(exclude={"body"}),
            capture(2, "html", "https://x/pea", None).model_dump(exclude={"body"}),
        ]
        (tmp_path / "index.json").write_text(
            json.dumps({"captures": entries, "blocked": {"t": 1}})
        )
        captures, blocked = load(tmp_path)
        assert captures[0].body == POSITIONS
        assert captures[1].body == HTML
        assert blocked == {"t": 1}
