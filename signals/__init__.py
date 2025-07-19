"""
Systematic trend-following signals module.

This module provides various technical analysis signals for trend-following strategies:
- Donchian Channel breakouts
- Moving Average crossovers  
- Time-series momentum
- Composite signal generation
"""

from .donchian import DonchianSignal
from .ma_crossover import MACrossoverSignal
from .momentum import MomentumSignal
from .composite import CompositeSignal

__all__ = [
    'DonchianSignal',
    'MACrossoverSignal', 
    'MomentumSignal',
    'CompositeSignal'
] 