"""
Main risk management coordinator for systematic trading.

This module coordinates all risk management components including position sizing,
stop losses, and drawdown control to provide comprehensive risk management.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime

from .position_sizing import VolatilitySizing
from .stops import ATRStop
from .drawdown import DrawdownControl


class RiskManager:
    """
    Main risk management coordinator.
    
    Coordinates position sizing, stop losses, and drawdown control
    to provide comprehensive risk management for systematic trading.
    """
    
    def __init__(self, 
                 volatility_sizing: VolatilitySizing = None,
                 atr_stop: ATRStop = None,
                 drawdown_control: DrawdownControl = None):
        """
        Initialize risk manager with individual components.
        
        Args:
            volatility_sizing: VolatilitySizing instance (default: create with defaults)
            atr_stop: ATRStop instance (default: create with defaults)
            drawdown_control: DrawdownControl instance (default: create with defaults)
        """
        self.volatility_sizing = volatility_sizing or VolatilitySizing()
        self.atr_stop = atr_stop or ATRStop()
        self.drawdown_control = drawdown_control or DrawdownControl()
        
        # Risk override flags
        self.risk_override = False
        self.max_portfolio_leverage = 3.0
        self.max_single_position_size = 0.20  # 20% of portfolio max
        
        # Performance tracking
        self.last_portfolio_value = None
        self.last_update_time = None
    
    def calculate_position_risk(self, 
                              data: pd.DataFrame,
                              signal_info: Dict[str, Any],
                              current_price: float = None,
                              asset_id: str = None) -> Dict[str, Any]:
        """
        Calculate comprehensive position risk metrics.
        
        Args:
            data: DataFrame with OHLCV data
            signal_info: Signal information with strength and direction
            current_price: Current market price
            asset_id: Asset identifier
            
        Returns:
            Dictionary with position risk metrics
        """
        if current_price is None:
            current_price = float(data['close'].iloc[-1])
        
        signal_strength = signal_info.get('strength', 0.0)
        signal_direction = signal_info.get('signal', 0)
        
        # Calculate position size
        sizing_result = self.volatility_sizing.calculate_position_size(
            data, signal_strength, current_price
        )
        
        # Apply drawdown scaling
        drawdown_scale = self.drawdown_control.get_position_scale_factor()
        scaled_position_size = sizing_result['position_size'] * drawdown_scale
        
        # Calculate stop loss
        stop_result = self.atr_stop.calculate_stop_level(
            data, signal_direction, current_price, asset_id
        )
        
        # Calculate risk per share
        if stop_result['stop_level'] is not None:
            risk_per_share = abs(current_price - stop_result['stop_level'])
            risk_percentage = risk_per_share / current_price
        else:
            risk_per_share = None
            risk_percentage = None
        
        # Apply position size limits
        final_position_size = min(
            abs(scaled_position_size),
            self.max_single_position_size
        )
        
        # Maintain signal direction
        if signal_direction < 0:
            final_position_size = -final_position_size
        
        return {
            'position_size': final_position_size,
            'original_size': sizing_result['position_size'],
            'drawdown_scale': drawdown_scale,
            'stop_level': stop_result['stop_level'],
            'risk_per_share': risk_per_share,
            'risk_percentage': risk_percentage,
            'atr': stop_result.get('atr'),
            'volatility': sizing_result['volatility'],
            'signal_strength': signal_strength,
            'current_price': current_price,
            'sizing_error': sizing_result.get('error'),
            'stop_error': stop_result.get('error')
        }
    
    def calculate_portfolio_risk(self, 
                               assets_data: Dict[str, pd.DataFrame],
                               signals: Dict[str, Dict[str, Any]],
                               current_portfolio_value: float,
                               total_capital: float = 1000000.0) -> Dict[str, Any]:
        """
        Calculate portfolio-level risk metrics.
        
        Args:
            assets_data: Dictionary mapping asset names to OHLCV data
            signals: Dictionary mapping asset names to signal information
            current_portfolio_value: Current portfolio value
            total_capital: Total capital available
            
        Returns:
            Dictionary with portfolio risk metrics
        """
        # Update drawdown control
        drawdown_update = self.drawdown_control.update_portfolio_value(
            current_portfolio_value
        )
        
        # Calculate individual position risks
        position_risks = {}
        total_leverage = 0.0
        total_risk = 0.0
        
        for asset_name, data in assets_data.items():
            if asset_name not in signals:
                continue
            
            signal_info = signals[asset_name]
            
            # Calculate position risk
            risk_result = self.calculate_position_risk(
                data, signal_info, asset_id=asset_name
            )
            
            position_risks[asset_name] = risk_result
            total_leverage += abs(risk_result['position_size'])
            
            # Calculate position risk in dollar terms
            if risk_result['risk_percentage'] is not None:
                position_dollar_risk = (
                    abs(risk_result['position_size']) * 
                    total_capital * 
                    risk_result['risk_percentage']
                )
                total_risk += position_dollar_risk
        
        # Portfolio-level risk metrics
        portfolio_risk_percentage = total_risk / total_capital if total_capital > 0 else 0.0
        
        # Check for risk violations
        violations = []
        
        if total_leverage > self.max_portfolio_leverage:
            violations.append(f"Portfolio leverage {total_leverage:.2f} exceeds maximum {self.max_portfolio_leverage}")
        
        if portfolio_risk_percentage > 0.05:  # 5% portfolio risk threshold
            violations.append(f"Portfolio risk {portfolio_risk_percentage:.2%} exceeds 5% threshold")
        
        if drawdown_update['halt_trading']:
            violations.append(f"Trading halted due to {drawdown_update['current_drawdown']:.2%} drawdown")
        
        return {
            'position_risks': position_risks,
            'total_leverage': total_leverage,
            'total_risk': total_risk,
            'portfolio_risk_percentage': portfolio_risk_percentage,
            'drawdown_metrics': drawdown_update,
            'violations': violations,
            'halt_trading': drawdown_update['halt_trading'],
            'scale_factor': drawdown_update['scale_factor']
        }
    
    def check_stop_losses(self, 
                         current_prices: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        Check stop losses for all positions.
        
        Args:
            current_prices: Dictionary mapping asset names to current prices
            
        Returns:
            Dictionary with stop loss check results
        """
        stop_results = {}
        
        for asset_name, current_price in current_prices.items():
            stop_check = self.atr_stop.check_stop_triggered(current_price, asset_name)
            stop_results[asset_name] = stop_check
        
        return stop_results
    
    def update_trailing_stops(self, 
                            assets_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
        """
        Update trailing stops for all positions.
        
        Args:
            assets_data: Dictionary mapping asset names to OHLCV data
            
        Returns:
            Dictionary with trailing stop update results
        """
        update_results = {}
        
        for asset_name, data in assets_data.items():
            update_result = self.atr_stop.update_stop_level(data, asset_name)
            update_results[asset_name] = update_result
        
        return update_results
    
    def should_reduce_exposure(self) -> bool:
        """
        Check if overall exposure should be reduced.
        
        Returns:
            True if exposure should be reduced
        """
        return (
            self.drawdown_control.should_halt_trading() or
            self.drawdown_control.get_position_scale_factor() < 1.0
        )
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive risk summary.
        
        Returns:
            Dictionary with risk summary
        """
        return {
            'volatility_sizing': self.volatility_sizing.get_sizing_info(),
            'atr_stops': self.atr_stop.get_stop_config(),
            'drawdown_control': self.drawdown_control.get_drawdown_config(),
            'risk_metrics': self.drawdown_control.get_risk_metrics(),
            'active_stops': self.atr_stop.get_all_stops(),
            'max_portfolio_leverage': self.max_portfolio_leverage,
            'max_single_position_size': self.max_single_position_size,
            'risk_override': self.risk_override
        }
    
    def reset_risk_tracking(self):
        """Reset all risk tracking."""
        self.drawdown_control.reset_tracking()
        self.atr_stop.stop_levels.clear()
        self.atr_stop.entry_prices.clear()
        self.atr_stop.position_directions.clear()
        self.last_portfolio_value = None
        self.last_update_time = None
    
    def set_risk_override(self, override: bool):
        """
        Set risk override flag.
        
        Args:
            override: True to override risk controls
        """
        self.risk_override = override
        print(f"Risk override set to: {override}")
    
    def validate_trade(self, 
                      asset_name: str,
                      position_size: float,
                      current_price: float,
                      total_capital: float) -> Dict[str, Any]:
        """
        Validate a potential trade against risk limits.
        
        Args:
            asset_name: Asset name
            position_size: Proposed position size
            current_price: Current market price
            total_capital: Total capital available
            
        Returns:
            Dictionary with validation results
        """
        validation_errors = []
        
        # Check if trading is halted
        if self.drawdown_control.should_halt_trading() and not self.risk_override:
            validation_errors.append("Trading halted due to excessive drawdown")
        
        # Check position size limits
        position_value = abs(position_size) * current_price
        position_percentage = position_value / total_capital
        
        if position_percentage > self.max_single_position_size:
            validation_errors.append(
                f"Position size {position_percentage:.2%} exceeds maximum "
                f"{self.max_single_position_size:.2%}"
            )
        
        # Check if stop loss exists for the position
        if asset_name not in self.atr_stop.stop_levels:
            validation_errors.append(f"No stop loss set for {asset_name}")
        
        return {
            'valid': len(validation_errors) == 0,
            'errors': validation_errors,
            'position_value': position_value,
            'position_percentage': position_percentage,
            'trading_halted': self.drawdown_control.should_halt_trading()
        } 