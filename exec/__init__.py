"""
Execution module for systematic trading with Coinbase Advanced Trade API.

This module provides order management, position tracking, and trade execution
capabilities using the Coinbase Advanced Python SDK.
"""

from .cb_adv_client import CoinbaseAdvancedClient
from .order_manager import OrderManager
from .position_tracker import PositionTracker

__all__ = [
    'CoinbaseAdvancedClient',
    'OrderManager',
    'PositionTracker'
] 