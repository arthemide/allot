-- Allot schema, in one file. Replayed on every boot, which is why every
-- statement is CREATE ... IF NOT EXISTS.
--
-- There is no migration framework and no schema versioning: this creates a
-- missing table, and nothing else. Changing an existing column means writing
-- the ALTER by hand against your own database, or deleting data/allot.db and
-- letting it be rebuilt.

PRAGMA foreign_keys = ON;

-- Litestream replicates the write-ahead log, so WAL is not optional when
-- off-site replication is on. It also lets reads and writes overlap, which the
-- per-request connections in src/databases/sqlite.py benefit from either way.
-- Unlike the rest of this file, journal_mode is persistent: it is stored in the
-- database header and survives every later connection.
PRAGMA journal_mode = WAL;

-- An envelope groups assets and carries the amount invested into it every
-- month, in EUR. There is no global savings figure: each envelope stands on
-- its own, and one never draws from another.
CREATE TABLE IF NOT EXISTS envelope (
    name           TEXT PRIMARY KEY,
    monthly_amount REAL NOT NULL DEFAULT 0 CHECK (monthly_amount >= 0)
);

-- One row per tracked asset. Assets are added from the ticker search, not from
-- a configuration file.
CREATE TABLE IF NOT EXISTS asset (
    symbol   TEXT PRIMARY KEY,
    label    TEXT NOT NULL,
    envelope TEXT NOT NULL REFERENCES envelope(name) ON UPDATE CASCADE,
    currency TEXT NOT NULL,

    -- Relative weight inside the envelope. Never constrained to sum to 1:
    -- the monthly split normalises by the total of the envelope's weights.
    weight REAL NOT NULL DEFAULT 1 CHECK (weight >= 0),

    -- Opening position carried over from the legacy database: holdings that
    -- predate transaction tracking and have no transaction to back them.
    -- base_prum is the weighted average price of that opening position.
    base_quantity REAL NOT NULL DEFAULT 0 CHECK (base_quantity >= 0),
    base_prum     REAL CHECK (base_prum IS NULL OR base_prum > 0),

    CHECK (base_quantity = 0 OR base_prum IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_asset_envelope ON asset (envelope);

-- Every buy and sell. Positions are never stored: quantity and PRUM are
-- recomputed from this table plus the asset's opening position.
CREATE TABLE IF NOT EXISTS "transaction" (
    id         INTEGER PRIMARY KEY,
    symbol     TEXT NOT NULL REFERENCES asset(symbol) ON DELETE CASCADE,
    date       TEXT NOT NULL,  -- ISO 8601, UTC
    side       TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity   REAL NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price > 0),
    fees       REAL NOT NULL DEFAULT 0 CHECK (fees >= 0),

    -- Broker/exchange reference, used to keep the migration idempotent and to
    -- avoid inserting the same order twice.
    external_id TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_transaction_symbol_date
    ON "transaction" (symbol, date);

-- Historical prices, so charts do not hit the network on every load.
CREATE TABLE IF NOT EXISTS price_cache (
    symbol TEXT NOT NULL,
    date   TEXT NOT NULL,  -- ISO 8601 date
    price  REAL NOT NULL,
    PRIMARY KEY (symbol, date)
) WITHOUT ROWID;
