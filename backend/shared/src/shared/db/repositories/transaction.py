from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.db.config import SessionLocal, with_db_retry
from shared.db.models.asset import AssetTable
from shared.db.models.transaction import AssetTransactionTable


class TransactionRepository:
    """Repository for managing asset transactions and calculating PRUM"""

    @staticmethod
    @with_db_retry(max_retries=3)
    def get_or_create_asset(
        symbol: str,
        name: str,
        asset_type: str = "crypto",
        fund_id: Optional[int] = None,
        base_prum: Optional[Decimal] = None,
        historical_quantity: Decimal = Decimal("0"),
        session=None,
    ) -> AssetTable:
        """
        Get existing asset or create new one.

        Args:
            symbol: Asset symbol (e.g., 'ETHUSDC', 'AAPL')
            name: Asset name (e.g., 'Ethereum', 'Apple Inc.')
            asset_type: Type of asset ('crypto', 'stock', etc.')
            fund_id: Optional fund ID to associate asset with
            base_prum: Historical average purchase price (for pre-tracked purchases)
            historical_quantity: Historical quantity (stored in shares_number)
            session: Optional database session (for testing)

        Returns:
            AssetTable instance
        """
        # Use provided session or create new one
        use_existing_session = session is not None
        if not session:
            session = SessionLocal()

        try:
            # Try to find existing asset
            stmt = select(AssetTable).where(
                AssetTable.symbol == symbol, AssetTable.asset_type == asset_type
            )
            asset = session.scalars(stmt).one_or_none()

            if asset:
                logger.info(f"Found existing asset: {symbol} (id={asset.id})")
                return asset

            # Create new asset
            asset = AssetTable(
                symbol=symbol,
                name=name,
                asset_type=asset_type,
                fund_id=fund_id,
                shares_number=float(historical_quantity)
                if historical_quantity
                else 0.0,
                cost=0.0,  # Will be calculated from transactions
                current_repartition=0.0,
                target_repartition=None,
                arbitration_threshold=0.0,
                threshold_to_alert=0.0,
                base_prum=base_prum,
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)

            # Load transactions relationship
            asset = session.scalars(
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.id == asset.id)
            ).one()

            logger.info(
                f"Created new asset: {symbol} (id={asset.id}, type={asset_type})"
            )
            return asset
        finally:
            if not use_existing_session:
                session.close()

    @staticmethod
    @with_db_retry(max_retries=3)
    def add_transaction(
        symbol: Optional[str] = None,
        asset_type: str = "crypto",
        asset_id: Optional[int] = None,
        transaction_type: str = "buy",
        quantity: Decimal = Decimal("0"),
        price: Decimal = Decimal("0"),
        total_cost: Decimal = Decimal("0"),
        order_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        session=None,
    ) -> AssetTransactionTable:
        """
        Record a new transaction.

        Args:
            symbol: Asset symbol (if asset_id not provided)
            asset_type: Asset type (if symbol used)
            asset_id: Asset ID (takes precedence over symbol)
            transaction_type: 'buy', 'sell', 'dividend', etc.
            quantity: Amount transacted
            price: Price per unit
            total_cost: Total transaction value
            order_id: External reference (Binance order ID, broker confirmation, etc.)
            timestamp: Transaction timestamp (defaults to now)
            session: Optional database session (for testing)

        Returns:
            AssetTransactionTable instance
        """
        use_existing_session = session is not None
        if not session:
            session = SessionLocal()

        try:
            # Look up asset_id if symbol provided
            if asset_id is None and symbol:
                stmt = select(AssetTable).where(
                    AssetTable.symbol == symbol, AssetTable.asset_type == asset_type
                )
                asset = session.scalars(stmt).one_or_none()
                if asset:
                    asset_id = asset.id

            if not asset_id:
                raise ValueError(f"Asset not found: {symbol}")

            # Begin transaction only if we created our own session
            if use_existing_session:
                transaction = AssetTransactionTable(
                    asset_id=asset_id,
                    transaction_type=transaction_type,
                    timestamp=timestamp or datetime.now(timezone.utc),
                    quantity=quantity,
                    price=price,
                    total_cost=total_cost,
                    order_id=order_id,
                )
                session.add(transaction)
                session.flush()
                session.refresh(transaction)
            else:
                with session.begin():
                    transaction = AssetTransactionTable(
                        asset_id=asset_id,
                        transaction_type=transaction_type,
                        timestamp=timestamp or datetime.now(timezone.utc),
                        quantity=quantity,
                        price=price,
                        total_cost=total_cost,
                        order_id=order_id,
                    )
                    session.add(transaction)
                    session.flush()
                    session.refresh(transaction)

            logger.info(
                f"Recorded transaction: asset_id={asset_id}, type={transaction_type}, "
                f"quantity={quantity}, price={price}, total={total_cost}"
            )
            return transaction
        finally:
            if not use_existing_session:
                session.close()

    @staticmethod
    @with_db_retry(max_retries=3)
    def calculate_prum(
        symbol: str, asset_type: str = "crypto", session=None
    ) -> Optional[Decimal]:
        """
        Calculate weighted average purchase price (PRUM) for an asset.

        Formula: PRUM = (base_cost + sum(transaction_costs)) / (base_quantity + sum(transaction_quantities))

        Args:
            symbol: Asset symbol
            asset_type: Asset type
            session: Optional database session (for testing)

        Returns:
            Weighted average purchase price or None if no purchases
        """
        use_existing_session = session is not None
        if not session:
            session = SessionLocal()

        try:
            # Get asset with all transactions
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.symbol == symbol, AssetTable.asset_type == asset_type)
            )
            asset = session.scalars(stmt).one_or_none()

            if not asset:
                logger.warning(f"Asset not found: {symbol} (type={asset_type})")
                return None

            total_qty = Decimal("0")
            total_cost = Decimal("0")

            # Include base historical data (shares_number represents historical quantity)
            if asset.base_prum and asset.shares_number and asset.shares_number > 0:
                historical_qty = Decimal(str(asset.shares_number))
                total_qty += historical_qty
                total_cost += historical_qty * Decimal(str(asset.base_prum))
                logger.debug(
                    f"Including historical: quantity={historical_qty}, prum={asset.base_prum}, "
                    f"cost={historical_qty * Decimal(str(asset.base_prum))}"
                )

            # Add all buy transactions
            for transaction in asset.transactions:
                if transaction.transaction_type == "buy":
                    total_qty += transaction.quantity
                    total_cost += transaction.total_cost
                    logger.debug(
                        f"Including transaction: quantity={transaction.quantity}, "
                        f"total_cost={transaction.total_cost}"
                    )

            if total_qty == 0:
                logger.warning(f"No purchases recorded for {symbol}")
                return None

            prum = total_cost / total_qty
            logger.info(
                f"PRUM calculated for {symbol}: {prum} (total_cost={total_cost}, total_qty={total_qty})"
            )
            return prum
        finally:
            if not use_existing_session:
                session.close()

    @staticmethod
    @with_db_retry(max_retries=3)
    def get_recent_transactions(
        symbol: str, asset_type: str = "crypto", limit: int = 10
    ) -> List[AssetTransactionTable]:
        """
        Get recent transactions for an asset.

        Args:
            symbol: Asset symbol
            asset_type: Asset type
            limit: Maximum number of transactions to return

        Returns:
            List of recent transactions
        """
        with SessionLocal() as session:
            stmt = (
                select(AssetTransactionTable)
                .join(AssetTable)
                .where(AssetTable.symbol == symbol, AssetTable.asset_type == asset_type)
                .order_by(AssetTransactionTable.timestamp.desc())
                .limit(limit)
            )
            transactions = session.scalars(stmt).all()
            return list(transactions)

    @staticmethod
    @with_db_retry(max_retries=3)
    def get_asset_statistics(symbol: str, asset_type: str = "crypto") -> dict:
        """
        Get purchase statistics for an asset.

        Args:
            symbol: Asset symbol
            asset_type: Asset type

        Returns:
            Dictionary with statistics
        """
        with SessionLocal() as session:
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.symbol == symbol, AssetTable.asset_type == asset_type)
            )
            asset = session.scalars(stmt).one_or_none()

            if not asset:
                return {}

            prum = TransactionRepository.calculate_prum(symbol, asset_type)

            # Calculate statistics for transactions only (excluding base)
            transactions = [
                t for t in asset.transactions if t.transaction_type == "buy"
            ]
            transaction_count = len(transactions)
            transaction_total_cost = sum(t.total_cost for t in transactions)
            transaction_total_qty = sum(t.quantity for t in transactions)

            return {
                "prum": str(prum) if prum else None,
                "historical_quantity": str(asset.shares_number),
                "base_prum": str(asset.base_prum) if asset.base_prum else None,
                "transaction_count": transaction_count,
                "transaction_total_quantity": str(transaction_total_qty),
                "transaction_total_cost": str(transaction_total_cost),
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_type": asset.asset_type,
                "asset_id": asset.id,
            }

    @staticmethod
    @with_db_retry(max_retries=3)
    def get_asset_by_symbol(
        symbol: str, asset_type: str = "crypto"
    ) -> Optional[AssetTable]:
        """
        Get asset by symbol and type.

        Args:
            symbol: Asset symbol
            asset_type: Asset type

        Returns:
            AssetTable instance or None
        """
        with SessionLocal() as session:
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.symbol == symbol, AssetTable.asset_type == asset_type)
            )
            asset = session.scalars(stmt).one_or_none()
            return asset
