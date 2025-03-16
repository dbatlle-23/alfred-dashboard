"""
Test harness for the experimental contextual anomaly detection system.
This module provides functions to test and evaluate the system with real data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Import the contextual anomaly detector
from utils.anomaly_experimental.contextual_detection import ContextualAnomalyDetector
from utils.anomaly_experimental.threshold_calculator import ThresholdCalculator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnomalyTestHarness:
    """
    Test harness for evaluating the contextual anomaly detection system.
    """
    
    def __init__(self, output_dir="test_results"):
        """
        Initialize the test harness.
        
        Args:
            output_dir (str): Directory to save test results
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def load_test_data(self, data_source=None, client_id=None, project_id=None, asset_id=None, consumption_type=None):
        """
        Load test data from various sources.
        
        Args:
            data_source (str or pd.DataFrame): Data source (file path or DataFrame)
            client_id (str, optional): Client ID to filter by
            project_id (str, optional): Project ID to filter by
            asset_id (str, optional): Asset ID to filter by
            consumption_type (str, optional): Consumption type to filter by
            
        Returns:
            pd.DataFrame: Test data
        """
        try:
            if isinstance(data_source, pd.DataFrame):
                # Use the provided DataFrame
                df = data_source.copy()
            elif isinstance(data_source, str) and os.path.exists(data_source):
                # Load from file
                if data_source.endswith('.csv'):
                    df = pd.read_csv(data_source)
                elif data_source.endswith('.json'):
                    df = pd.read_json(data_source)
                elif data_source.endswith('.xlsx') or data_source.endswith('.xls'):
                    df = pd.read_excel(data_source)
                else:
                    logger.error(f"Unsupported file format: {data_source}")
                    return None
            else:
                # Try to load from the data loader
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
                    consumption_tags = [consumption_type] if consumption_type else None
                    df = load_all_csv_data(
                        consumption_tags=consumption_tags,
                        project_id=project_id,
                        jwt_token=token
                    )
                except Exception as e:
                    logger.error(f"Error loading data from data loader: {str(e)}")
                    return None
            
            # Ensure date is datetime
            if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
                df['date'] = pd.to_datetime(df['date'])
            
            # Apply filters
            if client_id:
                df = df[df['client_id'] == client_id]
            
            if project_id:
                df = df[df['project_id'] == project_id]
            
            if asset_id:
                df = df[df['asset_id'] == asset_id]
            
            if consumption_type:
                df = df[df['consumption_type'] == consumption_type]
            
            logger.info(f"Loaded {len(df)} records for testing")
            return df
            
        except Exception as e:
            logger.error(f"Error loading test data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def run_test(self, test_data, threshold_method="std_dev", percentile=95, save_results=True):
        """
        Run a test of the contextual anomaly detection system.
        
        Args:
            test_data (pd.DataFrame): Test data
            threshold_method (str): Method to use for threshold calculation
            percentile (float): Percentile to use if method is "percentile"
            save_results (bool): Whether to save results to files
            
        Returns:
            dict: Test results
        """
        try:
            if test_data is None or test_data.empty:
                logger.error("No test data provided")
                return {"success": False, "message": "No test data provided"}
            
            # Create detector
            detector = ContextualAnomalyDetector()
            
            # Run detection
            start_time = datetime.now()
            result_df = detector.detect_anomalies(test_data, threshold_method=threshold_method, percentile=percentile)
            end_time = datetime.now()
            
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
            
            # Calculate processing time
            processing_time = (end_time - start_time).total_seconds()
            
            # Prepare results
            results = {
                "success": True,
                "total_records": total_records,
                "anomaly_records": anomaly_records,
                "anomaly_percentage": anomaly_percentage,
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "low_confidence": low_confidence,
                "absolute_change": absolute_change,
                "percentage_change": percentage_change,
                "processing_time": processing_time,
                "threshold_method": threshold_method,
                "percentile": percentile,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Save results if requested
            if save_results:
                self._save_results(result_df, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error running test: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "message": str(e)}
    
    def _save_results(self, result_df, results):
        """
        Save test results to files.
        
        Args:
            result_df (pd.DataFrame): DataFrame with detection results
            results (dict): Test results statistics
        """
        try:
            # Create timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save results DataFrame to CSV
            csv_path = os.path.join(self.output_dir, f"anomaly_results_{timestamp}.csv")
            result_df.to_csv(csv_path, index=False)
            logger.info(f"Saved results to {csv_path}")
            
            # Save statistics to JSON
            json_path = os.path.join(self.output_dir, f"anomaly_stats_{timestamp}.json")
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=4)
            logger.info(f"Saved statistics to {json_path}")
            
            # Generate and save visualizations
            self._generate_visualizations(result_df, timestamp)
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _generate_visualizations(self, result_df, timestamp):
        """
        Generate and save visualizations of the test results.
        
        Args:
            result_df (pd.DataFrame): DataFrame with detection results
            timestamp (str): Timestamp for filenames
        """
        try:
            # Create directory for visualizations
            viz_dir = os.path.join(self.output_dir, "visualizations")
            os.makedirs(viz_dir, exist_ok=True)
            
            # Filter for anomalies
            anomalies_df = result_df[result_df['is_contextual_anomaly']].copy()
            
            if anomalies_df.empty:
                logger.info("No anomalies detected, skipping visualizations")
                return
            
            # 1. Histogram of anomaly confidence levels
            plt.figure(figsize=(10, 6))
            sns.histplot(anomalies_df['contextual_anomaly_confidence'], bins=20, kde=True)
            plt.title('Distribution of Anomaly Confidence Levels')
            plt.xlabel('Confidence Level')
            plt.ylabel('Count')
            plt.savefig(os.path.join(viz_dir, f"confidence_histogram_{timestamp}.png"))
            plt.close()
            
            # 2. Bar chart of anomaly types
            plt.figure(figsize=(10, 6))
            anomaly_types = anomalies_df['contextual_anomaly_type'].value_counts()
            sns.barplot(x=anomaly_types.index, y=anomaly_types.values)
            plt.title('Anomaly Types')
            plt.xlabel('Type')
            plt.ylabel('Count')
            plt.savefig(os.path.join(viz_dir, f"anomaly_types_{timestamp}.png"))
            plt.close()
            
            # 3. Time series of anomalies by asset
            # Group by asset_id and consumption_type
            for (asset_id, consumption_type), group in result_df.groupby(['asset_id', 'consumption_type']):
                if group[group['is_contextual_anomaly']].empty:
                    continue
                
                plt.figure(figsize=(12, 6))
                
                # Determine consumption column
                consumption_col = 'consumption'
                if 'corrected_value' in group.columns:
                    consumption_col = 'corrected_value'
                
                # Plot consumption
                plt.plot(group['date'], group[consumption_col], label='Consumption', color='blue')
                
                # Highlight anomalies
                anomalies = group[group['is_contextual_anomaly']]
                plt.scatter(anomalies['date'], anomalies[consumption_col], color='red', s=50, label='Anomalies')
                
                plt.title(f'Consumption and Anomalies for Asset {asset_id} ({consumption_type})')
                plt.xlabel('Date')
                plt.ylabel('Consumption')
                plt.legend()
                plt.grid(True)
                
                # Format x-axis dates
                plt.gcf().autofmt_xdate()
                
                # Save figure
                plt.savefig(os.path.join(viz_dir, f"timeseries_{asset_id}_{timestamp}.png"))
                plt.close()
                
                # 4. Daily changes and thresholds
                plt.figure(figsize=(12, 6))
                
                # Plot daily changes
                plt.plot(group['date'], group['daily_change'], label='Daily Change', color='blue')
                
                # Highlight anomalies
                anomalies = group[group['is_contextual_anomaly']]
                plt.scatter(anomalies['date'], anomalies['daily_change'], color='red', s=50, label='Anomalies')
                
                # Plot thresholds if available
                if 'contextual_anomaly_threshold' in anomalies.columns and not anomalies.empty:
                    # Get unique thresholds
                    thresholds = anomalies['contextual_anomaly_threshold'].unique()
                    
                    for threshold in thresholds:
                        if pd.notna(threshold):
                            plt.axhline(y=threshold, color='green', linestyle='--', label=f'Threshold: {threshold:.2f}')
                            plt.axhline(y=-threshold, color='green', linestyle='--')
                
                plt.title(f'Daily Changes and Anomalies for Asset {asset_id} ({consumption_type})')
                plt.xlabel('Date')
                plt.ylabel('Daily Change')
                plt.legend()
                plt.grid(True)
                
                # Format x-axis dates
                plt.gcf().autofmt_xdate()
                
                # Save figure
                plt.savefig(os.path.join(viz_dir, f"daily_changes_{asset_id}_{timestamp}.png"))
                plt.close()
            
            logger.info(f"Generated visualizations in {viz_dir}")
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

def run_test_for_asset(asset_id, consumption_type, data_source=None, threshold_method="std_dev", percentile=95):
    """
    Run a test for a specific asset and consumption type.
    
    Args:
        asset_id (str): Asset ID
        consumption_type (str): Consumption type
        data_source (str or pd.DataFrame, optional): Data source
        threshold_method (str): Method to use for threshold calculation
        percentile (float): Percentile to use if method is "percentile"
        
    Returns:
        dict: Test results
    """
    # Create test harness
    harness = AnomalyTestHarness(output_dir=f"test_results/{asset_id}")
    
    # Load test data
    test_data = harness.load_test_data(
        data_source=data_source,
        asset_id=asset_id,
        consumption_type=consumption_type
    )
    
    if test_data is None or test_data.empty:
        return {"success": False, "message": f"No data found for asset {asset_id} and consumption type {consumption_type}"}
    
    # Run test
    return harness.run_test(test_data, threshold_method=threshold_method, percentile=percentile)

def run_test_for_project(project_id, consumption_type=None, data_source=None, threshold_method="std_dev", percentile=95):
    """
    Run a test for all assets in a project.
    
    Args:
        project_id (str): Project ID
        consumption_type (str, optional): Consumption type
        data_source (str or pd.DataFrame, optional): Data source
        threshold_method (str): Method to use for threshold calculation
        percentile (float): Percentile to use if method is "percentile"
        
    Returns:
        dict: Test results
    """
    # Create test harness
    harness = AnomalyTestHarness(output_dir=f"test_results/project_{project_id}")
    
    # Load test data
    test_data = harness.load_test_data(
        data_source=data_source,
        project_id=project_id,
        consumption_type=consumption_type
    )
    
    if test_data is None or test_data.empty:
        return {"success": False, "message": f"No data found for project {project_id}"}
    
    # Run test
    return harness.run_test(test_data, threshold_method=threshold_method, percentile=percentile)

def analyze_specific_anomaly(asset_id, date, consumption_type=None, data_source=None, days_context=30):
    """
    Analyze a specific potential anomaly.
    
    Args:
        asset_id (str): Asset ID
        date (str): Date of the potential anomaly (YYYY-MM-DD)
        consumption_type (str, optional): Consumption type
        data_source (str or pd.DataFrame, optional): Data source
        days_context (int): Number of days of context to include
        
    Returns:
        dict: Analysis results
    """
    try:
        # Parse date
        anomaly_date = pd.to_datetime(date)
        
        # Create test harness
        harness = AnomalyTestHarness(output_dir=f"test_results/specific_anomaly_{asset_id}")
        
        # Load test data
        start_date = (anomaly_date - timedelta(days=days_context)).strftime("%Y-%m-%d")
        end_date = (anomaly_date + timedelta(days=days_context)).strftime("%Y-%m-%d")
        
        # Load data
        test_data = harness.load_test_data(
            data_source=data_source,
            asset_id=asset_id,
            consumption_type=consumption_type
        )
        
        if test_data is None or test_data.empty:
            return {"success": False, "message": f"No data found for asset {asset_id}"}
        
        # Filter for date range
        test_data = test_data[(test_data['date'] >= start_date) & (test_data['date'] <= end_date)]
        
        if test_data.empty:
            return {"success": False, "message": f"No data found for the specified date range"}
        
        # Create threshold calculator
        calculator = ThresholdCalculator(asset_id, consumption_type if consumption_type else test_data['consumption_type'].iloc[0])
        
        # Calculate thresholds
        thresholds = calculator.get_thresholds(df=test_data)
        
        if not thresholds:
            return {"success": False, "message": "Failed to calculate thresholds"}
        
        # Create detector
        detector = ContextualAnomalyDetector(asset_id, consumption_type if consumption_type else test_data['consumption_type'].iloc[0])
        
        # Run detection
        result_df = detector.detect_anomalies(test_data)
        
        # Filter for the specific date
        anomaly_row = result_df[result_df['date'] == anomaly_date]
        
        if anomaly_row.empty:
            return {"success": False, "message": f"No data found for date {date}"}
        
        # Determine consumption column
        consumption_col = 'consumption'
        if 'corrected_value' in anomaly_row.columns:
            consumption_col = 'corrected_value'
        
        # Get previous day's data
        prev_date = anomaly_date - timedelta(days=1)
        prev_row = result_df[result_df['date'] == prev_date]
        
        prev_consumption = None
        if not prev_row.empty:
            prev_consumption = prev_row[consumption_col].iloc[0]
        
        # Prepare results
        is_anomaly = anomaly_row['is_contextual_anomaly'].iloc[0] if 'is_contextual_anomaly' in anomaly_row.columns else False
        
        analysis = {
            "success": True,
            "asset_id": asset_id,
            "date": date,
            "consumption": anomaly_row[consumption_col].iloc[0],
            "previous_consumption": prev_consumption,
            "daily_change": anomaly_row['daily_change'].iloc[0] if 'daily_change' in anomaly_row.columns else None,
            "daily_change_pct": anomaly_row['daily_change_pct'].iloc[0] if 'daily_change_pct' in anomaly_row.columns else None,
            "is_anomaly": is_anomaly,
            "confidence": anomaly_row['contextual_anomaly_confidence'].iloc[0] if 'contextual_anomaly_confidence' in anomaly_row.columns else None,
            "anomaly_type": anomaly_row['contextual_anomaly_type'].iloc[0] if 'contextual_anomaly_type' in anomaly_row.columns else None,
            "threshold": anomaly_row['contextual_anomaly_threshold'].iloc[0] if 'contextual_anomaly_threshold' in anomaly_row.columns else None,
            "thresholds": thresholds
        }
        
        # Generate visualization
        try:
            # Create directory for visualizations
            viz_dir = os.path.join(harness.output_dir, "visualizations")
            os.makedirs(viz_dir, exist_ok=True)
            
            # Plot consumption time series
            plt.figure(figsize=(12, 6))
            
            # Plot consumption
            plt.plot(test_data['date'], test_data[consumption_col], label='Consumption', color='blue')
            
            # Highlight the specific date
            plt.scatter([anomaly_date], [anomaly_row[consumption_col].iloc[0]], color='red', s=100, label='Selected Date')
            
            # Highlight other anomalies
            other_anomalies = result_df[(result_df['is_contextual_anomaly']) & (result_df['date'] != anomaly_date)]
            if not other_anomalies.empty:
                plt.scatter(other_anomalies['date'], other_anomalies[consumption_col], color='orange', s=50, label='Other Anomalies')
            
            plt.title(f'Consumption for Asset {asset_id} Around {date}')
            plt.xlabel('Date')
            plt.ylabel('Consumption')
            plt.legend()
            plt.grid(True)
            
            # Format x-axis dates
            plt.gcf().autofmt_xdate()
            
            # Save figure
            plt.savefig(os.path.join(viz_dir, f"specific_anomaly_{asset_id}_{date.replace('-', '')}.png"))
            plt.close()
            
            # Plot daily changes
            plt.figure(figsize=(12, 6))
            
            # Plot daily changes if the column exists
            if 'daily_change' in test_data.columns:
                plt.plot(test_data['date'], test_data['daily_change'], label='Daily Change', color='blue')
                
                # Highlight the specific date
                if 'daily_change' in anomaly_row.columns and not pd.isna(anomaly_row['daily_change'].iloc[0]):
                    plt.scatter([anomaly_date], [anomaly_row['daily_change'].iloc[0]], color='red', s=100, label='Selected Date')
                
                # Plot thresholds
                plt.axhline(y=thresholds['high_threshold'], color='red', linestyle='--', label=f'High Threshold: {thresholds["high_threshold"]:.2f}')
                plt.axhline(y=-thresholds['high_threshold'], color='red', linestyle='--')
                plt.axhline(y=thresholds['medium_threshold'], color='orange', linestyle='--', label=f'Medium Threshold: {thresholds["medium_threshold"]:.2f}')
                plt.axhline(y=-thresholds['medium_threshold'], color='orange', linestyle='--')
                
                plt.title(f'Daily Changes for Asset {asset_id} Around {date}')
                plt.xlabel('Date')
                plt.ylabel('Daily Change')
                plt.legend()
                plt.grid(True)
                
                # Format x-axis dates
                plt.gcf().autofmt_xdate()
                
                # Save figure
                plt.savefig(os.path.join(viz_dir, f"specific_anomaly_changes_{asset_id}_{date.replace('-', '')}.png"))
            else:
                logger.warning("No 'daily_change' column found in the data, skipping daily changes plot")
            
            plt.close()
            
            analysis["visualizations_path"] = viz_dir
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing specific anomaly: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    # Example usage
    print("This module provides functions to test the contextual anomaly detection system.")
    print("Import and use the functions in your code or interactive session.") 