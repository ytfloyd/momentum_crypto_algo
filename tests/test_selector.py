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
        
        # Mock product data - simulating what Coinbase API might return
        self.mock_products = [
            {
                "product_id": "CRYPTO1-USD",
                "quote_currency_id": "USD",
                "status": "online"
            },
            {
                "product_id": "CRYPTO2-USD", 
                "quote_currency_id": "USD",
                "status": "online"
            },
            {
                "product_id": "CRYPTO3-USD",
                "quote_currency_id": "USD", 
                "status": "online"
            },
            {
                "product_id": "CRYPTO4-EUR",  # Non-USD quote
                "quote_currency_id": "EUR",
                "status": "online"
            },
            {
                "product_id": "CRYPTO5-USD",  # Offline status
                "quote_currency_id": "USD",
                "status": "offline"
            }
        ]
        
        # Mock ticker data for dynamic crypto products
        self.mock_tickers = {
            "CRYPTO1-USD": {
                "price": "100.00",
                "volume": "1000.00"  # High volume
            },
            "CRYPTO2-USD": {
                "price": "50.00", 
                "volume": "2000.00"  # Higher volume
            },
            "CRYPTO3-USD": {
                "price": "25.00",
                "volume": "500.00"   # Lower volume
            }
        }
        
        # Mock candle data with positive momentum for testing
        self.mock_candles = {
            "CRYPTO1-USD": {
                "candles": [
                    {"close": "90.00"},   # candles[-3] (3 days ago price)
                    {"close": "95.00"},   # 1 day ago 
                    {"close": "110.00"}   # Most recent
                ]
            },
            "CRYPTO2-USD": {
                "candles": [
                    {"close": "45.00"},   # candles[-3] (3 days ago price)
                    {"close": "47.00"},   # 1 day ago
                    {"close": "55.00"}    # Most recent  
                ]
            },
            "CRYPTO3-USD": {
                "candles": [
                    {"close": "20.00"},   # candles[-3] (3 days ago price)
                    {"close": "22.00"},   # 1 day ago
                    {"close": "30.00"}    # Most recent
                ]
            }
        }
    
    def test_fetch_usd_products(self):
        """Test fetching USD-quoted products dynamically."""
        self.mock_client.list_products.return_value = {"products": self.mock_products}
        
        result = fetch_usd_products(self.mock_client)
        
        self.assertEqual(len(result), 3)  # Only online USD-quoted products
        product_ids = [p["product_id"] for p in result]
        self.assertIn("CRYPTO1-USD", product_ids)
        self.assertIn("CRYPTO2-USD", product_ids)
        self.assertIn("CRYPTO3-USD", product_ids)
        self.assertNotIn("CRYPTO4-EUR", product_ids)  # EUR quoted
        self.assertNotIn("CRYPTO5-USD", product_ids)  # Offline status
    
    @patch('agent.selector.time.sleep')
    def test_score_product(self, mock_sleep):
        """Test product scoring calculation for any dynamic product."""
        product_id = "CRYPTO1-USD"
        
        self.mock_client.get_product_market_ticker.return_value = self.mock_tickers[product_id]
        self.mock_client.get_product_candles.return_value = self.mock_candles[product_id]
        
        score, metadata = score_product(self.mock_client, product_id)
        
        # Expected calculation:
        # vol_usd = 1000 * 100 = 100,000
        # momentum = (100 - 90) / 90 = 10 / 90 = 0.1111...
        # score = 100,000 * 0.1111 = ~11,111
        # Note: candles[-3] gets the first element when there are only 3 elements
        
        self.assertGreater(score, 0)  # Score should be positive due to positive momentum
        self.assertIn("price", metadata)
        self.assertIn("vol", metadata)
        self.assertIn("mom", metadata)
        self.assertEqual(metadata["price"], Decimal("100.00"))
        
        # Check that rate limiting was called
        mock_sleep.assert_called_once_with(0.12)
    
    @patch('agent.selector.time.sleep')
    def test_score_product_insufficient_candles(self, mock_sleep):
        """Test product scoring with insufficient candle data."""
        product_id = "CRYPTO1-USD"
        
        self.mock_client.get_product_market_ticker.return_value = self.mock_tickers[product_id]
        self.mock_client.get_product_candles.return_value = {"candles": [{"close": "100.00"}]}
        
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
        
        # Test with top_n=3 and cash_buffer=0.05
        weights = build_target_weights(self.mock_client, top_n=3, cash_buffer=Decimal("0.05"))
        
        # Should have exactly 3 products (all our test cryptos have positive scores)
        self.assertEqual(len(weights), 3)
        
        # All weights should be positive
        for weight in weights.values():
            self.assertGreater(weight, 0)
        
        # Total weights should sum to approximately 0.95 (1 - 0.05 cash buffer)
        total_weight = sum(weights.values())
        self.assertAlmostEqual(float(total_weight), 0.95, places=2)
        
        # Should only include USD-quoted products (all our test products end with -USD)
        for product_id in weights.keys():
            self.assertTrue(product_id.endswith("-USD"))
            self.assertIn(product_id, ["CRYPTO1-USD", "CRYPTO2-USD", "CRYPTO3-USD"])
    
    @patch('agent.selector.time.sleep')
    def test_build_target_weights_excludes_zero_score(self, mock_sleep):
        """Test that zero-score assets are excluded from target weights."""
        # Mock products with one having insufficient candles (zero score)
        mock_products = [
            {
                "product_id": "GOOD-USD",
                "quote_currency_id": "USD",
                "status": "online"
            },
            {
                "product_id": "BAD-USD",
                "quote_currency_id": "USD",
                "status": "online"
            }
        ]
        
        self.mock_client.list_products.return_value = {"products": mock_products}
        
        # GOOD-USD has complete data, BAD-USD has insufficient data
        def mock_ticker_side_effect(product_id):
            if product_id == "GOOD-USD":
                return {"price": "100.00", "volume": "1000.00"}
            else:
                return {"price": "50.00", "volume": "2000.00"}
        
        def mock_candles_side_effect(product_id, **kwargs):
            if product_id == "GOOD-USD":
                return {
                    "candles": [
                        {"close": "90.00"},   # candles[-3] for positive momentum
                        {"close": "95.00"},
                        {"close": "110.00"}
                    ]
                }
            else:
                # BAD-USD has insufficient candles
                return {"candles": [{"close": "50.00"}]}
        
        self.mock_client.get_product_market_ticker.side_effect = mock_ticker_side_effect
        self.mock_client.get_product_candles.side_effect = mock_candles_side_effect
        
        weights = build_target_weights(self.mock_client, top_n=5, cash_buffer=Decimal("0.05"))
        
        # Should only include GOOD-USD (BAD-USD has zero score due to insufficient data)
        self.assertEqual(len(weights), 1)
        self.assertIn("GOOD-USD", weights)
        self.assertNotIn("BAD-USD", weights)
    
    @patch('agent.selector.time.sleep')
    def test_build_target_weights_empty_result(self, mock_sleep):
        """Test handling of empty results when no products score positively."""
        # Mock products but with zero scores
        mock_products = [
            {
                "product_id": "ZERO-USD",
                "quote_currency_id": "USD",
                "status": "online"
            }
        ]
        
        self.mock_client.list_products.return_value = {"products": mock_products}
        self.mock_client.get_product_market_ticker.return_value = {"price": "100.00", "volume": "1000.00"}
        self.mock_client.get_product_candles.return_value = {"candles": [{"close": "100.00"}]}
        
        weights = build_target_weights(self.mock_client, top_n=5, cash_buffer=Decimal("0.05"))
        
        # Should return empty dict when no products score positively
        self.assertEqual(weights, {})


if __name__ == '__main__':
    unittest.main() 