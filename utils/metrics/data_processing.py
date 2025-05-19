import pandas as pd
from datetime import datetime
from config.metrics_config import DATA_PROCESSING
from constants.metrics import CONSUMPTION_TAGS_MAPPING
from utils.adapters.anomaly_adapter import AnomalyAdapter
from utils.logging import get_logger
import time
from functools import lru_cache

logger = get_logger(__name__)

# Add a cache for processed data
_PROCESSED_DATA_CACHE = {}

def process_metrics_data(df, 
                        client_id=None, 
                        project_id=None, 
                        asset_id=None, 
                        consumption_tags=None, 
                        start_date=None, 
                        end_date=None,
                        use_cache=True):
    """
    Process metrics data by applying filters and returning the filtered DataFrame.
    
    Args:
        df: DataFrame with consumption data
        client_id: ID of the client to filter by
        project_id: ID of the project to filter by
        asset_id: ID of the asset to filter by
        consumption_tags: List of consumption tags to filter by
        start_date: Start date for filtering
        end_date: End date for filtering
        use_cache: Whether to use the cache for this process
        
    Returns:
        Filtered DataFrame
    """
    if df.empty:
        print("[INFO] process_metrics_data - Empty DataFrame provided")
        return df
    
    # Generate a cache key if caching is enabled
    if use_cache:
        # Generate a simple cache key based on filter parameters
        cache_key = f"{client_id}|{project_id}|{asset_id}|{'-'.join(sorted(consumption_tags)) if consumption_tags else 'None'}|{start_date}|{end_date}"
        
        # Check if we have this query result cached
        if cache_key in _PROCESSED_DATA_CACHE:
            print(f"[INFO] process_metrics_data - Using cached result for filters")
            return _PROCESSED_DATA_CACHE[cache_key].copy()
    
    # Measure processing time
    start_time = time.time()
    
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # If date column is string, convert to datetime
    if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # If consumption column is not float, convert it
    if 'consumption' in df.columns and not pd.api.types.is_float_dtype(df['consumption']):
        df['consumption'] = pd.to_numeric(df['consumption'], errors='coerce')
    
    # Apply filters
    from utils.data_loader import filter_data
    filtered_df = filter_data(
        df,
        client_id=client_id,
        project_id=project_id,
        asset_id=asset_id,
        consumption_tags=consumption_tags,
        start_date=start_date,
        end_date=end_date
    )
    
    # Cache the result if caching is enabled
    if use_cache:
        _PROCESSED_DATA_CACHE[cache_key] = filtered_df.copy()
    
    process_time = time.time() - start_time
    print(f"[INFO] process_metrics_data - Processed data in {process_time:.2f} seconds, {len(filtered_df)} rows")
    
    return filtered_df

# Clear function for processed data cache
def clear_processed_data_cache():
    """Clear the processed data cache."""
    global _PROCESSED_DATA_CACHE
    _PROCESSED_DATA_CACHE = {}
    print("[INFO] clear_processed_data_cache - Cache cleared")
    return True

def aggregate_data_by_project(df):
    """Aggregate data by project."""
    if df.empty:
        return df
    
    return df.groupby(['project_id', 'date'])['consumption'].sum().reset_index()

def aggregate_data_by_asset(df):
    """Aggregate data by asset."""
    if df.empty:
        return df
    
    return df.groupby(['asset_id', 'date'])['consumption'].sum().reset_index()

def aggregate_data_by_consumption_type(df):
    """Aggregate data by consumption type."""
    if df.empty:
        return df
    
    return df.groupby(['consumption_type', 'date'])['consumption'].sum().reset_index()

def aggregate_data_by_month_and_asset(df):
    """Aggregate data by month and asset."""
    if df.empty:
        return df
    
    # Ensure date is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Create year_month column
    df['year_month'] = df['date'].dt.strftime('%Y-%m')
    
    # Aggregate
    return df.groupby(['asset_id', 'year_month', 'consumption_type'])['consumption'].sum().reset_index()

def generate_monthly_readings_by_consumption_type(df, consumption_tags, start_date=None, end_date=None):
    """Generate monthly readings tables by consumption type."""
    if df.empty:
        print("generate_monthly_readings_by_consumption_type: DataFrame is empty")
        return {}
    
    print(f"generate_monthly_readings_by_consumption_type: Processing DataFrame with {len(df)} rows")
    
    # Ensure date is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter by date range if provided
    if start_date:
        start_date_dt = pd.to_datetime(start_date)
        df = df[df['date'] >= start_date_dt]
        print(f"Filtered by start_date {start_date} ({start_date_dt}): {len(df)} rows remaining")
    if end_date:
        end_date_dt = pd.to_datetime(end_date)
        df = df[df['date'] <= end_date_dt]
        print(f"Filtered by end_date {end_date} ({end_date_dt}): {len(df)} rows remaining")
    
    # Create tables for each consumption type
    tables = {}
    
    # Print unique consumption_type and tag values for debugging
    if 'consumption_type' in df.columns:
        unique_types = df['consumption_type'].unique()
        print(f"Unique consumption_type values in generate_monthly_readings_by_consumption_type: {unique_types}")
    if 'tag' in df.columns:
        unique_tags = df['tag'].unique()
        print(f"Unique tag values in generate_monthly_readings_by_consumption_type: {unique_tags}")
    
    for tag in consumption_tags:
        print(f"Processing tag: {tag}")
        
        # Create a more flexible filter for this tag
        tag_mask = pd.Series(False, index=df.index)
        
        # Check if tag is in consumption_type column
        if 'consumption_type' in df.columns:
            type_mask = df['consumption_type'].astype(str).str.contains(tag, case=False, na=False)
            tag_mask = tag_mask | type_mask
            print(f"Matches in consumption_type column: {type_mask.sum()}")
        
        # Check if tag is in tag column
        if 'tag' in df.columns:
            tag_col_mask = df['tag'].astype(str).str.contains(tag, case=False, na=False)
            tag_mask = tag_mask | tag_col_mask
            print(f"Matches in tag column: {tag_col_mask.sum()}")
        
        # Filter data for this consumption type
        tag_data = df[tag_mask].copy()
        print(f"Filtered data for tag {tag}: {len(tag_data)} rows")
        
        if not tag_data.empty:
            # Group by asset_id and month
            tag_data['year_month'] = tag_data['date'].dt.strftime('%Y-%m')
            monthly_data = {}
            
            # Process each asset
            for asset_id, asset_group in tag_data.groupby('asset_id'):
                print(f"Processing asset_id: {asset_id}, group size: {len(asset_group)}")
                
                # Initialize a dictionary to store monthly readings
                asset_monthly_readings = {}
                
                # Process each month for this asset
                for month, month_group in asset_group.groupby('year_month'):
                    try:
                        # Sort by date to ensure correct order
                        month_group = month_group.sort_values('date')
                        
                        # Get first and last reading of the month
                        first_reading = month_group['consumption'].iloc[0]
                        last_reading = month_group['consumption'].iloc[-1]
                        
                        # Calculate monthly consumption (last reading - first reading)
                        monthly_consumption = last_reading - first_reading
                        
                        # Store the last reading as the monthly reading
                        # This represents the accumulated reading at the end of the month
                        asset_monthly_readings[month] = last_reading
                        
                        print(f"Month {month}, Asset {asset_id}: First reading = {first_reading}, Last reading = {last_reading}, Monthly consumption = {monthly_consumption}")
                    except Exception as e:
                        print(f"Error processing month {month} for asset {asset_id}: {str(e)}")
                        import traceback
                        print(traceback.format_exc())
                
                if asset_monthly_readings:
                    monthly_data[asset_id] = pd.Series(asset_monthly_readings)
            
            # Create a new DataFrame from the monthly data
            if monthly_data:
                # Convert the dictionary to a DataFrame
                pivot = pd.DataFrame(monthly_data).T
                
                # Sort columns chronologically
                sorted_columns = sorted(pivot.columns)
                pivot = pivot[sorted_columns]
                
                # Create a copy for consumption calculations
                consumption_pivot = pivot.copy()
                
                # Calculate monthly consumption (difference between consecutive months)
                for i in range(1, len(sorted_columns)):
                    current_month = sorted_columns[i]
                    prev_month = sorted_columns[i-1]
                    consumption_pivot[f"{current_month} (Consumo)"] = consumption_pivot[current_month] - consumption_pivot[prev_month]
                
                # Reorganize columns to interleave readings and consumption
                new_columns = []
                for col in sorted_columns:
                    new_columns.append(col)
                    if f"{col} (Consumo)" in consumption_pivot.columns:
                        new_columns.append(f"{col} (Consumo)")
                
                # Keep only the columns that exist
                existing_columns = [col for col in new_columns if col in consumption_pivot.columns]
                consumption_pivot = consumption_pivot[existing_columns]
                
                # Reset index
                consumption_pivot = consumption_pivot.reset_index()
                
                # Rename asset_id column
                consumption_pivot = consumption_pivot.rename(columns={'index': 'Asset'})
                
                # Use the tag as the key, or a readable name if available
                readable_tag = CONSUMPTION_TAGS_MAPPING.get(tag, tag)
                tables[readable_tag] = consumption_pivot
                print(f"Created table for {readable_tag} with shape {consumption_pivot.shape}")
            else:
                print(f"No monthly data found for tag {tag}")
        else:
            print(f"No data found for tag {tag}")
    
    return tables

def prepare_data_for_export(df):
    """Prepare data for export to CSV or other formats."""
    if df.empty:
        return df
    
    export_df = df.copy()
    
    # Format dates
    if 'date' in export_df.columns:
        export_df['date'] = export_df['date'].dt.strftime(DATA_PROCESSING['date_format'])
    
    # Map consumption types to readable names
    if 'consumption_type' in export_df.columns:
        export_df['consumption_type'] = export_df['consumption_type'].map(
            CONSUMPTION_TAGS_MAPPING).fillna(export_df['consumption_type'])
    
    return export_df

def generate_monthly_consumption_summary(df, start_date=None, end_date=None):
    """
    Generate monthly consumption summary data.
    
    Args:
        df (pd.DataFrame): DataFrame with consumption data
        start_date (str, optional): Start date for filtering
        end_date (str, optional): End date for filtering
        
    Returns:
        pd.DataFrame: DataFrame with monthly summary data
    """
    print("=====================================================")
    print("DEBUGGING MONTHLY SUMMARY - FUNCTION CALLED")
    print("=====================================================")
    print(f"[INFO] generate_monthly_consumption_summary: DataFrame type: {type(df)}")
    print(f"[INFO] generate_monthly_consumption_summary: DataFrame shape: {df.shape if df is not None else 'None'}")
    print(f"[INFO] generate_monthly_consumption_summary: DataFrame empty?: {df.empty if df is not None else 'None'}")
    
    if df is None or df.empty:
        print("[INFO] generate_monthly_consumption_summary: DataFrame is empty or None")
        # Devolver un DataFrame vacío en lugar de datos de ejemplo
        return pd.DataFrame()
    
    # Verificar que las columnas necesarias estén presentes
    required_columns = ['date', 'consumption', 'asset_id']
    if not all(col in df.columns for col in required_columns):
        print(f"[ERROR] generate_monthly_consumption_summary: Missing required columns. Available columns: {df.columns.tolist()}")
        return pd.DataFrame()
    
    # Convertir fechas a datetime si son strings
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # Eliminar filas con fechas inválidas
        df = df.dropna(subset=['date'])
    
    # Convertir consumo a numérico si no lo es
    if not pd.api.types.is_numeric_dtype(df['consumption']):
        df['consumption'] = pd.to_numeric(df['consumption'], errors='coerce')
        # Eliminar filas con consumos inválidos
        df = df.dropna(subset=['consumption'])
    
    # Verificar si hay datos después de la limpieza
    if df.empty:
        print("[ERROR] generate_monthly_consumption_summary: DataFrame is empty after cleaning")
        return pd.DataFrame()
    
    # Añadir columna de mes
    df['month'] = df['date'].dt.strftime('%Y-%m')
    
    # Determinar la columna de consumo
    consumption_column = 'consumption'
    if 'corrected_value' in df.columns:
        consumption_column = 'corrected_value'
    
    # Agrupar por mes y calcular estadísticas
    try:
        # Crear un DataFrame para almacenar los consumos reales mensuales
        monthly_consumption_df = pd.DataFrame()
        
        # Procesar cada activo por separado
        for asset_id, asset_group in df.groupby('asset_id'):
            print(f"[INFO] Processing asset_id: {asset_id}")
            
            # Ordenar por fecha para asegurar el cálculo correcto
            asset_group = asset_group.sort_values('date')
            
            # Procesar cada mes para este activo
            monthly_consumptions = []
            
            for month, month_group in asset_group.groupby('month'):
                print(f"[INFO] Processing month: {month} for asset_id: {asset_id}")
                
                # Ordenar por fecha dentro del mes
                month_group = month_group.sort_values('date')
                
                # Obtener primera y última lectura del mes
                first_reading = month_group[consumption_column].iloc[0]
                last_reading = month_group[consumption_column].iloc[-1]
                
                # Calcular consumo mensual (última lectura - primera lectura)
                try:
                    # Convertir a números si son strings
                    if isinstance(first_reading, str):
                        first_reading = float(first_reading)
                    if isinstance(last_reading, str):
                        last_reading = float(last_reading)
                    
                    # Calcular el consumo real
                    real_consumption = last_reading - first_reading
                    
                    # Si el consumo es negativo (posible error o reinicio), usar el último valor
                    if real_consumption < 0:
                        print(f"[WARNING] Negative consumption detected for asset {asset_id}, month {month}: {real_consumption}. Using last reading: {last_reading}")
                        real_consumption = last_reading
                    
                    # Guardar el resultado
                    monthly_consumptions.append({
                        'asset_id': asset_id,
                        'month': month,
                        'real_consumption': real_consumption,
                        'first_reading': first_reading,
                        'last_reading': last_reading
                    })
                    
                    print(f"[INFO] Asset: {asset_id}, Month: {month}, First reading: {first_reading}, Last reading: {last_reading}, Consumption: {real_consumption}")
                except (ValueError, TypeError) as e:
                    print(f"[ERROR] Error calculating consumption for asset {asset_id}, month {month}: {str(e)}")
            
            # Añadir los consumos mensuales de este activo al DataFrame de consumos reales
            if monthly_consumptions:
                asset_consumption_df = pd.DataFrame(monthly_consumptions)
                monthly_consumption_df = pd.concat([monthly_consumption_df, asset_consumption_df])
        
        # Verificar si hay consumos reales calculados
        if monthly_consumption_df.empty:
            print(f"[WARNING] No real consumption calculated, using aggregation method")
            # Usar método de agregación como fallback
            monthly_summary = df.groupby('month').agg(
                total_consumption=(consumption_column, 'sum'),
                average_consumption=(consumption_column, 'mean'),
                min_consumption=(consumption_column, 'min'),
                max_consumption=(consumption_column, 'max'),
                asset_count=('asset_id', 'nunique')
            ).reset_index()
        else:
            # Calcular estadísticas sobre los consumos reales
            print(f"[INFO] Calculating statistics on real consumption")
            monthly_summary = monthly_consumption_df.groupby('month').agg(
                total_consumption=('real_consumption', 'sum'),
                average_consumption=('real_consumption', 'mean'),
                min_consumption=('real_consumption', 'min'),
                max_consumption=('real_consumption', 'max'),
                asset_count=('asset_id', 'nunique')
            ).reset_index()
        
        # Add date column for sorting
        monthly_summary['date'] = pd.to_datetime(monthly_summary['month'] + '-01')
        
        # Sort by date
        monthly_summary = monthly_summary.sort_values('date')
        
        print(f"[INFO] generate_monthly_consumption_summary: Generated monthly summary with {len(monthly_summary)} rows")
        return monthly_summary
        
    except Exception as e:
        print(f"[ERROR] generate_monthly_consumption_summary: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return pd.DataFrame()

def generate_calculation_metadata(df, monthly_summary):
    """
    Genera metadatos de cálculo para la tabla de resumen mensual.
    
    Args:
        df (pd.DataFrame): DataFrame original con datos detallados
        monthly_summary (pd.DataFrame): DataFrame con el resumen mensual
        
    Returns:
        dict: Metadatos de cálculo para cada celda
    """
    metadata = {}
    
    # Asegurarse de que las fechas estén en formato datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # Iterar por cada columna de interés
    for column in ['total_consumption', 'average_consumption', 'min_consumption', 'max_consumption', 'asset_count']:
        metadata[column] = {}
        
        # Iterar por cada fila (mes) en el resumen
        for idx, row in monthly_summary.iterrows():
            month_str = row['month']
            month_date = pd.to_datetime(month_str + '-01')
            
            # Filtrar datos originales para este mes
            month_data = df[df['date'].dt.strftime('%Y-%m') == month_str] if 'date' in df.columns else pd.DataFrame()
            
            # Metadatos comunes para todas las columnas
            common_metadata = {
                'period': month_str,
                'last_updated': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_source': 'Base de datos de lecturas',
                'record_count': len(month_data),
                'assets_included': ', '.join(month_data['asset_id'].astype(str).unique()) if 'asset_id' in month_data.columns and not month_data.empty else 'No disponible'
            }
            
            # Metadatos específicos para cada columna
            if column == 'total_consumption':
                formula = "SUM(última_lectura_mes - primera_lectura_mes) para todos los activos"
                description = "Suma total de los consumos reales (diferencia entre lecturas) de todos los activos en el mes"
                unit = get_consumption_unit(df)
                
                metadata[column][str(idx)] = {
                    **common_metadata,
                    'formula': formula,
                    'description': description,
                    'unit': unit
                }
                
            elif column == 'average_consumption':
                formula = "AVG(última_lectura_mes - primera_lectura_mes) para todos los activos"
                description = "Promedio de los consumos reales (diferencia entre lecturas) por activo en el mes"
                unit = get_consumption_unit(df)
                
                metadata[column][str(idx)] = {
                    **common_metadata,
                    'formula': formula,
                    'description': description,
                    'unit': unit
                }
                
            elif column == 'min_consumption':
                # Encontrar el activo con consumo mínimo
                # Ahora necesitamos calcular el consumo real para cada activo
                min_asset = 'No disponible'
                min_consumption = None
                
                if not month_data.empty and 'asset_id' in month_data.columns:
                    try:
                        # Calcular consumo real para cada activo
                        consumption_column = 'consumption'
                        if consumption_column not in month_data.columns and 'value' in month_data.columns:
                            consumption_column = 'value'
                        
                        for asset_id, asset_group in month_data.groupby('asset_id'):
                            # Ordenar por fecha
                            asset_group = asset_group.sort_values('date')
                            
                            # Calcular consumo real
                            if len(asset_group) >= 2:
                                first_reading = asset_group[consumption_column].iloc[0]
                                last_reading = asset_group[consumption_column].iloc[-1]
                                
                                # Convertir a números si son strings
                                try:
                                    if isinstance(first_reading, str):
                                        first_reading = float(first_reading)
                                    if isinstance(last_reading, str):
                                        last_reading = float(last_reading)
                                    
                                    real_consumption = last_reading - first_reading
                                    
                                    # Actualizar si es el mínimo
                                    if min_consumption is None or real_consumption < min_consumption:
                                        min_consumption = real_consumption
                                        min_asset = asset_id
                                except (ValueError, TypeError) as e:
                                    print(f"Error al convertir lecturas a números para el activo {asset_id}: {str(e)}")
                    except Exception as e:
                        print(f"Error al calcular activo con consumo mínimo: {str(e)}")
                    
                formula = "MIN(última_lectura_mes - primera_lectura_mes) entre todos los activos"
                description = "Consumo real mínimo (diferencia entre lecturas) registrado entre todos los activos en el mes"
                unit = get_consumption_unit(df)
                
                metadata[column][str(idx)] = {
                    **common_metadata,
                    'formula': formula,
                    'description': description,
                    'unit': unit,
                    'min_asset': min_asset
                }
                
            elif column == 'max_consumption':
                # Encontrar el activo con consumo máximo
                # Ahora necesitamos calcular el consumo real para cada activo
                max_asset = 'No disponible'
                max_consumption = None
                
                if not month_data.empty and 'asset_id' in month_data.columns:
                    try:
                        # Calcular consumo real para cada activo
                        consumption_column = 'consumption'
                        if consumption_column not in month_data.columns and 'value' in month_data.columns:
                            consumption_column = 'value'
                        
                        for asset_id, asset_group in month_data.groupby('asset_id'):
                            # Ordenar por fecha
                            asset_group = asset_group.sort_values('date')
                            
                            # Calcular consumo real
                            if len(asset_group) >= 2:
                                first_reading = asset_group[consumption_column].iloc[0]
                                last_reading = asset_group[consumption_column].iloc[-1]
                                
                                # Convertir a números si son strings
                                try:
                                    if isinstance(first_reading, str):
                                        first_reading = float(first_reading)
                                    if isinstance(last_reading, str):
                                        last_reading = float(last_reading)
                                    
                                    real_consumption = last_reading - first_reading
                                    
                                    # Actualizar si es el máximo
                                    if max_consumption is None or real_consumption > max_consumption:
                                        max_consumption = real_consumption
                                        max_asset = asset_id
                                except (ValueError, TypeError) as e:
                                    print(f"Error al convertir lecturas a números para el activo {asset_id}: {str(e)}")
                    except Exception as e:
                        print(f"Error al calcular activo con consumo máximo: {str(e)}")
                    
                formula = "MAX(última_lectura_mes - primera_lectura_mes) entre todos los activos"
                description = "Consumo real máximo (diferencia entre lecturas) registrado entre todos los activos en el mes"
                unit = get_consumption_unit(df)
                
                metadata[column][str(idx)] = {
                    **common_metadata,
                    'formula': formula,
                    'description': description,
                    'unit': unit,
                    'max_asset': max_asset
                }
                
            elif column == 'asset_count':
                formula = "COUNT(DISTINCT asset_id)"
                description = "Número de activos con lecturas en el mes"
                
                metadata[column][str(idx)] = {
                    **common_metadata,
                    'formula': formula,
                    'description': description
                }
    
    return metadata

def get_consumption_unit(df):
    """
    Determina la unidad de consumo basada en los datos.
    
    Args:
        df (pd.DataFrame): DataFrame con datos de consumo
        
    Returns:
        str: Unidad de consumo
    """
    # Intentar determinar la unidad basada en las etiquetas de consumo
    if 'tag' in df.columns:
        tags = df['tag'].unique()
        
        # Mapeo de tipos de consumo a unidades
        unit_mapping = {
            'Agua': 'm³',
            'Electricidad': 'kWh',
            'Gas': 'm³',
            'Calefacción': 'kWh'
        }
        
        # Buscar coincidencias en las etiquetas
        for tag in tags:
            for consumption_type, unit in unit_mapping.items():
                if consumption_type.lower() in str(tag).lower():
                    return unit
    
    # Si no se puede determinar, devolver un valor por defecto
    return "Unidades"

def generate_monthly_readings_table(df, start_date=None, end_date=None):
    """
    Genera una tabla de lecturas mensuales por activo.
    
    Args:
        df: DataFrame con los datos
        start_date: Fecha de inicio (opcional)
        end_date: Fecha de fin (opcional)
        
    Returns:
        DataFrame con la tabla de lecturas mensuales
    """
    if df.empty:
        print("No data available to generate monthly readings table")
        return pd.DataFrame()
    
    # Print information about the dataframe for debugging
    print(f"[DEBUG TABLA MENSUAL] Columnas en DataFrame: {df.columns.tolist()}")
    print(f"[DEBUG TABLA MENSUAL] Tipos de consumo únicos: {df['consumption_type'].unique() if 'consumption_type' in df.columns else 'No hay columna consumption_type'}")
    if 'tag' in df.columns:
        print(f"[DEBUG TABLA MENSUAL] Tags únicos: {df['tag'].unique()}")
    
    try:
        # Filter by date range if provided
        if start_date:
            start_date = pd.to_datetime(start_date)
            df = df[df['date'] >= start_date]
        
        if end_date:
            end_date = pd.to_datetime(end_date)
            df = df[df['date'] <= end_date]
        
        # Process each asset
        asset_readings = {}
        for asset_id, asset_group in df.groupby('asset_id'):
            print(f"[DEBUG TABLA MENSUAL] Procesando asset {asset_id}")
            
            # Get consumption type for this asset
            if 'consumption_type' in asset_group.columns:
                consumption_type = asset_group['consumption_type'].mode().iloc[0] if not asset_group['consumption_type'].empty else "Desconocido"
                print(f"[DEBUG TABLA MENSUAL] Asset {asset_id}: consumption_type = {consumption_type}")
                unique_types = asset_group['consumption_type'].unique()
                print(f"[DEBUG TABLA MENSUAL] Asset {asset_id}: consumptions_types únicos = {unique_types}")
            else:
                print(f"[DEBUG TABLA MENSUAL] Asset {asset_id}: No hay columna consumption_type")
                consumption_type = "Desconocido"

            # Process each month
            monthly_readings = {}
            for month, month_group in asset_group.groupby('month'):
                try:
                    # Sort by date
                    month_group = month_group.sort_values('date')
                    
                    # Get first and last readings
                    first_reading = month_group['consumption'].iloc[0]
                    last_reading = month_group['consumption'].iloc[-1]
                    
                    # Calculate monthly consumption
                    monthly_consumption = last_reading - first_reading
                    
                    # Store in dict
                    month_name = pd.to_datetime(str(month)).strftime('%B %Y')
                    monthly_readings[month_name] = {
                        'first_reading': first_reading,
                        'last_reading': last_reading,
                        'consumption': monthly_consumption
                    }
                except Exception as e:
                    print(f"Error processing month {month} for asset {asset_id}: {str(e)}")
            
            # Store asset data
            asset_readings[asset_id] = {
                'consumption_type': consumption_type,
                'monthly_readings': monthly_readings
            }
        
        # Create pivot table
        rows = []
        for asset_id, asset_data in asset_readings.items():
            consumption_type = asset_data['consumption_type']
            row = {'Asset': asset_id, 'consumption_type': consumption_type}
            
            # Add monthly readings
            for month, readings in asset_data['monthly_readings'].items():
                row[month] = readings['consumption']
            
            rows.append(row)
        
        # If no rows, return empty DataFrame
        if not rows:
            print("No rows generated for monthly readings table")
            return pd.DataFrame()
        
        # Create DataFrame
        pivot = pd.DataFrame(rows)
        
        # Print the DataFrame for debugging
        print(f"[DEBUG TABLA MENSUAL] DataFrame final generado: {pivot.shape}")
        print(f"[DEBUG TABLA MENSUAL] Columnas en DataFrame final: {pivot.columns.tolist()}")
        print(f"[DEBUG TABLA MENSUAL] Valores únicos de consumption_type en DataFrame final: {pivot['consumption_type'].unique() if 'consumption_type' in pivot.columns else 'No hay columna consumption_type'}")
        
        return pivot
    except Exception as e:
        print(f"Error generating monthly readings table: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return pd.DataFrame()
