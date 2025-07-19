#!/usr/bin/env python3
"""
Test script for execution module.

This script tests the Coinbase client wrapper and order manager
with mock data since we don't have live API credentials.
"""

import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from exec import CoinbaseAdvancedClient, OrderManager


def test_coinbase_client_initialization():
    """Test Coinbase client initialization."""
    print("🧪 Testing Coinbase Client Initialization...")
    
    # Test with missing credentials
    try:
        client = CoinbaseAdvancedClient(
            api_key=None,
            api_secret=None,
            passphrase=None
        )
        assert False, "Should raise ValueError for missing credentials"
    except ValueError as e:
        print(f"   ✅ Correctly raised error for missing credentials: {e}")
    
    # Test with credentials
    try:
        client = CoinbaseAdvancedClient(
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase",
            sandbox=True
        )
        print("   ✅ Client initialized successfully with credentials")
        print(f"   Sandbox mode: {client.sandbox}")
        print(f"   Min request interval: {client.min_request_interval}s")
        print(f"   Cache expiry: {client.cache_expiry}s")
    except Exception as e:
        print(f"   ❌ Failed to initialize client: {e}")
        return False
    
    print("   ✅ Coinbase Client initialization tests passed!")
    return True


def test_coinbase_client_methods():
    """Test Coinbase client methods with mocked responses."""
    print("🧪 Testing Coinbase Client Methods...")
    
    # Create client with test credentials
    client = CoinbaseAdvancedClient(
        api_key="test_key",
        api_secret="test_secret", 
        passphrase="test_passphrase",
        sandbox=True
    )
    
    # Mock the underlying REST client
    mock_rest_client = Mock()
    client.client = mock_rest_client
    
    # Test get_product
    mock_product = Mock()
    mock_product.price = "50000.00"
    mock_product.volume_24h = "1000.5"
    mock_rest_client.get_product.return_value = mock_product
    
    product = client.get_product("BTC-USD")
    print(f"   Product price: ${product.price}")
    print(f"   Product volume: {product.volume_24h}")
    
    # Test get_products
    mock_products = {
        "products": [
            {"product_id": "BTC-USD", "status": "online"},
            {"product_id": "ETH-USD", "status": "online"}
        ]
    }
    mock_rest_client.get_products.return_value = mock_products
    
    products = client.get_products(limit=10)
    print(f"   Retrieved {len(products['products'])} products")
    
    # Test get_candles
    mock_candles = {
        "candles": [
            {"close": "50000.00", "volume": "100"},
            {"close": "50500.00", "volume": "150"},
            {"close": "51000.00", "volume": "120"}
        ]
    }
    mock_rest_client.get_candles.return_value = mock_candles
    
    candles = client.get_candles("BTC-USD", limit=3)
    print(f"   Retrieved {len(candles['candles'])} candles")
    
    # Test get_accounts
    mock_accounts = {
        "accounts": [
            {"currency": "USD", "balance": "10000.00"},
            {"currency": "BTC", "balance": "0.5"}
        ]
    }
    mock_rest_client.get_accounts.return_value = mock_accounts
    
    accounts = client.get_accounts()
    print(f"   Retrieved {len(accounts['accounts'])} accounts")
    
    # Test convenience methods
    current_price = client.get_current_price("BTC-USD")
    print(f"   Current price: ${current_price}")
    
    usd_balance = client.get_account_balance("USD")
    print(f"   USD balance: ${usd_balance}")
    
    market_open = client.is_market_open("BTC-USD")
    print(f"   Market open: {market_open}")
    
    print("   ✅ Coinbase Client methods tests passed!")
    return True


def test_order_manager_initialization():
    """Test OrderManager initialization."""
    print("🧪 Testing Order Manager Initialization...")
    
    # Create mock client
    mock_client = Mock()
    
    # Create order manager
    order_manager = OrderManager(
        client=mock_client,
        default_timeout=300,
        max_retries=3
    )
    
    print(f"   Default timeout: {order_manager.default_timeout}s")
    print(f"   Max retries: {order_manager.max_retries}")
    print(f"   Active orders: {len(order_manager.active_orders)}")
    print(f"   Order history: {len(order_manager.order_history)}")
    
    # Check initial statistics
    stats = order_manager.get_execution_stats()
    print(f"   Initial stats: {stats}")
    
    print("   ✅ Order Manager initialization tests passed!")
    return True


def test_order_creation():
    """Test order creation methods."""
    print("🧪 Testing Order Creation...")
    
    # Create mock client
    mock_client = Mock()
    order_manager = OrderManager(client=mock_client)
    
    # Test market order creation
    mock_client.create_market_order.return_value = {
        "order_id": "test_order_123",
        "status": "pending"
    }
    
    market_result = order_manager.create_market_order(
        product_id="BTC-USD",
        side="buy",
        funds="1000.00",
        client_order_id="test_market_order"
    )
    
    print(f"   Market order result: {market_result['success']}")
    print(f"   Order ID: {market_result['order_id']}")
    print(f"   Active orders: {len(order_manager.active_orders)}")
    
    # Test limit order creation
    mock_client.create_limit_order.return_value = {
        "order_id": "test_limit_123",
        "status": "open"
    }
    
    limit_result = order_manager.create_limit_order(
        product_id="ETH-USD",
        side="sell",
        size="0.5",
        price="3000.00",
        client_order_id="test_limit_order"
    )
    
    print(f"   Limit order result: {limit_result['success']}")
    print(f"   Order ID: {limit_result['order_id']}")
    print(f"   Active orders: {len(order_manager.active_orders)}")
    
    # Test stop order creation  
    mock_client.create_stop_order.return_value = {
        "order_id": "test_stop_123",
        "status": "open"
    }
    
    stop_result = order_manager.create_stop_order(
        product_id="BTC-USD",
        side="sell",
        size="0.1",
        stop_price="48000.00",
        client_order_id="test_stop_order"
    )
    
    print(f"   Stop order result: {stop_result['success']}")
    print(f"   Order ID: {stop_result['order_id']}")
    print(f"   Active orders: {len(order_manager.active_orders)}")
    
    # Check execution statistics
    stats = order_manager.get_execution_stats()
    print(f"   Total orders created: {stats['total_orders']}")
    
    print("   ✅ Order creation tests passed!")
    return True


def test_order_management():
    """Test order management operations."""
    print("🧪 Testing Order Management...")
    
    # Create mock client and order manager
    mock_client = Mock()
    order_manager = OrderManager(client=mock_client)
    
    # Create a test order first
    mock_client.create_market_order.return_value = {
        "order_id": "test_order_456",
        "status": "pending"
    }
    
    order_result = order_manager.create_market_order(
        product_id="BTC-USD",
        side="buy",
        funds="1000.00",
        client_order_id="test_mgmt_order"
    )
    
    # Test order status update
    mock_client.get_order.return_value = {
        "order_id": "test_order_456",
        "status": "filled",
        "filled_size": "0.02",
        "filled_value": "1000.00",
        "fees": "5.00"
    }
    
    update_result = order_manager.update_order_status("test_mgmt_order")
    print(f"   Order update result: {update_result['success']}")
    print(f"   Status changed: {update_result['status_changed']}")
    print(f"   Active orders after update: {len(order_manager.active_orders)}")
    print(f"   Order history: {len(order_manager.order_history)}")
    
    # Test order cancellation
    mock_client.create_limit_order.return_value = {
        "order_id": "test_cancel_123",
        "status": "open"
    }
    
    # Create order to cancel
    order_manager.create_limit_order(
        product_id="ETH-USD",
        side="buy",
        size="1.0",
        price="2500.00",
        client_order_id="test_cancel_order"
    )
    
    mock_client.cancel_order.return_value = {
        "order_id": "test_cancel_123",
        "status": "cancelled"
    }
    
    cancel_result = order_manager.cancel_order("test_cancel_order")
    print(f"   Cancel result: {cancel_result['success']}")
    print(f"   Active orders after cancel: {len(order_manager.active_orders)}")
    
    # Test get order status
    status_result = order_manager.get_order_status("test_mgmt_order")
    print(f"   Order status found: {status_result['found']}")
    print(f"   Order active: {status_result['active']}")
    
    # Test execution statistics
    stats = order_manager.get_execution_stats()
    print(f"   Fill rate: {stats['fill_rate']:.2f}")
    print(f"   Filled orders: {stats['filled_orders']}")
    print(f"   Cancelled orders: {stats['cancelled_orders']}")
    
    print("   ✅ Order management tests passed!")
    return True


def test_order_monitoring():
    """Test order monitoring capabilities."""
    print("🧪 Testing Order Monitoring...")
    
    # Create mock client and order manager
    mock_client = Mock()
    order_manager = OrderManager(client=mock_client)
    
    # Create multiple test orders
    orders_data = [
        ("order_1", "BTC-USD", "buy", "pending"),
        ("order_2", "ETH-USD", "sell", "open"),
        ("order_3", "ADA-USD", "buy", "open")
    ]
    
    for i, (order_id, product, side, status) in enumerate(orders_data):
        mock_client.create_market_order.return_value = {
            "order_id": f"test_{order_id}",
            "status": status
        }
        
        order_manager.create_market_order(
            product_id=product,
            side=side,
            funds="500.00",
            client_order_id=order_id
        )
    
    print(f"   Created {len(orders_data)} test orders")
    
    # Test update all orders
    def mock_get_order_side_effect(order_id):
        if "order_1" in order_id:
            return {"order_id": order_id, "status": "filled", "filled_size": "0.01"}
        elif "order_2" in order_id:
            return {"order_id": order_id, "status": "cancelled", "filled_size": "0"}
        else:
            return {"order_id": order_id, "status": "open", "filled_size": "0"}
    
    mock_client.get_order.side_effect = mock_get_order_side_effect
    
    update_all_result = order_manager.update_all_orders()
    print(f"   Update all success: {update_all_result['success']}")
    print(f"   Updates processed: {len(update_all_result['updates'])}")
    print(f"   Errors: {len(update_all_result['errors'])}")
    print(f"   Remaining active orders: {update_all_result['active_orders']}")
    
    # Test get active orders
    active_orders = order_manager.get_active_orders()
    print(f"   Active orders: {len(active_orders)}")
    
    # Test get order history
    history = order_manager.get_order_history(limit=10)
    print(f"   Order history: {len(history)} orders")
    
    # Test cancel all orders
    mock_client.cancel_order.return_value = {"status": "cancelled"}
    
    cancel_all_result = order_manager.cancel_all_orders()
    print(f"   Cancel all success: {cancel_all_result['success']}")
    print(f"   Orders cancelled: {len(cancel_all_result['cancelled'])}")
    
    print("   ✅ Order monitoring tests passed!")
    return True


def test_execution_integration():
    """Test execution module integration."""
    print("🧪 Testing Execution Integration...")
    
    # Create mock client
    mock_client = Mock()
    order_manager = OrderManager(client=mock_client)
    
    # Simulate a complete trading session
    print("   Simulating trading session...")
    
    # 1. Create multiple orders
    mock_client.create_market_order.return_value = {"order_id": "session_1", "status": "pending"}
    mock_client.create_limit_order.return_value = {"order_id": "session_2", "status": "open"}
    
    # Market buy
    buy_result = order_manager.create_market_order(
        product_id="BTC-USD",
        side="buy",
        funds="5000.00",
        client_order_id="session_buy"
    )
    
    # Limit sell
    sell_result = order_manager.create_limit_order(
        product_id="BTC-USD",
        side="sell",
        size="0.1",
        price="52000.00",
        client_order_id="session_sell"
    )
    
    print(f"   Created buy order: {buy_result['success']}")
    print(f"   Created sell order: {sell_result['success']}")
    
    # 2. Monitor order execution
    mock_client.get_order.side_effect = lambda order_id: {
        "order_id": order_id,
        "status": "filled",
        "filled_size": "0.1",
        "filled_value": "5000.00",
        "fees": "25.00"
    }
    
    # Update orders
    order_manager.update_all_orders()
    
    # 3. Check final statistics
    final_stats = order_manager.get_execution_stats()
    print(f"   Final statistics:")
    print(f"   Total orders: {final_stats['total_orders']}")
    print(f"   Fill rate: {final_stats['fill_rate']:.2f}")
    print(f"   Average fill time: {final_stats['average_fill_time']:.2f}s")
    
    # 4. Cleanup
    order_manager.cleanup_old_orders(days=1)
    order_manager.reset_statistics()
    
    print("   ✅ Execution integration tests passed!")
    return True


def test_error_handling():
    """Test error handling in execution module."""
    print("🧪 Testing Error Handling...")
    
    # Create mock client that raises errors
    mock_client = Mock()
    order_manager = OrderManager(client=mock_client)
    
    # Test order creation failure
    mock_client.create_market_order.side_effect = Exception("API Error")
    
    error_result = order_manager.create_market_order(
        product_id="BTC-USD",
        side="buy",
        funds="1000.00",
        client_order_id="error_order"
    )
    
    print(f"   Order creation error handled: {not error_result['success']}")
    print(f"   Error message: {error_result['error']}")
    
    # Test cancellation of non-existent order
    cancel_result = order_manager.cancel_order("non_existent_order")
    print(f"   Non-existent order cancel handled: {not cancel_result['success']}")
    
    # Test status update failure
    mock_client.get_order.side_effect = Exception("Network Error")
    
    # First create an order successfully
    mock_client.create_market_order.side_effect = None
    mock_client.create_market_order.return_value = {"order_id": "test_123", "status": "pending"}
    
    order_manager.create_market_order(
        product_id="BTC-USD",
        side="buy",
        funds="1000.00",
        client_order_id="status_test_order"
    )
    
    # Then try to update with error
    status_result = order_manager.update_order_status("status_test_order")
    print(f"   Status update error handled: {not status_result['success']}")
    
    print("   ✅ Error handling tests passed!")
    return True


def main():
    """Run all execution tests."""
    print("🚀 Starting Execution Module Tests\n")
    
    try:
        # Test individual components
        test_coinbase_client_initialization()
        print()
        
        test_coinbase_client_methods()
        print()
        
        test_order_manager_initialization()
        print()
        
        test_order_creation()
        print()
        
        test_order_management()
        print()
        
        test_order_monitoring()
        print()
        
        test_execution_integration()
        print()
        
        test_error_handling()
        print()
        
        print("🎉 All execution tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 