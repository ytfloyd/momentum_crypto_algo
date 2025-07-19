"""
Utility functions for the Coinbase rebalancing agent.
"""

import logging
import os
import sys
import time
import uuid
import secrets
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta

import requests
from coinbase.rest import RESTClient
from cryptography.hazmat.primitives import serialization
import jwt
from rich.console import Console
from rich.logging import RichHandler

from . import config

# Set up rich console
console = Console()

# Constants
# Using authenticated Coinbase Advanced Trade API - no need for separate URL

# Generate unique client order ID
def generate_client_order_id() -> str:
    """Generate a unique client order ID using UUID."""
    return uuid.uuid4().hex

# Function to build JWT token
def build_jwt(api_key, api_secret, uri=None):
    """Build JWT token for Coinbase API authentication."""
    private_key_bytes = api_secret.encode("utf-8")
    private_key = serialization.load_pem_private_key(private_key_bytes, password=None)

    jwt_payload = {
        'sub': api_key,
        'iss': "cdp",
        'nbf': int(time.time()),  # Not before current time
        'exp': int(time.time()) + 120,  # Expires in 2 minutes
    }

    if uri:
        jwt_payload['uri'] = uri

    jwt_token = jwt.encode(
        jwt_payload,
        private_key,
        algorithm="ES256",
        headers={'kid': api_key, 'nonce': secrets.token_hex()},
    )
    
    return jwt_token

# Fetch product details using authenticated client
def get_product_details(client: RESTClient, product_id: str):
    """Fetch product details from Coinbase Advanced Trade API using authenticated client."""
    try:
        product_info = client.get_product(product_id)
        return product_info
    except Exception as e:
        print(f"Failed to retrieve product details for {product_id}: {e}")
        return None

# Fetch precision for a specific product (e.g., number of decimal places)
def get_precision_for_product(client: RESTClient, product_id: str):
    """Get the precision (decimal places) for a specific trading pair."""
    details = get_product_details(client, product_id)
    if details:
        base_increment = details.base_increment
        precision = abs(Decimal(str(base_increment)).as_tuple().exponent)
        print(f"Precision for {product_id} is {precision} decimal places.")
        return precision
    return None

def round_to_precision(value: Decimal, precision: int) -> Decimal:
    """Round a value to the specified number of decimal places."""
    if precision == 0:
        return value.quantize(Decimal('1'), rounding=ROUND_DOWN)
    else:
        quantizer = Decimal('0.' + '0' * (precision - 1) + '1')
        return value.quantize(quantizer, rounding=ROUND_DOWN)

def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True),
            logging.FileHandler(config.LOG_FILE, mode='a')
        ]
    )
    
    return logging.getLogger(__name__)

def get_client() -> RESTClient:
    """Initialize and return Coinbase API client."""
    if not all([config.API_KEY, config.API_SECRET]):
        raise ValueError("Missing API credentials")
    
    client = RESTClient(
        api_key=config.API_KEY,
        api_secret=config.API_SECRET
    )
    
    return client

# ===== ACCOUNT API CALLS =====

def get_account_details(client: RESTClient, account_uuid: str):
    """Get details for a specific account."""
    try:
        return client.get_account(account_uuid)
    except Exception as e:
        logging.error(f"Failed to get account details for {account_uuid}: {e}")
        return None

# ===== PRODUCT API CALLS =====

def get_all_products(client: RESTClient, limit: int = 1000) -> List[Dict]:
    """Get all available trading products."""
    try:
        response = client.get_products(limit=limit)
        return response.products if hasattr(response, 'products') else []
    except Exception as e:
        logging.error(f"Failed to get products: {e}")
        return []

def get_product_info(client: RESTClient, product_id: str):
    """Get detailed information for a specific product."""
    try:
        return client.get_product(product_id)
    except Exception as e:
        logging.error(f"Failed to get product info for {product_id}: {e}")
        return None

def get_product_book(client: RESTClient, product_id: str, limit: int = 50):
    """Get the order book for a product."""
    try:
        return client.get_product_book(product_id, limit=limit)
    except Exception as e:
        logging.error(f"Failed to get product book for {product_id}: {e}")
        return None

def get_best_bid_ask(client: RESTClient, product_ids: List[str]):
    """Get best bid and ask for multiple products."""
    try:
        return client.get_best_bid_ask(product_ids)
    except Exception as e:
        logging.error(f"Failed to get best bid/ask: {e}")
        return None

# ===== MARKET DATA API CALLS =====

def get_candles_data(client: RESTClient, product_id: str, start: str, end: str, granularity: str):
    """Get historical candle data for a product."""
    try:
        return client.get_candles(product_id, start=start, end=end, granularity=granularity)
    except Exception as e:
        logging.error(f"Failed to get candles for {product_id}: {e}")
        return None

def get_market_trades(client: RESTClient, product_id: str, limit: int = 100):
    """Get recent market trades for a product."""
    try:
        return client.get_market_trades(product_id, limit=limit)
    except Exception as e:
        logging.error(f"Failed to get market trades for {product_id}: {e}")
        return None

# ===== ORDER API CALLS =====

def create_market_buy_order(client: RESTClient, product_id: str, base_size: str):
    """Create a market buy order."""
    try:
        client_order_id = generate_client_order_id()
        return client.market_order_buy(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size
        )
    except Exception as e:
        logging.error(f"Failed to create market buy order for {product_id}: {e}")
        return None

def create_market_sell_order(client: RESTClient, product_id: str, base_size: str):
    """Create a market sell order."""
    try:
        client_order_id = generate_client_order_id()
        return client.market_order_sell(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size
        )
    except Exception as e:
        logging.error(f"Failed to create market sell order for {product_id}: {e}")
        return None

def create_limit_buy_order_gtc(client: RESTClient, product_id: str, base_size: str, limit_price: str):
    """Create a Good-Till-Canceled limit buy order."""
    try:
        client_order_id = generate_client_order_id()
        return client.limit_order_gtc_buy(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size,
            limit_price=limit_price
        )
    except Exception as e:
        logging.error(f"Failed to create limit buy order for {product_id}: {e}")
        return None

def create_limit_sell_order_gtc(client: RESTClient, product_id: str, base_size: str, limit_price: str):
    """Create a Good-Till-Canceled limit sell order."""
    try:
        client_order_id = generate_client_order_id()
        return client.limit_order_gtc_sell(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size,
            limit_price=limit_price
        )
    except Exception as e:
        logging.error(f"Failed to create limit sell order for {product_id}: {e}")
        return None

def create_limit_buy_order_ioc(client: RESTClient, product_id: str, base_size: str, limit_price: str):
    """Create an Immediate-Or-Cancel limit buy order."""
    try:
        client_order_id = generate_client_order_id()
        return client.limit_order_ioc_buy(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size,
            limit_price=limit_price
        )
    except Exception as e:
        logging.error(f"Failed to create IOC limit buy order for {product_id}: {e}")
        return None

def create_limit_sell_order_ioc(client: RESTClient, product_id: str, base_size: str, limit_price: str):
    """Create an Immediate-Or-Cancel limit sell order."""
    try:
        client_order_id = generate_client_order_id()
        return client.limit_order_ioc_sell(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size,
            limit_price=limit_price
        )
    except Exception as e:
        logging.error(f"Failed to create IOC limit sell order for {product_id}: {e}")
        return None

def get_order_details(client: RESTClient, order_id: str):
    """Get details for a specific order."""
    try:
        return client.get_order(order_id)
    except Exception as e:
        logging.error(f"Failed to get order details for {order_id}: {e}")
        return None

def list_orders(client: RESTClient, product_id: Optional[str] = None, order_status: Optional[str] = None, limit: int = 100):
    """List orders with optional filters."""
    try:
        return client.list_orders(product_id=product_id, order_status=order_status, limit=limit)
    except Exception as e:
        logging.error(f"Failed to list orders: {e}")
        return None

def get_fills(client: RESTClient, order_id: Optional[str] = None, product_id: Optional[str] = None, limit: int = 100):
    """Get fills (executed trades) with optional filters."""
    try:
        return client.get_fills(order_id=order_id, product_id=product_id, limit=limit)
    except Exception as e:
        logging.error(f"Failed to get fills: {e}")
        return None

def cancel_orders(client: RESTClient, order_ids: List[str]):
    """Cancel multiple orders."""
    try:
        return client.cancel_orders(order_ids)
    except Exception as e:
        logging.error(f"Failed to cancel orders: {e}")
        return None

# ===== PORTFOLIO MANAGEMENT =====

def get_portfolios(client: RESTClient):
    """Get all portfolios."""
    try:
        return client.get_portfolios()
    except Exception as e:
        logging.error(f"Failed to get portfolios: {e}")
        return None

def get_portfolio(client: RESTClient, portfolio_uuid: str):
    """Get a specific portfolio."""
    try:
        return client.get_portfolio(portfolio_uuid)
    except Exception as e:
        logging.error(f"Failed to get portfolio {portfolio_uuid}: {e}")
        return None

def get_portfolio_breakdown(client: RESTClient, portfolio_uuid: str):
    """Get portfolio breakdown including cash and asset allocations."""
    try:
        return client.get_portfolio_breakdown(portfolio_uuid)
    except Exception as e:
        logging.error(f"Failed to get portfolio breakdown {portfolio_uuid}: {e}")
        return None

# ===== HELPER FUNCTIONS FOR TIME RANGES =====

def get_time_range_for_candles(days_back: int = 3) -> Tuple[str, str]:
    """Get start and end timestamps for candle data (Unix timestamps as strings)."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back + 1)  # Extra day to ensure we have enough data
    
    return str(int(start_time.timestamp())), str(int(end_time.timestamp()))

# ===== ENHANCED TRADE EXECUTION =====

def execute_trade_with_precision(client: RESTClient, product_id: str, side: str, quantity: Decimal, dry_run: bool = False) -> bool:
    """Execute a trade with proper precision handling."""
    try:
        # Get product precision
        product_info = get_product_info(client, product_id)
        if not product_info:
            logging.error(f"Could not get product info for {product_id}")
            return False
        
        # Round quantity to proper precision
        base_increment = Decimal(product_info.base_increment)
        precision = abs(base_increment.as_tuple().exponent)
        rounded_quantity = round_to_precision(quantity, precision)
        
        if dry_run:
            logging.info(f"[DRY RUN] Would execute: {side.upper()} {rounded_quantity} {product_id}")
            return True
        
        # Execute the trade
        if side.lower() == "buy":
            response = create_market_buy_order(client, product_id, str(rounded_quantity))
        else:
            response = create_market_sell_order(client, product_id, str(rounded_quantity))
        
        if response and hasattr(response, 'success') and response.success:
            order_id = response.success_response.order_id if hasattr(response, 'success_response') else "unknown"
            logging.info(f"✅ Trade executed: {side.upper()} {rounded_quantity} {product_id} (Order ID: {order_id})")
            return True
        else:
            error_msg = response.error_response.message if (response and hasattr(response, 'error_response')) else "Unknown error"
            logging.error(f"❌ Trade failed: {error_msg}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Trade execution error for {product_id}: {e}")
        return False

def round_step(value: Decimal, step_size: Decimal) -> Decimal:
    """Round a value down to the nearest valid step size."""
    if step_size == 0:
        return value
    
    return (value // step_size) * step_size

def format_currency(amount: Decimal, currency: str = "USD") -> str:
    """Format a decimal amount as currency."""
    if currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount} {currency}"

def calculate_portfolio_value(positions: Dict[str, Decimal], prices: Dict[str, Decimal]) -> Decimal:
    """Calculate total portfolio value in USD."""
    total_value = Decimal("0")
    
    for symbol, quantity in positions.items():
        if symbol in prices:
            total_value += quantity * prices[symbol]
    
    return total_value

def calculate_current_weights(positions: Dict[str, Decimal], prices: Dict[str, Decimal], cash_buffer: Decimal = Decimal("0.05")) -> Dict[str, Decimal]:
    """
    Calculate current portfolio weights for crypto assets relative to total portfolio value.
    
    Args:
        positions: Current positions including cash
        prices: Current prices for crypto assets
        cash_buffer: Cash buffer percentage (used for consistency with target weights)
    
    Returns:
        Dict mapping crypto symbols to their current weights relative to total portfolio
    """
    # Calculate total portfolio value including cash
    total_value = Decimal("0")
    
    for symbol, quantity in positions.items():
        if symbol == "USD":
            total_value += quantity  # Add cash to total
        elif symbol in prices:
            value = quantity * prices[symbol]
            total_value += value

    if total_value == 0:
        return {}

    # Calculate weights for crypto assets relative to total portfolio (including cash)
    # This is consistent with how target weights are calculated
    current_weights = {}
    for symbol, quantity in positions.items():
        if symbol != "USD" and symbol in prices:
            value = quantity * prices[symbol]
            current_weights[symbol] = value / total_value

    return current_weights

def calculate_rebalance_trades(
    current_weights: Dict[str, Decimal],
    target_weights: Dict[str, Decimal],
    total_value: Decimal,
    prices: Dict[str, Decimal],
    cash_buffer: Decimal = Decimal("0.05")
) -> Dict[str, Tuple[str, Decimal]]:
    """
    Calculate required trades to rebalance portfolio.
    
    Args:
        current_weights: Current portfolio weights (including cash)
        target_weights: Target weights (sum to 1-cash_buffer)
        total_value: Total portfolio value including cash
        prices: Current prices for all assets
        cash_buffer: Percentage to keep as cash (e.g., 0.05 for 5%)
    
    Returns:
        Dict mapping symbol to (side, quantity) tuples
    """
    trades = {}
    
    # Calculate investable portion (exclude cash buffer)
    investable_value = total_value * (Decimal("1") - cash_buffer)
    
    # FIRST: Handle positions that are NOT in target weights (sell them completely)
    for symbol, current_weight in current_weights.items():
        if symbol not in target_weights and symbol in prices:
            # This position should be completely sold
            trade_value = current_weight * investable_value
            
            if trade_value >= config.MIN_NOTIONAL:
                price = prices[symbol]
                quantity = trade_value / price
                trades[symbol] = ("sell", quantity)
                logging.info(f"📤 Liquidating position not in target: {symbol} ({float(current_weight)*100:.2f}%)")
    
    # SECOND: Handle positions that ARE in target weights (rebalance them)
    for symbol, target_weight in target_weights.items():
        if symbol not in prices:
            continue
            
        current_weight = current_weights.get(symbol, Decimal("0"))
        weight_diff = target_weight - current_weight
        
        # Check if rebalancing is needed
        if abs(weight_diff) > config.TOLERANCE:
            # Calculate USD value to trade based on INVESTABLE portion, not total NAV
            trade_value = weight_diff * investable_value
            
            # Calculate quantity
            price = prices[symbol]
            quantity = abs(trade_value / price)
            
            # Check minimum notional
            if abs(trade_value) >= config.MIN_NOTIONAL:
                side = "buy" if weight_diff > 0 else "sell"
                trades[symbol] = (side, quantity)
    
    return trades

def fetch_nav_and_positions(client: RESTClient) -> Tuple[Dict[str, Decimal], Dict[str, Decimal], Decimal]:
    """
    Fetch current positions and prices from Coinbase.
    
    Returns:
        Tuple of (positions, prices, total_nav)
    """
    positions = {}
    prices = {}
    
    try:
        # If portfolio ID is specified, get portfolio-specific positions
        if config.PORTFOLIO_ID:
            logging.info(f"Using portfolio ID: {config.PORTFOLIO_ID}")
            
            # Get accounts, but focus on the specified portfolio
            accounts = client.get_accounts()
            
            # Get portfolio breakdown to see USDC cash balances
            portfolio_breakdown = client.get_portfolio_breakdown(config.PORTFOLIO_ID)
            
            # Process breakdown which includes cash balances
            if hasattr(portfolio_breakdown, 'breakdown'):
                for item in portfolio_breakdown.breakdown:
                    if hasattr(item, 'asset') and hasattr(item, 'value'):
                        asset = item.asset
                        value = Decimal(item.value.get('value', '0'))
                        
                        if asset == 'USDC' and value > 0:
                            # This is cash
                            positions["USD"] = value
                        elif asset != 'USDC' and value > 0:
                            # This is a crypto asset
                            symbol = f"{asset}-USDC"
                            # Get the actual quantity from accounts
                            for account in accounts.accounts:
                                if account.currency == asset:
                                    balance = Decimal(account.available_balance.get("value", "0"))
                                    if balance > 0:
                                        positions[symbol] = balance
                                    break
            else:
                logging.warning("Portfolio breakdown not available, falling back to account method")
                # Fallback to account method if portfolio breakdown fails
                for account in accounts.accounts:
                    currency = account.currency
                    balance = Decimal(account.available_balance.get("value", "0"))
                    
                    if balance > 0:
                        if currency == "USDC":
                            positions["USD"] = balance
                        elif currency != "USD":
                            symbol = f"{currency}-USDC"
                            positions[symbol] = balance
        else:
            # Original method: Get all accounts (no portfolio filtering)
            accounts = client.get_accounts()
            
            for account in accounts.accounts:
                currency = account.currency
                balance = Decimal(account.available_balance.get("value", "0"))
                
                if balance > 0:
                    # For crypto assets, we need to get the trading pair
                    if currency != "USD" and currency != "USDC":
                        symbol = f"{currency}-USDC"
                        positions[symbol] = balance
                    else:
                        # USD or USDC balance
                        positions["USD"] = balance
        
        # Get current prices for all positions (batch request for better performance)
        symbols_to_price = [symbol for symbol in positions if symbol != "USD"]
        
        if symbols_to_price:
            try:
                # Use batch pricing - get all products at once
                all_products = client.get_products(limit=500)["products"]
                product_prices = {p["product_id"]: Decimal(p["price"]) for p in all_products 
                                if p["product_id"] in symbols_to_price and p["price"]}
                
                # Use batch results where available, fall back to individual calls if needed
                for symbol in symbols_to_price:
                    if symbol in product_prices:
                        prices[symbol] = product_prices[symbol]
                    else:
                        try:
                            ticker = client.get_product(symbol)
                            prices[symbol] = Decimal(ticker.price)
                        except Exception as e:
                            logging.warning(f"Failed to get price for {symbol}: {e}")
                            continue
            except Exception as e:
                logging.warning(f"Batch pricing failed, falling back to individual calls: {e}")
                # Fallback to individual calls
                for symbol in symbols_to_price:
                    try:
                        ticker = client.get_product(symbol)
                        prices[symbol] = Decimal(ticker.price)
                    except Exception as e:
                        logging.warning(f"Failed to get price for {symbol}: {e}")
                        continue
        
        # Calculate total NAV
        total_nav = calculate_portfolio_value(positions, prices)
        if "USD" in positions:
            total_nav += positions["USD"]
        
        return positions, prices, total_nav
        
    except Exception as e:
        logging.error(f"Failed to fetch portfolio data: {e}")
        raise

def validate_trade_params(symbol: str, side: str, quantity: Decimal, price: Decimal) -> bool:
    """Validate trade parameters before execution."""
    if quantity <= 0:
        return False
    
    if price <= 0:
        return False
    
    # Check minimum notional
    notional = quantity * price
    if notional < config.MIN_NOTIONAL:
        return False
    
    return True

def log_portfolio_summary(positions: Dict[str, Decimal], prices: Dict[str, Decimal], total_nav: Decimal):
    """Log a summary of the current portfolio."""
    logger = logging.getLogger(__name__)
    
    logger.info(f"Portfolio Summary - Total NAV: {format_currency(total_nav)}")
    logger.info("Current Holdings:")
    
    for symbol, quantity in positions.items():
        if symbol == "USD":
            logger.info(f"  {symbol}: {format_currency(quantity)}")
        else:
            price = prices.get(symbol, Decimal("0"))
            value = quantity * price
            weight = (value / total_nav) * 100 if total_nav > 0 else 0
            logger.info(f"  {symbol}: {quantity:.8f} @ {format_currency(price)} = {format_currency(value)} ({weight:.2f}%)")

if __name__ == "__main__":
    # Test configuration
    logger = setup_logging()
    logger.info("Utils module loaded successfully") 