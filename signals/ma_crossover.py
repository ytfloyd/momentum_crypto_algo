"""
Moving Average crossover signal for trend-following.

Generates signals when a fast moving average crosses above or below a slow
moving average. This is a classic trend-following signal that captures
momentum shifts in the market.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseSignal


class MACrossoverSignal(BaseSignal):
    """
    Moving Average crossover signal.
    
    Generates long signals when fast MA crosses above slow MA,
    and short signals when fast MA crosses below slow MA.
    """
    
    def __init__(self, fast_period: int = 10, slow_period: int = 30, ma_type: str = 'sma'):
        """
        Initialize Moving Average crossover signal.
        
        Args:
            fast_period: Period for fast moving average (default: 10)
            slow_period: Period for slow moving average (default: 30)
            ma_type: Type of moving average ('sma' or 'ema', default: 'sma')
        """
        params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'ma_type': ma_type
        }
        super().__init__('MA_Crossover', params)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type.lower()
    
    def _calculate_ma(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate moving average based on specified type.
        
        Args:
            data: Price series
            period: Moving average period
            
        Returns:
            Moving average series
        """
        if self.ma_type == 'ema':
            return data.ewm(span=period, adjust=False).mean()
        else:  # Default to SMA
            return data.rolling(window=period).mean()
    
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate Moving Average crossover signal.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with signal, strength, and metadata
        """
        if not self.validate_data(data):
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        if len(data) < self.slow_period:
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        # Calculate moving averages
        data = data.copy()
        data['fast_ma'] = self._calculate_ma(data['close'], self.fast_period)
        data['slow_ma'] = self._calculate_ma(data['close'], self.slow_period)
        
        # Remove NaN values
        data = data.dropna()
        
        if len(data) < 2:
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        # Get current and previous values
        current_fast = data['fast_ma'].iloc[-1]
        current_slow = data['slow_ma'].iloc[-1]
        prev_fast = data['fast_ma'].iloc[-2]
        prev_slow = data['slow_ma'].iloc[-2]
        current_price = data['close'].iloc[-1]
        
        # Generate signal
        signal = 0
        strength = 0.0
        
        # Long signal: fast MA crosses above slow MA
        if prev_fast <= prev_slow and current_fast > current_slow:
            signal = 1
            # Calculate strength based on the difference between MAs
            ma_diff = abs(current_fast - current_slow)
            price_range = data['close'].rolling(window=20).std().iloc[-1]
            if price_range > 0:
                strength = min(1.0, ma_diff / price_range)
            else:
                strength = 0.5
        
        # Short signal: fast MA crosses below slow MA
        elif prev_fast >= prev_slow and current_fast < current_slow:
            signal = -1
            # Calculate strength based on the difference between MAs
            ma_diff = abs(current_fast - current_slow)
            price_range = data['close'].rolling(window=20).std().iloc[-1]
            if price_range > 0:
                strength = min(1.0, ma_diff / price_range)
            else:
                strength = 0.5
        
        # No crossover - maintain trend direction if MAs are separated
        elif current_fast > current_slow:
            signal = 1
            # Weaker strength for trend continuation
            ma_diff = abs(current_fast - current_slow)
            price_range = data['close'].rolling(window=20).std().iloc[-1]
            if price_range > 0:
                strength = min(0.5, ma_diff / price_range)
            else:
                strength = 0.2
        
        elif current_fast < current_slow:
            signal = -1
            # Weaker strength for trend continuation
            ma_diff = abs(current_fast - current_slow)
            price_range = data['close'].rolling(window=20).std().iloc[-1]
            if price_range > 0:
                strength = min(0.5, ma_diff / price_range)
            else:
                strength = 0.2
        
        # Update last signal
        self.last_signal = signal
        self.last_timestamp = data.index[-1] if not data.index.empty else None
        
        metadata = {
            'fast_ma': current_fast,
            'slow_ma': current_slow,
            'ma_diff': current_fast - current_slow,
            'current_price': current_price,
            'crossover': (prev_fast <= prev_slow and current_fast > current_slow) or 
                        (prev_fast >= prev_slow and current_fast < current_slow)
        }
        
        return {
            'signal': signal,
            'strength': strength,
            'metadata': metadata
        } 