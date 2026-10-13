-- Bank snapshots, in their own database (data/connectors/connectors.db).
-- Replayed on every connection, hence IF NOT EXISTS everywhere.
--
-- Every sync inserts a new snapshot; nothing is ever updated or replaced, so
-- the history is the table itself. Totals are not stored: they are sums.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS snapshots (
    id       INTEGER PRIMARY KEY,
    source   TEXT NOT NULL,  -- the bank key: "bourso", "afer"
    taken_at TEXT NOT NULL   -- ISO 8601, UTC
);

CREATE INDEX IF NOT EXISTS idx_snapshots_source ON snapshots (source, taken_at);

CREATE TABLE IF NOT EXISTS positions (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    -- A product name ("PEA", "PEA-PME"), never an account number.
    account      TEXT NOT NULL,
    -- "security", "managed" (profiled management), "cash", and for life
    -- insurance "euro_fund" or "unit_linked".
    support_type TEXT NOT NULL,
    -- Stable identity of the line, used to remember a manual ticker choice:
    -- the ISIN when the broker gives one, else "account|label".
    broker_key   TEXT NOT NULL,
    isin         TEXT,
    label        TEXT NOT NULL,
    quantity     REAL,
    value        REAL NOT NULL,
    currency     TEXT NOT NULL DEFAULT 'EUR',
    -- As the bank states them, where it does: PRU, last price, unrealised gain.
    unit_cost    REAL,
    unit_price   REAL,
    gain         REAL
);

CREATE INDEX IF NOT EXISTS idx_positions_snapshot ON positions (snapshot_id);
