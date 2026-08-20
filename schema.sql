-- Wealth tracking schema. Single file, versioned by PRAGMA user_version.
-- No migration framework: bump the version and add the DDL below when the
-- schema changes.
PRAGMA user_version = 1;

PRAGMA foreign_keys = ON;

-- One row per tracked asset. Envelope, weight and currency mirror config.toml;
-- config.toml stays the source of truth for allocation, this table is the
-- source of truth for holdings.
CREATE TABLE IF NOT EXISTS asset (
    symbol       TEXT PRIMARY KEY,
    label        TEXT NOT NULL,
    envelope     TEXT NOT NULL,
    currency     TEXT NOT NULL,
    price_source TEXT NOT NULL DEFAULT 'yfinance'
                 CHECK (price_source IN ('yfinance', 'manual')),

    -- Opening position carried over from the legacy database: holdings that
    -- predate transaction tracking and have no transaction to back them.
    -- base_prum is the weighted average price of that opening position.
    base_quantity REAL NOT NULL DEFAULT 0 CHECK (base_quantity >= 0),
    base_prum     REAL CHECK (base_prum IS NULL OR base_prum > 0),

    -- price_source = 'manual' only: value entered by hand, in `currency`.
    manual_value REAL CHECK (manual_value IS NULL OR manual_value >= 0),

    CHECK (base_quantity = 0 OR base_prum IS NOT NULL),
    CHECK (price_source <> 'manual' OR base_quantity = 0)
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
