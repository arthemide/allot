"""Transaction endpoints."""

from fastapi import APIRouter, HTTPException, status

from src import calc
from src.databases import sqlite as db
from src.models.schema import Transaction, TransactionCreate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[Transaction])
def list_transactions(symbol: str | None = None):
    rows = db.transactions_of(symbol) if symbol else db.all_transactions()
    return rows


@router.post("", response_model=Transaction, status_code=status.HTTP_201_CREATED)
def add_transaction(payload: TransactionCreate):
    asset = db.get_asset(payload.symbol)
    if asset is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No asset named {payload.symbol}"
        )
    transaction_id = db.add_transaction(
        payload.symbol,
        payload.date,
        payload.side,
        payload.quantity,
        payload.unit_price,
        payload.fees,
    )
    if not asset["by_amount"] and calc.is_fraction(payload.quantity):
        # A fraction traded is proof the broker sells this asset by the amount,
        # as the rule the flag replaced said. The user can still switch it back.
        db.set_by_amount(payload.symbol, True)
    return {"id": transaction_id, **payload.model_dump(exclude={"symbol"})}


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int):
    db.delete_transaction(transaction_id)
