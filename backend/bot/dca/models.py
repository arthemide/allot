from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel


class Kline(BaseModel):
    """Kline/candlestick data model"""

    open_time: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_time: int


class AssetBalance(BaseModel):
    """Asset balance data model"""

    free: Decimal
    locked: Decimal
    total: Decimal


class FlexiblePosition(BaseModel):
    """Simple Earn flexible position data model"""

    asset: str
    total_amount: Decimal
    tier_annual_percentage_rate: Optional[Dict[str, str]] = None
    latest_annual_percentage_rate: Optional[str] = None
    yesterday_real_time_rewards: Optional[Decimal] = None
    accumulated_rewards: Optional[Decimal] = None
    product_id: Optional[str] = None

    class Config:
        populate_by_name = True


class OrderFill(BaseModel):
    """Order fill data model"""

    price: Decimal
    qty: Decimal
    commission: Decimal
    commission_asset: str


class MarketOrder(BaseModel):
    """Market order response data model"""

    symbol: str
    order_id: int
    client_order_id: str
    transact_time: int
    price: Decimal
    orig_qty: Decimal
    executed_qty: Decimal
    cummulative_quote_qty: Decimal
    status: str
    type: str
    side: str
    fills: List[OrderFill] = []


class RedeemResponse(BaseModel):
    """Redeem operation response data model"""

    redeem_id: Optional[int] = None
    success: bool = True
