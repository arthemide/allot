"""Known sources, and how far each one speaks for its envelopes."""

from __future__ import annotations

from pydantic import BaseModel


class Source(BaseModel):
    id: str
    name: str
    # True when an account is the whole envelope, as a bank account is: an
    # asset of the envelope the source no longer reports was sold, whoever
    # added it. False when the source only speaks for the assets its lines
    # were mapped to, and leaves the rest of the envelope alone.
    owns_envelope: bool


SOURCES: dict[str, Source] = {
    "bourso": Source(id="bourso", name="BoursoBank", owns_envelope=True),
    "afer": Source(id="afer", name="Afer", owns_envelope=False),
}


def get(source: str) -> Source:
    if source not in SOURCES:
        raise KeyError(source)
    return SOURCES[source]
