"""Command line: one run at a time, against one bank.

uv run --group connectors python -m src.connectors discover bourso
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from src.connectors.banks import BANKS, Bank
from src.connectors.errors import LayoutChanged, SessionExpired
from src.connectors.paths import DATA_DIR, DB_PATH, DUMPS_DIR, LOCK, PROFILES_DIR
from src.connectors.summary import load, render, summarise


@contextmanager
def single_run():
    """Refuse a second run while one is going: one bank session at a time."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        sys.exit(f"Another run is going. If none is, delete {LOCK}.")
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        yield
    finally:
        LOCK.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m src.connectors")
    commands = parser.add_subparsers(dest="command", required=True)
    discover = commands.add_parser(
        "discover", help="log in by hand and record the JSON the site fetches"
    )
    discover.add_argument("bank", choices=sorted(BANKS))
    discover.add_argument(
        "--fresh",
        action="store_true",
        help="use a temporary browser profile instead of the saved bank session",
    )
    sync = commands.add_parser(
        "sync", help="read the positions with the saved session and store them"
    )
    sync.add_argument("bank", choices=sorted(BANKS))
    sync.add_argument(
        "--visible", action="store_true", help="show the browser while it reads"
    )
    again = commands.add_parser("summary", help="summarise a past discovery run")
    again.add_argument("dump_dir", type=Path)
    args = parser.parse_args()

    if args.command == "summary":
        print(render(summarise(*load(args.dump_dir))))
        return

    # Imported here so the pure modules never need Playwright installed.
    from src.connectors import browser

    bank = BANKS[args.bank]
    if args.command == "sync":
        run_sync(bank, args.visible)
        return
    with single_run():
        if args.fresh:
            # A clean device can reveal a stronger login method without erasing
            # the profile used by regular browser-driven syncs.
            with TemporaryDirectory(prefix=f"{bank.key}-", dir=PROFILES_DIR) as profile:
                recorder = asyncio.run(browser.discover(bank, Path(profile), DUMPS_DIR))
        else:
            recorder = asyncio.run(
                browser.discover(
                    bank,
                    profile_dir=PROFILES_DIR / bank.key,
                    dumps_dir=DUMPS_DIR,
                )
            )
    report = render(summarise(recorder.captures, dict(recorder.blocked)))
    (recorder.dump_dir / "summary.txt").write_text(report + "\n", encoding="utf-8")
    print(f"\n{len(recorder.captures)} responses written to {recorder.dump_dir}\n")
    print(report)


def run_sync(bank: Bank, visible: bool) -> None:
    from src.connectors import bourso, browser, store

    if bank.key != "bourso":
        sys.exit(f"sync {bank.key}: not written yet - run discover first.")
    with single_run():
        try:
            accounts = asyncio.run(
                browser.sync_bourso(bank, PROFILES_DIR / bank.key, visible)
            )
        except (SessionExpired, LayoutChanged) as error:
            sys.exit(str(error))
    rows = [row for name, p in accounts for row in bourso.to_rows(name, p)]
    snapshot_id = store.save_snapshot(DB_PATH, bank.key, rows)
    print(f"Snapshot {snapshot_id} stored in {DB_PATH}:")
    for row in rows:
        quantity = "" if row.quantity is None else f"{row.quantity:g}"
        print(
            f"  {row.account:<8} {row.support_type:<8} {row.isin or '-':<12} "
            f"{quantity:>10} {row.value:>12.2f} {row.currency}  {row.label}"
        )


if __name__ == "__main__":
    main()
