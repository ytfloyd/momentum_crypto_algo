"""
Volatility-based position sizing for systematic trading.

This module implements volatility targeting and risk parity position sizing
methods commonly used in systematic trend-following strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from decimal import Decimal


class VolatilitySizing:
    """
    Volatility-based position sizing manager.
    
    Calculates position sizes based on volatility targeting to achieve
    consistent risk across different assets and market conditions.
    """
    
    def __init__(self, 
                 target_volatility: float = 0.15,
                 lookback_period: int = 60,
                 min_periods: int = 20,
                 max_leverage: float = 2.0,
                 min_position_size: float = 0.001):
        """
        Initialize volatility sizing.
        
        Args:
            target_volatility: Target portfolio volatility (default: 0.15 or 15%)
            lookback_period: Period for volatility estimation (default: 60)
            min_periods: Minimum periods required for calculation (default: 20)
            max_leverage: Maximum leverage allowed (default: 2.0)
            min_position_size: Minimum position size (default: 0.001)
        """
        self.target_volatility = target_volatility
        self.lookback_period = lookback_period
        self.min_periods = min_periods
        self.max_leverage = max_leverage
        self.min_position_size = min_position_size
    
    def calculate_volatility(self, data: pd.DataFrame, 
                           method: str = 'ewm') -> Optional[float]:
        """
        Calculate realized volatility for an asset.
        
        Args:
            data: DataFrame with OHLCV data
            method: Volatility calculation method ('ewm' or 'rolling')
            
        Returns:
            Annualized volatility estimate
        """
        if len(data) < self.min_periods:
            return None
        
        # Calculate returns
        returns = data['close'].pct_change().dropna()
        
        if len(returns) < self.min_periods:
            return None
        
        # Calculate volatility
        if method == 'ewm':
            # Exponentially weighted moving average
            vol = returns.ewm(span=self.lookback_period, adjust=False).std()
        else:
            # Simple rolling window
            vol = returns.rolling(window=self.lookback_period, 
                                min_periods=self.min_periods).std()
        
        current_vol = vol.iloc[-1]
        
        if pd.isna(current_vol) or current_vol <= 0:
            return None
        
        # Annualize volatility (assuming daily data)
        annualized_vol = current_vol * np.sqrt(252)
        
        return float(annualized_vol)
    
    def calculate_position_size(self, 
                              data: pd.DataFrame,
                              signal_strength: float = 1.0,
                              current_price: float = None) -> Dict[str, Any]:
        """
        Calculate position size based on volatility targeting.
        
        Args:
            data: DataFrame with OHLCV data
            signal_strength: Signal strength (0-1)
            current_price: Current price (optional, uses last close if not provided)
            
        Returns:
            Dictionary with position size and metadata
        """
        if current_price is None:
            current_price = float(data['close'].iloc[-1])
        
        # Calculate volatility
        volatility = self.calculate_volatility(data)
        
        if volatility is None or volatility <= 0:
            return {
                'position_size': 0.0,
                'leverage': 0.0,
                'volatility': None,
                'error': 'Insufficient data for volatility calculation'
            }
        
        # Calculate base position size using volatility targeting
        # Position size = (target_vol / asset_vol) * signal_strength
        base_position_size = (self.target_volatility / volatility) * signal_strength
        
        # Apply leverage constraint
        leverage = abs(base_position_size)
        if leverage > self.max_leverage:
            base_position_size = self.max_leverage * (1 if base_position_size > 0 else -1)
            leverage = self.max_leverage
        
        # Apply minimum position size
        if abs(base_position_size) < self.min_position_size:
            base_position_size = 0.0
            leverage = 0.0
        
        return {
            'position_size': base_position_size,
            'leverage': leverage,
            'volatility': volatility,
            'target_volatility': self.target_volatility,
            'signal_strength': signal_strength,
            'current_price': current_price
        }
    
    def calculate_portfolio_sizes(self, 
                                 assets_data: Dict[str, pd.DataFrame],
                                 signals: Dict[str, Dict[str, Any]],
                                 total_capital: float = 1000000.0) -> Dict[str, Dict[str, Any]]:
        """
        Calculate position sizes for a portfolio of assets.
        
        Args:
            assets_data: Dictionary mapping asset names to OHLCV data
            signals: Dictionary mapping asset names to signal information
            total_capital: Total capital available for allocation
            
        Returns:
            Dictionary mapping asset names to position sizing information
        """
        portfolio_sizes = {}
        total_leverage = 0.0
        
        # Calculate individual position sizes
        for asset_name, data in assets_data.items():
            if asset_name not in signals:
                continue
                
            signal_info = signals[asset_name]
            signal_strength = signal_info.get('strength', 0.0)
            
            # Skip if no signal
            if signal_strength <= 0:
                portfolio_sizes[asset_name] = {
                    'position_size': 0.0,
                    'dollar_amount': 0.0,
                    'leverage': 0.0,
                    'volatility': None
                }
                continue
            
            # Calculate position size
            size_info = self.calculate_position_size(data, signal_strength)
            
            # Convert to dollar amounts
            current_price = float(data['close'].iloc[-1])
            dollar_amount = size_info['position_size'] * total_capital
            
            portfolio_sizes[asset_name] = {
                'position_size': size_info['position_size'],
                'dollar_amount': dollar_amount,
                'leverage': size_info['leverage'],
                'volatility': size_info['volatility'],
                'current_price': current_price,
                'signal_strength': signal_strength
            }
            
            total_leverage += size_info['leverage']
        
        # Scale down if total leverage exceeds maximum
        if total_leverage > self.max_leverage:
            scale_factor = self.max_leverage / total_leverage
            
            for asset_name in portfolio_sizes:
                portfolio_sizes[asset_name]['position_size'] *= scale_factor
                portfolio_sizes[asset_name]['dollar_amount'] *= scale_factor
                portfolio_sizes[asset_name]['leverage'] *= scale_factor
        
        return portfolio_sizes
    
    def get_sizing_info(self) -> Dict[str, Any]:
        """
        Get current sizing configuration.
        
        Returns:
            Dictionary with sizing parameters
        """
        return {
            'target_volatility': self.target_volatility,
            'lookback_period': self.lookback_period,
            'min_periods': self.min_periods,
            'max_leverage': self.max_leverage,
            'min_position_size': self.min_position_size
        } 