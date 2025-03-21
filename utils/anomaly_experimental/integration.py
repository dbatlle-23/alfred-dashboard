"""
Integration module for the experimental contextual anomaly detection system.
This module provides functions to integrate the experimental system with the main application.
"""

import pandas as pd
import logging

# Import the experimental modules
from utils.anomaly_experimental.contextual_detection import ContextualAnomalyDetector
from utils.anomaly_experimental.threshold_calculator import ThresholdCalculator
from utils.anomaly_experimental.config_loader import load_anomaly_config, get_config_for_consumption_type

# Set up logging
logger = logging.getLogger(__name__)

def detect_contextual_anomalies(df, threshold_method="std_dev", percentile=95, use_config=True):
    """
    Detect contextual anomalies in consumption data.
    This function can be called from the main application to use the experimental system.
    
    Args:
        df (pd.DataFrame): DataFrame with consumption data
        threshold_method (str): Method to use for threshold calculation
        percentile (float): Percentile to use if method is "percentile"
        use_config (bool): Whether to use the anomaly_config.json configuration
        
    Returns:
        pd.DataFrame: DataFrame with anomaly flags and confidence levels
    """
    try:
        # Create detector
        detector = ContextualAnomalyDetector()
        
        # If using configuration, override threshold_method
        if use_config:
            threshold_method = "config"
        
        # Run detection
        result_df = detector.detect_anomalies(df, threshold_method=threshold_method, percentile=percentile)
        
        return result_df
        
    except Exception as e:
        logger.error(f"Error detecting contextual anomalies: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return df

def analyze_asset_anomalies(asset_id, consumption_type, df=None, threshold_method="std_dev", percentile=95, use_config=True):
    """
    Analyze anomalies for a specific asset.
    
    Args:
        asset_id (str): Asset ID
        consumption_type (str): Consumption type
        df (pd.DataFrame, optional): DataFrame with consumption data
        threshold_method (str): Method to use for threshold calculation
        percentile (float): Percentile to use if method is "percentile"
        use_config (bool): Whether to use the anomaly_config.json configuration
        
    Returns:
        dict: Analysis results
    """
    try:
        # Create detector for this specific asset
        detector = ContextualAnomalyDetector(asset_id, consumption_type)
        
        # If using configuration, override threshold_method
        if use_config:
            threshold_method = "config"
            
            # Load configuration for this consumption type
            config = get_config_for_consumption_type(consumption_type)
            logger.info(f"Using configuration for {consumption_type}: {config}")
        
        # If no DataFrame is provided, try to load data
        if df is None:
            try:
                from utils.data_loader import load_all_csv_data
                
                # Get JWT token if available
                token = None
                try:
                    from utils.auth import get_jwt_token
                    token = get_jwt_token()
                except:
                    pass
                
                # Load data
                df = load_all_csv_data(
                    consumption_tags=[consumption_type],
                    jwt_token=token
                )
                
                # Filter for this asset
                df = df[df['asset_id'] == asset_id]
                
            except Exception as e:
                logger.error(f"Error loading data: {str(e)}")
                return {"success": False, "message": f"Error loading data: {str(e)}"}
        
        if df is None or df.empty:
            return {"success": False, "message": f"No data found for asset {asset_id}"}
        
        # Run detection
        result_df = detector.detect_anomalies(df, threshold_method=threshold_method, percentile=percentile)
        
        # Calculate statistics
        total_records = len(result_df)
        anomaly_records = result_df[result_df['is_contextual_anomaly']].shape[0]
        anomaly_percentage = (anomaly_records / total_records * 100) if total_records > 0 else 0
        
        # Group anomalies by confidence level
        high_confidence = result_df[result_df['contextual_anomaly_confidence'] >= 0.7].shape[0]
        medium_confidence = result_df[(result_df['contextual_anomaly_confidence'] >= 0.4) & (result_df['contextual_anomaly_confidence'] < 0.7)].shape[0]
        low_confidence = result_df[(result_df['contextual_anomaly_confidence'] > 0) & (result_df['contextual_anomaly_confidence'] < 0.4)].shape[0]
        
        # Group anomalies by type
        absolute_change = result_df[result_df['contextual_anomaly_type'] == 'absolute_change'].shape[0]
        percentage_change = result_df[result_df['contextual_anomaly_type'] == 'percentage_change'].shape[0]
        
        # Get top anomalies
        top_anomalies = []
        if anomaly_records > 0:
            # Sort by confidence
            top_df = result_df[result_df['is_contextual_anomaly']].sort_values('contextual_anomaly_confidence', ascending=False)
            
            # Get top 5 anomalies
            for idx, row in top_df.head(5).iterrows():
                # Determine consumption column
                consumption_col = 'consumption'
                if 'corrected_value' in row and not pd.isna(row['corrected_value']):
                    consumption_col = 'corrected_value'
                
                # Get previous day's data
                prev_date = row['date'] - pd.Timedelta(days=1)
                prev_row = result_df[result_df['date'] == prev_date]
                
                prev_consumption = None
                if not prev_row.empty:
                    prev_consumption = prev_row[consumption_col].iloc[0]
                
                # Add to list
                anomaly = {
                    "date": row['date'].strftime('%Y-%m-%d'),
                    "consumption": row[consumption_col],
                    "previous_consumption": prev_consumption,
                    "daily_change": row['daily_change'] if 'daily_change' in row and not pd.isna(row['daily_change']) else None,
                    "daily_change_pct": row['daily_change_pct'] if 'daily_change_pct' in row and not pd.isna(row['daily_change_pct']) else None,
                    "confidence": row['contextual_anomaly_confidence'],
                    "type": row['contextual_anomaly_type'],
                    "threshold": row['contextual_anomaly_threshold']
                }
                
                top_anomalies.append(anomaly)
        
        # Get thresholds used
        calculator = ThresholdCalculator(asset_id, consumption_type)
        thresholds = calculator.get_thresholds(df=df, method=threshold_method, percentile=percentile)
        
        # Prepare results
        results = {
            "success": True,
            "asset_id": asset_id,
            "consumption_type": consumption_type,
            "total_records": total_records,
            "anomaly_records": anomaly_records,
            "anomaly_percentage": anomaly_percentage,
            "high_confidence": high_confidence,
            "medium_confidence": medium_confidence,
            "low_confidence": low_confidence,
            "absolute_change": absolute_change,
            "percentage_change": percentage_change,
            "top_anomalies": top_anomalies,
            "threshold_method": threshold_method if not use_config else "config",
            "percentile": percentile,
            "thresholds": thresholds,
            "config_used": use_config
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing asset anomalies: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "message": str(e)}

def get_asset_thresholds(asset_id, consumption_type, df=None, threshold_method="std_dev", percentile=95, use_config=True):
    """
    Get thresholds for a specific asset.
    
    Args:
        asset_id (str): Asset ID
        consumption_type (str): Consumption type
        df (pd.DataFrame, optional): DataFrame with consumption data
        threshold_method (str): Method to use for threshold calculation
        percentile (float): Percentile to use if method is "percentile"
        use_config (bool): Whether to use the anomaly_config.json configuration
        
    Returns:
        dict: Thresholds
    """
    try:
        # Create threshold calculator
        calculator = ThresholdCalculator(asset_id, consumption_type)
        
        # If using configuration, override threshold_method
        if use_config:
            threshold_method = "config"
        
        # If no DataFrame is provided, try to load data
        if df is None:
            try:
                from utils.data_loader import load_all_csv_data
                
                # Get JWT token if available
                token = None
                try:
                    from utils.auth import get_jwt_token
                    token = get_jwt_token()
                except:
                    pass
                
                # Load data
                df = load_all_csv_data(
                    consumption_tags=[consumption_type],
                    jwt_token=token
                )
                
                # Filter for this asset
                df = df[df['asset_id'] == asset_id]
                
            except Exception as e:
                logger.error(f"Error loading data: {str(e)}")
                return None
        
        if df is None or df.empty:
            logger.error(f"No data found for asset {asset_id}")
            return None
        
        # Calculate thresholds
        thresholds = calculator.get_thresholds(df=df, method=threshold_method, percentile=percentile)
        
        return thresholds
        
    except Exception as e:
        logger.error(f"Error getting asset thresholds: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_anomaly_config():
    """
    Get the anomaly configuration from anomaly_config.json.
    
    Returns:
        dict: Anomaly configuration
    """
    return load_anomaly_config()

def analyze_readings(df, asset_id=None, consumption_type=None, use_config=True):
    """
    Analyze readings for anomalies.
    
    Args:
        df (pd.DataFrame): DataFrame with readings data (must have 'date' and 'value' columns)
        asset_id (str, optional): Asset ID
        consumption_type (str, optional): Consumption type
        use_config (bool): Whether to use the anomaly_config.json configuration
        
    Returns:
        dict: Analysis results including anomalies and thresholds
    """
    try:
        logger.info(f"Analyzing readings for asset {asset_id} and consumption type {consumption_type}")
        
        # Create detector
        detector = ContextualAnomalyDetector(asset_id, consumption_type)
        
        # Prepare data for detection
        # The detector expects 'consumption' column, so rename 'value' to 'consumption'
        detection_df = df.copy()
        if 'value' in detection_df.columns and 'consumption' not in detection_df.columns:
            detection_df = detection_df.rename(columns={'value': 'consumption'})
        
        # Add asset_id and consumption_type if provided
        if asset_id is not None and 'asset_id' not in detection_df.columns:
            detection_df['asset_id'] = asset_id
        
        if consumption_type is not None and 'consumption_type' not in detection_df.columns:
            detection_df['consumption_type'] = consumption_type
        
        # Run detection
        result_df = detector.detect_anomalies(detection_df, threshold_method="config" if use_config else "std_dev")
        
        # Extract anomalies
        anomalies_df = None
        if 'is_contextual_anomaly' in result_df.columns:
            anomalies_df = result_df[result_df['is_contextual_anomaly']].copy()
            
            # Rename 'consumption' back to 'value' for consistency
            if 'consumption' in anomalies_df.columns and 'value' not in anomalies_df.columns:
                anomalies_df = anomalies_df.rename(columns={'consumption': 'value'})
        
        # Get thresholds
        calculator = ThresholdCalculator(asset_id, consumption_type)
        thresholds = calculator.get_thresholds(df=detection_df, method="config" if use_config else "std_dev")
        
        # Prepare results
        results = {
            "anomalies": anomalies_df,
            "thresholds": thresholds,
            "total_records": len(df),
            "anomaly_records": len(anomalies_df) if anomalies_df is not None else 0,
            "asset_id": asset_id,
            "consumption_type": consumption_type
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing readings: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"anomalies": None, "thresholds": None, "error": str(e)} 