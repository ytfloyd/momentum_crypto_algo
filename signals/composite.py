"""
Composite signal that combines multiple individual signals.

This class aggregates signals from different indicators (Donchian, MA crossover, 
momentum) to create a robust trading signal with configurable weights and 
consensus requirements.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base import BaseSignal
from .donchian import DonchianSignal
from .ma_crossover import MACrossoverSignal
from .momentum import MomentumSignal


class CompositeSignal(BaseSignal):
    """
    Composite signal that combines multiple individual signals.
    
    Aggregates signals from different indicators using configurable weights
    and consensus rules to generate robust trading signals.
    """
    
    def __init__(self, signals: List[BaseSignal] = None, 
                 weights: List[float] = None, 
                 consensus_threshold: float = 0.6,
                 min_strength: float = 0.3):
        """
        Initialize composite signal.
        
        Args:
            signals: List of individual signals to combine (default: creates standard set)
            weights: List of weights for each signal (default: equal weights)
            consensus_threshold: Minimum weighted consensus required for signal (default: 0.6)
            min_strength: Minimum strength required for signal generation (default: 0.3)
        """
        if signals is None:
            # Create default signal set
            signals = [
                DonchianSignal(lookback_period=20, exit_period=10),
                MACrossoverSignal(fast_period=10, slow_period=30, ma_type='ema'),
                MomentumSignal(lookback_periods=[10, 20, 60])
            ]
        
        if weights is None:
            weights = [1.0] * len(signals)
        
        if len(weights) != len(signals):
            raise ValueError("Number of weights must match number of signals")
        
        params = {
            'signal_names': [signal.name for signal in signals],
            'weights': weights,
            'consensus_threshold': consensus_threshold,
            'min_strength': min_strength
        }
        super().__init__('Composite', params)
        self.signals = signals
        self.weights = weights
        self.consensus_threshold = consensus_threshold
        self.min_strength = min_strength
    
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate composite signal by combining individual signals.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with signal, strength, and metadata
        """
        if not self.validate_data(data):
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        # Generate signals from all individual indicators
        individual_signals = []
        signal_metadata = {}
        
        for i, signal in enumerate(self.signals):
            try:
                result = signal.generate_signal(data)
                individual_signals.append(result)
                signal_metadata[signal.name] = result
            except Exception as e:
                # Handle signal generation errors gracefully
                print(f"Error generating signal for {signal.name}: {e}")
                individual_signals.append({
                    'signal': 0, 
                    'strength': 0.0, 
                    'metadata': {'error': str(e)}
                })
                signal_metadata[signal.name] = {
                    'signal': 0, 
                    'strength': 0.0, 
                    'metadata': {'error': str(e)}
                }
        
        if not individual_signals:
            return {'signal': 0, 'strength': 0.0, 'metadata': {}}
        
        # Calculate weighted consensus
        long_weight = 0.0
        short_weight = 0.0
        total_weight = 0.0
        strengths = []
        
        for i, signal_result in enumerate(individual_signals):
            signal_value = signal_result['signal']
            strength = signal_result['strength']
            weight = self.weights[i]
            
            if signal_value == 1:  # Long signal
                long_weight += weight * strength
                strengths.append(strength)
            elif signal_value == -1:  # Short signal
                short_weight += weight * strength
                strengths.append(strength)
            
            total_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            long_consensus = long_weight / total_weight
            short_consensus = short_weight / total_weight
        else:
            long_consensus = 0.0
            short_consensus = 0.0
        
        # Generate composite signal
        composite_signal = 0
        composite_strength = 0.0
        
        # Check if consensus threshold is met
        if long_consensus >= self.consensus_threshold:
            composite_signal = 1
            composite_strength = long_consensus
        elif short_consensus >= self.consensus_threshold:
            composite_signal = -1
            composite_strength = short_consensus
        else:
            # Check for simple majority with lower strength
            if long_consensus > short_consensus and long_consensus > 0.5:
                composite_signal = 1
                composite_strength = long_consensus * 0.7  # Reduce strength for lower consensus
            elif short_consensus > long_consensus and short_consensus > 0.5:
                composite_signal = -1
                composite_strength = short_consensus * 0.7  # Reduce strength for lower consensus
        
        # Apply minimum strength filter
        if composite_strength < self.min_strength:
            composite_signal = 0
            composite_strength = 0.0
        
        # Update last signal
        self.last_signal = composite_signal
        self.last_timestamp = data.index[-1] if not data.index.empty else None
        
        # Calculate agreement metrics
        signal_values = [s['signal'] for s in individual_signals]
        agreement = {
            'long_count': sum(1 for s in signal_values if s == 1),
            'short_count': sum(1 for s in signal_values if s == -1),
            'neutral_count': sum(1 for s in signal_values if s == 0),
            'total_signals': len(signal_values)
        }
        
        metadata = {
            'individual_signals': signal_metadata,
            'long_consensus': long_consensus,
            'short_consensus': short_consensus,
            'agreement': agreement,
            'consensus_threshold': self.consensus_threshold,
            'min_strength': self.min_strength,
            'average_strength': np.mean(strengths) if strengths else 0.0
        }
        
        return {
            'signal': composite_signal,
            'strength': composite_strength,
            'metadata': metadata
        } 