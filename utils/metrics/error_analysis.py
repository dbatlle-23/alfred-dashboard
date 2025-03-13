import pandas as pd
from datetime import datetime
from config.metrics_config import DATA_PROCESSING

def analyze_readings_errors(df):
    """
    Analyze errors in readings data.
    
    Args:
        df (pd.DataFrame): Input DataFrame with readings data
        
    Returns:
        dict: Dictionary containing error analysis results
    """
    if df.empty:
        return {
            'total_errors': 0,
            'errors_by_asset': {},
            'errors_by_consumption_type': {},
            'errors_by_period': {},
            'items': []
        }

    # Create a copy to avoid modifying the original
    analysis_df = df.copy()

    # Ensure date is datetime
    if 'date' in analysis_df.columns:
        analysis_df['date'] = pd.to_datetime(analysis_df['date'])
        analysis_df['period'] = analysis_df['date'].dt.strftime('%Y-%m')

    # Identify errors
    error_conditions = [
        analysis_df['consumption'].isna(),
        analysis_df['consumption'] == 'Error',
        analysis_df['consumption'] == 'Sin datos disponibles',
        (analysis_df['consumption'].astype(str).str.contains('error', case=False, na=False))
    ]
    
    analysis_df['has_error'] = pd.concat(error_conditions, axis=1).any(axis=1)

    # Count errors by different categories
    errors_by_asset = analysis_df[analysis_df['has_error']].groupby('asset_id').size().to_dict()
    errors_by_consumption_type = analysis_df[analysis_df['has_error']].groupby('consumption_type').size().to_dict()
    errors_by_period = analysis_df[analysis_df['has_error']].groupby('period').size().to_dict()

    # Create list of error items
    error_items = []
    for _, row in analysis_df[analysis_df['has_error']].iterrows():
        error_item = {
            'asset_id': row['asset_id'],
            'consumption_type': row['consumption_type'],
            'date': row['date'].strftime('%Y-%m-%d'),
            'period': row['period'],
            'value': row['consumption']
        }
        error_items.append(error_item)

    return {
        'total_errors': len(error_items),
        'errors_by_asset': errors_by_asset,
        'errors_by_consumption_type': errors_by_consumption_type,
        'errors_by_period': errors_by_period,
        'items': error_items
    }

def filter_errors_by_criteria(error_data, criteria):
    """
    Filter errors based on given criteria.
    
    Args:
        error_data (dict): Dictionary containing error analysis results
        criteria (dict): Dictionary containing filter criteria
        
    Returns:
        dict: Filtered error data
    """
    if not error_data or not error_data.get('items'):
        return {
            'total': 0,
            'items': []
        }

    filtered_items = error_data['items'].copy()
    mode = criteria.get('mode', 'all')

    # Apply filters based on mode
    if mode == 'by_asset' and criteria.get('asset_id'):
        filtered_items = [
            item for item in filtered_items 
            if item['asset_id'] == criteria['asset_id']
        ]
    elif mode == 'by_consumption_type' and criteria.get('consumption_type'):
        filtered_items = [
            item for item in filtered_items 
            if item['consumption_type'] == criteria['consumption_type']
        ]
    elif mode == 'by_period' and criteria.get('period'):
        filtered_items = [
            item for item in filtered_items 
            if item['period'] == criteria['period']
        ]

    return {
        'total': len(filtered_items),
        'items': filtered_items
    }

def prepare_regeneration_preview(filtered_errors):
    """
    Prepare preview data for regeneration.
    
    Args:
        filtered_errors (dict): Dictionary containing filtered error data
        
    Returns:
        dict: Preview data for regeneration
    """
    if not filtered_errors or not filtered_errors.get('items'):
        return {
            'total': 0,
            'assets': [],
            'consumption_types': [],
            'periods': []
        }

    items = filtered_errors['items']
    
    # Get unique values
    assets = list(set(item['asset_id'] for item in items))
    consumption_types = list(set(item['consumption_type'] for item in items))
    periods = list(set(item['period'] for item in items))

    return {
        'total': len(items),
        'assets': assets,
        'consumption_types': consumption_types,
        'periods': periods
    }

def validate_readings(df, threshold=None):
    """
    Validate readings data for anomalies and errors.
    
    Args:
        df (pd.DataFrame): Input DataFrame with readings data
        threshold (float, optional): Threshold for anomaly detection
        
    Returns:
        tuple: (DataFrame with validation results, dict with validation summary)
    """
    if df.empty:
        return df, {'valid': 0, 'invalid': 0, 'anomalies': 0}

    validation_df = df.copy()
    threshold = threshold or DATA_PROCESSING['error_threshold']

    # Add validation columns
    validation_df['is_valid'] = ~validation_df['has_error']
    
    # Detect anomalies (values outside normal range)
    if 'consumption' in validation_df.columns:
        try:
            consumption_values = pd.to_numeric(validation_df['consumption'], errors='coerce')
            mean = consumption_values.mean()
            std = consumption_values.std()
            validation_df['is_anomaly'] = (
                (consumption_values > mean + (3 * std)) | 
                (consumption_values < mean - (3 * std))
            )
        except:
            validation_df['is_anomaly'] = False

    # Create summary
    summary = {
        'valid': validation_df['is_valid'].sum(),
        'invalid': (~validation_df['is_valid']).sum(),
        'anomalies': validation_df['is_anomaly'].sum() if 'is_anomaly' in validation_df.columns else 0
    }

    return validation_df, summary
