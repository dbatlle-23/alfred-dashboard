import pandas as pd
import numpy as np
from datetime import datetime
from config.metrics_config import DATA_PROCESSING

def validate_date_range(start_date, end_date):
    """
    Validate date range parameters.
    
    Args:
        start_date: Start date string or datetime
        end_date: End date string or datetime
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    try:
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
            
        if start_date > end_date:
            return False, "La fecha de inicio debe ser anterior a la fecha de fin"
            
        if end_date > datetime.now():
            return False, "La fecha de fin no puede ser futura"
            
        return True, ""
    except Exception as e:
        return False, f"Error al validar fechas: {str(e)}"

def validate_consumption_data(df):
    """
    Validate consumption data in DataFrame.
    
    Args:
        df: DataFrame with consumption data
        
    Returns:
        tuple: (bool, str, dict) - (is_valid, error_message, validation_results)
    """
    validation_results = {
        'missing_values': 0,
        'negative_values': 0,
        'zero_values': 0,
        'outliers': 0,
        'total_rows': len(df) if df is not None else 0
    }
    
    if df is None or df.empty:
        return False, "No hay datos para validar", validation_results
    
    try:
        # Check required columns
        required_columns = ['date', 'consumption', 'asset_id', 'consumption_type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}", validation_results
        
        # Convert consumption to numeric, keeping track of non-numeric values
        numeric_consumption = pd.to_numeric(df['consumption'], errors='coerce')
        validation_results['missing_values'] = numeric_consumption.isna().sum()
        
        # Check for negative values
        validation_results['negative_values'] = (numeric_consumption < 0).sum()
        
        # Check for zero values
        validation_results['zero_values'] = (numeric_consumption == 0).sum()
        
        # Check for outliers (values more than 3 standard deviations from mean)
        mean = numeric_consumption.mean()
        std = numeric_consumption.std()
        validation_results['outliers'] = ((numeric_consumption - mean).abs() > 3 * std).sum()
        
        # Determine if data is valid based on thresholds
        error_threshold = DATA_PROCESSING.get('error_threshold', 0.1)
        total_errors = (validation_results['missing_values'] + 
                       validation_results['negative_values'] + 
                       validation_results['outliers'])
        error_rate = total_errors / validation_results['total_rows']
        
        if error_rate > error_threshold:
            return False, f"Tasa de error ({error_rate:.2%}) supera el umbral ({error_threshold:.2%})", validation_results
        
        return True, "", validation_results
        
    except Exception as e:
        return False, f"Error al validar datos: {str(e)}", validation_results

def validate_aggregation_parameters(group_by, time_period=None):
    """
    Validate parameters for data aggregation.
    
    Args:
        group_by: Column or list of columns to group by
        time_period: Time period for temporal aggregation
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    valid_group_by = ['asset_id', 'project_id', 'consumption_type', 'date']
    valid_time_periods = ['D', 'W', 'M', 'Q', 'Y']
    
    try:
        if isinstance(group_by, str):
            group_by = [group_by]
            
        if not all(col in valid_group_by for col in group_by):
            invalid_cols = [col for col in group_by if col not in valid_group_by]
            return False, f"Columnas de agrupación inválidas: {', '.join(invalid_cols)}"
            
        if time_period and time_period not in valid_time_periods:
            return False, f"Período de tiempo inválido: {time_period}"
            
        return True, ""
        
    except Exception as e:
        return False, f"Error al validar parámetros: {str(e)}"

def validate_export_format(format_type):
    """
    Validate export format.
    
    Args:
        format_type: Export format type
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    valid_formats = ['csv', 'excel', 'json']
    
    if format_type not in valid_formats:
        return False, f"Formato de exportación inválido. Formatos válidos: {', '.join(valid_formats)}"
        
    return True, ""

def validate_filter_parameters(filters):
    """
    Validate filter parameters.
    
    Args:
        filters: Dictionary of filter parameters
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    try:
        valid_filters = {
            'client_id': str,
            'project_id': str,
            'asset_id': str,
            'consumption_type': (str, list),
            'start_date': (str, datetime),
            'end_date': (str, datetime)
        }
        
        for key, value in filters.items():
            if key not in valid_filters:
                return False, f"Filtro inválido: {key}"
                
            expected_type = valid_filters[key]
            if not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    type_names = ' o '.join([t.__name__ for t in expected_type])
                    return False, f"Tipo inválido para {key}. Se esperaba {type_names}"
                else:
                    return False, f"Tipo inválido para {key}. Se esperaba {expected_type.__name__}"
        
        return True, ""
        
    except Exception as e:
        return False, f"Error al validar filtros: {str(e)}"
