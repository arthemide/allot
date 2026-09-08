"""Asset, chart and ticker search endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.databases import sqlite as db
from src.models.schema import (
    AssetCreate,
    AssetUpdate,
    Chart,
    ImportCsv,
    ImportReport,
    OpeningPosition,
    Position,
    SearchHit,
    Summary,
)
from src.services import broker_csv, portfolio, prices, ratelimit

router = APIRouter(prefix="/assets", tags=["assets"])


def rate_limited(request: Request) -> None:
    """Refuse a caller hammering an endpoint that reaches out to Yahoo."""
    key = request.client.host if request.client else "unknown"
    if not ratelimit.allow(key):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many requests. This endpoint reaches out to Yahoo on every "
            "call, so it is capped.",
            headers={"Retry-After": str(ratelimit.retry_after(key))},
        )


@router.get("", response_model=list[Position])
def list_assets():
    """Every tracked asset with its recomputed position."""
    return portfolio.all_positions()


@router.post("", response_model=Position, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate):
    """Add an asset, normally picked from the ticker search."""
    existing = db.get_asset(payload.symbol)
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{payload.symbol} is already tracked, in envelope "
            f"{existing['envelope']}. Move it from there instead of adding "
            f"it again.",
        )
    if db.get_envelope(payload.envelope) is None:
        db.upsert_envelope(payload.envelope, 0.0)
    db.add_asset(
        payload.symbol,
        payload.label,
        payload.envelope,
        payload.currency,
        payload.weight,
    )
    return portfolio.position_of(db.get_asset(payload.symbol))


@router.get(
    "/search",
    response_model=list[SearchHit],
    dependencies=[Depends(rate_limited)],
)
def search_tickers(q: str, limit: int = 10):
    """Find a ticker by name, so the exchange suffix does not have to be guessed."""
    return prices.search(q, limit)


@router.post(
    "/import",
    response_model=ImportReport,
    dependencies=[Depends(rate_limited)],
)
def import_csv(payload: ImportCsv, envelope: str):
    """Seed opening positions from a broker's portfolio export.

    A snapshot, not a history: each row sets the asset's opening position to
    what the broker reports, PRUM included, so importing again replaces rather
    than adds. Manual transactions still stack on top. An asset already tracked
    keeps its envelope and weight - the import does not reorganise anything.
    """
    try:
        parsed = broker_csv.parse(payload.csv)
    except broker_csv.CsvError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))

    if db.get_envelope(envelope) is None:
        db.upsert_envelope(envelope, 0.0)

    imported, unresolved = [], []
    for row in parsed.rows:
        hits = prices.search(row.isin, limit=1)
        if not hits:
            unresolved.append({"isin": row.isin, "name": row.name})
            continue
        hit = hits[0]
        symbol = hit["symbol"]
        if db.get_asset(symbol) is None:
            db.add_asset(symbol, row.name, envelope, hit.get("currency") or "EUR")
        db.set_opening_position(symbol, row.quantity, row.prum * row.quantity)
        imported.append(
            {
                "symbol": symbol,
                "isin": row.isin,
                "label": row.name,
                "quantity": row.quantity,
                "prum": row.prum,
            }
        )
    return {"imported": imported, "unresolved": unresolved, "total": len(parsed.rows)}


@router.get("/summary", response_model=Summary)
def get_summary():
    """Totals across every asset, converted to EUR."""
    return portfolio.summary()


@router.get("/{symbol}", response_model=Position)
def get_asset(symbol: str):
    asset = db.get_asset(symbol)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    return portfolio.position_of(asset)


@router.put("/{symbol}", response_model=Position)
def update_asset(symbol: str, payload: AssetUpdate):
    """Change the label, the envelope or the weight inside the envelope."""
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    if db.get_envelope(payload.envelope) is None:
        db.upsert_envelope(payload.envelope, 0.0)
    db.update_asset(symbol, payload.label, payload.envelope, payload.weight)
    db.prune_empty_envelopes()
    return portfolio.position_of(db.get_asset(symbol))


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(symbol: str):
    """Deletes the asset and its transactions."""
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    db.delete_asset(symbol)
    db.prune_empty_envelopes()


@router.put("/{symbol}/opening", response_model=Position)
def set_opening_position(symbol: str, payload: OpeningPosition):
    """Set the holding that predates tracking, for a line with no history.

    A statement gives units held and total paid; the PRUM follows from those.
    """
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    if payload.quantity > 0 and not payload.invested:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A quantity needs the amount invested, otherwise there is no PRUM "
            "to compute. Leave the quantity at 0 to clear the opening position.",
        )
    db.set_opening_position(symbol, payload.quantity, payload.invested)
    return portfolio.position_of(db.get_asset(symbol))


@router.get(
    "/{symbol}/chart",
    response_model=Chart,
    dependencies=[Depends(rate_limited)],
)
def get_chart(symbol: str, window: str = portfolio.DEFAULT_RANGE):
    """Price history, transaction markers and the step PRUM curve.

    `window` is "tx" (a quarter before the first transaction) or one of
    "1y", "3y", "5y", "max".
    """
    if db.get_asset(symbol) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No asset named {symbol}")
    return portfolio.chart_data(symbol, window)
