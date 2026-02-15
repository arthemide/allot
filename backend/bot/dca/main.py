"""
Main entry point for Binance DCA bot.

Usage:
    # Start scheduler (automatic mode)
    python -m dca.main

    # Execute purchase immediately then start scheduler
    python -m dca.main --now

    # Execute single purchase (manual mode, no scheduler)
    python -m dca.main --once

    # Test mode (no real execution)
    python -m dca.main --test
"""

import argparse
import sys

from loguru import logger

from shared.logger import setup_logging

from .config import get_config
from .dca_executor import create_dca_executor
from .scheduler import DCAScheduler

setup_logging()


def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="DCA (Dollar Cost Averaging) Bot for Binance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start automatic scheduler
  python -m dca_bot.main

  # Execute immediately then start scheduler
  python -m dca_bot.main --now

  # Execute once (no scheduler)
  python -m dca_bot.main --once

  # Test mode (display config without executing)
  python -m dca_bot.main --test
        """,
    )

    parser.add_argument(
        "--now",
        action="store_true",
        help="Execute DCA purchase immediately at startup, then start scheduler",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute single DCA purchase then exit (no scheduler)",
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: display configuration without executing purchase",
    )

    return parser.parse_args()


def test_mode():
    """
    Test mode: display configuration and verify connection.
    """
    from .binance_client import BinanceClient

    config = get_config()
    logger.info("TEST MODE - No purchase will be executed")

    # Display configuration
    logger.info(str(config))

    # Test Binance connection
    try:
        client = BinanceClient(config.binance)
        logger.info("Testing Binance API connection...")

        account_info = client.get_account_info()
        logger.info(
            f"✅ Connection successful! Account type: {account_info.get('accountType')}"
        )

        # Display main balances
        balances = account_info.get("balances", [])
        logger.info("Main balances:")

        for balance in balances:
            free = float(balance["free"])
            locked = float(balance["locked"])

            if free > 0 or locked > 0:
                logger.info(f"  {balance['asset']}: free={free}, locked={locked}")

        # Test configured symbol
        symbol = config.dca.symbol
        logger.info(f"Testing symbol {symbol}...")

        symbol_info = client.get_symbol_info(symbol)
        logger.info(
            f"✅ Valid symbol: {symbol_info.get('symbol')}, status={symbol_info.get('status')}"
        )

        price = client.get_symbol_price(symbol)
        logger.info(f"Current price: {price} {config.dca.quote_asset}")

        # Calculate estimated quantity
        estimated_qty = config.dca.amount_usdc / float(price)
        logger.info(
            f"Estimated quantity for {config.dca.amount_usdc} USDC: ~{estimated_qty:.6f} {config.dca.base_asset}"
        )

        # Show last purchase info
        executor = create_dca_executor(config)
        recent = executor.tracker.get_recent_purchases(limit=1)
        if recent:
            last = recent[0]
            logger.info(
                f"Last purchase: {last.get('timestamp')} - {last.get('quantity')} {config.dca.base_asset}"
            )
        else:
            logger.info("No previous purchases found")

    except Exception as e:
        logger.error(f"❌ Error during test: {e}", exc_info=True)
        return False

    logger.info("✅ Tests completed successfully")
    return True


def main():
    """
    Main function.
    """
    args = parse_arguments()

    logger.info("🚀 Starting Binance DCA Bot")

    try:
        # Test mode
        if args.test:
            success = test_mode()
            sys.exit(0 if success else 1)

        # Create scheduler
        config = get_config()
        scheduler = DCAScheduler(config)

        # Single execution mode
        if args.once:
            logger.info("Single execution mode (--once)")
            scheduler.run_once()
            logger.info("✅ Execution completed")
            sys.exit(0)

        # Scheduler mode
        logger.info("Automatic scheduler mode")
        scheduler.start(run_immediately=args.now)

    except KeyboardInterrupt:
        logger.info("🛑 Stop requested by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
