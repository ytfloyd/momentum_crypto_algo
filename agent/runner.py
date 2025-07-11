"""
Main runner module for the Coinbase rebalancing agent.
"""

import logging
import sys
import time
from datetime import datetime, timedelta
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
        
        # Execute the actual trade
        if side == "buy":
            response = client.market_order_buy(
                product_id=symbol,
                base_size=str(quantity)
            )
        else:
            response = client.market_order_sell(
                product_id=symbol,
                base_size=str(quantity)
            )
        
        if response.get("success", False):
            order_id = response.get("order_id", "")
            logger.info(f"✅ Trade executed: {side.upper()} {quantity:.8f} {symbol} (Order ID: {order_id})")
            return True
        else:
            logger.error(f"❌ Trade failed: {response}")
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
            cash_buffer=yaml_config.get("cash_buffer", 0.05)
        )
        
        if not target_weights:
            logger.warning("⚠️ No target weights generated, skipping rebalancing")
            return
        
        logger.info(f"📊 Generated target weights for {len(target_weights)} assets")
        
        # Fetch current portfolio data
        positions, prices, total_nav = fetch_nav_and_positions(client)
        
        if total_nav == 0:
            logger.warning("⚠️ No assets found in portfolio")
            return
        
        # Log portfolio summary
        log_portfolio_summary(positions, prices, total_nav)
        
        # Calculate current weights
        current_weights = calculate_current_weights(positions, prices)
        
        # Calculate required trades
        trades = calculate_rebalance_trades(
            current_weights=current_weights,
            target_weights=target_weights,
            total_value=total_nav,
            prices=prices
        )
        
        if not trades:
            logger.info("✅ Portfolio is already balanced within tolerance")
            return
        
        # Display rebalancing summary
        display_rebalancing_summary(current_weights, target_weights, trades, prices, total_nav)
        
        # Execute trades
        successful_trades = 0
        failed_trades = 0
        
        for symbol, (side, quantity) in trades.items():
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
    current_weights: Dict[str, float],
    target_weights: Dict[str, float],
    trades: Dict[str, Tuple[str, float]],
    prices: Dict[str, float],
    total_nav: float
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
        current_weight = current_weights.get(symbol, 0)
        target_weight = target_weights[symbol]
        difference = target_weight - current_weight
        
        current_pct = f"{current_weight * 100:.2f}%"
        target_pct = f"{target_weight * 100:.2f}%"
        diff_pct = f"{difference * 100:+.2f}%"
        
        if symbol in trades:
            side, quantity = trades[symbol]
            price = prices[symbol]
            value = quantity * price
            
            action = f"{side.upper()}"
            quantity_str = f"{quantity:.8f}"
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

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Coinbase Portfolio Rebalancing Agent")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run rebalancing once and exit (don't start scheduler)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual trades)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    args = parser.parse_args()
    
    # Override config with command line arguments
    if args.dry_run:
        config.DRY_RUN = True
    
    try:
        if args.validate:
            config.validate_config()
            logger.info("✅ Configuration is valid")
            return
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
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