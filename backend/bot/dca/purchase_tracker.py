"""
Purchase tracker for DCA bot - PostgreSQL version.
Maintains purchase history in PostgreSQL to calculate average price (PRUM).
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from loguru import logger

# Import from shared package
from shared.db.repositories.transaction import TransactionRepository


class PurchaseTracker:
    """
    Tracks DCA purchases and calculates PRUM (average purchase price).

    Uses PostgreSQL to store:
    - Base PRUM and quantity from historical purchases
    - All new purchases made by the bot
    """

    def __init__(
        self,
        symbol: str,
        asset_name: str,
        fund_id: Optional[int] = None,
        base_prum: Optional[float] = None,
        base_quantity: float = 0.0,
        currency: str = "USD",
    ):
        """
        Initialize purchase tracker.

        Args:
            symbol: Trading symbol (e.g., "ETHUSDC")
            asset_name: Asset name (e.g., "Ethereum")
            fund_id: Optional fund ID to associate asset with
            base_prum: Initial average purchase price from historical purchases
            base_quantity: Initial quantity owned from historical purchases
            file_path: Deprecated, ignored (kept for API compatibility)
        """
        self.symbol = symbol
        self.asset_name = asset_name
        self.fund_id = fund_id
        self.base_prum = Decimal(str(base_prum)) if base_prum else None
        self.base_quantity = Decimal(str(base_quantity))
        self.currency = currency

        # Initialize or get existing asset in database
        self._initialize_asset()

    def _initialize_asset(self):
        """Initialize or retrieve asset from database."""
        try:
            self.asset = TransactionRepository.get_or_create_asset(
                symbol=self.symbol,
                name=self.asset_name,
                fund_id=self.fund_id,
                base_prum=self.base_prum,
                historical_quantity=self.base_quantity,
                currency=self.currency,
            )
            logger.info(
                f"Initialized purchase tracker for {self.symbol} (asset_id={self.asset.id})"
            )
        except Exception as e:
            logger.error(f"Error initializing asset: {e}")
            raise

    def add_purchase(
        self,
        quantity: Decimal,
        price: Decimal,
        total_cost: Decimal,
        order_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        """
        Record a new purchase.

        Args:
            quantity: Quantity purchased (e.g., 0.01 ETH)
            price: Price per unit (e.g., 3000 USDC)
            total_cost: Total cost (e.g., 30 USDC)
            order_id: Binance order ID
            timestamp: ISO timestamp (defaults to now)
        """
        try:
            # Parse timestamp if provided
            dt_timestamp = None
            if timestamp:
                # Handle both formats: with and without 'Z' suffix
                timestamp_clean = timestamp.replace("Z", "+00:00")
                dt_timestamp = datetime.fromisoformat(timestamp_clean)

            transaction = TransactionRepository.add_transaction(
                asset_id=self.asset.id,
                transaction_type="buy",
                quantity=quantity,
                price=price,
                total_cost=total_cost,
                order_id=order_id,
                timestamp=dt_timestamp,
            )

            logger.info(
                f"Recorded purchase: {quantity} @ {price} = {total_cost} (id={transaction.id})"
            )
        except Exception as e:
            logger.error(f"Error recording purchase: {e}")
            raise

    def calculate_prum(self) -> Optional[Decimal]:
        """
        Calculate weighted average purchase price (PRUM).

        Returns:
            Average purchase price or None if no purchases
        """
        try:
            prum = TransactionRepository.calculate_prum(self.symbol)

            if prum:
                logger.info(f"PRUM calculated: {prum}")
            else:
                logger.warning("No purchases recorded")

            return prum
        except Exception as e:
            logger.error(f"Error calculating PRUM: {e}")
            return None

    def get_statistics(self):
        """
        Get purchase statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            stats = TransactionRepository.get_asset_statistics(self.symbol)
            # Add last_updated for backward compatibility
            stats["last_updated"] = datetime.now(timezone.utc).isoformat()
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def get_recent_purchases(self, limit: int = 10) -> List[dict]:
        """
        Get recent purchases.

        Args:
            limit: Maximum number of purchases to return

        Returns:
            List of recent purchases as dictionaries
        """
        try:
            transactions = TransactionRepository.get_recent_transactions(
                self.symbol, limit=limit
            )

            # Convert to dict format for backward compatibility
            return [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "quantity": str(t.quantity),
                    "price": str(t.price),
                    "total_cost": str(t.total_cost),
                    "order_id": t.order_id,
                }
                for t in transactions
            ]
        except Exception as e:
            logger.error(f"Error getting recent purchases: {e}")
            return []
