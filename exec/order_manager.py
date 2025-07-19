"""
Order management system for systematic trading.

This module handles order creation, monitoring, and lifecycle management
for systematic trading strategies.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

from .cb_adv_client import CoinbaseAdvancedClient


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderManager:
    """
    Order management system for systematic trading.
    
    Handles order creation, monitoring, and lifecycle management
    with support for different order types and execution strategies.
    """
    
    def __init__(self, 
                 client: CoinbaseAdvancedClient,
                 default_timeout: int = 300,
                 max_retries: int = 3):
        """
        Initialize order manager.
        
        Args:
            client: Coinbase Advanced client
            default_timeout: Default order timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.client = client
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        
        # Track active orders
        self.active_orders = {}
        self.order_history = []
        
        # Execution statistics
        self.execution_stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'cancelled_orders': 0,
            'rejected_orders': 0,
            'total_fill_time': 0,
            'average_fill_time': 0
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def create_market_order(self, 
                          product_id: str,
                          side: str,
                          size: str = None,
                          funds: str = None,
                          client_order_id: str = None) -> Dict[str, Any]:
        """
        Create a market order.
        
        Args:
            product_id: Product ID
            side: Order side ("buy" or "sell")
            size: Order size in base currency
            funds: Order size in quote currency
            client_order_id: Client-specified order ID
            
        Returns:
            Order creation result
        """
        order_id = client_order_id or f"market_{int(time.time())}"
        
        try:
            # Create the order
            order_response = self.client.create_market_order(
                product_id=product_id,
                side=side,
                size=size,
                funds=funds,
                client_order_id=order_id
            )
            
            # Track the order
            order_info = {
                'order_id': order_response.get('order_id'),
                'client_order_id': order_id,
                'product_id': product_id,
                'side': side,
                'type': OrderType.MARKET.value,
                'size': size,
                'funds': funds,
                'status': OrderStatus.PENDING.value,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'filled_size': '0',
                'filled_value': '0',
                'fees': '0',
                'response': order_response
            }
            
            self.active_orders[order_id] = order_info
            self.execution_stats['total_orders'] += 1
            
            self.logger.info(f"Created market order: {order_id} for {product_id}")
            
            return {
                'success': True,
                'order_id': order_id,
                'order_info': order_info,
                'response': order_response
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create market order: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id
            }
    
    def create_limit_order(self, 
                         product_id: str,
                         side: str,
                         size: str,
                         price: str,
                         time_in_force: str = "GTC",
                         client_order_id: str = None) -> Dict[str, Any]:
        """
        Create a limit order.
        
        Args:
            product_id: Product ID
            side: Order side ("buy" or "sell")
            size: Order size in base currency
            price: Limit price
            time_in_force: Time in force
            client_order_id: Client-specified order ID
            
        Returns:
            Order creation result
        """
        order_id = client_order_id or f"limit_{int(time.time())}"
        
        try:
            # Create the order
            order_response = self.client.create_limit_order(
                product_id=product_id,
                side=side,
                size=size,
                price=price,
                time_in_force=time_in_force,
                client_order_id=order_id
            )
            
            # Track the order
            order_info = {
                'order_id': order_response.get('order_id'),
                'client_order_id': order_id,
                'product_id': product_id,
                'side': side,
                'type': OrderType.LIMIT.value,
                'size': size,
                'price': price,
                'time_in_force': time_in_force,
                'status': OrderStatus.OPEN.value,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'filled_size': '0',
                'filled_value': '0',
                'fees': '0',
                'response': order_response
            }
            
            self.active_orders[order_id] = order_info
            self.execution_stats['total_orders'] += 1
            
            self.logger.info(f"Created limit order: {order_id} for {product_id} at {price}")
            
            return {
                'success': True,
                'order_id': order_id,
                'order_info': order_info,
                'response': order_response
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create limit order: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id
            }
    
    def create_stop_order(self, 
                        product_id: str,
                        side: str,
                        size: str,
                        stop_price: str,
                        client_order_id: str = None) -> Dict[str, Any]:
        """
        Create a stop order.
        
        Args:
            product_id: Product ID
            side: Order side ("buy" or "sell")
            size: Order size in base currency
            stop_price: Stop price
            client_order_id: Client-specified order ID
            
        Returns:
            Order creation result
        """
        order_id = client_order_id or f"stop_{int(time.time())}"
        
        try:
            # Create the order
            order_response = self.client.create_stop_order(
                product_id=product_id,
                side=side,
                size=size,
                stop_price=stop_price,
                client_order_id=order_id
            )
            
            # Track the order
            order_info = {
                'order_id': order_response.get('order_id'),
                'client_order_id': order_id,
                'product_id': product_id,
                'side': side,
                'type': OrderType.STOP.value,
                'size': size,
                'stop_price': stop_price,
                'status': OrderStatus.OPEN.value,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'filled_size': '0',
                'filled_value': '0',
                'fees': '0',
                'response': order_response
            }
            
            self.active_orders[order_id] = order_info
            self.execution_stats['total_orders'] += 1
            
            self.logger.info(f"Created stop order: {order_id} for {product_id} at {stop_price}")
            
            return {
                'success': True,
                'order_id': order_id,
                'order_info': order_info,
                'response': order_response
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create stop order: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id
            }
    
    def cancel_order(self, client_order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            Cancellation result
        """
        if client_order_id not in self.active_orders:
            return {
                'success': False,
                'error': 'Order not found in active orders'
            }
        
        order_info = self.active_orders[client_order_id]
        order_id = order_info['order_id']
        
        try:
            # Cancel the order
            cancel_response = self.client.cancel_order(order_id)
            
            # Update order status
            order_info['status'] = OrderStatus.CANCELLED.value
            order_info['updated_at'] = datetime.now()
            
            # Move to history
            self.order_history.append(order_info)
            del self.active_orders[client_order_id]
            
            self.execution_stats['cancelled_orders'] += 1
            
            self.logger.info(f"Cancelled order: {client_order_id}")
            
            return {
                'success': True,
                'order_id': client_order_id,
                'response': cancel_response
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order {client_order_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': client_order_id
            }
    
    def update_order_status(self, client_order_id: str) -> Dict[str, Any]:
        """
        Update order status from exchange.
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            Updated order information
        """
        if client_order_id not in self.active_orders:
            return {
                'success': False,
                'error': 'Order not found in active orders'
            }
        
        order_info = self.active_orders[client_order_id]
        order_id = order_info['order_id']
        
        try:
            # Get current order status
            order_response = self.client.get_order(order_id)
            
            # Update order information
            old_status = order_info['status']
            order_info['status'] = order_response.get('status', old_status)
            order_info['filled_size'] = order_response.get('filled_size', '0')
            order_info['filled_value'] = order_response.get('filled_value', '0')
            order_info['fees'] = order_response.get('fees', '0')
            order_info['updated_at'] = datetime.now()
            
            # Move to history if completed
            if order_info['status'] in [OrderStatus.FILLED.value, 
                                      OrderStatus.CANCELLED.value,
                                      OrderStatus.REJECTED.value,
                                      OrderStatus.EXPIRED.value]:
                self.order_history.append(order_info)
                del self.active_orders[client_order_id]
                
                # Update statistics
                if order_info['status'] == OrderStatus.FILLED.value:
                    self.execution_stats['filled_orders'] += 1
                    fill_time = (order_info['updated_at'] - order_info['created_at']).total_seconds()
                    self.execution_stats['total_fill_time'] += fill_time
                    self.execution_stats['average_fill_time'] = (
                        self.execution_stats['total_fill_time'] / 
                        self.execution_stats['filled_orders']
                    )
                elif order_info['status'] == OrderStatus.REJECTED.value:
                    self.execution_stats['rejected_orders'] += 1
            
            return {
                'success': True,
                'order_id': client_order_id,
                'order_info': order_info,
                'status_changed': old_status != order_info['status']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update order status {client_order_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': client_order_id
            }
    
    def update_all_orders(self) -> Dict[str, Any]:
        """
        Update status of all active orders.
        
        Returns:
            Summary of updates
        """
        updates = []
        errors = []
        
        for client_order_id in list(self.active_orders.keys()):
            result = self.update_order_status(client_order_id)
            if result['success']:
                updates.append(result)
            else:
                errors.append(result)
        
        return {
            'success': len(errors) == 0,
            'updates': updates,
            'errors': errors,
            'active_orders': len(self.active_orders)
        }
    
    def get_order_status(self, client_order_id: str) -> Dict[str, Any]:
        """
        Get current order status.
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            Order status information
        """
        # Check active orders
        if client_order_id in self.active_orders:
            return {
                'found': True,
                'active': True,
                'order_info': self.active_orders[client_order_id]
            }
        
        # Check history
        for order in self.order_history:
            if order['client_order_id'] == client_order_id:
                return {
                    'found': True,
                    'active': False,
                    'order_info': order
                }
        
        return {
            'found': False,
            'active': False,
            'order_info': None
        }
    
    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active orders.
        
        Returns:
            Dictionary of active orders
        """
        return self.active_orders.copy()
    
    def get_order_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get order history.
        
        Args:
            limit: Maximum number of orders to return
            
        Returns:
            List of historical orders
        """
        return self.order_history[-limit:] if limit else self.order_history
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        stats = self.execution_stats.copy()
        
        # Calculate additional metrics
        if stats['total_orders'] > 0:
            stats['fill_rate'] = stats['filled_orders'] / stats['total_orders']
            stats['rejection_rate'] = stats['rejected_orders'] / stats['total_orders']
            stats['cancellation_rate'] = stats['cancelled_orders'] / stats['total_orders']
        else:
            stats['fill_rate'] = 0.0
            stats['rejection_rate'] = 0.0
            stats['cancellation_rate'] = 0.0
        
        return stats
    
    def cancel_all_orders(self) -> Dict[str, Any]:
        """
        Cancel all active orders.
        
        Returns:
            Summary of cancellations
        """
        cancelled = []
        errors = []
        
        for client_order_id in list(self.active_orders.keys()):
            result = self.cancel_order(client_order_id)
            if result['success']:
                cancelled.append(result)
            else:
                errors.append(result)
        
        return {
            'success': len(errors) == 0,
            'cancelled': cancelled,
            'errors': errors
        }
    
    def cleanup_old_orders(self, days: int = 7):
        """
        Clean up old orders from history.
        
        Args:
            days: Number of days to keep in history
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        self.order_history = [
            order for order in self.order_history
            if order['created_at'] > cutoff_date
        ]
        
        self.logger.info(f"Cleaned up orders older than {days} days")
    
    def reset_statistics(self):
        """Reset execution statistics."""
        self.execution_stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'cancelled_orders': 0,
            'rejected_orders': 0,
            'total_fill_time': 0,
            'average_fill_time': 0
        } 