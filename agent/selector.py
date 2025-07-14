"""
Dynamic product selection module for the Coinbase rebalancing agent.

This module provides functionality to dynamically select and score USD-quoted
cryptocurrency products from Coinbase Advanced Trade API based on volume and momentum.
"""

import time
from decimal import Decimal
from typing import Dict, List, Tuple
import operator
from coinbase.rest import RESTClient


def fetch_usd_products(client: RESTClient) -> List[dict]:
    """
    Return every live USD-quoted spot product on Coinbase Advanced Trade.
    
    Args:
        client: RESTClient instance for Coinbase API
        
    Returns:
        List of product dictionaries for USD-quoted products with online status
    """
    try:
        prods = client.get_products(limit=500)["products"]
        return [
            p for p in prods
            if p["quote_currency_id"] == "USDC" and p["status"] == "online"
        ]
    except Exception as e:
        print(f"Error fetching products: {e}")
        return []


def score_product(client: RESTClient, product_id: str) -> Tuple[Decimal, dict]:
    """
    Calculate a simple score for a product based on 24h USD volume and 3-day momentum.
    
    Simple score = 24h USD volume × 3-day momentum.
    Return (score, meta) so we can sort later; skip illiquid new listings.
    
    Args:
        client: RESTClient instance for Coinbase API
        product_id: Product ID to score (e.g., "BTC-USD")
        
    Returns:
        Tuple of (score, metadata_dict) where score is volume * momentum
        and metadata contains price, volume, and momentum values
    """
    # TODO: Replace time.sleep with async batching for better performance
    time.sleep(0.02)  # Rate limiting guard - reduced from 0.12 to 0.02
    
    tk = client.get_product(product_id)
    vol_usd = Decimal(tk.volume_24h) * Decimal(tk.price)
    
    # Calculate start and end times for 3 days of data
    import datetime
    end_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = end_time - datetime.timedelta(days=4)  # Get 4 days to ensure we have 3 complete days
    
    candles = client.get_candles(
        product_id, 
        start=str(int(start_time.timestamp())), 
        end=str(int(end_time.timestamp())), 
        granularity="ONE_DAY", 
        limit=3
    )["candles"]
    
    if len(candles) < 3:
        return Decimal("0"), {}
    
    close_3d_ago = Decimal(candles[-3]["close"])
    current_price = Decimal(tk.price)
    mom3d = (current_price - close_3d_ago) / close_3d_ago
    
    score = vol_usd * mom3d
    metadata = {
        "price": current_price,
        "vol": vol_usd,
        "mom": mom3d
    }
    
    return score, metadata


def build_target_weights(  # pylint: disable=too-many-locals
    client: RESTClient,
    top_n: int = 25,
    cash_buffer: Decimal = Decimal("0.05"),
) -> Dict[str, Decimal]:
    """
    Build target portfolio weights based on dynamic scoring.
    
    Return {product_id: weight} summing to 1-cash_buffer, ranked by score.
    
    Args:
        client: RESTClient instance for Coinbase API
        top_n: Number of top-scored products to include in portfolio
        cash_buffer: Percentage to keep as cash (e.g., 0.05 for 5%)
        
    Returns:
        Dictionary mapping product IDs to their target weights
    """
    scored = []
    
    for product in fetch_usd_products(client):
        score, _ = score_product(client, product["product_id"])
        if score > 0:
            scored.append((product["product_id"], score))
    
    # Sort by score descending and take top N
    scored.sort(key=operator.itemgetter(1), reverse=True)
    picks = scored[:top_n]
    
    # Calculate total score and normalize weights
    total_score = sum(score for _, score in picks)
    
    if total_score == 0:
        return {}
    
    # Build weights that sum to (1 - cash_buffer)
    target_allocation = Decimal("1") - cash_buffer
    
    return {
        product_id: (Decimal(str(score)) / Decimal(str(total_score))) * target_allocation
        for product_id, score in picks
    } 