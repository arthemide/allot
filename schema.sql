-- Allot schema, in one file. Replayed on every boot, which is why every
-- statement is CREATE ... IF NOT EXISTS.
--
-- There is no migration framework and no schema versioning: this creates a
-- missing table, and nothing else. A column added to an existing table also
-- needs its ALTER in src/databases/sqlite.py init(), or existing databases
-- never get it. Changing an existing column means writing the ALTER by hand
-- against your own database, or deleting data/allot.db and letting it be
-- rebuilt.

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

    -- 1 when the asset is bought for an amount (fund, crypto), 0 when it is
    -- bought by the whole share. The user's choice, seeded on creation.
    by_amount INTEGER NOT NULL DEFAULT 0 CHECK (by_amount IN (0, 1)),

    -- Opening position carried over from the legacy database: holdings that
    -- predate transaction tracking and have no transaction to back them.
    -- base_prum is the weighted average price of that opening position.
    base_quantity REAL NOT NULL DEFAULT 0 CHECK (base_quantity >= 0),
    base_prum     REAL CHECK (base_prum IS NULL OR base_prum > 0),

    CHECK (base_quantity = 0 OR base_prum IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_asset_envelope ON asset (envelope);

-- Where a strategy starts, and where it is recalibrated. The cash in an
-- envelope is never stored: it is recomputed from this row, the monthly amount
-- and the transactions. An envelope without a row here knows nothing about
-- cash and just splits its monthly amount.
CREATE TABLE IF NOT EXISTS envelope_start (
    envelope     TEXT PRIMARY KEY
                 REFERENCES envelope(name) ON UPDATE CASCADE ON DELETE CASCADE,

    -- Start of the strategy, or the date of the last recalibration.
    started_on   TEXT NOT NULL,

    -- Cash already there on that date; 0 for a strategy starting from nothing.
    opening_cash REAL NOT NULL DEFAULT 0 CHECK (opening_cash >= 0)
);

-- Which envelope a bank account syncs into, picked by the user the first time
-- the account shows up. A NULL envelope leaves the account out of Allot. An
-- envelope that goes away takes its rows along, so the account is asked
-- about again rather than synced somewhere unexpected.
CREATE TABLE IF NOT EXISTS bank_account (
    account  TEXT PRIMARY KEY,  -- the account's label at the bank: "PEA"
    envelope TEXT REFERENCES envelope(name) ON UPDATE CASCADE ON DELETE CASCADE
);

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

CREATE TABLE IF NOT EXISTS source_account (
    source   TEXT NOT NULL,
    account  TEXT NOT NULL,
    envelope TEXT REFERENCES envelope(name) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (source, account)
);

-- Which ticker a line of a source maps to, picked by the user the first time
-- the line shows up. A NULL symbol leaves the line out. Not a foreign key: the
-- ticker is chosen before the import creates its asset. Deleting the asset
-- deletes the row (sqlite.delete_asset), so the line is asked about again.
CREATE TABLE IF NOT EXISTS source_line (
    source TEXT NOT NULL,
    label  TEXT NOT NULL,
    symbol TEXT,
    PRIMARY KEY (source, label)
);
