"""
Binance client for spot, earn and trading operations.
Uses the official Binance REST API.
"""

import time
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
from decimal import Decimal, ROUND_DOWN
from .models import (
    AssetBalance,
    MarketOrder,
    FlexiblePosition,
    OrderFill,
    RedeemResponse,
    Kline
)

from .config import BinanceConfig
from loguru import logger

class BinanceAPIError(Exception):
    """Exception for Binance API errors"""
    def __init__(self, message: str, code: Optional[int] = None):
        self.code = code
        super().__init__(message)


class BinanceClient:
    """
    Client to interact with Binance API.
    Handles authentication, signed requests and spot operations.
    """
    
    # Base Binance URLs
    BASE_URL = "https://api.binance.com"
    
    def __init__(self, config: BinanceConfig):
        """
        Initialize Binance client.
        
        Args:
            config: Configuration containing API keys
        """
        self.api_key = config.api_key
        self.api_secret = config.api_secret
        self.base_url = self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key
        })
        
        logger.info("Binance client initialized")
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC SHA256 signature for authentication.
        
        Args:
            params: Request parameters
            
        Returns:
            Hexadecimal signature
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _request(
        self,
        method: str,
        endpoint: str,
        signed: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform a request to Binance API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            signed: If True, adds timestamp and signature
            **kwargs: Additional parameters for requests
            
        Returns:
            API JSON response
            
        Raises:
            BinanceAPIError: In case of API error
        """
        url = f"{self.base_url}{endpoint}"
        params = kwargs.get('params', {})
        
        if signed:
            # Add timestamp and signature for authenticated requests
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
            kwargs['params'] = params
        
        try:
            response = self.session.request(method, url, **kwargs)
            data = response.json()
            
            # Check if response contains an error
            if response.status_code != 200:
                error_msg = data.get('msg', 'Unknown error')
                error_code = data.get('code')
                logger.error(f"Binance API error: {error_code} - {error_msg}")
                raise BinanceAPIError(error_msg, error_code)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            raise BinanceAPIError(f"Network error: {e}")
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Retrieve spot account information.
        
        Returns:
            Account information including balances
        """
        logger.debug("Retrieving account information")
        return self._request('GET', '/api/v3/account', signed=True)
    
    def get_asset_balance(self, asset: str) -> AssetBalance:
        """
        Retrieve balance of a specific asset on spot account.
        
        Args:
            asset: Asset symbol (e.g., "USDC", "ETH")
            
        Returns:
            AssetBalance object with free, locked and total amounts
        """
        account_info = self.get_account_info()
        
        for balance in account_info.get('balances', []):
            if balance['asset'] == asset:
                free = Decimal(balance['free'])
                locked = Decimal(balance['locked'])
                total = free + locked
                
                logger.debug(f"Balance {asset}: free={free}, locked={locked}, total={total}")
                
                return AssetBalance(
                    free=free,
                    locked=locked,
                    total=total
                )
        
        # Asset not found or balance = 0
        logger.debug(f"Asset {asset} not found or balance = 0")
        return AssetBalance(free=Decimal('0'), locked=Decimal('0'), total=Decimal('0'))
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Retrieve information about a trading symbol.
        Useful to know trading rules (lot size, precision, etc.)
        
        Args:
            symbol: Trading pair (e.g., "ETHUSDC")
            
        Returns:
            Symbol information
            
        Raises:
            BinanceAPIError: If the symbol doesn't exist
        """
        exchange_info = self._request('GET', '/api/v3/exchangeInfo', params={'symbol': symbol})
        
        symbols = exchange_info.get('symbols', [])
        if not symbols:
            raise BinanceAPIError(f"Symbol {symbol} not found")
        
        return symbols[0]
    
    def get_symbol_price(self, symbol: str) -> Decimal:
        """
        Retrieve current price of a symbol.
        
        Args:
            symbol: Trading pair (e.g., "ETHUSDC")
            
        Returns:
            Current price as Decimal
        """
        data = self._request('GET', '/api/v3/ticker/price', params={'symbol': symbol})
        price = Decimal(data['price'])
        logger.debug(f"Current price {symbol}: {price}")
        return price
    
    def create_market_order(
        self,
        symbol: str,
        side: str,
        quote_order_qty: Optional[str] = None,
        quantity: Optional[str] = None
    ) -> MarketOrder:
        """
        Create a market order.
        
        Args:
            symbol: Trading pair (e.g., "ETHUSDC")
            side: "BUY" or "SELL"
            quote_order_qty: Amount in quote currency (for BUY, e.g., "50" USDC)
            quantity: Quantity in base currency (e.g., "0.02" ETH)
            
        Returns:
            MarketOrder object with executed order details
            
        Note:
            For DCA purchase, use quote_order_qty to specify the amount in USDC.
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET'
        }
        
        if quote_order_qty:
            params['quoteOrderQty'] = quote_order_qty
        elif quantity:
            params['quantity'] = quantity
        else:
            raise ValueError("You must specify either 'quote_order_qty' or 'quantity'")
        
        logger.info(f"Creating {side} market order: {symbol} - {params}")
        
        result = self._request('POST', '/api/v3/order', signed=True, params=params)
        
        logger.info(f"Order executed: orderId={result.get('orderId')}, "
                   f"status={result.get('status')}, "
                   f"executedQty={result.get('executedQty')}")
        
        return MarketOrder(
            symbol=result['symbol'],
            order_id=result['orderId'],
            client_order_id=result['clientOrderId'],
            transact_time=result['transactTime'],
            price=Decimal(result['price']),
            orig_qty=Decimal(result['origQty']),
            executed_qty=Decimal(result['executedQty']),
            cummulative_quote_qty=Decimal(result['cummulativeQuoteQty']),
            status=result['status'],
            type=result['type'],
            side=result['side'],
            fills=[
                OrderFill(
                    price=Decimal(fill['price']),
                    qty=Decimal(fill['qty']),
                    commission=Decimal(fill['commission']),
                    commission_asset=fill['commissionAsset']
                )
                for fill in result.get('fills', [])
            ]
        )

    def get_simple_earn_flexible_position(self, asset: Optional[str] = None) -> List[FlexiblePosition]:
        """
        Retrieve flexible positions from Simple Earn.
        
        Args:
            asset: Specific asset (optional)
            
        Returns:
            List of FlexiblePosition objects
        """
        params = {}
        if asset:
            params['asset'] = asset
        
        logger.debug(f"Retrieving Simple Earn flexible positions{' for ' + asset if asset else ''}")
        result = self._request('GET', '/sapi/v1/simple-earn/flexible/position', signed=True, params=params)
        
        return [
            FlexiblePosition(
                asset=row['asset'],
                total_amount=Decimal(row.get('totalAmount', '0')),
                tier_annual_percentage_rate=row.get('tierAnnualPercentageRate'),
                latest_annual_percentage_rate=row.get('latestAnnualPercentageRate'),
                yesterday_real_time_rewards=Decimal(row['yesterdayRealTimeRewards']) if row.get('yesterdayRealTimeRewards') else None,
                accumulated_rewards=Decimal(row['accumulatedRewards']) if row.get('accumulatedRewards') else None,
                product_id=row.get('productId')
            )
            for row in result.get('rows', [])
        ]
    
    def redeem_flexible_product(self, product_id: str, amount: str) -> RedeemResponse:
        """
        Redeem (withdraw) funds from a Simple Earn flexible product.
        
        Args:
            product_id: Flexible product ID
            amount: Amount to redeem
            
        Returns:
            RedeemResponse object with operation result
        """
        params = {
            'productId': product_id,
            'amount': amount,
            'destAccount': 'SPOT'  # Transfer to spot account
        }
        
        logger.info(f"Redeeming flexible product: productId={product_id}, amount={amount}")
        result = self._request('POST', '/sapi/v1/simple-earn/flexible/redeem', signed=True, params=params)
        
        return RedeemResponse(
            redeem_id=result.get('redeemId'),
            success=result.get('success', True)
        )
    
    def get_flexible_product_position_by_asset(self, asset: str) -> Optional[FlexiblePosition]:
        """
        Retrieve flexible position for a specific asset.
        
        Args:
            asset: Asset to search for (e.g., "USDC")
            
        Returns:
            FlexiblePosition object if found, None otherwise
        """
        positions = self.get_simple_earn_flexible_position(asset=asset)
        
        for position in positions:
            if position.asset == asset:
                logger.debug(f"Position flexible {asset}: {position.total_amount}")
                
                if position.total_amount > 0:
                    return position
        
        logger.debug(f"No flexible position found for {asset}")
        return None

    def get_klines(self, symbol: str, interval: str, limit: int = 3) -> List[Kline]:
        """
        Retrieve historical klines/candlestick data.
        
        Args:
            symbol: Trading pair (e.g., "ETHUSDC")
            interval: Kline interval (e.g., "1d", "1w", "2w")
            limit: Number of klines to retrieve (default: 3 for last 3 periods)
            
        Returns:
            List of Kline objects containing parsed candlestick data
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        logger.debug(f"Retrieving {limit} klines for {symbol} (interval={interval})")
        result = self._request('GET', '/api/v3/klines', params=params)
        
        # Parse klines
        parsed_klines = [
            Kline(
                open_time=kline[0],
                open=Decimal(kline[1]),
                high=Decimal(kline[2]),
                low=Decimal(kline[3]),
                close=Decimal(kline[4]),
                volume=Decimal(kline[5]),
                close_time=kline[6]
            )
            for kline in result
        ]
        
        logger.debug(f"Retrieved {len(parsed_klines)} klines")
        return parsed_klines
    
    def get_all_orders(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Retrieve all spot trading orders for a symbol.
        
        Note: This only returns spot market/limit orders, NOT:
        - Buy Crypto With Card transactions
        - Deposits/Withdrawals
        - Converts
        Use get_asset_transaction_history() for complete transaction history.
        
        Args:
            symbol: Trading pair (e.g., "ETHUSDC")
            limit: Maximum number of orders to retrieve (default: 500, max: 1000)
            
        Returns:
            List of all spot trading orders
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        logger.debug(f"Retrieving all orders for {symbol}")
        return self._request('GET', '/api/v3/allOrders', signed=True, params=params)