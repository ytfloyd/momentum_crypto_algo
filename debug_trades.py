#!/usr/bin/env python3

import os
import sys
from decimal import Decimal
from agent.utils import get_client, fetch_nav_and_positions, calculate_current_weights, calculate_rebalance_trades
from agent.selector import build_target_weights
from agent.config import DRY_RUN

def debug_trades():
    """Debug the trade calculation and execution process."""
    print("🔍 Debugging trade calculation and execution...")
    
    try:
        # Initialize client
        client = get_client()
        print("✅ Client initialized")
        
        # Build target weights
        target_weights = build_target_weights(client, top_n=25, cash_buffer=Decimal("0.05"))
        print(f"✅ Generated {len(target_weights)} target weights")
        
        # Show top 5 target weights
        print("\n🎯 Top 5 Target Weights:")
        for symbol, weight in sorted(target_weights.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {symbol}: {float(weight)*100:.2f}%")
        
        # Fetch current portfolio data
        positions, prices, total_nav = fetch_nav_and_positions(client)
        print(f"\n💰 Portfolio Summary:")
        print(f"  Total NAV: ${total_nav:,.2f}")
        print(f"  Number of positions: {len(positions)}")
        print(f"  Number of prices: {len(prices)}")
        
        if total_nav == 0:
            print("❌ No assets found in portfolio")
            return
        
        # Calculate current weights
        current_weights = calculate_current_weights(positions, prices, cash_buffer=Decimal("0.05"))
        print(f"\n📊 Current weights calculated for {len(current_weights)} assets")
        
        # Show current weights for assets in target weights
        print("\n📈 Current vs Target Weights (for top 5 targets):")
        for symbol, target_weight in sorted(target_weights.items(), key=lambda x: x[1], reverse=True)[:5]:
            current_weight = current_weights.get(symbol, Decimal("0"))
            difference = target_weight - current_weight
            print(f"  {symbol}:")
            print(f"    Current: {float(current_weight)*100:.2f}%")
            print(f"    Target:  {float(target_weight)*100:.2f}%")
            print(f"    Diff:    {float(difference)*100:+.2f}%")
        
        # Calculate required trades
        trades = calculate_rebalance_trades(
            current_weights=current_weights,
            target_weights=target_weights,
            total_value=total_nav,
            prices=prices,
            cash_buffer=Decimal("0.05")
        )
        
        print(f"\n🔄 Trade Calculation Results:")
        print(f"  Number of trades calculated: {len(trades)}")
        
        if trades:
            print("\n📋 Trades to execute:")
            for symbol, (side, quantity) in trades.items():
                price = prices.get(symbol, Decimal("0"))
                value = quantity * price
                print(f"  {side.upper()} {float(quantity):.8f} {symbol} @ ${float(price):.4f} = ${float(value):.2f}")
        else:
            print("✅ No trades needed - portfolio is balanced")
        
        # Check if we're in dry run mode
        print(f"\n🔧 Configuration:")
        print(f"  DRY_RUN: {DRY_RUN}")
        print(f"  Portfolio ID: {os.getenv('CB_PORTFOLIO_ID', 'Not set')}")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_trades() 