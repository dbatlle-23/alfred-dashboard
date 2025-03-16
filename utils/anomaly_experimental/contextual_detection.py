"""
Contextual anomaly detection module.
This module detects anomalies based on asset-specific historical patterns.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Import the threshold calculator
from utils.anomaly_experimental.threshold_calculator import ThresholdCalculator

# Set up logging
logger = logging.getLogger(__name__)

class ContextualAnomalyDetector:
    """
    Detect contextual anomalies in consumption data based on asset-specific patterns.
    """
    
    def __init__(self, asset_id=None, consumption_type=None):
        """
        Initialize the contextual anomaly detector.
        
        Args:
            asset_id (str, optional): The ID of the asset
            consumption_type (str, optional): The type of consumption
        """
        self.asset_id = asset_id
        self.consumption_type = consumption_type
        self.threshold_calculator = None
        
        if asset_id and consumption_type:
            self.threshold_calculator = ThresholdCalculator(asset_id, consumption_type)
    
    def detect_anomalies(self, df, threshold_method="std_dev", percentile=95):
        """
        Detect contextual anomalies in consumption data.
        
        Args:
            df (pd.DataFrame): DataFrame with consumption data
            threshold_method (str): Method to use for threshold calculation
            percentile (float): Percentile to use if method is "percentile"
            
        Returns:
            pd.DataFrame: DataFrame with anomaly flags and confidence levels
        """
        if df is None or df.empty:
            logger.warning("Empty DataFrame provided to detect_anomalies")
            return df
        
        try:
            # Make a copy to avoid modifying the original
            result_df = df.copy()
            
            # Ensure date is datetime
            if 'date' in result_df.columns and not pd.api.types.is_datetime64_any_dtype(result_df['date']):
                result_df['date'] = pd.to_datetime(result_df['date'])
            
            # If asset_id and consumption_type were not provided at initialization,
            # we need to process each asset and consumption type separately
            if self.asset_id is None or self.consumption_type is None:
                # Initialize columns for anomaly detection results
                result_df['is_contextual_anomaly'] = False
                result_df['contextual_anomaly_confidence'] = 0.0
                result_df['contextual_anomaly_type'] = None
                result_df['contextual_anomaly_threshold'] = None
                
                # Group by asset_id and consumption_type
                for (asset_id, consumption_type), group in result_df.groupby(['asset_id', 'consumption_type']):
                    # Create a threshold calculator for this asset and consumption type
                    calculator = ThresholdCalculator(asset_id, consumption_type)
                    
                    # Get thresholds
                    thresholds = calculator.get_thresholds(df=result_df, method=threshold_method, percentile=percentile)
                    
                    if thresholds:
                        # Process this group
                        processed_group = self._process_group(group, thresholds)
                        
                        # Update the result DataFrame
                        for idx in processed_group.index:
                            result_df.loc[idx, 'is_contextual_anomaly'] = processed_group.loc[idx, 'is_contextual_anomaly']
                            result_df.loc[idx, 'contextual_anomaly_confidence'] = processed_group.loc[idx, 'contextual_anomaly_confidence']
                            result_df.loc[idx, 'contextual_anomaly_type'] = processed_group.loc[idx, 'contextual_anomaly_type']
                            result_df.loc[idx, 'contextual_anomaly_threshold'] = processed_group.loc[idx, 'contextual_anomaly_threshold']
            else:
                # Process a single asset and consumption type
                # Filter for the specified asset and consumption type
                filtered_df = result_df[
                    (result_df['asset_id'] == self.asset_id) & 
                    (result_df['consumption_type'] == self.consumption_type)
                ]
                
                if not filtered_df.empty:
                    # Get thresholds
                    thresholds = self.threshold_calculator.get_thresholds(df=result_df, method=threshold_method, percentile=percentile)
                    
                    if thresholds:
                        # Process this filtered DataFrame
                        processed_df = self._process_group(filtered_df, thresholds)
                        
                        # Initialize columns for anomaly detection results
                        result_df['is_contextual_anomaly'] = False
                        result_df['contextual_anomaly_confidence'] = 0.0
                        result_df['contextual_anomaly_type'] = None
                        result_df['contextual_anomaly_threshold'] = None
                        
                        # Update the result DataFrame
                        for idx in processed_df.index:
                            result_df.loc[idx, 'is_contextual_anomaly'] = processed_df.loc[idx, 'is_contextual_anomaly']
                            result_df.loc[idx, 'contextual_anomaly_confidence'] = processed_df.loc[idx, 'contextual_anomaly_confidence']
                            result_df.loc[idx, 'contextual_anomaly_type'] = processed_df.loc[idx, 'contextual_anomaly_type']
                            result_df.loc[idx, 'contextual_anomaly_threshold'] = processed_df.loc[idx, 'contextual_anomaly_threshold']
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error detecting contextual anomalies: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df
    
    def _process_group(self, group_df, thresholds):
        """
        Process a group of data for a single asset and consumption type.
        
        Args:
            group_df (pd.DataFrame): DataFrame for a single asset and consumption type
            thresholds (dict): Thresholds for this asset
            
        Returns:
            pd.DataFrame: Processed DataFrame with anomaly flags
        """
        try:
            # Sort by date
            group_df = group_df.sort_values('date')
            
            # Determine consumption column
            consumption_col = 'consumption'
            if 'corrected_value' in group_df.columns:
                consumption_col = 'corrected_value'
            
            # Calculate day-to-day changes
            group_df['daily_change'] = group_df[consumption_col].diff()
            group_df['daily_change_pct'] = group_df[consumption_col].pct_change() * 100
            
            # Initialize anomaly columns
            group_df['is_contextual_anomaly'] = False
            group_df['contextual_anomaly_confidence'] = 0.0
            group_df['contextual_anomaly_type'] = None
            group_df['contextual_anomaly_threshold'] = None
            
            # Check for anomalies
            for idx, row in group_df.iterrows():
                if pd.isna(row['daily_change']) or pd.isna(row['daily_change_pct']):
                    continue
                
                # Check absolute change
                abs_change = abs(row['daily_change'])
                if abs_change > thresholds['high_threshold']:
                    group_df.at[idx, 'is_contextual_anomaly'] = True
                    
                    # Calculate confidence based on how much the change exceeds the threshold
                    excess_ratio = abs_change / thresholds['high_threshold']
                    confidence = min(0.9, 0.5 + (excess_ratio - 1) * 0.1)
                    group_df.at[idx, 'contextual_anomaly_confidence'] = confidence
                    group_df.at[idx, 'contextual_anomaly_type'] = 'absolute_change'
                    group_df.at[idx, 'contextual_anomaly_threshold'] = thresholds['high_threshold']
                    
                    logger.info(f"Detected absolute change anomaly: {row['date']} - {abs_change} > {thresholds['high_threshold']}")
                elif abs_change > thresholds['medium_threshold']:
                    group_df.at[idx, 'is_contextual_anomaly'] = True
                    
                    # Medium confidence for medium threshold
                    excess_ratio = abs_change / thresholds['medium_threshold']
                    confidence = min(0.7, 0.3 + (excess_ratio - 1) * 0.1)
                    group_df.at[idx, 'contextual_anomaly_confidence'] = confidence
                    group_df.at[idx, 'contextual_anomaly_type'] = 'absolute_change'
                    group_df.at[idx, 'contextual_anomaly_threshold'] = thresholds['medium_threshold']
                    
                    logger.info(f"Detected medium absolute change anomaly: {row['date']} - {abs_change} > {thresholds['medium_threshold']}")
                
                # Check percentage change
                abs_change_pct = abs(row['daily_change_pct'])
                if abs_change_pct > thresholds['high_threshold_pct']:
                    # If already flagged as anomaly, keep the higher confidence
                    if group_df.at[idx, 'is_contextual_anomaly']:
                        excess_ratio = abs_change_pct / thresholds['high_threshold_pct']
                        new_confidence = min(0.95, 0.6 + (excess_ratio - 1) * 0.1)
                        if new_confidence > group_df.at[idx, 'contextual_anomaly_confidence']:
                            group_df.at[idx, 'contextual_anomaly_confidence'] = new_confidence
                            group_df.at[idx, 'contextual_anomaly_type'] = 'percentage_change'
                            group_df.at[idx, 'contextual_anomaly_threshold'] = thresholds['high_threshold_pct']
                    else:
                        group_df.at[idx, 'is_contextual_anomaly'] = True
                        excess_ratio = abs_change_pct / thresholds['high_threshold_pct']
                        confidence = min(0.95, 0.6 + (excess_ratio - 1) * 0.1)
                        group_df.at[idx, 'contextual_anomaly_confidence'] = confidence
                        group_df.at[idx, 'contextual_anomaly_type'] = 'percentage_change'
                        group_df.at[idx, 'contextual_anomaly_threshold'] = thresholds['high_threshold_pct']
                        
                        logger.info(f"Detected percentage change anomaly: {row['date']} - {abs_change_pct}% > {thresholds['high_threshold_pct']}%")
                elif abs_change_pct > thresholds['medium_threshold_pct']:
                    # If already flagged as anomaly, only update if current confidence is low
                    if group_df.at[idx, 'is_contextual_anomaly'] and group_df.at[idx, 'contextual_anomaly_confidence'] < 0.5:
                        excess_ratio = abs_change_pct / thresholds['medium_threshold_pct']
                        new_confidence = min(0.7, 0.4 + (excess_ratio - 1) * 0.1)
                        if new_confidence > group_df.at[idx, 'contextual_anomaly_confidence']:
                            group_df.at[idx, 'contextual_anomaly_confidence'] = new_confidence
                            group_df.at[idx, 'contextual_anomaly_type'] = 'percentage_change'
                            group_df.at[idx, 'contextual_anomaly_threshold'] = thresholds['medium_threshold_pct']
                    elif not group_df.at[idx, 'is_contextual_anomaly']:
                        group_df.at[idx, 'is_contextual_anomaly'] = True
                        excess_ratio = abs_change_pct / thresholds['medium_threshold_pct']
                        confidence = min(0.7, 0.4 + (excess_ratio - 1) * 0.1)
                        group_df.at[idx, 'contextual_anomaly_confidence'] = confidence
                        group_df.at[idx, 'contextual_anomaly_type'] = 'percentage_change'
                        group_df.at[idx, 'contextual_anomaly_threshold'] = thresholds['medium_threshold_pct']
                        
                        logger.info(f"Detected medium percentage change anomaly: {row['date']} - {abs_change_pct}% > {thresholds['medium_threshold_pct']}%")
            
            return group_df
            
        except Exception as e:
            logger.error(f"Error processing group: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return group_df 