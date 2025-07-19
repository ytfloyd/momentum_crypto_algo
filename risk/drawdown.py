"""
Drawdown control module for systematic trading.

This module monitors portfolio drawdowns and implements risk controls
to protect capital during adverse market conditions.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class DrawdownControl:
    """
    Drawdown control manager.
    
    Monitors portfolio performance and implements risk controls
    based on drawdown levels to protect capital.
    """
    
    def __init__(self, 
                 max_drawdown: float = 0.20,
                 lookback_period: int = 252,
                 scaling_threshold: float = 0.10,
                 min_scale_factor: float = 0.1,
                 recovery_threshold: float = 0.95):
        """
        Initialize drawdown control.
        
        Args:
            max_drawdown: Maximum allowable drawdown (default: 0.20 or 20%)
            lookback_period: Period for calculating rolling max (default: 252)
            scaling_threshold: Drawdown level to start scaling down (default: 0.10 or 10%)
            min_scale_factor: Minimum position scale factor (default: 0.1)
            recovery_threshold: Portfolio recovery threshold to resume normal sizing (default: 0.95)
        """
        self.max_drawdown = max_drawdown
        self.lookback_period = lookback_period
        self.scaling_threshold = scaling_threshold
        self.min_scale_factor = min_scale_factor
        self.recovery_threshold = recovery_threshold
        
        # Portfolio performance tracking
        self.portfolio_values = []
        self.timestamps = []
        self.current_scale_factor = 1.0
        self.is_scaled_down = False
        self.max_portfolio_value = 0.0
        
        # Risk metrics
        self.current_drawdown = 0.0
        self.max_drawdown_period = 0.0
        self.drawdown_duration = 0
        self.last_peak_date = None
    
    def update_portfolio_value(self, 
                             portfolio_value: float,
                             timestamp: datetime = None) -> Dict[str, Any]:
        """
        Update portfolio value and calculate drawdown metrics.
        
        Args:
            portfolio_value: Current portfolio value
            timestamp: Timestamp for the update (default: current time)
            
        Returns:
            Dictionary with drawdown metrics and scaling information
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.portfolio_values.append(portfolio_value)
        self.timestamps.append(timestamp)
        
        # Keep only recent values for efficiency
        if len(self.portfolio_values) > self.lookback_period * 2:
            self.portfolio_values = self.portfolio_values[-self.lookback_period:]
            self.timestamps = self.timestamps[-self.lookback_period:]
        
        # Calculate current drawdown
        self.max_portfolio_value = max(self.max_portfolio_value, portfolio_value)
        self.current_drawdown = (self.max_portfolio_value - portfolio_value) / self.max_portfolio_value
        
        # Update maximum drawdown in period
        portfolio_series = pd.Series(self.portfolio_values, index=self.timestamps)
        rolling_max = portfolio_series.rolling(window=self.lookback_period, min_periods=1).max()
        drawdowns = (rolling_max - portfolio_series) / rolling_max
        self.max_drawdown_period = drawdowns.max()
        
        # Update drawdown duration
        if self.current_drawdown > 0:
            if self.last_peak_date is None:
                self.last_peak_date = timestamp
            self.drawdown_duration = (timestamp - self.last_peak_date).days
        else:
            self.last_peak_date = None
            self.drawdown_duration = 0
        
        # Calculate scaling factor
        scale_factor = self._calculate_scale_factor()
        
        # Check if we need to halt trading
        halt_trading = self.current_drawdown >= self.max_drawdown
        
        return {
            'current_drawdown': self.current_drawdown,
            'max_drawdown_period': self.max_drawdown_period,
            'drawdown_duration': self.drawdown_duration,
            'scale_factor': scale_factor,
            'halt_trading': halt_trading,
            'portfolio_value': portfolio_value,
            'max_portfolio_value': self.max_portfolio_value,
            'is_scaled_down': self.is_scaled_down
        }
    
    def _calculate_scale_factor(self) -> float:
        """
        Calculate position scaling factor based on current drawdown.
        
        Returns:
            Scaling factor between min_scale_factor and 1.0
        """
        if self.current_drawdown < self.scaling_threshold:
            # No scaling needed
            new_scale_factor = 1.0
            if self.is_scaled_down:
                # Check if we've recovered enough to resume normal sizing
                recovery_ratio = self.max_portfolio_value / max(self.portfolio_values)
                if recovery_ratio >= self.recovery_threshold:
                    self.is_scaled_down = False
                    new_scale_factor = 1.0
                else:
                    # Maintain current scaled position
                    new_scale_factor = self.current_scale_factor
            
        elif self.current_drawdown >= self.max_drawdown:
            # Halt trading
            new_scale_factor = 0.0
            self.is_scaled_down = True
            
        else:
            # Scale down proportionally
            scale_range = self.max_drawdown - self.scaling_threshold
            drawdown_excess = self.current_drawdown - self.scaling_threshold
            
            # Linear scaling from 1.0 to min_scale_factor
            scale_reduction = drawdown_excess / scale_range
            new_scale_factor = 1.0 - scale_reduction * (1.0 - self.min_scale_factor)
            new_scale_factor = max(self.min_scale_factor, new_scale_factor)
            
            self.is_scaled_down = True
        
        self.current_scale_factor = new_scale_factor
        return new_scale_factor
    
    def get_position_scale_factor(self) -> float:
        """
        Get current position scaling factor.
        
        Returns:
            Current scaling factor
        """
        return self.current_scale_factor
    
    def should_halt_trading(self) -> bool:
        """
        Check if trading should be halted due to excessive drawdown.
        
        Returns:
            True if trading should be halted
        """
        return self.current_drawdown >= self.max_drawdown
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive risk metrics.
        
        Returns:
            Dictionary with all risk metrics
        """
        if not self.portfolio_values:
            return {
                'current_drawdown': 0.0,
                'max_drawdown_period': 0.0,
                'drawdown_duration': 0,
                'scale_factor': 1.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_portfolio_value': 0.0,
                'current_portfolio_value': 0.0
            }
        
        # Calculate additional metrics
        portfolio_series = pd.Series(self.portfolio_values, index=self.timestamps)
        returns = portfolio_series.pct_change().dropna()
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0.0
        
        # Sharpe ratio (assuming risk-free rate of 0)
        sharpe_ratio = (returns.mean() * 252) / volatility if volatility > 0 else 0.0
        
        # Calmar ratio (annualized return / max drawdown)
        if len(self.portfolio_values) > 1:
            total_return = (self.portfolio_values[-1] / self.portfolio_values[0]) - 1
            days_elapsed = (self.timestamps[-1] - self.timestamps[0]).days
            annualized_return = (1 + total_return) ** (365 / days_elapsed) - 1 if days_elapsed > 0 else 0
            calmar_ratio = annualized_return / self.max_drawdown_period if self.max_drawdown_period > 0 else 0
        else:
            calmar_ratio = 0.0
        
        return {
            'current_drawdown': self.current_drawdown,
            'max_drawdown_period': self.max_drawdown_period,
            'drawdown_duration': self.drawdown_duration,
            'scale_factor': self.current_scale_factor,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'calmar_ratio': calmar_ratio,
            'max_portfolio_value': self.max_portfolio_value,
            'current_portfolio_value': self.portfolio_values[-1] if self.portfolio_values else 0.0,
            'total_observations': len(self.portfolio_values)
        }
    
    def reset_tracking(self):
        """Reset all tracking variables."""
        self.portfolio_values = []
        self.timestamps = []
        self.current_scale_factor = 1.0
        self.is_scaled_down = False
        self.max_portfolio_value = 0.0
        self.current_drawdown = 0.0
        self.max_drawdown_period = 0.0
        self.drawdown_duration = 0
        self.last_peak_date = None
    
    def get_drawdown_config(self) -> Dict[str, Any]:
        """
        Get current drawdown control configuration.
        
        Returns:
            Dictionary with drawdown control parameters
        """
        return {
            'max_drawdown': self.max_drawdown,
            'lookback_period': self.lookback_period,
            'scaling_threshold': self.scaling_threshold,
            'min_scale_factor': self.min_scale_factor,
            'recovery_threshold': self.recovery_threshold
        }
    
    def export_performance_data(self) -> pd.DataFrame:
        """
        Export performance data for analysis.
        
        Returns:
            DataFrame with timestamp, portfolio value, and drawdown
        """
        if not self.portfolio_values:
            return pd.DataFrame()
        
        df = pd.DataFrame({
            'timestamp': self.timestamps,
            'portfolio_value': self.portfolio_values
        })
        
        # Calculate rolling metrics
        df['rolling_max'] = df['portfolio_value'].cummax()
        df['drawdown'] = (df['rolling_max'] - df['portfolio_value']) / df['rolling_max']
        df['returns'] = df['portfolio_value'].pct_change()
        
        return df 