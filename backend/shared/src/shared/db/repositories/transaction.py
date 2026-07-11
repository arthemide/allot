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
        fund_id: Optional[int] = None,
        base_prum: Optional[Decimal] = None,
        historical_quantity: Decimal = Decimal("0"),
        currency: str = "USD",
        session=None,
    ) -> AssetTable:
        """
        Get existing asset or create new one.

        Args:
            symbol: Asset symbol (e.g., 'ETHUSDC', 'AAPL')
            name: Asset name (e.g., 'Ethereum', 'Apple Inc.')
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
            # Try to find existing asset by symbol only
            stmt = select(AssetTable).where(AssetTable.symbol == symbol)
            asset = session.scalars(stmt).first()

            if asset:
                logger.info(f"Found existing asset: {symbol} (id={asset.id})")
                return asset

            # Create new asset
            asset = AssetTable(
                symbol=symbol,
                name=name,
                fund_id=fund_id,
                shares_number=float(historical_quantity)
                if historical_quantity
                else 0.0,
                cost=0.0,
                current_repartition=0.0,
                target_repartition=None,
                arbitration_threshold=0.0,
                threshold_to_alert=0.0,
                base_prum=base_prum,
                currency=currency,
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

            logger.info(f"Created new asset: {symbol} (id={asset.id})")
            return asset
        finally:
            if not use_existing_session:
                session.close()

    @staticmethod
    @with_db_retry(max_retries=3)
    def add_transaction(
        symbol: Optional[str] = None,
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
            asset_id: Asset ID (takes precedence over symbol)
            transaction_type: 'buy', 'sell', etc.
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
                stmt = select(AssetTable).where(AssetTable.symbol == symbol)
                asset = session.scalars(stmt).first()
                if asset:
                    asset_id = asset.id

            if not asset_id:
                raise ValueError(f"Asset not found: {symbol}")

            # Idempotency: an order already recorded must not be inserted twice
            # (scheduler misfire retries, manual re-runs, etc.)
            if order_id:
                existing = session.scalars(
                    select(AssetTransactionTable).where(
                        AssetTransactionTable.asset_id == asset_id,
                        AssetTransactionTable.order_id == order_id,
                    )
                ).first()
                if existing:
                    logger.warning(
                        f"Transaction with order_id={order_id} already recorded "
                        f"for asset_id={asset_id} (id={existing.id}) - skipping insert"
                    )
                    return existing

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
                session.commit()
                # Refresh after commit to load attributes while session is still open
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
    def calculate_prum(symbol: str, session=None) -> Optional[Decimal]:
        """
        Calculate weighted average purchase price (PRUM) for an asset.

        Formula: PRUM = (base_cost + sum(transaction_costs)) / (base_quantity + sum(transaction_quantities))

        Args:
            symbol: Asset symbol
            session: Optional database session (for testing)

        Returns:
            Weighted average purchase price or None if no purchases
        """
        use_existing_session = session is not None
        if not session:
            session = SessionLocal()

        try:
            # Get asset with all transactions (search by symbol only)
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.symbol == symbol)
            )
            asset = session.scalars(stmt).first()

            if not asset:
                logger.warning(f"Asset not found: {symbol}")
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
    def calculate_total_quantity(symbol: str, session=None) -> Optional[Decimal]:
        """
        Calculate the total quantity held for an asset:
        base historical quantity + buys - sells.

        Args:
            symbol: Asset symbol
            session: Optional database session (for testing)

        Returns:
            Total quantity or None if asset not found
        """
        use_existing_session = session is not None
        if not session:
            session = SessionLocal()

        try:
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.symbol == symbol)
            )
            asset = session.scalars(stmt).first()

            if not asset:
                logger.warning(f"Asset not found: {symbol}")
                return None

            total_qty = Decimal(str(asset.shares_number or 0))
            for transaction in asset.transactions:
                if transaction.transaction_type == "buy":
                    total_qty += transaction.quantity
                elif transaction.transaction_type == "sell":
                    total_qty -= transaction.quantity

            return total_qty
        finally:
            if not use_existing_session:
                session.close()

    @staticmethod
    @with_db_retry(max_retries=3)
    def get_recent_transactions(
        symbol: str, limit: int = 10
    ) -> List[AssetTransactionTable]:
        """
        Get recent transactions for an asset.

        Args:
            symbol: Asset symbol
            limit: Maximum number of transactions to return

        Returns:
            List of recent transactions
        """
        with SessionLocal() as session:
            stmt = (
                select(AssetTransactionTable)
                .join(AssetTable)
                .where(AssetTable.symbol == symbol)
                .order_by(AssetTransactionTable.timestamp.desc())
                .limit(limit)
            )
            transactions = session.scalars(stmt).all()
            return list(transactions)

    @staticmethod
    @with_db_retry(max_retries=3)
    def get_asset_statistics(symbol: str) -> dict:
        """
        Get purchase statistics for an asset.

        Args:
            symbol: Asset symbol

        Returns:
            Dictionary with statistics
        """
        with SessionLocal() as session:
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.symbol == symbol)
            )
            asset = session.scalars(stmt).first()

            if not asset:
                return {}

            prum = TransactionRepository.calculate_prum(symbol)

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
                "asset_id": asset.id,
            }

    @staticmethod
    @with_db_retry(max_retries=3)
    def get_asset_by_symbol(symbol: str) -> Optional[AssetTable]:
        """
        Get asset by symbol.

        Args:
            symbol: Asset symbol

        Returns:
            AssetTable instance or None
        """
        with SessionLocal() as session:
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.symbol == symbol)
            )
            asset = session.scalars(stmt).first()
            return asset
