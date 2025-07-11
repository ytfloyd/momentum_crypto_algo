"""
Configuration file for the Coinbase rebalancing agent.
"""

import os
from decimal import Decimal
from typing import Dict

# Target portfolio weights (must sum to 1.0)
TARGET_WEIGHTS: Dict[str, Decimal] = {
    "BTC-USD": Decimal("0.14"),    # 14% Bitcoin
    "ETH-USD": Decimal("0.185"),   # 18.5% Ethereum
    "SOL-USD": Decimal("0.15"),    # 15% Solana
    "ADA-USD": Decimal("0.125"),   # 12.5% Cardano
    "DOT-USD": Decimal("0.1"),     # 10% Polkadot
    "AVAX-USD": Decimal("0.1"),    # 10% Avalanche
    "LINK-USD": Decimal("0.08"),   # 8% Chainlink
    "ATOM-USD": Decimal("0.08"),   # 8% Cosmos
    "ALGO-USD": Decimal("0.06"),   # 6% Algorand
    "MATIC-USD": Decimal("0.05"),  # 5% Polygon
}

# Rebalancing parameters
TOLERANCE = Decimal("0.007")      # 0.7% tolerance (deviation from target)
MIN_NOTIONAL = Decimal("10")      # Minimum trade size in USD
MAX_SLIPPAGE = Decimal("0.005")   # Maximum allowed slippage (0.5%)

# Trading parameters
REBALANCE_INTERVAL_MINUTES = int(os.getenv("REBALANCE_INTERVAL_MINUTES", "60"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# API Configuration
API_KEY = os.getenv("CB_API_KEY", "")
API_SECRET = os.getenv("CB_API_SECRET", "")
API_PASSPHRASE = os.getenv("CB_API_PASSPHRASE", "")
PORTFOLIO_ID = os.getenv("CB_PORTFOLIO_ID", "")
API_URL = os.getenv("CB_API_URL", "https://api.coinbase.com")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/rebalance_agent.log")

# Validation
def validate_config():
    """Validate configuration settings."""
    # Check required environment variables
    required_vars = [API_KEY, API_SECRET, API_PASSPHRASE, PORTFOLIO_ID]
    missing_vars = [var for var in required_vars if not var]
    if missing_vars and not DRY_RUN:
        raise ValueError("Missing required environment variables for live trading")
    
    print(f"✓ Configuration validated")
    print(f"  - Using dynamic target weights")
    print(f"  - Tolerance: {TOLERANCE * 100}%")
    print(f"  - Min notional: ${MIN_NOTIONAL}")
    print(f"  - Dry run: {DRY_RUN}")
    print(f"  - API URL: {API_URL}")

if __name__ == "__main__":
    validate_config() 