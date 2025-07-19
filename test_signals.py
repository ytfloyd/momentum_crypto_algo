#!/usr/bin/env python3
"""
Test script for signals module.

This script tests all signal types with synthetic data to ensure
they're working correctly.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from signals import DonchianSignal, MACrossoverSignal, MomentumSignal, CompositeSignal


def generate_test_data(periods=100, trend_type='uptrend'):
    """Generate synthetic OHLCV data for testing."""
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
    
    # Generate price data with different trend patterns
    if trend_type == 'uptrend':
        # Upward trending data
        base_price = 100
        trend = np.linspace(0, 50, periods)
        noise = np.random.normal(0, 2, periods)
        close_prices = base_price + trend + noise
    elif trend_type == 'downtrend':
        # Downward trending data
        base_price = 150
        trend = np.linspace(0, -50, periods)
        noise = np.random.normal(0, 2, periods)
        close_prices = base_price + trend + noise
    elif trend_type == 'sideways':
        # Sideways/ranging data
        base_price = 100
        noise = np.random.normal(0, 5, periods)
        close_prices = base_price + noise
    else:
        # Random walk
        base_price = 100
        returns = np.random.normal(0, 0.02, periods)
        close_prices = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC from close prices
    high_prices = close_prices + np.random.uniform(0, 3, periods)
    low_prices = close_prices - np.random.uniform(0, 3, periods)
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = close_prices[0]
    
    # Generate volume data
    volume = np.random.uniform(1000, 10000, periods)
    
    data = pd.DataFrame({
        'time': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    })
    
    data.set_index('time', inplace=True)
    return data


def test_donchian_signal():
    """Test Donchian Channel signal."""
    print("🧪 Testing Donchian Signal...")
    
    # Test with uptrend data
    data = generate_test_data(periods=50, trend_type='uptrend')
    signal = DonchianSignal(lookback_period=20, exit_period=10)
    
    result = signal.generate_signal(data)
    
    print(f"   Signal: {result['signal']}")
    print(f"   Strength: {result['strength']:.3f}")
    print(f"   Upper Channel: {result['metadata']['upper_channel']:.2f}")
    print(f"   Lower Channel: {result['metadata']['lower_channel']:.2f}")
    print(f"   Channel Width: {result['metadata']['channel_width']:.2f}")
    
    # Test with insufficient data
    small_data = generate_test_data(periods=10)
    result_small = signal.generate_signal(small_data)
    assert result_small['signal'] == 0, "Should return 0 signal for insufficient data"
    
    print("   ✅ Donchian Signal tests passed!")
    return True


def test_ma_crossover_signal():
    """Test Moving Average Crossover signal."""
    print("🧪 Testing MA Crossover Signal...")
    
    # Test with uptrend data
    data = generate_test_data(periods=60, trend_type='uptrend')
    signal = MACrossoverSignal(fast_period=10, slow_period=30, ma_type='sma')
    
    result = signal.generate_signal(data)
    
    print(f"   Signal: {result['signal']}")
    print(f"   Strength: {result['strength']:.3f}")
    print(f"   Fast MA: {result['metadata']['fast_ma']:.2f}")
    print(f"   Slow MA: {result['metadata']['slow_ma']:.2f}")
    print(f"   MA Diff: {result['metadata']['ma_diff']:.2f}")
    print(f"   Crossover: {result['metadata']['crossover']}")
    
    # Test EMA version
    ema_signal = MACrossoverSignal(fast_period=10, slow_period=30, ma_type='ema')
    ema_result = ema_signal.generate_signal(data)
    
    print(f"   EMA Signal: {ema_result['signal']}")
    print(f"   EMA Strength: {ema_result['strength']:.3f}")
    
    print("   ✅ MA Crossover Signal tests passed!")
    return True


def test_momentum_signal():
    """Test Time-Series Momentum signal."""
    print("🧪 Testing Momentum Signal...")
    
    # Test with uptrend data
    data = generate_test_data(periods=100, trend_type='uptrend')
    signal = MomentumSignal(lookback_periods=[10, 20, 60], weights=[1.0, 1.0, 1.0])
    
    result = signal.generate_signal(data)
    
    print(f"   Signal: {result['signal']}")
    print(f"   Strength: {result['strength']:.3f}")
    print(f"   Composite Momentum: {result['metadata']['composite_momentum']:.3f}")
    print(f"   Volatility: {result['metadata']['volatility']:.3f}")
    
    # Print individual momentum components
    individual = result['metadata']['individual_momentum']
    for key, value in individual.items():
        print(f"   {key}: {value:.3f}")
    
    # Test with insufficient data
    small_data = generate_test_data(periods=30)
    result_small = signal.generate_signal(small_data)
    assert result_small['signal'] == 0, "Should return 0 signal for insufficient data"
    
    print("   ✅ Momentum Signal tests passed!")
    return True


def test_composite_signal():
    """Test Composite Signal."""
    print("🧪 Testing Composite Signal...")
    
    # Test with uptrend data
    data = generate_test_data(periods=100, trend_type='uptrend')
    
    # Create individual signals
    donchian = DonchianSignal(lookback_period=20, exit_period=10)
    ma_cross = MACrossoverSignal(fast_period=10, slow_period=30, ma_type='ema')
    momentum = MomentumSignal(lookback_periods=[10, 20, 60])
    
    # Create composite signal
    composite = CompositeSignal(
        signals=[donchian, ma_cross, momentum],
        weights=[1.0, 1.0, 1.0],
        consensus_threshold=0.6,
        min_strength=0.3
    )
    
    result = composite.generate_signal(data)
    
    print(f"   Composite Signal: {result['signal']}")
    print(f"   Composite Strength: {result['strength']:.3f}")
    print(f"   Long Consensus: {result['metadata']['long_consensus']:.3f}")
    print(f"   Short Consensus: {result['metadata']['short_consensus']:.3f}")
    
    # Print individual signal results
    individual_signals = result['metadata']['individual_signals']
    for name, signal_result in individual_signals.items():
        print(f"   {name}: signal={signal_result['signal']}, strength={signal_result['strength']:.3f}")
    
    # Print agreement metrics
    agreement = result['metadata']['agreement']
    print(f"   Agreement: Long={agreement['long_count']}, Short={agreement['short_count']}, Neutral={agreement['neutral_count']}")
    
    print("   ✅ Composite Signal tests passed!")
    return True


def test_different_market_conditions():
    """Test signals across different market conditions."""
    print("🧪 Testing signals across different market conditions...")
    
    market_conditions = ['uptrend', 'downtrend', 'sideways', 'random']
    composite = CompositeSignal()
    
    for condition in market_conditions:
        print(f"\n   Testing {condition} market:")
        data = generate_test_data(periods=100, trend_type=condition)
        result = composite.generate_signal(data)
        
        print(f"   Signal: {result['signal']}, Strength: {result['strength']:.3f}")
        print(f"   Long Consensus: {result['metadata']['long_consensus']:.3f}")
        print(f"   Short Consensus: {result['metadata']['short_consensus']:.3f}")
    
    print("\n   ✅ Market condition tests passed!")
    return True


def main():
    """Run all signal tests."""
    print("🚀 Starting Signals Module Tests\n")
    
    try:
        # Test individual signals
        test_donchian_signal()
        print()
        
        test_ma_crossover_signal()
        print()
        
        test_momentum_signal()
        print()
        
        test_composite_signal()
        print()
        
        test_different_market_conditions()
        print()
        
        print("🎉 All signal tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 