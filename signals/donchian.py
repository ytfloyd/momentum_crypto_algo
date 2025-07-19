"""
Donchian Channel breakout signal for trend-following.

The Donchian Channel is a volatility indicator that plots the highest high 
and lowest low over a specified period. Breakouts above the upper channel 
signal long positions, while breakouts below the lower channel signal short positions.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .base import BaseSignal


class DonchianSignal(BaseSignal):
    """
    Donchian Channel breakout signal.
    
    Generates signals when price breaks above the upper channel (long) 
    or below the lower channel (short).
    """
    
    def __init__(self, lookback_period: int = 20, exit_period: int = 10):
        """
        Initialize Donchian Channel signal.
        
        Args:
            lookback_period: Period for calculating channel bounds (default: 20)
            exit_period: Period for exit signals (default: 10)
        """
        params = {
            'lookback_period': lookback_period,
            'exit_period': exit_period
        }
        super().__init__('Donchian', params)
        self.lookback_period = lookback_period
        self.exit_period = exit_period
    
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate Donchian Channel breakout signal.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with signal, strength, and metadata
        """
        if not self.validate_data(data):
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        if len(data) < self.lookback_period:
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        # Calculate Donchian Channel bounds
        data = data.copy()
        data['upper_channel'] = data['high'].rolling(window=self.lookback_period).max()
        data['lower_channel'] = data['low'].rolling(window=self.lookback_period).min()
        
        # Calculate exit bounds (shorter period)
        data['upper_exit'] = data['high'].rolling(window=self.exit_period).max()
        data['lower_exit'] = data['low'].rolling(window=self.exit_period).min()
        
        # Get current values
        current_price = data['close'].iloc[-1]
        current_high = data['high'].iloc[-1]
        current_low = data['low'].iloc[-1]
        
        upper_channel = data['upper_channel'].iloc[-1]
        lower_channel = data['lower_channel'].iloc[-1]
        upper_exit = data['upper_exit'].iloc[-1]
        lower_exit = data['lower_exit'].iloc[-1]
        
        # Generate signal
        signal = 0
        strength = 0.0
        
        # Long signal: price breaks above upper channel
        if current_high > upper_channel:
            signal = 1
            # Calculate strength based on how far above the channel
            channel_width = upper_channel - lower_channel
            if channel_width > 0:
                strength = min(1.0, (current_price - upper_channel) / channel_width)
            else:
                strength = 0.5
        
        # Short signal: price breaks below lower channel
        elif current_low < lower_channel:
            signal = -1
            # Calculate strength based on how far below the channel
            channel_width = upper_channel - lower_channel
            if channel_width > 0:
                strength = min(1.0, (lower_channel - current_price) / channel_width)
            else:
                strength = 0.5
        
        # Exit signals (for existing positions)
        elif hasattr(self, 'last_signal') and self.last_signal:
            if self.last_signal == 1 and current_low < lower_exit:
                signal = 0  # Exit long
                strength = 0.0
            elif self.last_signal == -1 and current_high > upper_exit:
                signal = 0  # Exit short
                strength = 0.0
        
        # Update last signal
        self.last_signal = signal
        self.last_timestamp = data.index[-1] if not data.index.empty else None
        
        metadata = {
            'upper_channel': upper_channel,
            'lower_channel': lower_channel,
            'upper_exit': upper_exit,
            'lower_exit': lower_exit,
            'channel_width': upper_channel - lower_channel,
            'current_price': current_price
        }
        
        return {
            'signal': signal,
            'strength': strength,
            'metadata': metadata
        } 