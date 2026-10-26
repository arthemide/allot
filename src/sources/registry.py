"""Known sources, and the shape of the data they hand Allot."""

from __future__ import annotations

from pydantic import BaseModel


class Source(BaseModel):
    id: str
    name: str
    # "woob": the bank is read on the server. "bookmarklet": in the browser.
    kind: str


SOURCES: dict[str, Source] = {
    "bourso": Source(id="bourso", name="BoursoBank", kind="woob"),
    "afer": Source(id="afer", name="Afer", kind="bookmarklet"),
}


def get(source: str) -> Source:
    if source not in SOURCES:
        raise KeyError(source)
    return SOURCES[source]
