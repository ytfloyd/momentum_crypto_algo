"""
Utility functions for the Coinbase rebalancing agent.
"""

import logging
import os
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Optional, Tuple

from coinbase.rest import RESTClient
from rich.console import Console
from rich.logging import RichHandler

from . import config

# Set up rich console
console = Console()

def setup_logging():
    """Set up logging with rich formatting."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True),
            logging.FileHandler(config.LOG_FILE) if config.LOG_FILE else logging.NullHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def get_client() -> RESTClient:
    """Initialize and return Coinbase API client."""
    if not all([config.API_KEY, config.API_SECRET, config.API_PASSPHRASE]):
        raise ValueError("Missing API credentials")
    
    client = RESTClient(
        api_key=config.API_KEY,
        api_secret=config.API_SECRET,
        api_passphrase=config.API_PASSPHRASE,
        base_url=config.API_URL
    )
    
    return client

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
        return f"{amount:,.8f} {currency}"

def calculate_portfolio_value(positions: Dict[str, Decimal], prices: Dict[str, Decimal]) -> Decimal:
    """Calculate total portfolio value in USD."""
    total_value = Decimal("0")
    
    for symbol, quantity in positions.items():
        if symbol in prices:
            total_value += quantity * prices[symbol]
    
    return total_value

def calculate_current_weights(positions: Dict[str, Decimal], prices: Dict[str, Decimal]) -> Dict[str, Decimal]:
    """Calculate current portfolio weights."""
    total_value = calculate_portfolio_value(positions, prices)
    
    if total_value == 0:
        return {}
    
    current_weights = {}
    for symbol, quantity in positions.items():
        if symbol in prices:
            value = quantity * prices[symbol]
            current_weights[symbol] = value / total_value
    
    return current_weights

def calculate_rebalance_trades(
    current_weights: Dict[str, Decimal],
    target_weights: Dict[str, Decimal],
    total_value: Decimal,
    prices: Dict[str, Decimal]
) -> Dict[str, Tuple[str, Decimal]]:
    """
    Calculate required trades to rebalance portfolio.
    
    Returns:
        Dict mapping symbol to (side, quantity) tuples
    """
    trades = {}
    
    for symbol, target_weight in target_weights.items():
        if symbol not in prices:
            continue
            
        current_weight = current_weights.get(symbol, Decimal("0"))
        weight_diff = target_weight - current_weight
        
        # Check if rebalancing is needed
        if abs(weight_diff) > config.TOLERANCE:
            # Calculate USD value to trade
            trade_value = weight_diff * total_value
            
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
        # Get accounts
        accounts = client.get_accounts()
        
        for account in accounts.get("accounts", []):
            currency = account.get("currency", {}).get("code", "")
            balance = Decimal(account.get("available_balance", {}).get("value", "0"))
            
            if balance > 0:
                # For crypto assets, we need to get the trading pair
                if currency != "USD":
                    symbol = f"{currency}-USD"
                    positions[symbol] = balance
                else:
                    # USD balance
                    positions["USD"] = balance
        
        # Get current prices for all positions
        for symbol in positions:
            if symbol != "USD":
                try:
                    ticker = client.get_product_ticker(symbol)
                    price = Decimal(ticker.get("price", "0"))
                    prices[symbol] = price
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