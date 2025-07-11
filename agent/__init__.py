"""
Coinbase Portfolio Rebalancing Agent

An automated cryptocurrency portfolio rebalancing agent that maintains target asset allocations
using the Coinbase Advanced Trade API.
"""

from .runner import rebalance, main
from .config import TARGET_WEIGHTS, TOLERANCE, MIN_NOTIONAL, validate_config
from .utils import (
    get_client,
    fetch_nav_and_positions,
    calculate_current_weights,
    calculate_rebalance_trades,
    format_currency,
    setup_logging,
)

__version__ = "1.0.0"
__author__ = "Coinbase Rebalance Agent"
__email__ = "your.email@example.com"

# Expose main functions for external use
__all__ = [
    "rebalance",
    "main",
    "TARGET_WEIGHTS",
    "TOLERANCE",
    "MIN_NOTIONAL",
    "validate_config",
    "get_client",
    "fetch_nav_and_positions",
    "calculate_current_weights",
    "calculate_rebalance_trades",
    "format_currency",
    "setup_logging",
] 