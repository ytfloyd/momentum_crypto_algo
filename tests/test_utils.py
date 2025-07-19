"""
Unit tests for the agent utilities module.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from agent.utils import (
    round_step,
    format_currency,
    calculate_portfolio_value,
    calculate_current_weights,
    calculate_rebalance_trades,
    validate_trade_params,
)
from agent import config


class TestRoundStep:
    """Test the round_step function."""

    def test_round_step_basic(self):
        """Test basic rounding functionality."""
        result = round_step(Decimal("10.5"), Decimal("0.1"))
        assert result == Decimal("10.5")

    def test_round_step_down(self):
        """Test rounding down."""
        result = round_step(Decimal("10.67"), Decimal("0.1"))
        assert result == Decimal("10.6")

    def test_round_step_zero_step(self):
        """Test with zero step size."""
        result = round_step(Decimal("10.67"), Decimal("0"))
        assert result == Decimal("10.67")

    def test_round_step_large_step(self):
        """Test with large step size."""
        result = round_step(Decimal("10.67"), Decimal("5"))
        assert result == Decimal("10")

    def test_round_step_exact_multiple(self):
        """Test with exact multiple."""
        result = round_step(Decimal("10.0"), Decimal("0.1"))
        assert result == Decimal("10.0")

    def test_round_step_small_values(self):
        """Test with small values."""
        result = round_step(Decimal("0.0012345"), Decimal("0.0001"))
        assert result == Decimal("0.0012")

    def test_round_step_crypto_precision(self):
        """Test with crypto-like precision."""
        result = round_step(Decimal("1.23456789"), Decimal("0.00000001"))
        assert result == Decimal("1.23456789")


class TestFormatCurrency:
    """Test the format_currency function."""

    def test_format_usd(self):
        """Test USD formatting."""
        result = format_currency(Decimal("1234.56"))
        assert result == "$1,234.56"

    def test_format_crypto(self):
        """Test crypto formatting."""
        result = format_currency(Decimal("1.23456789"), "BTC")
        assert result == "1.23456789 BTC"

    def test_format_large_amount(self):
        """Test large amount formatting."""
        result = format_currency(Decimal("1000000.50"))
        assert result == "$1,000,000.50"

    def test_format_zero(self):
        """Test zero formatting."""
        result = format_currency(Decimal("0"))
        assert result == "$0.00"


class TestCalculatePortfolioValue:
    """Test the calculate_portfolio_value function."""

    def test_calculate_portfolio_value_basic(self):
        """Test basic portfolio value calculation."""
        positions = {
            "BTC-USD": Decimal("1.0"),
            "ETH-USD": Decimal("10.0"),
        }
        prices = {
            "BTC-USD": Decimal("50000.0"),
            "ETH-USD": Decimal("3000.0"),
        }
        result = calculate_portfolio_value(positions, prices)
        assert result == Decimal("80000.0")

    def test_calculate_portfolio_value_empty(self):
        """Test with empty portfolio."""
        positions = {}
        prices = {}
        result = calculate_portfolio_value(positions, prices)
        assert result == Decimal("0")

    def test_calculate_portfolio_value_missing_prices(self):
        """Test with missing prices."""
        positions = {
            "BTC-USD": Decimal("1.0"),
            "ETH-USD": Decimal("10.0"),
        }
        prices = {
            "BTC-USD": Decimal("50000.0"),
            # ETH-USD price missing
        }
        result = calculate_portfolio_value(positions, prices)
        assert result == Decimal("50000.0")


class TestCalculateCurrentWeights:
    """Test the calculate_current_weights function."""

    def test_calculate_current_weights_basic(self):
        """Test basic weight calculation."""
        positions = {
            "BTC-USD": Decimal("1.0"),
            "ETH-USD": Decimal("10.0"),
        }
        prices = {
            "BTC-USD": Decimal("50000.0"),
            "ETH-USD": Decimal("3000.0"),
        }
        result = calculate_current_weights(positions, prices)
        expected = {
            "BTC-USD": Decimal("0.625"),  # 50000 / 80000
            "ETH-USD": Decimal("0.375"),  # 30000 / 80000
        }
        assert result == expected

    def test_calculate_current_weights_zero_portfolio(self):
        """Test with zero portfolio value."""
        positions = {}
        prices = {}
        result = calculate_current_weights(positions, prices)
        assert result == {}

    def test_calculate_current_weights_missing_prices(self):
        """Test with missing prices."""
        positions = {
            "BTC-USD": Decimal("1.0"),
            "ETH-USD": Decimal("10.0"),
        }
        prices = {
            "BTC-USD": Decimal("50000.0"),
            # ETH-USD price missing
        }
        result = calculate_current_weights(positions, prices)
        expected = {
            "BTC-USD": Decimal("1.0"),  # 50000 / 50000
        }
        assert result == expected


class TestCalculateRebalanceTrades:
    """Test the calculate_rebalance_trades function."""

    def test_calculate_rebalance_trades_basic(self):
        """Test basic rebalance calculation."""
        current_weights = {
            "BTC-USD": Decimal("0.5"),
            "ETH-USD": Decimal("0.5"),
        }
        target_weights = {
            "BTC-USD": Decimal("0.6"),
            "ETH-USD": Decimal("0.4"),
        }
        total_value = Decimal("10000")
        prices = {
            "BTC-USD": Decimal("50000"),
            "ETH-USD": Decimal("3000"),
        }
        
        result = calculate_rebalance_trades(current_weights, target_weights, total_value, prices, cash_buffer=Decimal("0"))
        
        # BTC needs to increase by 10% = $1000, quantity = 1000/50000 = 0.02
        # ETH needs to decrease by 10% = $1000, quantity = 1000/3000 = 0.333...
        
        assert "BTC-USD" in result
        assert "ETH-USD" in result
        assert result["BTC-USD"][0] == "buy"
        assert result["ETH-USD"][0] == "sell"
        assert result["BTC-USD"][1] == Decimal("1000") / Decimal("50000")
        assert result["ETH-USD"][1] == Decimal("1000") / Decimal("3000")

    def test_calculate_rebalance_trades_within_tolerance(self):
        """Test when portfolio is within tolerance."""
        current_weights = {
            "BTC-USD": Decimal("0.5"),
            "ETH-USD": Decimal("0.5"),
        }
        target_weights = {
            "BTC-USD": Decimal("0.502"),  # Only 0.2% difference
            "ETH-USD": Decimal("0.498"),
        }
        total_value = Decimal("10000")
        prices = {
            "BTC-USD": Decimal("50000"),
            "ETH-USD": Decimal("3000"),
        }
        
        result = calculate_rebalance_trades(current_weights, target_weights, total_value, prices)
        
        # Should be empty since differences are within tolerance (0.7%)
        assert result == {}

    def test_calculate_rebalance_trades_below_minimum(self):
        """Test trades below minimum notional."""
        current_weights = {
            "BTC-USD": Decimal("0.5"),
        }
        target_weights = {
            "BTC-USD": Decimal("0.51"),  # 1% difference
        }
        total_value = Decimal("100")  # Small portfolio
        prices = {
            "BTC-USD": Decimal("50000"),
        }
        
        result = calculate_rebalance_trades(current_weights, target_weights, total_value, prices)
        
        # Trade value = 1% of $100 = $1, which is below MIN_NOTIONAL ($10)
        assert result == {}

    def test_calculate_rebalance_trades_missing_prices(self):
        """Test with missing prices."""
        current_weights = {
            "BTC-USD": Decimal("0.5"),
            "ETH-USD": Decimal("0.5"),
        }
        target_weights = {
            "BTC-USD": Decimal("0.6"),
            "ETH-USD": Decimal("0.4"),
        }
        total_value = Decimal("10000")
        prices = {
            "BTC-USD": Decimal("50000"),
            # ETH-USD price missing
        }
        
        result = calculate_rebalance_trades(current_weights, target_weights, total_value, prices)
        
        # Only BTC should be included
        assert "BTC-USD" in result
        assert "ETH-USD" not in result


class TestValidateTradeParams:
    """Test the validate_trade_params function."""

    def test_validate_trade_params_valid(self):
        """Test valid trade parameters."""
        result = validate_trade_params(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("50000")
        )
        assert result is True

    def test_validate_trade_params_zero_quantity(self):
        """Test with zero quantity."""
        result = validate_trade_params(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0"),
            price=Decimal("50000")
        )
        assert result is False

    def test_validate_trade_params_negative_quantity(self):
        """Test with negative quantity."""
        result = validate_trade_params(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("-0.1"),
            price=Decimal("50000")
        )
        assert result is False

    def test_validate_trade_params_zero_price(self):
        """Test with zero price."""
        result = validate_trade_params(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("0")
        )
        assert result is False

    def test_validate_trade_params_below_minimum_notional(self):
        """Test with trade below minimum notional."""
        result = validate_trade_params(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.0001"),  # $5 notional
            price=Decimal("50000")
        )
        assert result is False

    def test_validate_trade_params_at_minimum_notional(self):
        """Test with trade at minimum notional."""
        result = validate_trade_params(
            symbol="BTC-USD",
            side="buy",
            quantity=Decimal("0.0002"),  # $10 notional
            price=Decimal("50000")
        )
        assert result is True


# Integration tests
class TestIntegration:
    """Integration tests for combined functionality."""

    def test_full_rebalance_calculation(self):
        """Test full rebalancing calculation flow."""
        # Setup portfolio
        positions = {
            "BTC-USD": Decimal("0.5"),
            "ETH-USD": Decimal("16.666667"),  # Approximately $50k worth
        }
        prices = {
            "BTC-USD": Decimal("50000"),
            "ETH-USD": Decimal("3000"),
        }
        
        # Calculate current state
        total_value = calculate_portfolio_value(positions, prices)
        current_weights = calculate_current_weights(positions, prices)
        
        # Define target weights
        target_weights = {
            "BTC-USD": Decimal("0.6"),
            "ETH-USD": Decimal("0.4"),
        }
        
        # Calculate trades
        trades = calculate_rebalance_trades(current_weights, target_weights, total_value, prices)
        
        # Verify trades are calculated correctly
        assert len(trades) == 2
        assert "BTC-USD" in trades
        assert "ETH-USD" in trades
        
        # Verify trade directions
        assert trades["BTC-USD"][0] == "buy"
        assert trades["ETH-USD"][0] == "sell"
        
        # Verify all trades are valid
        for symbol, (side, quantity) in trades.items():
            price = prices[symbol]
            assert validate_trade_params(symbol, side, quantity, price)


if __name__ == "__main__":
    pytest.main([__file__]) 