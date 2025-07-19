"""
Main runner module for the Coinbase rebalancing agent.
"""

import logging
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Tuple

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from rich.console import Console
from rich.table import Table

from . import config
from .selector import build_target_weights
from .utils import (
    calculate_current_weights,
    calculate_rebalance_trades,
    fetch_nav_and_positions,
    format_currency,
    get_client,
    log_portfolio_summary,
    setup_logging,
    validate_trade_params,
)

# Set up rich console and logging
console = Console()
logger = setup_logging()

def execute_trade(client, symbol: str, side: str, quantity: float, dry_run: bool = True) -> bool:
    """Execute a trade on Coinbase."""
    try:
        if dry_run:
            logger.info(f"[DRY RUN] Would execute: {side.upper()} {quantity:.8f} {symbol}")
            return True
        
        # Import the utility functions
        from .utils import generate_client_order_id, get_precision_for_product, round_to_precision
        
        # Generate unique client order ID
        client_order_id = generate_client_order_id()
        
        # Get precision for the product and round quantity appropriately
        precision = get_precision_for_product(client, symbol)
        if precision is not None:
            quantity_decimal = Decimal(str(quantity))
            quantity_decimal = round_to_precision(quantity_decimal, precision)
            quantity = float(quantity_decimal)
        
        # Execute the actual trade
        if side == "buy":
            response = client.market_order_buy(
                product_id=symbol,
                base_size=str(quantity),
                client_order_id=client_order_id
            )
        else:
            response = client.market_order_sell(
                product_id=symbol,
                base_size=str(quantity),
                client_order_id=client_order_id
            )
        
        # Handle response (response is a CreateOrderResponse object)
        if response:
            # Access success as an object attribute, not dictionary key
            if hasattr(response, 'success') and response.success == True:
                # Successful trade - extract order ID from success_response
                if hasattr(response, 'success_response') and response.success_response:
                    order_id = response.success_response.order_id if hasattr(response.success_response, 'order_id') else 'unknown'
                else:
                    order_id = 'unknown'
                
                logger.info(f"✅ Trade executed: {side.upper()} {quantity:.8f} {symbol} (Order ID: {order_id})")
                return True
            elif hasattr(response, 'success') and response.success == False:
                # Failed trade - extract error message from error_response
                if hasattr(response, 'error_response') and response.error_response:
                    error_msg = response.error_response.message if hasattr(response.error_response, 'message') else str(response.error_response)
                else:
                    error_msg = "Unknown error"
                
                logger.error(f"❌ Trade failed: {error_msg}")
                return False
            else:
                # Unexpected response format
                logger.error(f"❌ Trade failed: Invalid response format - {response}")
                return False
        else:
            # No response
            logger.error(f"❌ Trade failed: No response received")
            return False
            
    except Exception as e:
        logger.error(f"❌ Trade execution error for {symbol}: {e}")
        return False

def rebalance():
    """Main rebalancing function."""
    logger.info("🔄 Starting rebalancing cycle...")
    
    try:
        # Load YAML configuration
        with open("config.yml", "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)
        
        # Validate configuration
        config.validate_config()
        
        # Initialize client
        client = get_client()
        
        # Build dynamic target weights
        target_weights = build_target_weights(
            client, 
            top_n=yaml_config.get("top_n", 25),
            cash_buffer=Decimal(str(yaml_config.get("cash_buffer", 0.05)))
        )
        
        if not target_weights:
            logger.warning("⚠️ No target weights generated, skipping rebalancing")
            return
        
        logger.info(f"📊 Generated target weights for {len(target_weights)} assets")
        
        # Log detailed target weights
        logger.info("🎯 Target Weights:")
        for symbol, weight in sorted(target_weights.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {symbol}: {float(weight)*100:.2f}%")
        
        # Fetch current portfolio data
        positions, prices, total_nav = fetch_nav_and_positions(client)
        
        if total_nav == 0:
            logger.warning("⚠️ No assets found in portfolio")
            return
        
        # Log portfolio summary
        log_portfolio_summary(positions, prices, total_nav)
        
        # Calculate current weights
        current_weights = calculate_current_weights(positions, prices, cash_buffer=Decimal(str(yaml_config.get("cash_buffer", 0.05))))
        
        # Calculate required trades
        trades = calculate_rebalance_trades(
            current_weights=current_weights,
            target_weights=target_weights,
            total_value=total_nav,
            prices=prices,
            cash_buffer=Decimal(str(yaml_config.get("cash_buffer", 0.05)))
        )
        
        if not trades:
            logger.info("✅ Portfolio is already balanced within tolerance")
            return
        
        # Display rebalancing summary
        display_rebalancing_summary(current_weights, target_weights, trades, prices, total_nav)
        
        # Log detailed rebalancing summary to file
        log_rebalancing_details(current_weights, target_weights, trades, prices, total_nav)
        
        # Separate trades into sells and buys
        sell_trades = {symbol: (side, qty) for symbol, (side, qty) in trades.items() if side == "sell"}
        buy_trades = {symbol: (side, qty) for symbol, (side, qty) in trades.items() if side == "buy"}
        
        successful_trades = 0
        failed_trades = 0
        
        # Execute SELL orders first to generate cash
        if sell_trades:
            logger.info(f"🔄 Executing {len(sell_trades)} SELL orders first...")
            for symbol, (side, quantity) in sell_trades.items():
                price = prices[symbol]
                
                # Validate trade parameters
                if not validate_trade_params(symbol, side, quantity, price):
                    logger.warning(f"⚠️ Invalid trade parameters for {symbol}, skipping")
                    failed_trades += 1
                    continue
                
                # Execute the trade
                if execute_trade(client, symbol, side, float(quantity), dry_run=config.DRY_RUN):
                    successful_trades += 1
                else:
                    failed_trades += 1
            
            # Wait for SELL orders to settle before buying
            if not config.DRY_RUN and successful_trades > 0:
                logger.info("⏳ Waiting for SELL orders to settle...")
                time.sleep(2)  # Allow time for settlement
        
        # Execute BUY orders after sells have settled
        if buy_trades:
            logger.info(f"🔄 Executing {len(buy_trades)} BUY orders...")
            for symbol, (side, quantity) in buy_trades.items():
                price = prices[symbol]
                
                # Validate trade parameters
                if not validate_trade_params(symbol, side, quantity, price):
                    logger.warning(f"⚠️ Invalid trade parameters for {symbol}, skipping")
                    failed_trades += 1
                    continue
                
                # Execute the trade
                if execute_trade(client, symbol, side, float(quantity), dry_run=config.DRY_RUN):
                    successful_trades += 1
                else:
                    failed_trades += 1
        
        # Log results
        logger.info(f"🎯 Rebalancing complete: {successful_trades} successful, {failed_trades} failed")
        
    except Exception as e:
        logger.error(f"❌ Rebalancing failed: {e}")
        raise

def display_rebalancing_summary(
    current_weights: Dict[str, Decimal],
    target_weights: Dict[str, Decimal],
    trades: Dict[str, Tuple[str, Decimal]],
    prices: Dict[str, Decimal],
    total_nav: Decimal
):
    """Display a summary table of the rebalancing plan."""
    
    table = Table(title="Rebalancing Summary")
    table.add_column("Asset", style="cyan")
    table.add_column("Current Weight", justify="right")
    table.add_column("Target Weight", justify="right")
    table.add_column("Difference", justify="right")
    table.add_column("Action", style="green")
    table.add_column("Quantity", justify="right")
    table.add_column("Value", justify="right")
    
    for symbol in target_weights:
        current_weight = current_weights.get(symbol, Decimal("0"))
        target_weight = target_weights[symbol]
        difference = target_weight - current_weight
        
        current_pct = f"{float(current_weight) * 100:.2f}%"
        target_pct = f"{float(target_weight) * 100:.2f}%"
        diff_pct = f"{float(difference) * 100:+.2f}%"
        
        if symbol in trades:
            side, quantity = trades[symbol]
            price = prices[symbol]
            value = quantity * price
            
            action = f"{side.upper()}"
            quantity_str = f"{float(quantity):.8f}"
            value_str = format_currency(value)
            
            # Color code the difference
            if difference > 0:
                diff_style = "green"
            else:
                diff_style = "red"
            
            table.add_row(
                symbol,
                current_pct,
                target_pct,
                f"[{diff_style}]{diff_pct}[/{diff_style}]",
                action,
                quantity_str,
                value_str
            )
        else:
            table.add_row(
                symbol,
                current_pct,
                target_pct,
                f"[dim]{diff_pct}[/dim]",
                "[dim]No action[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]"
            )
    
    console.print(table)

def log_rebalancing_details(
    current_weights: Dict[str, Decimal],
    target_weights: Dict[str, Decimal],
    trades: Dict[str, Tuple[str, Decimal]],
    prices: Dict[str, Decimal],
    total_nav: Decimal
):
    """Log detailed rebalancing information to the log file."""
    logger.info("=" * 80)
    logger.info("📋 DETAILED REBALANCING SUMMARY")
    logger.info("=" * 80)
    
    logger.info(f"Total Portfolio Value: {format_currency(total_nav)}")
    logger.info(f"Number of trades to execute: {len(trades)}")
    
    # Log each asset's details
    for symbol in sorted(target_weights.keys()):
        current_weight = current_weights.get(symbol, Decimal("0"))
        target_weight = target_weights[symbol]
        difference = target_weight - current_weight
        
        current_pct = float(current_weight) * 100
        target_pct = float(target_weight) * 100
        diff_pct = float(difference) * 100
        
        logger.info(f"\n{symbol}:")
        logger.info(f"  Current Weight: {current_pct:.2f}%")
        logger.info(f"  Target Weight:  {target_pct:.2f}%")
        logger.info(f"  Difference:     {diff_pct:+.2f}%")
        
        if symbol in trades:
            side, quantity = trades[symbol]
            price = prices[symbol]
            value = quantity * price
            
            logger.info(f"  Action: {side.upper()} {float(quantity):.8f} {symbol}")
            logger.info(f"  Price:  {format_currency(price)}")
            logger.info(f"  Value:  {format_currency(value)}")
        else:
            logger.info(f"  Action: No trade needed")
    
    logger.info("=" * 80)

def start_scheduler():
    """Start the rebalancing scheduler."""
    # Load YAML configuration
    with open("config.yml", "r", encoding="utf-8") as f:
        yaml_config = yaml.safe_load(f)
    
    rebalance_interval = yaml_config.get("rebalance_interval_minutes", 60)
    
    scheduler = BlockingScheduler()
    
    # Add rebalancing job
    scheduler.add_job(
        func=rebalance,
        trigger=IntervalTrigger(minutes=rebalance_interval),
        id='rebalance_job',
        name='Portfolio Rebalancing',
        replace_existing=True
    )
    
    logger.info(f"🚀 Rebalancing agent started")
    logger.info(f"   Interval: {rebalance_interval} minutes")
    logger.info(f"   Dry run: {config.DRY_RUN}")
    logger.info(f"   Next run: {datetime.now() + timedelta(minutes=rebalance_interval)}")
    
    # Run initial rebalance
    logger.info("🔄 Running initial rebalance...")
    rebalance()
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("🛑 Rebalancing agent stopped by user")
        scheduler.shutdown()
    except Exception as e:
        logger.error(f"❌ Scheduler error: {e}")
        scheduler.shutdown()
        raise

def parse_arguments():
    parser = argparse.ArgumentParser(description='Run the trading strategy.')
    parser.add_argument('--mode', choices=['backtest', 'paper', 'live'], required=True, help='Mode to run the strategy in')
    return parser.parse_args()

def main():
    args = parse_arguments()
    logger.info(f"Running strategy in {args.mode} mode")
    # Add logic to handle different modes
    if args.mode == 'backtest':
        logger.info("Backtest mode selected")
        # Implement backtest logic
    elif args.mode == 'paper':
        logger.info("Paper trading mode selected")
        # Implement paper trading logic
    elif args.mode == 'live':
        logger.info("Live trading mode selected")
        # Implement live trading logic
    else:
        logger.error("Invalid mode selected")
        sys.exit(1)

    # Environment variables are loaded in config.py
    
    try:
        if args.once:
            logger.info("🔄 Running single rebalancing cycle...")
            rebalance()
        else:
            start_scheduler()
            
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 