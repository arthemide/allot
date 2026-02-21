from typing import List, Optional

from fastapi import APIRouter

from src.models.pydantic.schema import TransactionSchema
from src.services.transaction import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=List[TransactionSchema])
def get_transactions(
    fund_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    limit: int = 100,
):
    """Get all transactions with optional filters"""
    return TransactionService.get_all(fund_id=fund_id, asset_id=asset_id, limit=limit)
