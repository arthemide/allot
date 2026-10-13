"""Refresh the vendored woob boursorama module from woob's signed repository.

woob no longer cuts core releases (3.7 is the last one on PyPI), but it still
publishes its modules to https://updates.woob.tech/3/main/, the repository
`woob update` reads. That repository keeps only the latest build of each
module, so the module is vendored and every refresh lands as a reviewed diff.

woob's own installer is not used: it skips the signature check when gpg is
missing and trusts whatever keyring it downloads first. Here the keyring is
committed next to the module and pinned by its sha256, gpgv is mandatory, and
both the index and the archive must carry a good signature from that keyring.

    uv run --group woob python scripts/woob_update.py [--force]

Exits non-zero, leaving vendor/ untouched, on any failed check.
"""

from __future__ import annotations

import argparse
import configparser
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "woob-modules"
MODULE = "boursorama"

REPOSITORY = "https://updates.woob.tech/3/main/"
KEYRING = VENDOR / "trusted.gpg"
# The trust anchor. Changing either value is a manual decision: check the new
# keyring with the woob maintainers before bumping them.
KEYRING_SHA256 = "a1755b379793ff4922a7bfb5f566c019205f805b96f3420aee95938cd0d1634a"
KEY_UPDATE = 202103171007

LOCK = VENDOR / f"{MODULE}.lock"
# Shipped by the repository but useless here: the module's own test suite and
# bytecode built on woob's side.
DROPPED = ("test.py",)

TIMEOUT = 30


class UpdateError(RuntimeError):
    """A check failed; nothing was written."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--force",
        action="store_true",
        help="vendor the module again even if its version did not change",
    )
    args = parser.parse_args(argv)
    try:
        version = update(force=args.force)
    except UpdateError as error:
        print(f"woob update failed: {error}", file=sys.stderr)
        return 1
    _github_output("version", version)
    return 0


def update(force: bool = False) -> str:
    """Vendor the latest signed module; return its version."""
    gpgv = shutil.which("gpgv") or shutil.which("gpgv2")
    if gpgv is None:
        raise UpdateError("gpgv is required to check signatures (install gnupg)")
    keyring = KEYRING.read_bytes()
    if hashlib.sha256(keyring).hexdigest() != KEYRING_SHA256:
        raise UpdateError(f"{KEYRING} does not match its pinned sha256")

    index = _verified(gpgv, "modules.list")
    entry = select(index.decode("utf-8"), woob_version())

    current = read_lock().get("version")
    if current == entry["version"] and not force:
        print(f"{MODULE} {current} is already up to date")
        return current

    archive = _verified(gpgv, f"{MODULE}.tar.gz")
    install(archive)
    write_lock(
        {
            "version": entry["version"],
            "woob_spec": entry["woob_spec"],
            "sha256": hashlib.sha256(archive).hexdigest(),
            "repository": REPOSITORY,
            "fetched_on": datetime.now(timezone.utc).date().isoformat(),
        }
    )
    print(f"vendored {MODULE} {entry['version']} (was {current or 'none'})")
    return entry["version"]


def select(index: str, woob: str) -> dict[str, str]:
    """Read the module's entry from a signed index and check it fits."""
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(index)
    defaults = parser.defaults()
    if defaults.get("signed") != "1":
        raise UpdateError("the repository no longer declares itself signed")
    if int(defaults.get("key_update", "0")) > KEY_UPDATE:
        raise UpdateError(
            "woob rotated its keyring: review the new trusted.gpg, then bump "
            "KEYRING_SHA256 and KEY_UPDATE in this script"
        )
    if not parser.has_section(MODULE):
        raise UpdateError(f"the repository no longer lists {MODULE}")
    section = parser[MODULE]
    if section.get("dependencies", "").strip():
        raise UpdateError(
            f"{MODULE} now depends on other modules ({section['dependencies']}): "
            "vendor them too"
        )
    spec = section.get("woob_spec", "")
    if Version(woob) not in SpecifierSet(spec):
        raise UpdateError(f"{MODULE} requires woob {spec}, the lock has {woob}")
    return {"version": section["version"], "woob_spec": spec}


def check_members(archive: tarfile.TarFile) -> None:
    """Refuse anything but plain files and folders under the module folder."""
    for member in archive.getmembers():
        parts = Path(member.name).parts
        if (
            not parts
            or parts[0] != MODULE
            or member.name.startswith("/")
            or ".." in parts
        ):
            raise UpdateError(f"unexpected path in the archive: {member.name}")
        if not (member.isfile() or member.isdir()):
            raise UpdateError(f"unexpected entry type in the archive: {member.name}")


def install(archive: bytes) -> None:
    """Swap the vendored module for the content of a verified archive."""
    with tempfile.TemporaryDirectory(dir=VENDOR) as staging:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            check_members(tar)
            tar.extractall(staging, filter="data")
        fresh = Path(staging) / MODULE
        if not (fresh / "__init__.py").is_file():
            raise UpdateError("the archive does not hold a module")
        for cache in fresh.rglob("__pycache__"):
            shutil.rmtree(cache)
        for name in DROPPED:
            (fresh / name).unlink(missing_ok=True)

        target = VENDOR / MODULE
        previous = Path(staging) / "previous"
        if target.exists():
            target.rename(previous)
        try:
            fresh.rename(target)
        except OSError:
            if previous.exists():
                previous.rename(target)
            raise


def woob_version() -> str:
    """The woob core version uv.lock pins, which the module must accept."""
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    for package in lock.get("package", []):
        if package.get("name") == "woob":
            return package["version"]
    raise UpdateError("woob is not in uv.lock")


def read_lock() -> dict[str, str]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(LOCK, encoding="utf-8")
    return dict(parser[MODULE]) if parser.has_section(MODULE) else {}


def write_lock(values: dict[str, str]) -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser[MODULE] = values
    with LOCK.open("w", encoding="utf-8") as handle:
        handle.write(
            "# Written by scripts/woob_update.py: the module build vendored next\n"
            "# to this file, as published and signed by woob.\n"
        )
        parser.write(handle)


def _verified(gpgv: str, name: str) -> bytes:
    """Download a file and its detached signature; return it once checked."""
    data = _download(name)
    signature = _download(f"{name}.sig")
    with tempfile.TemporaryDirectory() as home:
        data_path = Path(home) / name
        sig_path = Path(home) / f"{name}.sig"
        data_path.write_bytes(data)
        sig_path.write_bytes(signature)
        result = subprocess.run(
            [
                gpgv,
                "--homedir",
                home,
                "--keyring",
                str(KEYRING),
                str(sig_path),
                str(data_path),
            ],
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        raise UpdateError(f"bad signature for {name}:\n{result.stderr.strip()}")
    return data


def _download(name: str) -> bytes:
    request = urllib.request.Request(
        REPOSITORY + name, headers={"User-Agent": "allot-woob-update"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except OSError as error:
        raise UpdateError(f"cannot download {name}: {error}") from error


def _github_output(key: str, value: str) -> None:
    path = os.getenv("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{key}={value}\n")


if __name__ == "__main__":
    sys.exit(main())
