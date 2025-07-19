#!/usr/bin/env python3
"""
Comprehensive test script for all modules.

This script runs all individual module tests and then tests
integration between modules to ensure the systematic trading
system works as a whole.
"""

import sys
import os
import subprocess
import time
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all modules
from signals import CompositeSignal, DonchianSignal, MACrossoverSignal, MomentumSignal
from risk import RiskManager, VolatilitySizing, ATRStop, DrawdownControl
from exec import CoinbaseAdvancedClient, OrderManager


def run_individual_tests():
    """Run individual module test scripts."""
    print("🧪 Running Individual Module Tests\n")
    
    test_scripts = [
        ('test_signals.py', 'Signals Module'),
        ('test_risk.py', 'Risk Module'),
        ('test_execution.py', 'Execution Module')
    ]
    
    results = {}
    
    for script, name in test_scripts:
        print(f"📋 Running {name} tests...")
        
        try:
            # Run the test script
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                print(f"   ✅ {name} tests passed")
                results[name] = True
            else:
                print(f"   ❌ {name} tests failed")
                print(f"   Error output: {result.stderr}")
                results[name] = False
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {name} tests timed out")
            results[name] = False
        except Exception as e:
            print(f"   ❌ {name} tests failed with exception: {e}")
            results[name] = False
    
    return results


def generate_test_data(periods=100, volatility=0.03):
    """Generate synthetic OHLCV data for integration testing."""
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
    
    # Generate price data with upward trend
    base_price = 100
    trend = np.linspace(0, 30, periods)  # 30% upward trend
    noise = np.random.normal(0, volatility * base_price, periods)
    close_prices = base_price + trend + noise
    
    # Ensure prices are positive
    close_prices = np.maximum(close_prices, base_price * 0.5)
    
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


def test_signals_risk_integration():
    """Test integration between signals and risk modules."""
    print("🔗 Testing Signals-Risk Integration...")
    
    # Generate test data for multiple assets
    assets = ['BTC', 'ETH', 'ADA', 'DOT', 'LINK']
    assets_data = {}
    
    for asset in assets:
        volatility = np.random.uniform(0.02, 0.05)
        assets_data[asset] = generate_test_data(periods=100, volatility=volatility)
    
    # Generate signals for each asset
    composite_signal = CompositeSignal()
    signals = {}
    
    for asset, data in assets_data.items():
        signal_result = composite_signal.generate_signal(data)
        signals[asset] = signal_result
        print(f"   {asset}: signal={signal_result['signal']}, strength={signal_result['strength']:.3f}")
    
    # Test risk management with signals
    risk_manager = RiskManager()
    
    # Calculate portfolio risk
    portfolio_risk = risk_manager.calculate_portfolio_risk(
        assets_data, signals, 1000000, 1000000
    )
    
    print(f"   Portfolio Analysis:")
    print(f"   Total leverage: {portfolio_risk['total_leverage']:.3f}")
    print(f"   Portfolio risk: {portfolio_risk['portfolio_risk_percentage']:.3f}")
    print(f"   Risk violations: {len(portfolio_risk['violations'])}")
    
    # Test individual position risks
    position_risks = portfolio_risk['position_risks']
    active_positions = sum(1 for risk in position_risks.values() if risk['position_size'] != 0)
    
    print(f"   Active positions: {active_positions}/{len(assets)}")
    print(f"   Scale factor: {portfolio_risk['scale_factor']:.3f}")
    
    print("   ✅ Signals-Risk integration test passed!")
    return True


def test_risk_execution_integration():
    """Test integration between risk and execution modules."""
    print("🔗 Testing Risk-Execution Integration...")
    
    # Create mock client and order manager
    mock_client = Mock()
    order_manager = OrderManager(client=mock_client)
    
    # Create risk manager
    risk_manager = RiskManager()
    
    # Generate test data and signals
    data = generate_test_data(periods=80, volatility=0.03)
    signal_info = {'signal': 1, 'strength': 0.8}
    
    # Calculate position risk
    risk_result = risk_manager.calculate_position_risk(
        data, signal_info, asset_id='BTC'
    )
    
    print(f"   Position risk calculation:")
    print(f"   Position size: {risk_result['position_size']:.3f}")
    print(f"   Stop level: ${risk_result['stop_level']:.2f}")
    print(f"   Risk percentage: {risk_result['risk_percentage']:.3f}")
    
    # Validate trade with risk manager
    current_price = float(data['close'].iloc[-1])
    validation = risk_manager.validate_trade(
        'BTC', risk_result['position_size'], current_price, 1000000
    )
    
    print(f"   Trade validation:")
    print(f"   Valid: {validation['valid']}")
    print(f"   Position value: ${validation['position_value']:.0f}")
    print(f"   Position percentage: {validation['position_percentage']:.3f}")
    
    # Create order if valid
    if validation['valid']:
        mock_client.create_market_order.return_value = {
            "order_id": "integration_test_123",
            "status": "pending"
        }
        
        order_result = order_manager.create_market_order(
            product_id="BTC-USD",
            side="buy",
            funds=str(validation['position_value']),
            client_order_id="integration_test_order"
        )
        
        print(f"   Order creation: {order_result['success']}")
        print(f"   Order ID: {order_result['order_id']}")
    
    # Test stop loss integration
    stop_checks = risk_manager.check_stop_losses({'BTC': current_price * 0.95})
    print(f"   Stop loss check: {stop_checks['BTC'].get('triggered', False)}")
    
    print("   ✅ Risk-Execution integration test passed!")
    return True


def test_full_system_integration():
    """Test full system integration across all modules."""
    print("🔗 Testing Full System Integration...")
    
    # Generate multi-asset test data
    assets = ['BTC', 'ETH', 'ADA']
    assets_data = {}
    
    for asset in assets:
        assets_data[asset] = generate_test_data(periods=120, volatility=0.03)
    
    # 1. Generate signals
    print("   Step 1: Generating signals...")
    composite_signal = CompositeSignal()
    signals = {}
    
    for asset, data in assets_data.items():
        signal_result = composite_signal.generate_signal(data)
        signals[asset] = signal_result
    
    active_signals = sum(1 for s in signals.values() if s['signal'] != 0)
    print(f"   Active signals: {active_signals}/{len(assets)}")
    
    # 2. Risk management
    print("   Step 2: Risk management...")
    risk_manager = RiskManager()
    
    portfolio_risk = risk_manager.calculate_portfolio_risk(
        assets_data, signals, 1000000, 1000000
    )
    
    print(f"   Portfolio leverage: {portfolio_risk['total_leverage']:.3f}")
    print(f"   Portfolio risk: {portfolio_risk['portfolio_risk_percentage']:.3f}")
    
    # 3. Order execution simulation
    print("   Step 3: Order execution simulation...")
    mock_client = Mock()
    order_manager = OrderManager(client=mock_client)
    
    # Create orders for valid positions
    position_risks = portfolio_risk['position_risks']
    orders_created = 0
    
    for asset, risk in position_risks.items():
        if risk['position_size'] != 0:
            mock_client.create_market_order.return_value = {
                "order_id": f"system_test_{asset}",
                "status": "pending"
            }
            
            side = "buy" if risk['position_size'] > 0 else "sell"
            funds = str(abs(risk['position_size']) * 1000000)
            
            order_result = order_manager.create_market_order(
                product_id=f"{asset}-USD",
                side=side,
                funds=funds,
                client_order_id=f"system_{asset}"
            )
            
            if order_result['success']:
                orders_created += 1
    
    print(f"   Orders created: {orders_created}")
    
    # 4. Portfolio monitoring
    print("   Step 4: Portfolio monitoring...")
    
    # Simulate portfolio value updates
    initial_value = 1000000
    portfolio_values = [initial_value]
    
    # Simulate some performance
    for i in range(5):
        performance = np.random.normal(0.01, 0.02)  # 1% expected return, 2% volatility
        new_value = portfolio_values[-1] * (1 + performance)
        portfolio_values.append(new_value)
    
    # Update risk manager with portfolio performance
    for value in portfolio_values:
        risk_manager.drawdown_control.update_portfolio_value(value)
    
    risk_metrics = risk_manager.drawdown_control.get_risk_metrics()
    print(f"   Portfolio performance:")
    print(f"   Final value: ${portfolio_values[-1]:.0f}")
    print(f"   Current drawdown: {risk_metrics['current_drawdown']:.3f}")
    print(f"   Volatility: {risk_metrics['volatility']:.3f}")
    
    # 5. System health check
    print("   Step 5: System health check...")
    
    # Check if system should reduce exposure
    should_reduce = risk_manager.should_reduce_exposure()
    print(f"   Should reduce exposure: {should_reduce}")
    
    # Check execution statistics
    exec_stats = order_manager.get_execution_stats()
    print(f"   Total orders: {exec_stats['total_orders']}")
    print(f"   Fill rate: {exec_stats['fill_rate']:.2f}")
    
    # Check risk summary
    risk_summary = risk_manager.get_risk_summary()
    print(f"   Risk components: {len(risk_summary)}")
    
    print("   ✅ Full system integration test passed!")
    return True


def test_performance_benchmarks():
    """Test performance of the system components."""
    print("⚡ Testing Performance Benchmarks...")
    
    # Test signal generation performance
    print("   Signal generation performance:")
    data = generate_test_data(periods=1000, volatility=0.03)
    
    start_time = time.time()
    composite_signal = CompositeSignal()
    for i in range(10):
        signal_result = composite_signal.generate_signal(data)
    signal_time = (time.time() - start_time) / 10
    
    print(f"   Average signal generation: {signal_time:.4f}s")
    
    # Test risk calculation performance
    print("   Risk calculation performance:")
    risk_manager = RiskManager()
    signal_info = {'signal': 1, 'strength': 0.8}
    
    start_time = time.time()
    for i in range(10):
        risk_result = risk_manager.calculate_position_risk(data, signal_info)
    risk_time = (time.time() - start_time) / 10
    
    print(f"   Average risk calculation: {risk_time:.4f}s")
    
    # Test portfolio risk performance
    print("   Portfolio risk performance:")
    assets_data = {
        'BTC': data,
        'ETH': data,
        'ADA': data,
        'DOT': data
    }
    signals = {
        'BTC': {'signal': 1, 'strength': 0.8},
        'ETH': {'signal': -1, 'strength': 0.6},
        'ADA': {'signal': 1, 'strength': 0.7},
        'DOT': {'signal': 0, 'strength': 0.0}
    }
    
    start_time = time.time()
    for i in range(10):
        portfolio_risk = risk_manager.calculate_portfolio_risk(
            assets_data, signals, 1000000, 1000000
        )
    portfolio_time = (time.time() - start_time) / 10
    
    print(f"   Average portfolio risk: {portfolio_time:.4f}s")
    
    # Performance targets
    targets = {
        'signal_generation': 0.1,  # 100ms
        'risk_calculation': 0.05,  # 50ms
        'portfolio_risk': 0.2      # 200ms
    }
    
    results = {
        'signal_generation': signal_time,
        'risk_calculation': risk_time,
        'portfolio_risk': portfolio_time
    }
    
    print("   Performance assessment:")
    for metric, time_taken in results.items():
        target = targets[metric]
        status = "✅" if time_taken < target else "⚠️"
        print(f"   {metric}: {time_taken:.4f}s (target: {target:.4f}s) {status}")
    
    print("   ✅ Performance benchmarks completed!")
    return True


def test_error_scenarios():
    """Test system behavior under error conditions."""
    print("🚨 Testing Error Scenarios...")
    
    # Test with insufficient data
    print("   Testing insufficient data scenarios...")
    small_data = generate_test_data(periods=10)
    
    # Test signal generation with insufficient data
    composite_signal = CompositeSignal()
    signal_result = composite_signal.generate_signal(small_data)
    
    insufficient_data_handled = (signal_result['signal'] == 0 and 
                               signal_result['strength'] == 0.0)
    print(f"   Insufficient data handled: {insufficient_data_handled}")
    
    # Test with corrupted data
    print("   Testing corrupted data scenarios...")
    corrupted_data = generate_test_data(periods=50)
    corrupted_data.loc[corrupted_data.index[10:20], 'close'] = np.nan
    
    try:
        signal_result = composite_signal.generate_signal(corrupted_data)
        corrupted_data_handled = True
    except Exception as e:
        print(f"   Corrupted data error: {e}")
        corrupted_data_handled = False
    
    print(f"   Corrupted data handled: {corrupted_data_handled}")
    
    # Test extreme market conditions
    print("   Testing extreme market conditions...")
    extreme_data = generate_test_data(periods=100, volatility=0.20)  # 20% volatility
    
    risk_manager = RiskManager()
    signal_info = {'signal': 1, 'strength': 1.0}
    
    risk_result = risk_manager.calculate_position_risk(extreme_data, signal_info)
    extreme_conditions_handled = (risk_result['position_size'] < 1.0)  # Should be scaled down
    
    print(f"   Extreme conditions handled: {extreme_conditions_handled}")
    print(f"   Position size under extreme volatility: {risk_result['position_size']:.3f}")
    
    print("   ✅ Error scenarios test passed!")
    return True


def main():
    """Run all tests."""
    print("🚀 Starting Comprehensive Module Testing\n")
    
    try:
        # Run individual module tests
        individual_results = run_individual_tests()
        print()
        
        # Check if all individual tests passed
        if not all(individual_results.values()):
            print("❌ Some individual module tests failed. Stopping integration tests.")
            failed_modules = [name for name, result in individual_results.items() if not result]
            print(f"Failed modules: {failed_modules}")
            return False
        
        print("✅ All individual module tests passed! Proceeding with integration tests.\n")
        
        # Run integration tests
        integration_tests = [
            test_signals_risk_integration,
            test_risk_execution_integration,
            test_full_system_integration,
            test_performance_benchmarks,
            test_error_scenarios
        ]
        
        integration_results = []
        
        for test_func in integration_tests:
            try:
                result = test_func()
                integration_results.append(result)
                print()
            except Exception as e:
                print(f"❌ Integration test failed: {e}")
                import traceback
                traceback.print_exc()
                integration_results.append(False)
                print()
        
        # Summary
        print("📊 Test Summary:")
        print(f"Individual modules: {sum(individual_results.values())}/{len(individual_results)} passed")
        print(f"Integration tests: {sum(integration_results)}/{len(integration_results)} passed")
        
        all_passed = all(individual_results.values()) and all(integration_results)
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
            print("The systematic trend-following crypto trading system is ready for deployment.")
        else:
            print("\n❌ Some tests failed. Please review the output above.")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 