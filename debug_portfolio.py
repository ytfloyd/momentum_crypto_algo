#!/usr/bin/env python3
"""
Debug script to diagnose portfolio data retrieval issues.
Compare what the API returns vs actual portfolio.
"""

import json
from decimal import Decimal
from agent.utils import get_client
from agent.config import validate_config, PORTFOLIO_ID

def debug_portfolio_data():
    """Debug the portfolio data retrieval to find discrepancies."""
    print("🔍 Debugging Portfolio Data Retrieval...")
    print("=" * 60)
    
    # Validate configuration first
    validate_config()
    
    # Initialize client
    client = get_client()
    
    print(f"\n0. Configuration:")
    print("-" * 30)
    print(f"Portfolio ID configured: {PORTFOLIO_ID}")
    
    print("\n1. Raw Accounts Data:")
    print("-" * 30)
    try:
        accounts = client.get_accounts()
        print(f"Number of accounts: {len(accounts.accounts)}")
        
        total_value = Decimal("0")
        usdc_accounts = []
        
        for i, account in enumerate(accounts.accounts):
            currency = account.currency
            balance = Decimal(account.available_balance.get("value", "0"))
            hold = Decimal(account.hold.get("value", "0")) if hasattr(account, 'hold') and account.hold else Decimal("0")
            
            if currency == "USDC" or currency == "USD":
                usdc_accounts.append((currency, balance, hold))
            
            if balance > 0:
                print(f"  Account {i+1}: {currency} = {balance} available, {hold} hold")
                total_value += balance
                
        print(f"\nCash accounts found:")
        for currency, balance, hold in usdc_accounts:
            print(f"  {currency}: ${balance} available, ${hold} hold")
                
        print(f"\nTotal available balance across all accounts: ${total_value}")
        
    except Exception as e:
        print(f"❌ Error getting accounts: {e}")
        return
    
    print("\n2. Portfolio Breakdown (if portfolio ID set):")
    print("-" * 30)
    if PORTFOLIO_ID:
        try:
            portfolio_breakdown = client.get_portfolio_breakdown(PORTFOLIO_ID)
            if hasattr(portfolio_breakdown, 'breakdown'):
                print(f"Portfolio breakdown found with {len(portfolio_breakdown.breakdown)} items:")
                for item in portfolio_breakdown.breakdown:
                    if hasattr(item, 'asset') and hasattr(item, 'value'):
                        asset = item.asset
                        value = Decimal(item.value.get('value', '0'))
                        print(f"  {asset}: ${value}")
            else:
                print("Portfolio breakdown format not recognized")
        except Exception as e:
            print(f"❌ Error getting portfolio breakdown: {e}")
    else:
        print("No portfolio ID configured")
    
    print("\n3. Portfolio Data (all portfolios):")
    print("-" * 30)
    try:
        portfolios = client.get_portfolios()
        if hasattr(portfolios, 'portfolios'):
            print(f"Number of portfolios: {len(portfolios.portfolios)}")
            for i, portfolio in enumerate(portfolios.portfolios):
                print(f"  Portfolio {i+1}: {portfolio.name} (UUID: {portfolio.uuid})")
                if portfolio.uuid == PORTFOLIO_ID:
                    print(f"    ⭐ This is the configured portfolio!")
        else:
            print("No portfolios found or different response format")
    except Exception as e:
        print(f"❌ Error getting portfolios: {e}")
    
    print("\n4. Current bot calculation (with new logic):")
    print("-" * 30)
    try:
        from agent.utils import fetch_nav_and_positions
        positions, prices, total_nav = fetch_nav_and_positions(client)
        
        print(f"Bot calculated NAV: ${total_nav}")
        print("Bot sees these positions:")
        for symbol, quantity in positions.items():
            if symbol == "USD":
                print(f"  Cash (USD/USDC): ${quantity}")
            else:
                price = prices.get(symbol, Decimal("0"))
                value = quantity * price
                print(f"  {symbol}: {quantity} @ ${price} = ${value}")
                
    except Exception as e:
        print(f"❌ Error with bot calculation: {e}")
    
    print("\n5. Expected vs Actual:")
    print("-" * 30)
    print("Expected (from your actual portfolio):")
    print("  Total: $10,038.77")
    print("  USDC (cash): $5,746.80")
    print("  BONK: 49,928,281 BONK = $1,317.60")
    print("  PENGU: 33,841 PENGU = $1,003.89")
    print("  And 10 other crypto positions...")

if __name__ == "__main__":
    debug_portfolio_data() 