import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from utils.logging import get_logger

# Configure logger
logger = get_logger(__name__)

def calculate_total_consumption(data, start_date=None, end_date=None):
    """
    Calculate the total water consumption within the specified date range.
    
    Args:
        data (pandas.DataFrame): DataFrame containing consumption data with 'date' and 'consumption' columns
        start_date (str or datetime, optional): Start date for the calculation period
        end_date (str or datetime, optional): End date for the calculation period
        
    Returns:
        float: Total consumption value
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        logger.warning("No data provided for total consumption calculation")
        return 0
    
    if 'date' not in data.columns or 'consumption' not in data.columns:
        logger.error("Data must contain 'date' and 'consumption' columns")
        return 0
    
    # Create a copy to avoid modifying the original DataFrame
    df = data.copy()
    
    # Convert date to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Filter by date range if specified
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    # Sum the consumption values
    return df['consumption'].sum()

def calculate_average_consumption(data, period='daily', start_date=None, end_date=None):
    """
    Calculate the average water consumption over the specified period.
    
    Args:
        data (pandas.DataFrame): DataFrame containing consumption data with 'date' and 'consumption' columns
        period (str): Aggregation period ('daily', 'weekly', 'monthly')
        start_date (str or datetime, optional): Start date for the calculation period
        end_date (str or datetime, optional): End date for the calculation period
        
    Returns:
        float: Average consumption value
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        logger.warning("No data provided for average consumption calculation")
        return 0
    
    if 'date' not in data.columns or 'consumption' not in data.columns:
        logger.error("Data must contain 'date' and 'consumption' columns")
        return 0
    
    # Create a copy to avoid modifying the original DataFrame
    df = data.copy()
    
    # Convert date to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Filter by date range if specified
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    # Calculate average based on the specified period
    if period == 'weekly':
        df['week'] = df['date'].dt.isocalendar().week
        return df.groupby('week')['consumption'].mean().mean()
    elif period == 'monthly':
        df['month'] = df['date'].dt.month
        return df.groupby('month')['consumption'].mean().mean()
    else:  # default to daily
        return df['consumption'].mean()

def detect_peak_hours(hourly_data, threshold_percentile=90):
    """
    Detect peak hours of water consumption.
    
    Args:
        hourly_data (pandas.DataFrame): DataFrame containing hourly consumption data with 'hour' and 'consumption' columns
        threshold_percentile (int): Percentile threshold for determining peak hours (default: 90)
        
    Returns:
        list: List of peak hour ranges
    """
    if not isinstance(hourly_data, pd.DataFrame) or hourly_data.empty:
        logger.warning("No hourly data provided for peak hour detection")
        return []
    
    if 'hour' not in hourly_data.columns or 'consumption' not in hourly_data.columns:
        logger.error("Hourly data must contain 'hour' and 'consumption' columns")
        return []
    
    # Calculate threshold for peak hours
    threshold = np.percentile(hourly_data['consumption'], threshold_percentile)
    
    # Identify peak hours (hours where consumption is above the threshold)
    peak_hours = hourly_data[hourly_data['consumption'] >= threshold]['hour'].tolist()
    
    # Group consecutive hours into ranges
    if not peak_hours:
        return []
        
    peak_hours.sort()
    ranges = []
    range_start = peak_hours[0]
    prev_hour = peak_hours[0]
    
    for hour in peak_hours[1:]:
        if hour != prev_hour + 1:
            # End of a range
            if range_start == prev_hour:
                ranges.append(f"{range_start}-{range_start + 1} h")
            else:
                ranges.append(f"{range_start}-{prev_hour + 1} h")
            range_start = hour
        prev_hour = hour
    
    # Add the last range
    if range_start == prev_hour:
        ranges.append(f"{range_start}-{range_start + 1} h")
    else:
        ranges.append(f"{range_start}-{prev_hour + 1} h")
    
    return ranges

def compare_time_periods(data, current_start, current_end, previous_start=None, previous_end=None):
    """
    Compare water consumption between two time periods.
    
    Args:
        data (pandas.DataFrame): DataFrame containing consumption data with 'date' and 'consumption' columns
        current_start (str or datetime): Start date for the current period
        current_end (str or datetime): End date for the current period
        previous_start (str or datetime, optional): Start date for the previous period
        previous_end (str or datetime, optional): End date for the previous period
        
    Returns:
        dict: Comparison results including total consumption, average consumption, and percentage difference
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        logger.warning("No data provided for time period comparison")
        return {"error": "No data available"}
    
    if 'date' not in data.columns or 'consumption' not in data.columns:
        logger.error("Data must contain 'date' and 'consumption' columns")
        return {"error": "Invalid data format"}
    
    # Create a copy to avoid modifying the original DataFrame
    df = data.copy()
    
    # Convert date to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Convert input dates to datetime
    current_start = pd.to_datetime(current_start)
    current_end = pd.to_datetime(current_end)
    
    # Calculate duration of current period
    current_duration = (current_end - current_start).days + 1
    
    # If no previous period specified, use the same duration before the current period
    if previous_start is None or previous_end is None:
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=current_duration - 1)
    else:
        previous_start = pd.to_datetime(previous_start)
        previous_end = pd.to_datetime(previous_end)
    
    # Filter data for current and previous periods
    current_data = df[(df['date'] >= current_start) & (df['date'] <= current_end)]
    previous_data = df[(df['date'] >= previous_start) & (df['date'] <= previous_end)]
    
    # Calculate total consumption for each period
    current_total = current_data['consumption'].sum() if not current_data.empty else 0
    previous_total = previous_data['consumption'].sum() if not previous_data.empty else 0
    
    # Calculate average daily consumption for each period
    current_avg = current_data['consumption'].mean() if not current_data.empty else 0
    previous_avg = previous_data['consumption'].mean() if not previous_data.empty else 0
    
    # Calculate percentage difference
    if previous_total > 0:
        total_pct_diff = ((current_total - previous_total) / previous_total) * 100
    else:
        total_pct_diff = 0
    
    if previous_avg > 0:
        avg_pct_diff = ((current_avg - previous_avg) / previous_avg) * 100
    else:
        avg_pct_diff = 0
    
    # Return comparison results
    return {
        "current_period": {
            "start": current_start,
            "end": current_end,
            "total_consumption": current_total,
            "average_consumption": current_avg
        },
        "previous_period": {
            "start": previous_start,
            "end": previous_end,
            "total_consumption": previous_total,
            "average_consumption": previous_avg
        },
        "comparison": {
            "total_difference": current_total - previous_total,
            "total_pct_difference": total_pct_diff,
            "avg_difference": current_avg - previous_avg,
            "avg_pct_difference": avg_pct_diff
        }
    }

def detect_anomalies_in_water_consumption(data, method='zscore', threshold=3.0, min_periods=7):
    """
    Detect anomalies in water consumption data.
    
    Args:
        data (pandas.DataFrame): DataFrame containing consumption data with 'date' and 'consumption' columns
        method (str): Method for anomaly detection ('zscore', 'iqr', 'percentile')
        threshold (float): Threshold for anomaly detection (e.g., z-score threshold)
        min_periods (int): Minimum number of periods required to perform anomaly detection
        
    Returns:
        list: Anomalies detected in the data with date, value, and additional information
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        logger.warning("No data provided for anomaly detection")
        return []
    
    if 'date' not in data.columns or 'consumption' not in data.columns:
        logger.error("Data must contain 'date' and 'consumption' columns")
        return []
    
    # Create a copy to avoid modifying the original DataFrame
    df = data.copy()
    
    # Convert date to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date
    df = df.sort_values('date')
    
    # Check if we have enough data points
    if len(df) < min_periods:
        logger.warning(f"Not enough data points for anomaly detection (minimum required: {min_periods})")
        return []
    
    anomalies = []
    
    if method == 'zscore':
        # Z-score method
        mean = df['consumption'].mean()
        std = df['consumption'].std()
        
        # Skip if standard deviation is zero (all values are the same)
        if std == 0:
            logger.warning("Standard deviation is zero, skipping z-score anomaly detection")
            return []
        
        # Calculate z-scores
        df['zscore'] = (df['consumption'] - mean) / std
        
        # Identify anomalies
        anomaly_df = df[abs(df['zscore']) > threshold]
        
        for _, row in anomaly_df.iterrows():
            direction = "superior" if row['zscore'] > 0 else "inferior"
            percentage = abs((row['consumption'] - mean) / mean * 100) if mean > 0 else 0
            
            anomalies.append({
                'date': row['date'],
                'value': row['consumption'],
                'zscore': row['zscore'],
                'direction': direction,
                'percentage': percentage,
                'expected': mean
            })
    
    elif method == 'iqr':
        # IQR method
        q1 = df['consumption'].quantile(0.25)
        q3 = df['consumption'].quantile(0.75)
        iqr = q3 - q1
        
        # Calculate lower and upper bounds
        lower_bound = q1 - (threshold * iqr)
        upper_bound = q3 + (threshold * iqr)
        
        # Identify anomalies
        anomaly_df = df[(df['consumption'] < lower_bound) | (df['consumption'] > upper_bound)]
        
        for _, row in anomaly_df.iterrows():
            direction = "superior" if row['consumption'] > q3 else "inferior"
            median = df['consumption'].median()
            percentage = abs((row['consumption'] - median) / median * 100) if median > 0 else 0
            
            anomalies.append({
                'date': row['date'],
                'value': row['consumption'],
                'direction': direction,
                'percentage': percentage,
                'expected': median
            })
    
    elif method == 'percentile':
        # Percentile method
        lower_percentile = (100 - threshold) / 2
        upper_percentile = 100 - lower_percentile
        
        lower_bound = df['consumption'].quantile(lower_percentile / 100)
        upper_bound = df['consumption'].quantile(upper_percentile / 100)
        
        # Identify anomalies
        anomaly_df = df[(df['consumption'] < lower_bound) | (df['consumption'] > upper_bound)]
        
        for _, row in anomaly_df.iterrows():
            direction = "superior" if row['consumption'] > df['consumption'].median() else "inferior"
            median = df['consumption'].median()
            percentage = abs((row['consumption'] - median) / median * 100) if median > 0 else 0
            
            anomalies.append({
                'date': row['date'],
                'value': row['consumption'],
                'direction': direction,
                'percentage': percentage,
                'expected': median
            })
    
    else:
        logger.error(f"Unknown anomaly detection method: {method}")
    
    return anomalies

def generate_water_consumption_analysis(data, config=None):
    """
    Generate a comprehensive water consumption analysis.
    
    Args:
        data (pandas.DataFrame): DataFrame containing consumption data with 'date' and 'consumption' columns
        config (dict, optional): Configuration parameters for the analysis
            
    Returns:
        dict: Complete analysis results
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        logger.warning("No data provided for water consumption analysis")
        return {"error": "No data available for analysis"}
    
    if 'date' not in data.columns or 'consumption' not in data.columns:
        logger.error("Data must contain 'date' and 'consumption' columns")
        return {"error": "Invalid data format"}
    
    # Default configuration
    default_config = {
        'anomaly_method': 'zscore',
        'anomaly_threshold': 3.0,
        'peak_hours_percentile': 90,
        'include_hourly_analysis': True
    }
    
    # Merge with provided config
    if config and isinstance(config, dict):
        analysis_config = {**default_config, **config}
    else:
        analysis_config = default_config
    
    # Create a copy to avoid modifying the original DataFrame
    df = data.copy()
    
    # Convert date to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Calculate total and average consumption
    total_consumption = calculate_total_consumption(df)
    daily_avg = calculate_average_consumption(df, period='daily')
    weekly_avg = calculate_average_consumption(df, period='weekly')
    monthly_avg = calculate_average_consumption(df, period='monthly')
    
    # Detect anomalies
    anomalies = detect_anomalies_in_water_consumption(
        df, 
        method=analysis_config['anomaly_method'],
        threshold=analysis_config['anomaly_threshold']
    )
    
    # Prepare hourly data if available
    hourly_data = None
    peak_hours = []
    
    if analysis_config['include_hourly_analysis'] and 'hour' in df.columns:
        hourly_data = df.groupby('hour')['consumption'].mean().reset_index()
        peak_hours = detect_peak_hours(hourly_data, threshold_percentile=analysis_config['peak_hours_percentile'])
    
    # Prepare daily data
    daily_data = df.copy()
    
    # Prepare monthly data
    monthly_data = df.copy()
    monthly_data['month'] = monthly_data['date'].dt.strftime('%Y-%m')
    monthly_data = monthly_data.groupby('month')['consumption'].sum().reset_index()
    
    # Compile the analysis results
    analysis_results = {
        'total_consumption': total_consumption,
        'average_daily': daily_avg,
        'average_weekly': weekly_avg,
        'average_monthly': monthly_avg,
        'peak_hours': peak_hours,
        'num_anomalies': len(anomalies),
        'anomalies': anomalies,
        'daily_data': df,
        'monthly_data': monthly_data,
        'hourly_data': hourly_data
    }
    
    return analysis_results 