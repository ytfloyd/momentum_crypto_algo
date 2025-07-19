"""
Time-series momentum signal for trend-following.

Measures the rate of change in price over various lookback periods.
This is a fundamental component of trend-following strategies that
captures persistent price movements.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base import BaseSignal


class MomentumSignal(BaseSignal):
    """
    Time-series momentum signal.
    
    Calculates momentum over multiple time periods and generates
    signals based on the composite momentum score.
    """
    
    def __init__(self, lookback_periods: List[int] = [10, 20, 60], 
                 weights: List[float] = None, min_periods: int = 60):
        """
        Initialize time-series momentum signal.
        
        Args:
            lookback_periods: List of periods for momentum calculation (default: [10, 20, 60])
            weights: List of weights for each period (default: equal weights)
            min_periods: Minimum periods required for signal generation (default: 60)
        """
        if weights is None:
            weights = [1.0] * len(lookback_periods)
        
        if len(weights) != len(lookback_periods):
            raise ValueError("Number of weights must match number of lookback periods")
        
        params = {
            'lookback_periods': lookback_periods,
            'weights': weights,
            'min_periods': min_periods
        }
        super().__init__('Momentum', params)
        self.lookback_periods = lookback_periods
        self.weights = weights
        self.min_periods = min_periods
    
    def _calculate_momentum(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate momentum (rate of change) for a given period.
        
        Args:
            data: Price series
            period: Lookback period
            
        Returns:
            Momentum series
        """
        return data.pct_change(periods=period)
    
    def _normalize_momentum(self, momentum: pd.Series, lookback: int = 252) -> pd.Series:
        """
        Normalize momentum using a rolling z-score.

        This function computes a rolling mean and standard deviation
        over a specified lookback window to normalize the raw momentum
        series. If there is insufficient data to compute a full
        rolling window (e.g., early in the series or when the
        lookback period exceeds the length of the input), it falls
        back to using a smaller minimum number of periods and replaces
        any resulting NaNs with sensible defaults. This approach
        ensures that momentum normalization always returns numeric
        values, even for shorter time series.

        Args:
            momentum: Raw momentum series
            lookback: Period for rolling statistics (default: 252)

        Returns:
            Normalized momentum series
        """
        # Adapt min_periods based on series length to avoid NaNs
        min_periods = max(1, min(len(momentum), lookback // 2))

        # Compute rolling mean and standard deviation
        rolling_mean = momentum.rolling(window=lookback, min_periods=min_periods).mean()
        rolling_std = momentum.rolling(window=lookback, min_periods=min_periods).std()

        # Replace NaN rolling_mean with 0.0 to ensure a baseline
        rolling_mean = rolling_mean.fillna(0.0)

        # Replace NaN or zero std with 1.0 to avoid division by zero
        rolling_std = rolling_std.fillna(1.0)
        rolling_std = rolling_std.replace(0, 1.0)

        # Return z-score normalized series
        return (momentum - rolling_mean) / rolling_std
    
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate time-series momentum signal.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with signal, strength, and metadata
        """
        if not self.validate_data(data):
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        if len(data) < self.min_periods:
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        data = data.copy()
        current_price = data['close'].iloc[-1]
        
        # Calculate momentum for each period
        momentum_scores = []
        momentum_metadata = {}
        
        for i, period in enumerate(self.lookback_periods):
            if len(data) < period:
                continue
                
            # Calculate raw momentum
            momentum = self._calculate_momentum(data['close'], period)
            
            # Normalize momentum
            normalized_momentum = self._normalize_momentum(momentum)
            
            # Get current momentum score
            current_momentum = normalized_momentum.iloc[-1]
            
            if not pd.isna(current_momentum):
                # Apply weight
                weighted_momentum = current_momentum * self.weights[i]
                momentum_scores.append(weighted_momentum)
                
                momentum_metadata[f'momentum_{period}'] = current_momentum
                momentum_metadata[f'weighted_momentum_{period}'] = weighted_momentum
        
        if not momentum_scores:
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        # Calculate composite momentum score
        composite_momentum = sum(momentum_scores) / sum(self.weights[:len(momentum_scores)])
        
        # Generate signal based on composite momentum
        signal = 0
        strength = 0.0
        
        # Define thresholds for signal generation
        long_threshold = 0.5   # Positive momentum threshold for long signals
        short_threshold = -0.5  # Negative momentum threshold for short signals
        
        if composite_momentum > long_threshold:
            signal = 1
            strength = min(1.0, abs(composite_momentum) / 2.0)  # Scale strength
        elif composite_momentum < short_threshold:
            signal = -1
            strength = min(1.0, abs(composite_momentum) / 2.0)  # Scale strength
        else:
            # Neutral zone - no signal
            signal = 0
            strength = 0.0
        
        # Update last signal
        self.last_signal = signal
        self.last_timestamp = data.index[-1] if not data.index.empty else None
        
        # Calculate additional metadata
        volatility = data['close'].pct_change().rolling(window=20).std().iloc[-1]
        
        metadata = {
            'composite_momentum': composite_momentum,
            'individual_momentum': momentum_metadata,
            'current_price': current_price,
            'volatility': volatility,
            'signal_threshold': long_threshold if signal == 1 else short_threshold if signal == -1 else 0
        }
        
        return {
            'signal': signal,
            'strength': strength,
            'metadata': metadata
        }
