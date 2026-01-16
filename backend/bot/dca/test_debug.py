"""
Debug test script to check Binance API connections without making purchases.
Tests:
- Account access
- Balance retrieval
- Simple Earn positions
- Symbol information
- Price retrieval
"""

from decimal import Decimal

from loguru import logger

from .binance_client import BinanceClient
from .config import get_config
from .purchase_tracker import PurchaseTracker


def test_account_info(client: BinanceClient):
    """Test account information retrieval."""
    print("\n" + "=" * 60)
    print("TEST 1: Account Information")
    print("=" * 60)
    try:
        account_info = client.get_account_info()
        print("✅ Account retrieved successfully")
        print(f"   Can trade: {account_info.get('canTrade')}")
        print(f"   Can deposit: {account_info.get('canDeposit')}")
        print(f"   Can withdraw: {account_info.get('canWithdraw')}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_balance(client: BinanceClient, asset: str = "USDC"):
    """Test balance retrieval for specific asset."""
    print("\n" + "=" * 60)
    print(f"TEST 2: {asset} Balance")
    print("=" * 60)
    try:
        balance = client.get_asset_balance(asset)
        print("✅ Balance retrieved successfully")
        print(f"   Free: {balance.free} {asset}")
        print(f"   Locked: {balance.locked} {asset}")
        print(f"   Total: {balance.total} {asset}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_earn_positions(client: BinanceClient, asset: str = "USDC"):
    """Test Simple Earn flexible positions."""
    print("\n" + "=" * 60)
    print(f"TEST 3: Simple Earn Positions ({asset})")
    print("=" * 60)
    try:
        # Test 1: Get all flexible positions
        all_positions = client.get_simple_earn_flexible_position()
        print(f"✅ Retrieved {len(all_positions)} total flexible positions")

        # Test 2: Get specific asset position
        asset_positions = client.get_simple_earn_flexible_position(asset=asset)
        print(f"   Found {len(asset_positions)} positions for {asset}")

        if asset_positions:
            for pos in asset_positions:
                print("\n   Position details:")
                print(f"   - Asset: {pos.asset}")
                print(f"   - Product ID: {pos.product_id}")
                print(f"   - Total Amount: {pos.total_amount}")
        else:
            print(f"   ⚠️  No flexible positions found for {asset}")
            print(f"   This means you have no {asset} in Simple Earn")

        # Test 3: Try the helper method
        print("\n   Testing helper method...")
        position = client.get_flexible_product_position_by_asset(asset)
        if position:
            print(f"   ✅ Helper found position: {position.total_amount} {asset}")
        else:
            print("   ℹ️  Helper returned None (no position or zero balance)")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error("Error details:", exc_info=True)
        return False


def test_symbol_info(client: BinanceClient, symbol: str = "ETHUSDC"):
    """Test symbol information retrieval."""
    print("\n" + "=" * 60)
    print(f"TEST 4: Symbol Information ({symbol})")
    print("=" * 60)
    try:
        symbol_info = client.get_symbol_info(symbol)
        print("✅ Symbol information retrieved")
        print(f"   Status: {symbol_info.get('status')}")
        print(f"   Base asset: {symbol_info.get('baseAsset')}")
        print(f"   Quote asset: {symbol_info.get('quoteAsset')}")

        # Find LOT_SIZE filter
        filters = {f["filterType"]: f for f in symbol_info.get("filters", [])}
        lot_size = filters.get("LOT_SIZE", {})
        print(f"   Min quantity: {lot_size.get('minQty')}")
        print(f"   Step size: {lot_size.get('stepSize')}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_price(client: BinanceClient, symbol: str = "ETHUSDC"):
    """Test price retrieval."""
    print("\n" + "=" * 60)
    print(f"TEST 5: Current Price ({symbol})")
    print("=" * 60)
    try:
        price = client.get_symbol_price(symbol)
        print(f"✅ Price retrieved: {price}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_klines(client: BinanceClient, symbol: str = "ETHUSDC"):
    """Test klines/candlestick data retrieval."""
    print("\n" + "=" * 60)
    print(f"TEST 6: Historical Klines ({symbol})")
    print("=" * 60)
    try:
        klines = client.get_klines(symbol, interval="1w", limit=3)
        print(f"✅ Retrieved {len(klines)} klines")
        for i, kline in enumerate(klines, 1):
            positive = "📈 Positive" if kline.close > kline.open else "📉 Negative"
            print(f"   Kline {i}: open={kline.open}, close={kline.close} ({positive})")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_prum_calculation(
    client: BinanceClient, config, symbol: str = "ETHUSDC", base_asset: str = "ETH"
):
    """Test PRUM (average purchase price) calculation."""
    print("\n" + "=" * 60)
    print(f"TEST 7: PRUM Calculation ({symbol})")
    print("=" * 60)
    try:
        # Check if there's a position first
        balance = client.get_asset_balance(base_asset)
        total_balance = balance.total
        print(f"   Current {base_asset} balance: {total_balance}")

        # Initialize Purchase Tracker (now uses PostgreSQL)
        tracker = PurchaseTracker(
            symbol=config.dca.symbol,
            asset_name=config.dca.base_asset,
            fund_id=None,
            base_prum=config.dca.base_prum,
            base_quantity=config.dca.base_quantity,
        )

        # Get tracker statistics
        stats = tracker.get_statistics()
        print("\n   Purchase Tracker Stats:")
        print(f"   - Base PRUM: {stats.get('base_prum', 'N/A')}")
        print(f"   - Historical Quantity: {stats.get('historical_quantity', '0')}")
        print(f"   - Bot Purchases: {stats.get('transaction_count', 0)}")
        print(
            f"   - Bot Total Quantity: {stats.get('transaction_total_quantity', '0')}"
        )
        print(f"   - Bot Total Cost: {stats.get('transaction_total_cost', '0')}")

        # Calculate PRUM using tracker
        prum = tracker.calculate_prum()

        if prum is None:
            print("\n   ℹ️  No PRUM calculated")
            if total_balance == "0" or float(total_balance) == 0:
                print(f"   No {base_asset} position found")
            else:
                print("   No purchase history in tracker despite having balance")
                print(
                    "   💡 Set DCA_BASE_PRUM and DCA_BASE_QUANTITY in .env to track existing position"
                )
            return True

        # Get current price for comparison
        current_price = client.get_symbol_price(symbol)

        print("\n✅ PRUM calculated successfully")
        print(f"   Average purchase price (PRUM): {prum}")
        print(f"   Current market price: {current_price}")

        # Calculate profit/loss
        pnl_percent = (current_price - prum) / prum * 100
        pnl_indicator = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
        print(f"   {pnl_indicator} P&L: {pnl_percent:+.2f}%")

        # Check decision logic factor
        price_above_prum = current_price > prum * Decimal(
            "1.03"
        )  # Adding 3% buffer to avoid frequent skips
        print(
            f"   Price above PRUM (+3% buffer): {'Yes ⬆️' if price_above_prum else 'No ⬇️'}"
        )

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error("Error details:", exc_info=True)
        return False


def test_order_history(client: BinanceClient, symbol: str = "ETHUSDC"):
    """Test order history retrieval."""
    print("\n" + "=" * 60)
    print(f"TEST 8: Order History ({symbol})")
    print("=" * 60)
    try:
        orders = client.get_all_orders(symbol, limit=10)
        print(f"✅ Retrieved {len(orders)} orders")

        if not orders:
            print(f"   ℹ️  No orders found for {symbol}")
            print("   This is expected if you haven't made any purchases yet")
            return True

        # Count orders by type
        buy_orders = sum(
            1 for o in orders if o["side"] == "BUY" and o["status"] == "FILLED"
        )
        sell_orders = sum(
            1 for o in orders if o["side"] == "SELL" and o["status"] == "FILLED"
        )

        print(f"   BUY orders (FILLED): {buy_orders}")
        print(f"   SELL orders (FILLED): {sell_orders}")

        # Show last 3 orders
        if len(orders) > 0:
            print(f"\n   Last {min(3, len(orders))} orders:")
            for order in orders[-3:]:
                side_emoji = "🟢" if order["side"] == "BUY" else "🔴"
                print(
                    f"   {side_emoji} {order['side']} - Qty: {order['executedQty']} - Status: {order['status']}"
                )

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error("Error details:", exc_info=True)
        return False


def main():
    """Run all debug tests."""
    print("\n" + "=" * 60)
    print("BINANCE API DEBUG TESTS")
    print("=" * 60)
    print("This script will test API connectivity without making any trades.")

    # Load configuration
    try:
        config = get_config()
        print("\n✅ Configuration loaded")
        print(f"   Symbol: {config.dca.symbol}")
        print(f"   Amount: {config.dca.amount_usdc} USDC")
    except Exception as e:
        print(f"\n❌ Failed to load configuration: {e}")
        return

    # Initialize client
    try:
        client = BinanceClient(config.binance)
        print("✅ Binance client initialized")
    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}")
        return

    # Run tests
    results = []
    results.append(("Account Info", test_account_info(client)))
    results.append(("USDC Balance", test_balance(client, "USDC")))
    results.append(("ETH Balance", test_balance(client, config.dca.base_asset)))
    results.append(("Earn Positions", test_earn_positions(client, "USDC")))
    results.append(("Symbol Info", test_symbol_info(client, config.dca.symbol)))
    results.append(("Price", test_price(client, config.dca.symbol)))
    results.append(("Klines", test_klines(client, config.dca.symbol)))
    results.append(("Order History", test_order_history(client, config.dca.symbol)))
    results.append(
        (
            "PRUM Calculation",
            test_prum_calculation(
                client, config, config.dca.symbol, config.dca.base_asset
            ),
        )
    )

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Your API configuration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above for details.")


if __name__ == "__main__":
    main()
