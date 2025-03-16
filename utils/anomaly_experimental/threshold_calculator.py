"""
Threshold calculator for contextual anomaly detection.
This module calculates asset-specific thresholds for detecting abnormal consumption changes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Import the config loader
from utils.anomaly_experimental.config_loader import get_config_for_consumption_type, convert_config_to_thresholds

# Set up logging
logger = logging.getLogger(__name__)

class ThresholdCalculator:
    """
    Calculate asset-specific thresholds for detecting abnormal consumption changes.
    """
    
    def __init__(self, asset_id, consumption_type):
        """
        Initialize the threshold calculator.
        
        Args:
            asset_id (str): The ID of the asset
            consumption_type (str): The type of consumption (e.g., ENERGY_ACTIVE)
        """
        self.asset_id = asset_id
        self.consumption_type = consumption_type
        self.historical_data = None
        self.thresholds = None
        
        # Load configuration for this consumption type
        self.config = get_config_for_consumption_type(consumption_type)
        logger.info(f"Loaded configuration for {consumption_type}: {self.config}")
    
    def load_historical_data(self, df=None, days=90):
        """
        Load historical consumption data for this asset.
        
        Args:
            df (pd.DataFrame, optional): DataFrame with consumption data
            days (int, optional): Number of days of historical data to use
            
        Returns:
            bool: True if data was loaded successfully, False otherwise
        """
        try:
            if df is not None:
                # Filter the provided DataFrame for this asset and consumption type
                self.historical_data = df[
                    (df['asset_id'] == self.asset_id) & 
                    (df['consumption_type'] == self.consumption_type)
                ].copy()
                
                # Ensure date is datetime
                if 'date' in self.historical_data.columns and not pd.api.types.is_datetime64_any_dtype(self.historical_data['date']):
                    self.historical_data['date'] = pd.to_datetime(self.historical_data['date'])
                
                # Filter for the specified number of days
                if days > 0:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    self.historical_data = self.historical_data[self.historical_data['date'] >= cutoff_date]
                
                logger.info(f"Loaded {len(self.historical_data)} records for asset {self.asset_id}")
                return len(self.historical_data) > 0
            else:
                # If no DataFrame is provided, try to load from data files
                # This is a placeholder - implement according to your data storage
                logger.warning("No DataFrame provided and direct data loading not implemented")
                return False
                
        except Exception as e:
            logger.error(f"Error loading historical data: {str(e)}")
            return False
    
    def calculate_thresholds(self, method="std_dev", percentile=95, min_data_points=10):
        """
        Calculate thresholds for normal day-to-day variations.
        
        Args:
            method (str): Method to use for threshold calculation ("std_dev", "percentile", or "config")
            percentile (float): Percentile to use if method is "percentile"
            min_data_points (int): Minimum number of data points required
            
        Returns:
            dict: Dictionary with threshold values or None if calculation failed
        """
        if self.historical_data is None or len(self.historical_data) < min_data_points:
            logger.warning(f"Insufficient data for asset {self.asset_id}: {len(self.historical_data) if self.historical_data is not None else 0} points")
            
            # If we don't have enough data, use configuration directly
            if method == "config" or method == "config_only":
                return convert_config_to_thresholds(self.config)
            elif len(self.historical_data) < 2:  # Need at least 2 points for diff
                return None
        
        try:
            # Sort by date to ensure correct calculation of daily changes
            self.historical_data = self.historical_data.sort_values('date')
            
            # Calculate day-to-day changes
            consumption_col = 'consumption'
            if 'corrected_value' in self.historical_data.columns:
                consumption_col = 'corrected_value'
                
            self.historical_data['daily_change'] = self.historical_data[consumption_col].diff()
            self.historical_data['daily_change_pct'] = self.historical_data[consumption_col].pct_change() * 100
            
            # Remove NaN values
            daily_changes = self.historical_data['daily_change'].dropna()
            daily_changes_pct = self.historical_data['daily_change_pct'].dropna()
            
            if len(daily_changes) < min_data_points and method != "config" and method != "config_only":
                logger.warning(f"Insufficient daily change data for asset {self.asset_id}: {len(daily_changes)} points")
                
                # If we don't have enough data, use configuration directly
                if method == "config" or method == "config_only":
                    return convert_config_to_thresholds(self.config)
                elif len(daily_changes) < 2:  # Need at least 2 points for statistics
                    return None
            
            # Calculate statistics for historical data
            mean_change = daily_changes.mean()
            std_change = daily_changes.std()
            mean_change_pct = daily_changes_pct.mean()
            std_change_pct = daily_changes_pct.std()
            
            historical_stats = {
                'mean_change': mean_change,
                'std_change': std_change,
                'mean_change_pct': mean_change_pct,
                'std_change_pct': std_change_pct,
                'data_points': len(daily_changes)
            }
            
            # Calculate thresholds based on the selected method
            if method == "config" or method == "config_only":
                # Use configuration values with historical statistics
                thresholds = convert_config_to_thresholds(self.config, historical_stats)
                
            elif method == "std_dev":
                # Use standard deviation multiplier from config if available
                std_multiplier = self.config.get('std_multiplier', 3.0)
                
                # Calculate thresholds based on standard deviations
                thresholds = {
                    'low_threshold': abs(mean_change) + 2 * std_change,
                    'medium_threshold': abs(mean_change) + 3 * std_change,
                    'high_threshold': abs(mean_change) + 4 * std_change,
                    'low_threshold_pct': abs(mean_change_pct) + 2 * std_change_pct,
                    'medium_threshold_pct': abs(mean_change_pct) + 3 * std_change_pct,
                    'high_threshold_pct': abs(mean_change_pct) + 4 * std_change_pct,
                    'method': 'std_dev',
                    'data_points': len(daily_changes),
                    'mean_change': mean_change,
                    'std_change': std_change,
                    'std_multiplier': std_multiplier
                }
                
            elif method == "percentile":
                # Calculate percentiles of absolute changes
                abs_changes = daily_changes.abs()
                abs_changes_pct = daily_changes_pct.abs()
                
                low_percentile = max(50, percentile - 10)
                medium_percentile = percentile
                high_percentile = min(99, percentile + 5)
                
                thresholds = {
                    'low_threshold': abs_changes.quantile(low_percentile / 100),
                    'medium_threshold': abs_changes.quantile(medium_percentile / 100),
                    'high_threshold': abs_changes.quantile(high_percentile / 100),
                    'low_threshold_pct': abs_changes_pct.quantile(low_percentile / 100),
                    'medium_threshold_pct': abs_changes_pct.quantile(medium_percentile / 100),
                    'high_threshold_pct': abs_changes_pct.quantile(high_percentile / 100),
                    'method': 'percentile',
                    'data_points': len(daily_changes),
                    'percentile_used': percentile
                }
            else:
                logger.error(f"Unknown threshold calculation method: {method}")
                return None
            
            # Add configuration values to thresholds
            thresholds['daily_max'] = self.config.get('daily_max', 10.0)
            thresholds['monthly_max'] = self.config.get('monthly_max', 200.0)
            thresholds['sudden_increase'] = self.config.get('sudden_increase', 5.0)
            
            # Store the calculated thresholds
            self.thresholds = thresholds
            
            logger.info(f"Calculated thresholds for asset {self.asset_id}: {thresholds}")
            return thresholds
            
        except Exception as e:
            logger.error(f"Error calculating thresholds: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_thresholds(self, df=None, recalculate=False, method="std_dev", percentile=95):
        """
        Get thresholds for this asset, calculating them if necessary.
        
        Args:
            df (pd.DataFrame, optional): DataFrame with consumption data
            recalculate (bool): Whether to force recalculation of thresholds
            method (str): Method to use for threshold calculation
            percentile (float): Percentile to use if method is "percentile"
            
        Returns:
            dict: Dictionary with threshold values
        """
        # Load data if provided or if we don't have historical data
        if df is not None or self.historical_data is None:
            self.load_historical_data(df)
        
        # Calculate thresholds if we don't have them or if recalculation is requested
        if self.thresholds is None or recalculate:
            self.calculate_thresholds(method=method, percentile=percentile)
        
        # Return thresholds or default values if calculation failed
        if self.thresholds is not None:
            return self.thresholds
        else:
            # Use configuration values for default thresholds
            return convert_config_to_thresholds(self.config) 