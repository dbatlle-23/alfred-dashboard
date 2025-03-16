"""
Configuration loader for the experimental anomaly detection system.
This module loads and processes the anomaly configuration from anomaly_config.json.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "daily_max": 10.0,
    "monthly_max": 200.0,
    "sudden_increase": 5.0,
    "std_multiplier": 3.0
}

def load_anomaly_config(config_path: str = "data/analyzed_data/anomaly_config.json") -> Dict[str, Dict[str, float]]:
    """
    Load the anomaly configuration from the specified file.
    
    Args:
        config_path (str): Path to the anomaly configuration file
        
    Returns:
        Dict[str, Dict[str, float]]: Dictionary with configuration values for each consumption type
    """
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded anomaly configuration from {config_path}")
            return config
        else:
            logger.warning(f"Anomaly configuration file not found at {config_path}, using default values")
            return {"default": DEFAULT_CONFIG}
    except Exception as e:
        logger.error(f"Error loading anomaly configuration: {str(e)}")
        return {"default": DEFAULT_CONFIG}

def get_config_for_consumption_type(consumption_type: str, config: Optional[Dict[str, Dict[str, float]]] = None) -> Dict[str, float]:
    """
    Get the configuration for a specific consumption type.
    
    Args:
        consumption_type (str): Consumption type
        config (Dict[str, Dict[str, float]], optional): Configuration dictionary
        
    Returns:
        Dict[str, float]: Configuration values for the specified consumption type
    """
    if config is None:
        config = load_anomaly_config()
    
    # Try to get configuration for the specific consumption type
    if consumption_type in config:
        return config[consumption_type]
    
    # If not found, return default configuration
    return config.get("default", DEFAULT_CONFIG)

def convert_config_to_thresholds(config: Dict[str, float], historical_stats: Dict[str, float] = None) -> Dict[str, float]:
    """
    Convert configuration values to thresholds for anomaly detection.
    
    Args:
        config (Dict[str, float]): Configuration values
        historical_stats (Dict[str, float], optional): Historical statistics
        
    Returns:
        Dict[str, float]: Thresholds for anomaly detection
    """
    # If historical statistics are provided, use them to calculate thresholds
    if historical_stats and 'mean_change' in historical_stats and 'std_change' in historical_stats:
        mean_change = historical_stats['mean_change']
        std_change = historical_stats['std_change']
        
        # Use std_multiplier from config
        std_multiplier = config.get('std_multiplier', 3.0)
        
        thresholds = {
            'low_threshold': abs(mean_change) + std_multiplier * std_change,
            'medium_threshold': abs(mean_change) + (std_multiplier + 1) * std_change,
            'high_threshold': abs(mean_change) + (std_multiplier + 2) * std_change,
            'sudden_increase': config.get('sudden_increase', 5.0),
            'daily_max': config.get('daily_max', 10.0),
            'monthly_max': config.get('monthly_max', 200.0),
            'method': 'config_adjusted'
        }
    else:
        # Without historical stats, use configuration values directly
        sudden_increase = config.get('sudden_increase', 5.0)
        
        thresholds = {
            'low_threshold': config.get('daily_max', 10.0) * 0.5,
            'medium_threshold': config.get('daily_max', 10.0),
            'high_threshold': config.get('daily_max', 10.0) * 2,
            'low_threshold_pct': sudden_increase * 0.5,
            'medium_threshold_pct': sudden_increase,
            'high_threshold_pct': sudden_increase * 2,
            'method': 'config_direct'
        }
    
    return thresholds 