"""The banks a connector can open, and the hosts each one may reach."""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict


class Bank(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    start_url: str
    # Registrable domains; their subdomains are allowed too.
    allowed_domains: tuple[str, ...]
    # What to open by hand before pressing Enter.
    target: str

    def allows(self, url: str) -> bool:
        """Whether a request to `url` may leave the machine.

        Browser-internal schemes (data:, blob:, about:) never reach the network.
        """
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https", "ws", "wss"):
            return True
        host = (parts.hostname or "").lower()
        return any(
            host == domain or host.endswith("." + domain)
            for domain in self.allowed_domains
        )


BANKS = {
    bank.key: bank
    for bank in (
        Bank(
            key="bourso",
            name="BoursoBank",
            start_url="https://clients.boursobank.com/",
            allowed_domains=("boursobank.com", "boursorama.com"),
            target="the PEA portfolio, with every line listed",
        ),
        Bank(
            key="afer",
            name="Afer",
            start_url="https://adherent.gie-afer.fr/",
            allowed_domains=("gie-afer.fr",),
            target="the membership detail, with the split across funds",
        ),
    )
}
