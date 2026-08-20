"""Read and validate config.toml.

config.toml is the source of truth for allocation: which envelopes exist, how
the monthly savings split across them, and how each envelope splits across its
assets. Holdings live in the database, never here.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.toml"
TOLERANCE = 1e-9


@dataclass(frozen=True)
class AssetConfig:
    ticker: str
    label: str
    envelope: str
    weight: float
    currency: str
    price_source: str


@dataclass(frozen=True)
class Config:
    monthly_savings: float
    envelope_shares: dict[str, float]
    assets: list[AssetConfig]

    def assets_of(self, envelope: str) -> list[AssetConfig]:
        return [a for a in self.assets if a.envelope == envelope]

    def envelope_amount(self, envelope: str) -> float:
        return self.monthly_savings * self.envelope_shares.get(envelope, 0.0)


class ConfigError(Exception):
    """config.toml is present but does not add up."""


def load(path: Path = CONFIG_PATH) -> Config:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    shares = {name: float(e["share"]) for name, e in raw["envelopes"].items()}
    assets = [
        AssetConfig(
            ticker=entry["ticker"],
            label=entry.get("label", entry["ticker"]),
            envelope=entry["envelope"],
            weight=float(entry["weight"]),
            currency=entry["currency"],
            price_source=entry.get("price_source", "yfinance"),
        )
        for entry in raw.get("assets", [])
    ]

    _validate(shares, assets)
    return Config(
        monthly_savings=float(raw["monthly_savings"]),
        envelope_shares=shares,
        assets=assets,
    )


def _validate(shares: dict[str, float], assets: list[AssetConfig]) -> None:
    total = sum(shares.values())
    if abs(total - 1.0) > TOLERANCE:
        raise ConfigError(f"envelope shares sum to {total}, expected 1")

    for asset in assets:
        if asset.envelope not in shares:
            raise ConfigError(
                f"asset {asset.ticker} refers to unknown envelope {asset.envelope}"
            )

    by_envelope: dict[str, float] = {}
    for asset in assets:
        by_envelope[asset.envelope] = by_envelope.get(asset.envelope, 0.0) + asset.weight
    for envelope, weight in by_envelope.items():
        if abs(weight - 1.0) > TOLERANCE:
            raise ConfigError(
                f"weights of envelope {envelope} sum to {weight}, expected 1"
            )
