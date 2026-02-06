"""
DCA Executor - Main Dollar Cost Averaging logic.
Handles balance verification, earn transfer, and order execution.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from loguru import logger

from .binance_client import BinanceAPIError, BinanceClient
from .config import Config
from .email_notifier import get_notifier
from .purchase_tracker import PurchaseTracker
from .retry import retry_with_backoff


class DCAExecutor:
    """
    Main class to execute DCA purchases.
    """

    def __init__(self, client: BinanceClient, config: Config):
        """
        Initialize DCA executor.

        Args:
            client: Configured Binance client
            config: Bot configuration
        """
        self.client = client
        self.config = config
        self.dca_config = config.dca

        # Initialize purchase tracker
        self.tracker = PurchaseTracker(
            symbol=config.dca.symbol,
            asset_name=f"{config.dca.base_asset}",  # e.g., "ETH"
            fund_id=None,  # No fund for crypto assets
            base_prum=config.dca.base_prum,
            base_quantity=config.dca.base_quantity,
        )

    def should_execute_purchase(self) -> Tuple[bool, str]:
        """
        Determine if purchase should be executed based on momentum and PRUM.

        LOGIC:
        - If last N periods are POSITIVE (close > open)
          AND current price > PRUM + buffer
          => SKIP purchase (avoid buying in euphoria)
        - Otherwise => EXECUTE purchase

        Returns:
            Tuple (should_execute, reason)
        """
        symbol = self.dca_config.symbol
        num_periods = self.dca_config.momentum_periods
        prum_buffer = self.dca_config.prum_buffer
        kline_interval = self.dca_config.kline_interval

        try:
            # 1. Get current price
            current_price = self.client.get_symbol_price(symbol)
            logger.info(f"Current price {symbol}: {current_price}")

            # 2. Get klines for momentum analysis
            # We need num_periods + 1 to have the previous COMPLETED periods
            klines_needed = num_periods + 1
            klines = self.client.get_klines(symbol, interval=kline_interval, limit=klines_needed)

            if len(klines) < klines_needed:
                logger.warning(
                    f"Not enough historical data (got {len(klines)} klines, need {klines_needed})"
                )
                return True, "Insufficient historical data - executing by default"

            # Get the N previous COMPLETED periods (excluding current incomplete period)
            completed_periods = klines[-(num_periods + 1):-1]

            # Check if all periods are positive (close > open)
            all_periods_positive = True
            for i, period in enumerate(completed_periods):
                is_positive = period.close > period.open
                logger.info(
                    f"Period -{num_periods - i}: open={period.open}, close={period.close}, positive={is_positive}"
                )
                if not is_positive:
                    all_periods_positive = False

            # 3. Calculate PRUM (average purchase price) using tracker
            prum = self.tracker.calculate_prum()

            if prum is None:
                logger.info("No existing position (PRUM = None) - executing purchase")
                return True, "No existing position - first purchase"

            logger.info(f"PRUM (average purchase price): {prum}")

            # 4. Apply decision logic
            prum_threshold = prum * Decimal(str(1 + prum_buffer))
            price_above_prum = current_price > prum_threshold

            logger.info(
                f"Decision factors: all_periods_positive={all_periods_positive}, "
                f"price_above_prum={price_above_prum} (threshold: {prum_threshold}, buffer: {prum_buffer * 100:.0f}%)"
            )

            if all_periods_positive and price_above_prum:
                reason = (
                    f"Purchase skipped: bullish momentum ({num_periods} positive periods) "
                    f"+ price above PRUM+{prum_buffer * 100:.0f}% ({current_price} > {prum_threshold})"
                )
                logger.warning(f"🚫 SKIP PURCHASE - {reason}")
                return False, reason

            # Otherwise, execute purchase
            if not all_periods_positive:
                reason = f"Execute: not all {num_periods} periods positive (non-bullish momentum)"
            elif not price_above_prum:
                reason = (
                    f"Execute: price below PRUM+{prum_buffer * 100:.0f}% ({current_price} <= {prum_threshold})"
                )
            else:
                reason = "Execute: purchase conditions met"

            logger.info(f"✅ EXECUTE PURCHASE - {reason}")
            return True, reason

        except Exception as e:
            logger.error(f"Error in should_execute_purchase: {e}", exc_info=True)
            logger.warning(
                "Error during decision logic - executing by default for safety"
            )
            return True, f"Error in decision logic ({str(e)}) - executing by default"

    @retry_with_backoff(max_retries=3, initial_delay=1.0, exceptions=(BinanceAPIError,))
    def check_and_ensure_balance(self, required_amount: Decimal) -> bool:
        """
        Check if USDC balance is sufficient. If not, attempt to transfer from Earn.

        Args:
            required_amount: Required amount in USDC

        Returns:
            True if balance is sufficient, False otherwise
        """
        quote_asset = self.dca_config.quote_asset

        # 1. Check spot balance
        balance = self.client.get_asset_balance(quote_asset)
        free_balance = balance.free

        logger.info(f"Spot balance {quote_asset}: {free_balance}")

        if free_balance >= required_amount:
            logger.info(f"Sufficient balance: {free_balance} >= {required_amount}")
            return True

        # 2. Insufficient balance, check earn
        shortage = required_amount - free_balance
        logger.warning(f"Insufficient spot balance. Missing: {shortage} {quote_asset}")
        logger.info("Checking funds in Simple Earn...")

        try:
            # Retrieve flexible position for USDC
            earn_position = self.client.get_flexible_product_position_by_asset(
                quote_asset
            )

            if not earn_position:
                logger.error(f"No flexible {quote_asset} position found in Earn")
                return False

            earn_amount = earn_position.total_amount
            product_id = earn_position.product_id

            logger.info(f"Available amount in Earn: {earn_amount} {quote_asset}")

            if earn_amount < shortage:
                logger.error(
                    f"Insufficient funds in Earn. Available: {earn_amount}, Required: {shortage}"
                )
                return False

            # 3. Transfer from earn to spot
            logger.info(f"Transferring {shortage} {quote_asset} from Earn to Spot...")

            redeem_result = self.client.redeem_flexible_product(
                product_id=product_id, amount=str(shortage)
            )

            logger.info(f"Transfer successful: {redeem_result}")

            # Check balance again after transfer
            new_balance = self.client.get_asset_balance(quote_asset)
            new_free_balance = new_balance.free

            logger.info(
                f"New spot balance after transfer: {new_free_balance} {quote_asset}"
            )

            if new_free_balance >= required_amount:
                logger.info("Sufficient balance after transfer from Earn")
                return True
            else:
                logger.error(
                    f"Still insufficient balance after transfer: {new_free_balance}"
                )
                return False

        except BinanceAPIError as e:
            logger.error(f"Error during transfer from Earn: {e}")
            return False

    @retry_with_backoff(max_retries=3, initial_delay=2.0, exceptions=(BinanceAPIError,))
    def execute_dca_purchase(self) -> Optional[Dict[str, Any]]:
        """
        Execute complete DCA purchase:
        1. Check decision logic (momentum + PRUM)
        2. Check/ensure balance (if purchase should execute)
        3. Execute market order (if purchase should execute)
        4. Log details

        Returns:
            Order result if successful, None otherwise (or if skipped)
        """
        symbol = self.dca_config.symbol
        amount_usdc = Decimal(str(self.dca_config.amount_usdc))

        logger.info(f"START DCA EXECUTION - {datetime.now().isoformat()}")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Amount: {amount_usdc} {self.dca_config.quote_asset}")

        try:
            # 1. Check if purchase should be executed (MAIN DECISION LOGIC)
            should_execute, reason = self.should_execute_purchase()

            logger.info(f"Decision: {'EXECUTE' if should_execute else 'SKIP'}")
            logger.info(f"Reason: {reason}")

            if not should_execute:
                logger.warning("🚫 DCA PURCHASE SKIPPED")
                logger.warning(f"Reason: {reason}")
                logger.info(f"Timestamp: {datetime.now().isoformat()}")

                # Send email notification
                get_notifier().notify_purchase_skipped(symbol, reason)

                return None

            # 2. Check and ensure balance
            if not self.check_and_ensure_balance(amount_usdc):
                logger.error("❌ Insufficient balance. DCA purchase cancelled.")
                logger.error("ALERT: Please fund your account!")
                get_notifier().notify_error(
                    "Insufficient Balance",
                    "DCA purchase cancelled due to insufficient funds.",
                )
                return None

            # 3. Get current price (for logging)
            current_price = self.client.get_symbol_price(symbol)
            logger.info(f"Current price {symbol}: {current_price}")

            # 4. Execute market order
            logger.info(
                f"Executing MARKET BUY order for {amount_usdc} {self.dca_config.quote_asset}..."
            )

            order_result = self.client.create_market_order(
                symbol=symbol, side="BUY", quote_order_qty=str(amount_usdc)
            )

            # 5. Extract and log order details
            order_id = order_result.order_id
            status = order_result.status
            executed_qty = order_result.executed_qty

            # Calculate fees and average price
            fills = order_result.fills
            total_fees = Decimal("0")
            total_cost = Decimal("0")
            total_qty = Decimal("0")

            for fill in fills:
                qty = fill.qty
                price = fill.price
                commission = fill.commission

                total_qty += qty
                total_cost += qty * price
                total_fees += commission

            avg_price = total_cost / total_qty if total_qty > 0 else Decimal("0")

            # 6. Record purchase in tracker
            self.tracker.add_purchase(
                quantity=executed_qty,
                price=avg_price,
                total_cost=total_cost,
                order_id=str(order_id),
                timestamp=datetime.now().isoformat(),
            )

            # 7. Log summary
            logger.info("✅ DCA PURCHASE SUCCESSFUL!")
            logger.info(f"Order ID: {order_id}")
            logger.info(f"Status: {status}")
            logger.info(
                f"Quantity purchased: {executed_qty} {self.dca_config.base_asset}"
            )
            logger.info(f"Average price: {avg_price} {self.dca_config.quote_asset}")
            logger.info(f"Total cost: {total_cost} {self.dca_config.quote_asset}")
            logger.info(f"Fees: {total_fees}")
            logger.info(f"Reason: {reason}")
            logger.info(f"Timestamp: {datetime.now().isoformat()}")

            # Log updated PRUM
            new_prum = self.tracker.calculate_prum()
            logger.info(f"Updated PRUM: {new_prum}")

            # Send email notification
            get_notifier().notify_purchase_success(
                symbol=symbol,
                quantity=float(executed_qty),
                price=float(avg_price),
                cost=float(total_cost),
                reason=reason,
            )

            return order_result

        except BinanceAPIError as e:
            logger.error(f"❌ Binance API error during DCA purchase: {e}")
            get_notifier().notify_error("Binance API Error", str(e))
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error during DCA purchase: {e}", exc_info=True)
            get_notifier().notify_error("Unexpected Error", str(e))
            return None

    def run(self) -> bool:
        """
        Main entry point to execute DCA.

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.execute_dca_purchase()
            return result is not None
        except Exception as e:
            logger.error(f"Error during DCA execution: {e}", exc_info=True)
            return False


def create_dca_executor(config: Config) -> DCAExecutor:
    """
    Factory function to create a DCAExecutor with Binance client.

    Args:
        config: Bot configuration

    Returns:
        DCAExecutor instance
    """
    client = BinanceClient(config.binance)
    return DCAExecutor(client, config)
