"""
Execution module public API.

This package exposes the high-level execution classes for interacting with the
Coinbase Advanced Trade API.  The `PositionTracker` class referenced in earlier
versions of this code base has been removed, because it was never implemented
in this repository.  If you require position tracking functionality, consider
implementing it separately or integrating with the Coinbase Advanced SDK once
available.

Only the `CoinbaseAdvancedClient` and `OrderManager` classes are exported by
default.
"""

from .cb_adv_client import CoinbaseAdvancedClient  # noqa: F401
from .order_manager import OrderManager  # noqa: F401

__all__ = [
    'CoinbaseAdvancedClient',
    'OrderManager',
]
