"""
ATR-based stop loss management for systematic trading.

This module implements Average True Range (ATR) based stop losses,
which are commonly used in trend-following strategies to manage risk
while allowing for normal market volatility.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


class ATRStop:
    """
    ATR-based stop loss manager.
    
    Calculates and manages stop loss levels based on Average True Range (ATR)
    to provide volatility-adjusted risk management.
    """
    
    def __init__(self, 
                 atr_period: int = 14,
                 stop_multiplier: float = 2.0,
                 min_stop_distance: float = 0.005,
                 max_stop_distance: float = 0.10,
                 trailing_stop: bool = True):
        """
        Initialize ATR stop loss manager.
        
        Args:
            atr_period: Period for ATR calculation (default: 14)
            stop_multiplier: ATR multiplier for stop distance (default: 2.0)
            min_stop_distance: Minimum stop distance as fraction of price (default: 0.005 or 0.5%)
            max_stop_distance: Maximum stop distance as fraction of price (default: 0.10 or 10%)
            trailing_stop: Whether to use trailing stops (default: True)
        """
        self.atr_period = atr_period
        self.stop_multiplier = stop_multiplier
        self.min_stop_distance = min_stop_distance
        self.max_stop_distance = max_stop_distance
        self.trailing_stop = trailing_stop
        
        # Track stop levels for each position
        self.stop_levels = {}
        self.entry_prices = {}
        self.position_directions = {}
    
    def calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            ATR series
        """
        if len(data) < self.atr_period:
            return pd.Series(dtype=float)
        
        # Calculate True Range
        data = data.copy()
        data['prev_close'] = data['close'].shift(1)
        
        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        data['tr1'] = data['high'] - data['low']
        data['tr2'] = abs(data['high'] - data['prev_close'])
        data['tr3'] = abs(data['low'] - data['prev_close'])
        
        data['true_range'] = data[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Calculate ATR using exponential moving average
        atr = data['true_range'].ewm(span=self.atr_period, adjust=False).mean()
        
        return atr
    
    def calculate_stop_level(self, 
                           data: pd.DataFrame,
                           position_direction: int,
                           entry_price: float = None,
                           asset_id: str = None) -> Dict[str, Any]:
        """
        Calculate stop loss level based on ATR.
        
        Args:
            data: DataFrame with OHLCV data
            position_direction: 1 for long, -1 for short
            entry_price: Entry price for the position
            asset_id: Asset identifier for tracking stops
            
        Returns:
            Dictionary with stop level and metadata
        """
        if len(data) < self.atr_period:
            return {
                'stop_level': None,
                'stop_distance': None,
                'atr': None,
                'error': 'Insufficient data for ATR calculation'
            }
        
        # Calculate ATR
        atr = self.calculate_atr(data)
        current_atr = atr.iloc[-1]
        
        if pd.isna(current_atr) or current_atr <= 0:
            return {
                'stop_level': None,
                'stop_distance': None,
                'atr': None,
                'error': 'Invalid ATR value'
            }
        
        current_price = float(data['close'].iloc[-1])
        
        if entry_price is None:
            entry_price = current_price
        
        # Calculate stop distance
        stop_distance = current_atr * self.stop_multiplier
        
        # Apply minimum and maximum stop distance constraints
        min_distance = current_price * self.min_stop_distance
        max_distance = current_price * self.max_stop_distance
        
        stop_distance = max(min_distance, min(stop_distance, max_distance))
        
        # Calculate stop level based on position direction
        if position_direction == 1:  # Long position
            initial_stop = entry_price - stop_distance
            
            # If using trailing stops, move stop up but never down
            if self.trailing_stop and asset_id and asset_id in self.stop_levels:
                previous_stop = self.stop_levels[asset_id]
                stop_level = max(initial_stop, previous_stop)
            else:
                stop_level = initial_stop
                
        else:  # Short position
            initial_stop = entry_price + stop_distance
            
            # If using trailing stops, move stop down but never up
            if self.trailing_stop and asset_id and asset_id in self.stop_levels:
                previous_stop = self.stop_levels[asset_id]
                stop_level = min(initial_stop, previous_stop)
            else:
                stop_level = initial_stop
        
        # Update tracking if asset_id provided
        if asset_id:
            self.stop_levels[asset_id] = stop_level
            self.entry_prices[asset_id] = entry_price
            self.position_directions[asset_id] = position_direction
        
        return {
            'stop_level': stop_level,
            'stop_distance': stop_distance,
            'atr': current_atr,
            'entry_price': entry_price,
            'current_price': current_price,
            'position_direction': position_direction,
            'trailing_stop': self.trailing_stop
        }
    
    def check_stop_triggered(self, 
                           current_price: float,
                           asset_id: str) -> Dict[str, Any]:
        """
        Check if stop loss has been triggered for a position.
        
        Args:
            current_price: Current market price
            asset_id: Asset identifier
            
        Returns:
            Dictionary with stop trigger status and details
        """
        if asset_id not in self.stop_levels:
            return {
                'triggered': False,
                'stop_level': None,
                'error': 'No stop level found for asset'
            }
        
        stop_level = self.stop_levels[asset_id]
        position_direction = self.position_directions.get(asset_id, 0)
        
        triggered = False
        
        if position_direction == 1:  # Long position
            triggered = current_price <= stop_level
        elif position_direction == -1:  # Short position
            triggered = current_price >= stop_level
        
        return {
            'triggered': triggered,
            'stop_level': stop_level,
            'current_price': current_price,
            'position_direction': position_direction,
            'stop_distance': abs(current_price - stop_level)
        }
    
    def update_stop_level(self, 
                         data: pd.DataFrame,
                         asset_id: str) -> Dict[str, Any]:
        """
        Update stop level for existing position (for trailing stops).
        
        Args:
            data: DataFrame with OHLCV data
            asset_id: Asset identifier
            
        Returns:
            Dictionary with updated stop information
        """
        if asset_id not in self.position_directions:
            return {
                'updated': False,
                'error': 'No position found for asset'
            }
        
        position_direction = self.position_directions[asset_id]
        entry_price = self.entry_prices[asset_id]
        
        result = self.calculate_stop_level(
            data, position_direction, entry_price, asset_id
        )
        
        if result.get('stop_level') is not None:
            return {
                'updated': True,
                'stop_level': result['stop_level'],
                'atr': result['atr'],
                'stop_distance': result['stop_distance']
            }
        
        return {
            'updated': False,
            'error': result.get('error', 'Failed to update stop level')
        }
    
    def remove_position(self, asset_id: str) -> bool:
        """
        Remove position tracking for an asset.
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            True if position was removed, False if not found
        """
        removed = False
        
        if asset_id in self.stop_levels:
            del self.stop_levels[asset_id]
            removed = True
        
        if asset_id in self.entry_prices:
            del self.entry_prices[asset_id]
        
        if asset_id in self.position_directions:
            del self.position_directions[asset_id]
        
        return removed
    
    def get_all_stops(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all current stop levels.
        
        Returns:
            Dictionary mapping asset IDs to stop information
        """
        stops = {}
        
        for asset_id in self.stop_levels:
            stops[asset_id] = {
                'stop_level': self.stop_levels[asset_id],
                'entry_price': self.entry_prices.get(asset_id),
                'position_direction': self.position_directions.get(asset_id)
            }
        
        return stops
    
    def get_stop_config(self) -> Dict[str, Any]:
        """
        Get current stop configuration.
        
        Returns:
            Dictionary with stop parameters
        """
        return {
            'atr_period': self.atr_period,
            'stop_multiplier': self.stop_multiplier,
            'min_stop_distance': self.min_stop_distance,
            'max_stop_distance': self.max_stop_distance,
            'trailing_stop': self.trailing_stop
        } 