"""The only part that drives a browser. Not unit-tested: it needs a human.

`discover` opens a visible window where the user does everything - logging
in, 2FA, navigating - while this code listens. `sync` reuses the session the
profile kept and only ever loads pages by address. Neither clicks, types or
submits, and both refuse every host outside the bank's domains.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import random
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlsplit

from playwright.async_api import BrowserContext, Page, Response, Route, async_playwright

from src.connectors import bourso
from src.connectors.banks import Bank
from src.connectors.errors import LayoutChanged, SessionExpired
from src.connectors.mask import mask_html, mask_json, mask_url
from src.connectors.summary import Capture

# Seconds between two pages of a sync, drawn at random each time.
PAUSE = (2.0, 6.0)

# Chromium's own background traffic: updates, sync, metrics, safe browsing.
QUIET_CHROMIUM = [
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-domain-reliability",
    "--disable-client-side-phishing-detection",
    "--disable-default-apps",
    "--metrics-recording-only",
    "--no-pings",
    "--no-first-run",
    "--disable-features=Translate,OptimizationHints,MediaRouter",
]


class Recorder:
    """Masks each response worth keeping and writes it to the run's folder."""

    def __init__(self, dump_dir: Path):
        self.dump_dir = dump_dir
        self.captures: list[Capture] = []
        self.blocked: Counter[str] = Counter()
        self.pending: set[asyncio.Task] = set()

    @staticmethod
    def _shape(value):
        """Keep JSON keys and scalar sizes without writing authentication data."""
        if isinstance(value, dict):
            return {key: Recorder._shape(item) for key, item in value.items()}
        if isinstance(value, list):
            return [Recorder._shape(item) for item in value[:3]]
        if isinstance(value, str):
            try:
                encoded = base64.b64decode(value, validate=True) if value else b""
            except (binascii.Error, ValueError):
                encoded = b""
            return {
                "type": "string",
                "length": len(value),
                "base64_bytes": len(encoded) if encoded else None,
            }
        return type(value).__name__

    def on_response(self, response: Response) -> None:
        task = asyncio.ensure_future(self._record(response))
        self.pending.add(task)
        task.add_done_callback(self.pending.discard)

    async def _record(self, response: Response) -> None:
        request = response.request
        content_type = (response.headers.get("content-type") or "").split(";")[0]
        if request.resource_type in ("xhr", "fetch") and "json" in content_type:
            kind = "json"
        elif (
            request.resource_type in ("document", "xhr", "fetch")
            and "html" in content_type
        ):
            # Fragments too: BoursoBank loads its account list as HTML in XHR.
            kind = "html"
        else:
            return
        try:
            text = await response.text()
        except Exception:  # redirects and aborted loads have no body
            return

        seq = len(self.captures) + 1
        url = mask_url(response.url)
        if kind == "json":
            try:
                parsed = json.loads(text)
                body = mask_json(parsed)
                shape = self._shape(parsed)
            except ValueError:
                body = mask_html(text)
                shape = None
            file = f"{seq:03d}.json"
            payload = {"url": url, "method": request.method, "body": body}
            if shape is not None:
                payload["shape"] = shape
            content = json.dumps(payload, ensure_ascii=False, indent=2)
        else:
            body = mask_html(text)
            file = f"{seq:03d}.html"
            content = body
        (self.dump_dir / file).write_text(content, encoding="utf-8")
        self.captures.append(
            Capture(
                seq=seq,
                kind=kind,
                method=request.method,
                url=url,
                status=response.status,
                content_type=content_type,
                file=file,
                body=body,
            )
        )

    def write_index(self) -> None:
        index = {
            "captures": [c.model_dump(exclude={"body"}) for c in self.captures],
            "blocked": dict(self.blocked),
        }
        (self.dump_dir / "index.json").write_text(
            json.dumps(index, indent=2), encoding="utf-8"
        )


@asynccontextmanager
async def _browser(
    bank: Bank, profile_dir: Path, headless: bool, blocked: Counter[str]
) -> AsyncIterator[BrowserContext]:
    """The persistent profile, gated to the bank's domains."""
    profile_dir.mkdir(parents=True, exist_ok=True)

    async def gate(route: Route) -> None:
        url = route.request.url
        if bank.allows(url):
            await route.continue_()
        else:
            blocked[urlsplit(url).hostname or url] += 1
            await route.abort("blockedbyclient")

    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            args=QUIET_CHROMIUM,
            # Service workers would answer requests the gate never sees.
            service_workers="block",
            locale="fr-FR",
        )
        await context.route("**/*", gate)
        try:
            yield context
        finally:
            try:
                await context.close()
            except Exception:  # the user may have closed the window already
                pass


async def discover(bank: Bank, profile_dir: Path, dumps_dir: Path) -> Recorder:
    dump_dir = dumps_dir / bank.key / datetime.now().strftime("%Y%m%d-%H%M%S")
    dump_dir.mkdir(parents=True)
    recorder = Recorder(dump_dir)

    async with _browser(bank, profile_dir, False, recorder.blocked) as context:
        context.on("response", recorder.on_response)
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(bank.start_url)

        print(
            f"\nLog in to {bank.name} in the browser window, then open {bank.target}."
        )
        print("Recording. Press Enter here once the page is fully loaded.")
        await asyncio.to_thread(input)

        if recorder.pending:
            await asyncio.wait(set(recorder.pending), timeout=10)

    recorder.write_index()
    return recorder


async def _visit(page: Page, bank: Bank, url: str, rendered: bool = False) -> str:
    """Load one page by address, after a pause, and return its HTML.

    The HTML the server sent, or with `rendered` the page once its scripts have
    loaded what they load.
    """
    await asyncio.sleep(random.uniform(*PAUSE))
    response = await page.goto(
        url, wait_until="networkidle" if rendered else "domcontentloaded"
    )
    if bourso.is_login_url(page.url):
        raise SessionExpired(bank.name, bank.key)
    if response is None or not response.ok:
        status = response.status if response else "no response"
        raise LayoutChanged(f"{urlsplit(url).path} answered {status}")
    return await page.content() if rendered else await response.text()


async def sync_bourso(
    bank: Bank, profile_dir: Path, visible: bool
) -> list[tuple[str, bourso.Portfolio]]:
    """Every PEA the account lists, parsed. Nothing is stored here."""
    blocked: Counter[str] = Counter()
    async with _browser(bank, profile_dir, not visible, blocked) as context:
        page = context.pages[0] if context.pages else await context.new_page()
        paths: list[str] = []
        tried: list[str] = []
        for listing in bourso.ACCOUNT_LISTS:
            try:
                html = await _visit(page, bank, bourso.ORIGIN + listing, rendered=True)
            except LayoutChanged as error:  # this page is gone; try the next
                tried.append(str(error))
                continue
            paths = bourso.find_pea_paths(html)
            if paths:
                break
            tried.append(f"{listing} lists no PEA")
        if not paths:
            raise LayoutChanged(
                "no PEA link found ("
                + "; ".join(tried)
                + "). Run discover, open the account list, and send the summary."
            )
        return [
            (
                bourso.account_name(path),
                bourso.parse_positions(
                    await _visit(page, bank, bourso.ORIGIN + path + bourso.POSITIONS)
                ),
            )
            for path in paths
        ]
