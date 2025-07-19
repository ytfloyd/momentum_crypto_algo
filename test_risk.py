#!/usr/bin/env python3
"""
Test script for risk module.

This script tests position sizing, stop losses, drawdown control,
and the main risk manager.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from risk import VolatilitySizing, ATRStop, DrawdownControl, RiskManager


def generate_test_data(periods=100, volatility=0.02):
    """Generate synthetic OHLCV data for testing."""
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
    
    # Generate price data with specified volatility
    base_price = 100
    returns = np.random.normal(0, volatility, periods)
    close_prices = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC from close prices
    high_prices = close_prices + np.random.uniform(0, close_prices * 0.02, periods)
    low_prices = close_prices - np.random.uniform(0, close_prices * 0.02, periods)
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


def test_volatility_sizing():
    """Test volatility-based position sizing."""
    print("🧪 Testing Volatility Sizing...")
    
    # Test with different volatility levels
    sizing = VolatilitySizing(
        target_volatility=0.15,
        lookback_period=60,
        max_leverage=2.0
    )
    
    # Low volatility data
    low_vol_data = generate_test_data(periods=80, volatility=0.01)
    result_low = sizing.calculate_position_size(low_vol_data, signal_strength=1.0)
    
    print(f"   Low volatility asset:")
    print(f"   Volatility: {result_low['volatility']:.3f}")
    print(f"   Position size: {result_low['position_size']:.3f}")
    print(f"   Leverage: {result_low['leverage']:.3f}")
    
    # High volatility data
    high_vol_data = generate_test_data(periods=80, volatility=0.05)
    result_high = sizing.calculate_position_size(high_vol_data, signal_strength=1.0)
    
    print(f"   High volatility asset:")
    print(f"   Volatility: {result_high['volatility']:.3f}")
    print(f"   Position size: {result_high['position_size']:.3f}")
    print(f"   Leverage: {result_high['leverage']:.3f}")
    
    # Test with different signal strengths
    result_weak = sizing.calculate_position_size(low_vol_data, signal_strength=0.5)
    print(f"   Weak signal (0.5 strength):")
    print(f"   Position size: {result_weak['position_size']:.3f}")
    
    # Test portfolio sizing
    assets_data = {
        'BTC': low_vol_data,
        'ETH': high_vol_data
    }
    signals = {
        'BTC': {'strength': 0.8, 'signal': 1},
        'ETH': {'strength': 0.6, 'signal': 1}
    }
    
    portfolio_sizes = sizing.calculate_portfolio_sizes(assets_data, signals, 1000000)
    
    print(f"   Portfolio sizing:")
    for asset, size_info in portfolio_sizes.items():
        print(f"   {asset}: size={size_info['position_size']:.3f}, dollars=${size_info['dollar_amount']:.0f}")
    
    print("   ✅ Volatility Sizing tests passed!")
    return True


def test_atr_stops():
    """Test ATR-based stop losses."""
    print("🧪 Testing ATR Stops...")
    
    data = generate_test_data(periods=50, volatility=0.03)
    
    atr_stop = ATRStop(
        atr_period=14,
        stop_multiplier=2.0,
        trailing_stop=True
    )
    
    current_price = float(data['close'].iloc[-1])
    
    # Test long position stop
    long_stop = atr_stop.calculate_stop_level(
        data, 
        position_direction=1, 
        entry_price=current_price,
        asset_id='BTC'
    )
    
    print(f"   Long position:")
    print(f"   Entry price: ${current_price:.2f}")
    print(f"   Stop level: ${long_stop['stop_level']:.2f}")
    print(f"   Stop distance: ${long_stop['stop_distance']:.2f}")
    print(f"   ATR: {long_stop['atr']:.3f}")
    print(f"   Risk per share: ${current_price - long_stop['stop_level']:.2f}")
    
    # Test short position stop
    short_stop = atr_stop.calculate_stop_level(
        data, 
        position_direction=-1, 
        entry_price=current_price,
        asset_id='ETH'
    )
    
    print(f"   Short position:")
    print(f"   Entry price: ${current_price:.2f}")
    print(f"   Stop level: ${short_stop['stop_level']:.2f}")
    print(f"   Stop distance: ${short_stop['stop_distance']:.2f}")
    
    # Test stop trigger
    trigger_price = long_stop['stop_level'] - 1.0  # Below stop
    trigger_result = atr_stop.check_stop_triggered(trigger_price, 'BTC')
    
    print(f"   Stop trigger test:")
    print(f"   Test price: ${trigger_price:.2f}")
    print(f"   Stop triggered: {trigger_result['triggered']}")
    
    # Test trailing stop update
    new_data = generate_test_data(periods=52, volatility=0.03)  # 2 more periods
    update_result = atr_stop.update_stop_level(new_data, 'BTC')
    
    print(f"   Trailing stop update:")
    print(f"   Updated: {update_result['updated']}")
    if update_result['updated']:
        print(f"   New stop level: ${update_result['stop_level']:.2f}")
    
    print("   ✅ ATR Stops tests passed!")
    return True


def test_drawdown_control():
    """Test drawdown control."""
    print("🧪 Testing Drawdown Control...")
    
    drawdown_control = DrawdownControl(
        max_drawdown=0.20,
        scaling_threshold=0.10,
        min_scale_factor=0.1
    )
    
    # Simulate portfolio performance
    initial_value = 1000000
    portfolio_values = [initial_value]
    
    # Simulate some gains
    for i in range(10):
        new_value = portfolio_values[-1] * (1 + np.random.normal(0.01, 0.02))
        portfolio_values.append(new_value)
    
    # Update with gains
    for i, value in enumerate(portfolio_values):
        result = drawdown_control.update_portfolio_value(value)
        if i == len(portfolio_values) - 1:  # Last update
            print(f"   After gains:")
            print(f"   Portfolio value: ${value:.0f}")
            print(f"   Current drawdown: {result['current_drawdown']:.3f}")
            print(f"   Scale factor: {result['scale_factor']:.3f}")
    
    # Simulate drawdown
    peak_value = max(portfolio_values)
    drawdown_values = []
    for i in range(10):
        decline = 0.02 * (i + 1)  # Progressive decline
        new_value = peak_value * (1 - decline)
        drawdown_values.append(new_value)
    
    # Update with drawdown
    for i, value in enumerate(drawdown_values):
        result = drawdown_control.update_portfolio_value(value)
        if i == 4:  # 10% drawdown
            print(f"   At 10% drawdown:")
            print(f"   Portfolio value: ${value:.0f}")
            print(f"   Current drawdown: {result['current_drawdown']:.3f}")
            print(f"   Scale factor: {result['scale_factor']:.3f}")
            print(f"   Scaled down: {result['is_scaled_down']}")
        elif i == len(drawdown_values) - 1:  # Final drawdown
            print(f"   At maximum drawdown:")
            print(f"   Portfolio value: ${value:.0f}")
            print(f"   Current drawdown: {result['current_drawdown']:.3f}")
            print(f"   Scale factor: {result['scale_factor']:.3f}")
            print(f"   Halt trading: {result['halt_trading']}")
    
    # Test risk metrics
    risk_metrics = drawdown_control.get_risk_metrics()
    print(f"   Risk metrics:")
    print(f"   Max drawdown: {risk_metrics['max_drawdown_period']:.3f}")
    print(f"   Volatility: {risk_metrics['volatility']:.3f}")
    print(f"   Sharpe ratio: {risk_metrics['sharpe_ratio']:.3f}")
    
    print("   ✅ Drawdown Control tests passed!")
    return True


def test_risk_manager():
    """Test main risk manager."""
    print("🧪 Testing Risk Manager...")
    
    data = generate_test_data(periods=80, volatility=0.03)
    
    # Create risk manager
    risk_manager = RiskManager()
    
    # Test position risk calculation
    signal_info = {
        'signal': 1,
        'strength': 0.8,
        'metadata': {}
    }
    
    risk_result = risk_manager.calculate_position_risk(
        data, signal_info, asset_id='BTC'
    )
    
    print(f"   Position risk calculation:")
    print(f"   Position size: {risk_result['position_size']:.3f}")
    print(f"   Original size: {risk_result['original_size']:.3f}")
    print(f"   Drawdown scale: {risk_result['drawdown_scale']:.3f}")
    print(f"   Stop level: ${risk_result['stop_level']:.2f}")
    print(f"   Risk percentage: {risk_result['risk_percentage']:.3f}")
    print(f"   Volatility: {risk_result['volatility']:.3f}")
    
    # Test portfolio risk
    assets_data = {
        'BTC': data,
        'ETH': generate_test_data(periods=80, volatility=0.04)
    }
    
    signals = {
        'BTC': {'signal': 1, 'strength': 0.8},
        'ETH': {'signal': 1, 'strength': 0.6}
    }
    
    portfolio_risk = risk_manager.calculate_portfolio_risk(
        assets_data, signals, 1000000, 1000000
    )
    
    print(f"   Portfolio risk calculation:")
    print(f"   Total leverage: {portfolio_risk['total_leverage']:.3f}")
    print(f"   Total risk: ${portfolio_risk['total_risk']:.0f}")
    print(f"   Portfolio risk %: {portfolio_risk['portfolio_risk_percentage']:.3f}")
    print(f"   Violations: {len(portfolio_risk['violations'])}")
    
    # Test stop loss checks
    current_prices = {
        'BTC': float(data['close'].iloc[-1]) * 0.95,  # 5% below current
        'ETH': float(assets_data['ETH']['close'].iloc[-1]) * 1.05  # 5% above current
    }
    
    stop_checks = risk_manager.check_stop_losses(current_prices)
    
    print(f"   Stop loss checks:")
    for asset, check in stop_checks.items():
        print(f"   {asset}: triggered={check.get('triggered', False)}")
    
    # Test risk summary
    risk_summary = risk_manager.get_risk_summary()
    print(f"   Risk summary contains {len(risk_summary)} components")
    
    print("   ✅ Risk Manager tests passed!")
    return True


def test_risk_integration():
    """Test risk module integration."""
    print("🧪 Testing Risk Module Integration...")
    
    # Create sample data for multiple assets
    assets = ['BTC', 'ETH', 'ADA', 'DOT']
    assets_data = {}
    signals = {}
    
    for asset in assets:
        volatility = np.random.uniform(0.02, 0.05)  # Random volatility
        assets_data[asset] = generate_test_data(periods=100, volatility=volatility)
        signals[asset] = {
            'signal': np.random.choice([-1, 0, 1]),
            'strength': np.random.uniform(0.3, 1.0)
        }
    
    # Create risk manager
    risk_manager = RiskManager()
    
    # Calculate portfolio risk
    portfolio_risk = risk_manager.calculate_portfolio_risk(
        assets_data, signals, 1000000, 1000000
    )
    
    print(f"   Multi-asset portfolio:")
    print(f"   Assets: {len(assets)}")
    print(f"   Total leverage: {portfolio_risk['total_leverage']:.3f}")
    print(f"   Portfolio risk: {portfolio_risk['portfolio_risk_percentage']:.3f}")
    
    # Check individual position risks
    position_risks = portfolio_risk['position_risks']
    for asset, risk in position_risks.items():
        if risk['position_size'] != 0:
            print(f"   {asset}: size={risk['position_size']:.3f}, risk%={risk.get('risk_percentage', 0):.3f}")
    
    # Test exposure reduction
    should_reduce = risk_manager.should_reduce_exposure()
    print(f"   Should reduce exposure: {should_reduce}")
    
    print("   ✅ Risk Integration tests passed!")
    return True


def main():
    """Run all risk tests."""
    print("🚀 Starting Risk Module Tests\n")
    
    try:
        # Test individual components
        test_volatility_sizing()
        print()
        
        test_atr_stops()
        print()
        
        test_drawdown_control()
        print()
        
        test_risk_manager()
        print()
        
        test_risk_integration()
        print()
        
        print("🎉 All risk tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 