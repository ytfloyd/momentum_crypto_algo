"""
Coinbase Advanced Trade API client wrapper for systematic trading.

This module provides a wrapper around the Coinbase Advanced Python SDK
with additional functionality for systematic trading strategies.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from coinbase.rest import RESTClient
from coinbase.websocket import WSClient


class CoinbaseAdvancedClient:
    """
    Wrapper for Coinbase Advanced Trade API with trading-specific functionality.
    
    Provides methods for order management, market data, and account information
    with error handling and rate limiting appropriate for systematic trading.
    """
    
    def __init__(self, 
                 api_key: str = None,
                 api_secret: str = None,
                 passphrase: str = None,
                 sandbox: bool = False):
        """
        Initialize Coinbase Advanced client.
        
        Args:
            api_key: Coinbase API key (defaults to env var)
            api_secret: Coinbase API secret (defaults to env var)
            passphrase: Coinbase passphrase (defaults to env var)
            sandbox: Whether to use sandbox environment
        """
        self.api_key = api_key or os.getenv('COINBASE_API_KEY')
        self.api_secret = api_secret or os.getenv('COINBASE_API_SECRET')
        self.passphrase = passphrase or os.getenv('COINBASE_PASSPHRASE')
        self.sandbox = sandbox
        
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise ValueError("Missing required Coinbase API credentials")
        
        # Initialize REST client
        self.client = RESTClient(
            api_key=self.api_key,
            api_secret=self.api_secret,
            passphrase=self.passphrase,
            sandbox=sandbox
        )
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Cache for product information
        self.product_cache = {}
        self.cache_expiry = 300  # 5 minutes
        self.last_cache_update = 0
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def _handle_api_call(self, func, *args, **kwargs):
        """Handle API calls with rate limiting and error handling."""
        self._rate_limit()
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            raise
    
    def get_accounts(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            Dictionary with account information
        """
        return self._handle_api_call(self.client.get_accounts)
    
    def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get product information with caching.
        
        Args:
            product_id: Product ID (e.g., "BTC-USD")
            
        Returns:
            Product information dictionary
        """
        current_time = time.time()
        
        # Check cache
        if (product_id in self.product_cache and 
            current_time - self.last_cache_update < self.cache_expiry):
            return self.product_cache[product_id]
        
        # Fetch from API
        product = self._handle_api_call(self.client.get_product, product_id)
        
        # Update cache
        self.product_cache[product_id] = product
        self.last_cache_update = current_time
        
        return product
    
    def get_products(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get all products.
        
        Args:
            limit: Maximum number of products to return
            
        Returns:
            Dictionary with products list
        """
        return self._handle_api_call(self.client.get_products, limit=limit)
    
    def get_candles(self, 
                   product_id: str,
                   start: str = None,
                   end: str = None,
                   granularity: str = "ONE_DAY",
                   limit: int = 300) -> Dict[str, Any]:
        """
        Get historical candles for a product.
        
        Args:
            product_id: Product ID
            start: Start time (ISO 8601 or Unix timestamp)
            end: End time (ISO 8601 or Unix timestamp)
            granularity: Candle granularity
            limit: Maximum number of candles
            
        Returns:
            Dictionary with candles data
        """
        return self._handle_api_call(
            self.client.get_candles,
            product_id=product_id,
            start=start,
            end=end,
            granularity=granularity,
            limit=limit
        )
    
    def create_order(self, 
                    product_id: str,
                    side: str,
                    order_type: str,
                    size: str = None,
                    funds: str = None,
                    price: str = None,
                    stop_price: str = None,
                    time_in_force: str = "GTC",
                    client_order_id: str = None) -> Dict[str, Any]:
        """
        Create a new order.
        
        Args:
            product_id: Product ID
            side: Order side ("buy" or "sell")
            order_type: Order type ("market", "limit", "stop", "stop_limit")
            size: Order size in base currency
            funds: Order size in quote currency (for market orders)
            price: Limit price
            stop_price: Stop price for stop orders
            time_in_force: Time in force ("GTC", "IOC", "FOK")
            client_order_id: Client-specified order ID
            
        Returns:
            Order creation response
        """
        order_data = {
            "product_id": product_id,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force
        }
        
        if size:
            order_data["size"] = size
        if funds:
            order_data["funds"] = funds
        if price:
            order_data["price"] = price
        if stop_price:
            order_data["stop_price"] = stop_price
        if client_order_id:
            order_data["client_oid"] = client_order_id
        
        return self._handle_api_call(self.client.create_order, **order_data)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        return self._handle_api_call(self.client.cancel_order, order_id)
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get order details.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order details
        """
        return self._handle_api_call(self.client.get_order, order_id)
    
    def get_orders(self, 
                  product_id: str = None,
                  status: str = None,
                  limit: int = 100) -> Dict[str, Any]:
        """
        Get orders with optional filtering.
        
        Args:
            product_id: Filter by product ID
            status: Filter by order status
            limit: Maximum number of orders
            
        Returns:
            Orders list
        """
        params = {"limit": limit}
        if product_id:
            params["product_id"] = product_id
        if status:
            params["status"] = status
            
        return self._handle_api_call(self.client.get_orders, **params)
    
    def get_fills(self, 
                 product_id: str = None,
                 order_id: str = None,
                 limit: int = 100) -> Dict[str, Any]:
        """
        Get fills (executed trades).
        
        Args:
            product_id: Filter by product ID
            order_id: Filter by order ID
            limit: Maximum number of fills
            
        Returns:
            Fills list
        """
        params = {"limit": limit}
        if product_id:
            params["product_id"] = product_id
        if order_id:
            params["order_id"] = order_id
            
        return self._handle_api_call(self.client.get_fills, **params)
    
    def get_portfolio_breakdown(self, portfolio_uuid: str) -> Dict[str, Any]:
        """
        Get portfolio breakdown.
        
        Args:
            portfolio_uuid: Portfolio UUID
            
        Returns:
            Portfolio breakdown
        """
        return self._handle_api_call(
            self.client.get_portfolio_breakdown, 
            portfolio_uuid=portfolio_uuid
        )
    
    def get_portfolios(self) -> Dict[str, Any]:
        """
        Get all portfolios.
        
        Returns:
            Portfolios list
        """
        return self._handle_api_call(self.client.get_portfolios)
    
    def create_market_order(self, 
                           product_id: str,
                           side: str,
                           size: str = None,
                           funds: str = None,
                           client_order_id: str = None) -> Dict[str, Any]:
        """
        Create a market order (convenience method).
        
        Args:
            product_id: Product ID
            side: Order side ("buy" or "sell")
            size: Order size in base currency
            funds: Order size in quote currency
            client_order_id: Client-specified order ID
            
        Returns:
            Order creation response
        """
        return self.create_order(
            product_id=product_id,
            side=side,
            order_type="market",
            size=size,
            funds=funds,
            client_order_id=client_order_id
        )
    
    def create_limit_order(self, 
                          product_id: str,
                          side: str,
                          size: str,
                          price: str,
                          time_in_force: str = "GTC",
                          client_order_id: str = None) -> Dict[str, Any]:
        """
        Create a limit order (convenience method).
        
        Args:
            product_id: Product ID
            side: Order side ("buy" or "sell")
            size: Order size in base currency
            price: Limit price
            time_in_force: Time in force
            client_order_id: Client-specified order ID
            
        Returns:
            Order creation response
        """
        return self.create_order(
            product_id=product_id,
            side=side,
            order_type="limit",
            size=size,
            price=price,
            time_in_force=time_in_force,
            client_order_id=client_order_id
        )
    
    def create_stop_order(self, 
                         product_id: str,
                         side: str,
                         size: str,
                         stop_price: str,
                         client_order_id: str = None) -> Dict[str, Any]:
        """
        Create a stop order (convenience method).
        
        Args:
            product_id: Product ID
            side: Order side ("buy" or "sell")
            size: Order size in base currency
            stop_price: Stop price
            client_order_id: Client-specified order ID
            
        Returns:
            Order creation response
        """
        return self.create_order(
            product_id=product_id,
            side=side,
            order_type="stop",
            size=size,
            stop_price=stop_price,
            client_order_id=client_order_id
        )
    
    def get_current_price(self, product_id: str) -> Decimal:
        """
        Get current market price for a product.
        
        Args:
            product_id: Product ID
            
        Returns:
            Current price as Decimal
        """
        product = self.get_product(product_id)
        return Decimal(product.price)
    
    def get_account_balance(self, currency: str) -> Decimal:
        """
        Get account balance for a specific currency.
        
        Args:
            currency: Currency code (e.g., "USD", "BTC")
            
        Returns:
            Balance as Decimal
        """
        accounts = self.get_accounts()
        
        for account in accounts.get("accounts", []):
            if account.get("currency") == currency:
                return Decimal(account.get("balance", "0"))
        
        return Decimal("0")
    
    def is_market_open(self, product_id: str) -> bool:
        """
        Check if market is open for a product.
        
        Args:
            product_id: Product ID
            
        Returns:
            True if market is open
        """
        try:
            product = self.get_product(product_id)
            return product.get("status") == "online"
        except:
            return False 