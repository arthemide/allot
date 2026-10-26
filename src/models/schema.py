"""The models the app passes around.

Everything above `Trade` is the HTTP surface; everything below it is internal
and never leaves the process.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Position(BaseModel):
    symbol: str
    label: str
    envelope: str
    currency: str
    weight: float
    by_amount: bool
    base_quantity: float
    base_prum: float | None
    quantity: float
    prum: float
    invested: float
    price: float | None
    market_value: float | None
    gain: float | None
    gain_percent: float | None


class PricePoint(BaseModel):
    date: str
    price: float


class PrumPoint(BaseModel):
    date: str
    prum: float


class Transaction(BaseModel):
    id: int
    date: str
    side: Literal["buy", "sell"]
    quantity: float
    unit_price: float
    fees: float


class Chart(BaseModel):
    symbol: str
    currency: str = "EUR"
    prices: list[PricePoint] = []
    transactions: list[Transaction] = []
    prum: list[PrumPoint] = []


class TransactionCreate(BaseModel):
    symbol: str
    date: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    unit_price: float = Field(gt=0)
    fees: float = Field(default=0.0, ge=0)


class SearchHit(BaseModel):
    """One ticker search result, price included so a dead symbol is visible."""

    symbol: str
    label: str
    exchange: str
    type: str
    currency: str | None
    price: float | None


class AssetCreate(BaseModel):
    symbol: str
    label: str
    envelope: str
    currency: str
    weight: float = Field(default=1.0, ge=0)
    # None: seeded from the ticker (calc.bought_by_amount).
    by_amount: bool | None = None


class AssetUpdate(BaseModel):
    label: str
    envelope: str
    weight: float = Field(ge=0)
    # None: left as it is, so a client that does not know the flag keeps it.
    by_amount: bool | None = None


class TickerChange(BaseModel):
    """The Yahoo ticker an asset is quoted under from now on."""

    symbol: str = Field(min_length=1, max_length=32)


class OpeningPosition(BaseModel):
    """A holding that predates tracking, as it reads on a statement."""

    quantity: float = Field(ge=0)
    invested: float | None = Field(default=None, ge=0)


class ImportCsv(BaseModel):
    """A broker's portfolio export, as text: the front reads the file itself."""

    csv: str = Field(min_length=1, max_length=256 * 1024)


class ImportedLine(BaseModel):
    symbol: str
    # None for a line mapped to its ticker by hand (a source without ISINs).
    isin: str | None
    label: str
    quantity: float
    prum: float


class UnresolvedLine(BaseModel):
    """A row no ticker in its currency answers to; nothing was written for it.

    `isin` is None for a line the broker does not tag.
    """

    isin: str | None
    name: str


class ElsewhereLine(BaseModel):
    """An imported asset that already lives in a different envelope.

    Its opening position was updated, but the import left it where it was: the
    envelope and weight are the user's, not the CSV's to reorganise.
    """

    symbol: str
    isin: str | None
    label: str
    envelope: str


class ConflictLine(BaseModel):
    """A bank line the recorded trades cannot be reconciled with; left as it was.

    The trades are the history the cash is derived from, so a sync never
    deletes them: when they already hold more than the bank reports (an
    unrecorded sell, say), the user fixes the trades and syncs again.
    """

    symbol: str
    label: str
    # What the bank reports, and what the trades recorded here already make.
    bank_quantity: float
    tracked_quantity: float


class AvailableLine(BaseModel):
    """A line held as an amount, without units: a cash balance, a euro fund.

    It cannot hold a position, so nothing is written for it. The report shows
    it so that the money is not silently missing from the picture.
    """

    account: str
    envelope: str
    label: str
    value: float
    currency: str


class ImportReport(BaseModel):
    imported: list[ImportedLine]
    unresolved: list[UnresolvedLine]
    # Imported, but already filed under another envelope - a heads-up, not an error.
    elsewhere: list[ElsewhereLine]
    # Only a bank sync reconciles against the trades; a CSV import never has any.
    conflicts: list[ConflictLine] = []
    # Only a source sync reads amounts without units; a CSV import never has any.
    available: list[AvailableLine] = []
    total: int


class ConnectorLogin(BaseModel):
    """Bank credentials, used once and never stored."""

    login: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ConnectorAnswer(BaseModel):
    """The second factor: an SMS/email code, or an acknowledged app tap."""

    answer: str = ""


class AccountChoice(BaseModel):
    """An account of a source no envelope was chosen for yet."""

    account: str
    # Security lines it holds, to tell accounts apart.
    lines: int
    # An existing envelope of the same name, offered as the default.
    envelope: str | None = None


class ConnectorAccounts(BaseModel):
    """The envelope each new account syncs into; None leaves it out of Allot."""

    envelopes: dict[str, str | None]


class ConnectorStatus(BaseModel):
    """Where a login stands, and the import once it is through.

    `status` is "otp" or "app_validation" while the bank waits for a second
    factor, "accounts" while new accounts wait for an envelope (`accounts`),
    then "done". `report` is filled only on "done".
    """

    session_id: str
    status: Literal["otp", "app_validation", "accounts", "done"]
    prompt: str = ""
    accounts: list[AccountChoice] = []
    report: ImportReport | None = None


class Envelope(BaseModel):
    name: str
    monthly_amount: float = Field(ge=0)
    # Only set when the envelope tracks its cash; see EnvelopeStart.
    started_on: str | None = None
    opening_cash: float | None = None
    available: float | None = None


class EnvelopeStart(BaseModel):
    """Where a strategy starts, or where it is recalibrated.

    `opening_cash` is what is actually sitting in the envelope on that date -
    0 for a strategy that starts from nothing.
    """

    started_on: str
    opening_cash: float = Field(default=0.0, ge=0)


class SummaryAsset(BaseModel):
    symbol: str
    label: str
    currency: str
    invested: float
    market_value: float
    gain: float
    gain_percent: float | None


class SummaryEnvelope(BaseModel):
    envelope: str
    invested: float
    market_value: float
    gain: float
    gain_percent: float | None
    assets: list[SummaryAsset]


class Summary(BaseModel):
    """Everything totalled in EUR; the only place currencies are mixed."""

    currency: str
    eur_usd_rate: float | None
    invested: float
    market_value: float
    gain: float
    gain_percent: float | None
    envelopes: list[SummaryEnvelope]


class FeedUrl(BaseModel):
    """Where a calendar subscribes, and whether that address carries a token."""

    url: str
    token: bool


class Login(BaseModel):
    """The one credential this app knows about."""

    password: str


class Session(BaseModel):
    """What the front needs at boot to decide between login screen and app."""

    required: bool
    authenticated: bool


class PositionRow(BaseModel):
    """One line of a bank account, as a connector read it."""

    model_config = ConfigDict(frozen=True)

    source: str = "bourso"
    account: str
    # "security" for a holding, "cash" for the account's cash balance.
    support_type: str
    isin: str | None = None
    label: str
    quantity: float | None = None
    value: float
    currency: str = "EUR"
    # As the bank states them, where it does: PRU, last price, unrealised gain.
    unit_cost: float | None = None
    unit_price: float | None = None
    gain: float | None = None
    # Whether a new asset made from this line is bought for an amount.
    by_amount: bool = False


class SnapshotLine(BaseModel):
    """One holding of a broker snapshot, whatever the source (CSV or sync).

    `isin` and `prum` are optional because a connector reads lines the broker
    does not tag or price: those are reported unresolved, never guessed.
    `currency`, when known, is what the Yahoo listing must be quoted in.
    """

    model_config = ConfigDict(frozen=True)

    isin: str | None
    name: str
    quantity: float
    prum: float | None
    currency: str | None = None
    symbol: str | None = None
    by_amount: bool = False


class SourceLine(BaseModel):
    """One holding read from a source, before resolution."""

    model_config = ConfigDict(frozen=True)

    label: str
    isin: str | None = None
    quantity: float | None = None
    unit_cost: float | None = None
    invested: float | None = None
    unit_value: float | None = None
    valuation: float | None = None
    currency: str | None = None
    value_date: str | None = None
    by_amount: bool = True


class SourceAccount(BaseModel):
    label: str
    product: str = ""
    balance: float | None = None
    available: bool = True
    lines: list[SourceLine] = Field(default_factory=list)


class SourceSnapshot(BaseModel):
    source: str
    version: int = 1
    read_on: str = ""
    accounts: list[SourceAccount] = Field(default_factory=list)


class PendingLine(BaseModel):
    """A line without an ISIN no ticker was chosen for yet; `symbol` is a guess."""

    # The first account it shows up in: leaving that account out hides it.
    account: str
    label: str
    symbol: str | None = None


class PendingChoices(BaseModel):
    accounts: list[AccountChoice] = Field(default_factory=list)
    lines: list[PendingLine] = Field(default_factory=list)


class AccountPlacement(BaseModel):
    account: str
    envelope: str | None = None


class LineMapping(BaseModel):
    label: str
    symbol: str | None = None


class SourceImport(BaseModel):
    snapshot: SourceSnapshot
    placements: list[AccountPlacement] = Field(default_factory=list)
    mappings: list[LineMapping] = Field(default_factory=list)


class Trade(BaseModel):
    """A single buy or sell."""

    model_config = ConfigDict(frozen=True)

    side: str  # "buy" or "sell"
    quantity: float
    unit_price: float
    fees: float = 0.0


class PositionResult(BaseModel):
    """A holding, recomputed from trades. Never stored."""

    model_config = ConfigDict(frozen=True)

    quantity: float
    prum: float
    invested: float


class Candidate(BaseModel):
    """One asset competing for the envelope's cash, everything in EUR."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    price: float
    # Weight times the PRUM multiplier: the share this asset should hold.
    weight: float
    # What is already held, so the split follows the drift.
    held_value: float = 0.0


class Lot(BaseModel):
    """Whole units to buy of one asset."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    units: int
    amount: float


class CashBalance(BaseModel):
    """What is sitting in cash in an envelope, derived rather than stored.

    The terms travel with the figure so it can be argued with against a
    statement.
    """

    model_config = ConfigDict(frozen=True)

    started_on: str
    opening_cash: float
    months: int
    paid_in: float
    spent: float
    returned: float
    available: float


class EnvelopeAsset(BaseModel):
    """One asset of an envelope, as the split needs it: everything in EUR."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    weight: float
    by_amount: bool
    currency: str
    price: float | None
    # 0.0 when the quote is missing, so the arithmetic never guards for None.
    price_eur: float
    prum: float | None
    multiplier: float
    held_eur: float


class PlanAsset(EnvelopeAsset):
    """One asset line in the monthly plan: an amount, or a number of shares."""

    amount: float
    units: int | None = None


class WaitingAsset(EnvelopeAsset):
    """An asset the envelope is saving up for but cannot afford yet."""

    missing: float
    months_left: int | None


class PlanEntry(BaseModel):
    """One envelope's plan for the month."""

    model_config = ConfigDict(frozen=True)

    envelope: str
    amount: float
    cash: CashBalance | None
    market_value: float
    assets: list[PlanAsset]
    waiting: list[WaitingAsset]
    budget: float
    carry: float


class ProjectionEntry(BaseModel):
    """One envelope's projected plan for a future month."""

    model_config = ConfigDict(frozen=True)

    envelope: str
    tracked: bool
    budget: float
    assets: list[PlanAsset]
    carry: float


class ProjectionStep(BaseModel):
    """One month of projection: every envelope's planned state."""

    model_config = ConfigDict(frozen=True)

    month: date
    envelopes: list[ProjectionEntry]
