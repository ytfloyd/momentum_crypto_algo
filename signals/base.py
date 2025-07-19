"""
Base signal class for systematic trend-following signals.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class BaseSignal(ABC):
    """
    Abstract base class for all trading signals.
    
    All signals must implement the generate_signal method and provide
    a consistent interface for signal generation.
    """
    
    def __init__(self, name: str, params: Dict[str, Any]):
        """
        Initialize the signal.
        
        Args:
            name: Name of the signal
            params: Dictionary of signal parameters
        """
        self.name = name
        self.params = params
        self.last_signal = None
        self.last_timestamp = None
        
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate trading signal based on price data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary containing:
            - signal: 1 (long), -1 (short), 0 (neutral)
            - strength: Signal strength (0-1)
            - metadata: Additional signal information
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate that the data has required columns.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required_columns)
    
    def get_signal_info(self) -> Dict[str, Any]:
        """
        Get information about the signal.
        
        Returns:
            Dictionary with signal name, parameters, and last signal
        """
        return {
            'name': self.name,
            'params': self.params,
            'last_signal': self.last_signal,
            'last_timestamp': self.last_timestamp
        } 