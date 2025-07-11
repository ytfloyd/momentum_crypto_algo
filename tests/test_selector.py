"""
Unit tests for the dynamic selector module.
"""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from agent.selector import build_target_weights, fetch_usd_products, score_product


class TestSelector(unittest.TestCase):
    """Test cases for the dynamic selector functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        
        # Mock product data
        self.mock_products = [
            {
                "product_id": "BTC-USD",
                "quote_currency_id": "USD",
                "status": "online"
            },
            {
                "product_id": "ETH-USD",
                "quote_currency_id": "USD",
                "status": "online"
            },
            {
                "product_id": "SOL-USD",
                "quote_currency_id": "USD",
                "status": "online"
            },
            {
                "product_id": "ADA-EUR",
                "quote_currency_id": "EUR",
                "status": "online"
            },
            {
                "product_id": "LINK-USD",
                "quote_currency_id": "USD",
                "status": "offline"
            }
        ]
        
        # Mock ticker data
        self.mock_tickers = {
            "BTC-USD": {
                "price": "50000.00",
                "volume": "1000.00"
            },
            "ETH-USD": {
                "price": "3000.00",
                "volume": "2000.00"
            },
            "SOL-USD": {
                "price": "100.00",
                "volume": "1500.00"
            }
        }
        
        # Mock candle data (3 days)
        self.mock_candles = {
            "BTC-USD": {
                "candles": [
                    {"close": "52000.00"},  # Most recent
                    {"close": "51000.00"},  # 1 day ago
                    {"close": "48000.00"}   # 3 days ago
                ]
            },
            "ETH-USD": {
                "candles": [
                    {"close": "3000.00"},   # Most recent
                    {"close": "2900.00"},   # 1 day ago
                    {"close": "2800.00"}    # 3 days ago
                ]
            },
            "SOL-USD": {
                "candles": [
                    {"close": "100.00"},    # Most recent
                    {"close": "95.00"},     # 1 day ago
                    {"close": "90.00"}      # 3 days ago
                ]
            }
        }
    
    def test_fetch_usd_products(self):
        """Test fetching USD-quoted products."""
        self.mock_client.list_products.return_value = {"products": self.mock_products}
        
        result = fetch_usd_products(self.mock_client)
        
        self.assertEqual(len(result), 2)  # Only BTC-USD and ETH-USD should be included
        product_ids = [p["product_id"] for p in result]
        self.assertIn("BTC-USD", product_ids)
        self.assertIn("ETH-USD", product_ids)
        self.assertNotIn("ADA-EUR", product_ids)  # EUR quoted
        self.assertNotIn("LINK-USD", product_ids)  # Offline status
    
    @patch('agent.selector.time.sleep')
    def test_score_product(self, mock_sleep):
        """Test product scoring calculation."""
        product_id = "BTC-USD"
        
        self.mock_client.get_product_market_ticker.return_value = self.mock_tickers[product_id]
        self.mock_client.get_product_candles.return_value = self.mock_candles[product_id]
        
        score, metadata = score_product(self.mock_client, product_id)
        
        # Expected calculation:
        # vol_usd = 1000 * 50000 = 50,000,000
        # momentum = (50000 - 48000) / 48000 = 2000 / 48000 = 0.04167
        # score = 50,000,000 * 0.04167 = ~2,083,333
        
        self.assertGreater(score, 0)
        self.assertIn("price", metadata)
        self.assertIn("vol", metadata)
        self.assertIn("mom", metadata)
        self.assertEqual(metadata["price"], Decimal("50000.00"))
        
        # Check that rate limiting was called
        mock_sleep.assert_called_once_with(0.12)
    
    @patch('agent.selector.time.sleep')
    def test_score_product_insufficient_candles(self, mock_sleep):
        """Test product scoring with insufficient candle data."""
        product_id = "BTC-USD"
        
        self.mock_client.get_product_market_ticker.return_value = self.mock_tickers[product_id]
        self.mock_client.get_product_candles.return_value = {"candles": [{"close": "50000.00"}]}
        
        score, metadata = score_product(self.mock_client, product_id)
        
        self.assertEqual(score, Decimal("0"))
        self.assertEqual(metadata, {})
    
    @patch('agent.selector.time.sleep')
    def test_build_target_weights(self, mock_sleep):
        """Test building target weights."""
        # Mock the fetch_usd_products call
        self.mock_client.list_products.return_value = {"products": self.mock_products}
        
        # Mock the ticker and candle calls for each product
        def mock_ticker_side_effect(product_id):
            return self.mock_tickers.get(product_id, {"price": "100.00", "volume": "100.00"})
        
        def mock_candles_side_effect(product_id, **kwargs):
            return self.mock_candles.get(product_id, {
                "candles": [
                    {"close": "100.00"},
                    {"close": "95.00"},
                    {"close": "90.00"}
                ]
            })
        
        self.mock_client.get_product_market_ticker.side_effect = mock_ticker_side_effect
        self.mock_client.get_product_candles.side_effect = mock_candles_side_effect
        
        # Test with top_n=2 and cash_buffer=0.05
        weights = build_target_weights(self.mock_client, top_n=2, cash_buffer=Decimal("0.05"))
        
        # Should have exactly 2 products
        self.assertEqual(len(weights), 2)
        
        # All weights should be positive
        for weight in weights.values():
            self.assertGreater(weight, 0)
        
        # Total weights should sum to approximately 0.95 (1 - 0.05 cash buffer)
        total_weight = sum(weights.values())
        self.assertAlmostEqual(float(total_weight), 0.95, places=2)
        
        # Should only include USD-quoted products
        for product_id in weights.keys():
            self.assertTrue(product_id.endswith("-USD"))
    
    @patch('agent.selector.time.sleep')
    def test_build_target_weights_excludes_zero_score(self, mock_sleep):
        """Test that zero-score assets are excluded from target weights."""
        # Mock products with one having insufficient candles (zero score)
        mock_products = [
            {
                "product_id": "BTC-USD",
                "quote_currency_id": "USD",
                "status": "online"
            },
            {
                "product_id": "ETH-USD",
                "quote_currency_id": "USD",
                "status": "online"
            }
        ]
        
        self.mock_client.list_products.return_value = {"products": mock_products}
        
        # BTC has good data
        def mock_ticker_side_effect(product_id):
            if product_id == "BTC-USD":
                return {"price": "50000.00", "volume": "1000.00"}
            else:
                return {"price": "3000.00", "volume": "2000.00"}
        
        def mock_candles_side_effect(product_id, **kwargs):
            if product_id == "BTC-USD":
                return {
                    "candles": [
                        {"close": "50000.00"},
                        {"close": "49000.00"},
                        {"close": "48000.00"}
                    ]
                }
            else:
                # ETH has insufficient candles
                return {"candles": [{"close": "3000.00"}]}
        
        self.mock_client.get_product_market_ticker.side_effect = mock_ticker_side_effect
        self.mock_client.get_product_candles.side_effect = mock_candles_side_effect
        
        weights = build_target_weights(self.mock_client, top_n=5, cash_buffer=Decimal("0.05"))
        
        # Should only include BTC-USD (ETH-USD has zero score)
        self.assertEqual(len(weights), 1)
        self.assertIn("BTC-USD", weights)
        self.assertNotIn("ETH-USD", weights)
    
    @patch('agent.selector.time.sleep')
    def test_build_target_weights_empty_result(self, mock_sleep):
        """Test handling of empty results when no products score positively."""
        # Mock products but with zero scores
        mock_products = [
            {
                "product_id": "BTC-USD",
                "quote_currency_id": "USD",
                "status": "online"
            }
        ]
        
        self.mock_client.list_products.return_value = {"products": mock_products}
        self.mock_client.get_product_market_ticker.return_value = {"price": "50000.00", "volume": "1000.00"}
        self.mock_client.get_product_candles.return_value = {"candles": [{"close": "50000.00"}]}
        
        weights = build_target_weights(self.mock_client, top_n=5, cash_buffer=Decimal("0.05"))
        
        # Should return empty dict when no products score positively
        self.assertEqual(weights, {})


if __name__ == '__main__':
    unittest.main() 