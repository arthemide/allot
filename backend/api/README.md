# Stock Alerting API

REST API for stock search and portfolio (fund) management.

## Technology Stack

- **FastAPI** — web framework
- **SQLAlchemy** — ORM for database access
- **PostgreSQL** — relational database

## Directory Structure

```
api/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── routes/
│   │   ├── stocks.py        # Stock search endpoints
│   │   └── funds.py         # Fund CRUD endpoints
│   ├── services/
│   │   ├── fund.py          # Fund business logic
│   │   ├── stock.py         # Stock business logic
│   │   ├── utils.py         # Shared utilities
│   │   └── yfinance_utils.py# yfinance wrapper
│   ├── databases/
│   │   ├── fund.py          # Fund database operations
│   │   └── stock.py         # Stock database operations
│   └── models/
│       └── pydantic/
│           └── schema.py    # Pydantic schemas
├── tests/                   # Test suite
├── pyproject.toml
└── Dockerfile
```

## Setup

```bash
# From the backend/ workspace root
```
make api-install

# Set database connection
export DATABASE_URL=postgresql://user:password@localhost:5432/stock_alerting
```

## Running the API

```bash
make api-dev
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Endpoints

### General

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |

### Stocks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/stocks/search?q=<query>&max_results=<n>` | Search stocks by name or ticker |

### Funds

| Method | Path | Description |
|--------|------|-------------|
| GET | `/funds` | List all funds |
| GET | `/funds/{fund_id}` | Get a fund by ID |
| POST | `/funds` | Create a new fund |
| PUT | `/funds/{fund_id}` | Update a fund |
| DELETE | `/funds/{fund_id}` | Delete a fund |
| POST | `/funds/{fund_id}/stocks` | Add a stock to a fund |
| PUT | `/funds/{fund_id}/stocks/{stock_id}` | Update a stock in a fund |
| DELETE | `/funds/{fund_id}/stocks/{stock_id}` | Remove a stock from a fund |

## Testing

```bash
make api-test
```

## Docker

```bash
# Build from the backend/ directory
docker build -f api/Dockerfile -t stock-alerting-api .

# Run
docker run -p 8000:8000 -e DATABASE_URL=... stock-alerting-api
```
