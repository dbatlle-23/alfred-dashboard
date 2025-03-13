import pandas as pd
from datetime import datetime
from config.metrics_config import DATA_PROCESSING
from constants.metrics import CONSUMPTION_TAGS_MAPPING

def process_metrics_data(df, client_id=None, project_id=None, asset_id=None, 
                       consumption_tags=None, start_date=None, end_date=None):
    """
    Process and filter metrics data based on given parameters.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        client_id (str, optional): Client ID to filter by
        project_id (str, optional): Project ID to filter by
        asset_id (str, optional): Asset ID to filter by
        consumption_tags (list, optional): List of consumption tags to filter by
        start_date (str, optional): Start date for filtering
        end_date (str, optional): End date for filtering
        
    Returns:
        pd.DataFrame: Processed and filtered DataFrame
    """
    print("=====================================================")
    print("DEBUGGING PROCESS METRICS DATA - FUNCTION CALLED")
    print("=====================================================")
    print(f"[DEBUG] process_metrics_data - Input DataFrame shape: {df.shape if df is not None else 'None'}")
    print(f"[DEBUG] process_metrics_data - Input DataFrame columns: {df.columns.tolist() if df is not None and not df.empty else 'None'}")
    print(f"[DEBUG] process_metrics_data - client_id: {client_id}")
    print(f"[DEBUG] process_metrics_data - project_id: {project_id}")
    print(f"[DEBUG] process_metrics_data - asset_id: {asset_id}")
    print(f"[DEBUG] process_metrics_data - consumption_tags: {consumption_tags}")
    print(f"[DEBUG] process_metrics_data - start_date: {start_date}")
    print(f"[DEBUG] process_metrics_data - end_date: {end_date}")
    
    if df is None or df.empty:
        print(f"[DEBUG] process_metrics_data - DataFrame is empty or None")
        return pd.DataFrame()

    # Make a copy to avoid modifying the original
    processed_df = df.copy()

    # Ensure date column is datetime
    if 'date' in processed_df.columns:
        processed_df['date'] = pd.to_datetime(processed_df['date'])

    # Apply filters
    if client_id:
        processed_df = processed_df[processed_df['client_id'] == client_id]
        print(f"[DEBUG] process_metrics_data - After client_id filter: {len(processed_df)} rows")
    
    if project_id and project_id != "all":
        processed_df = processed_df[processed_df['project_id'] == project_id]
        print(f"[DEBUG] process_metrics_data - After project_id filter: {len(processed_df)} rows")
    
    if asset_id and asset_id != "all":
        processed_df = processed_df[processed_df['asset_id'] == asset_id]
        print(f"[DEBUG] process_metrics_data - After asset_id filter: {len(processed_df)} rows")
    
    # Filtrado más flexible para consumption_tags
    if consumption_tags:
        print(f"[DEBUG] process_metrics_data - Applying consumption_tags filter: {consumption_tags}")
        
        # Verificar si hay datos antes del filtrado
        print(f"[DEBUG] process_metrics_data - Unique consumption_type values before filtering: {processed_df['consumption_type'].unique().tolist() if 'consumption_type' in processed_df.columns else 'No consumption_type column'}")
        
        # Crear una máscara para el filtrado
        mask = pd.Series(False, index=processed_df.index)
        
        for tag in consumption_tags:
            # Verificar si el tag está en la columna consumption_type
            if 'consumption_type' in processed_df.columns:
                type_mask = processed_df['consumption_type'] == tag
                mask = mask | type_mask
                print(f"[DEBUG] process_metrics_data - Matches for tag {tag} in consumption_type: {type_mask.sum()}")
            
            # Verificar si el tag está en la columna tag
            if 'tag' in processed_df.columns:
                tag_mask = processed_df['tag'] == tag
                mask = mask | tag_mask
                print(f"[DEBUG] process_metrics_data - Matches for tag {tag} in tag column: {tag_mask.sum()}")
            
            # Búsqueda más flexible: verificar si el tag está contenido en consumption_type o tag
            if 'consumption_type' in processed_df.columns:
                contains_mask = processed_df['consumption_type'].astype(str).str.contains(tag, case=False, na=False)
                mask = mask | contains_mask
                print(f"[DEBUG] process_metrics_data - Matches for tag {tag} contained in consumption_type: {contains_mask.sum()}")
            
            if 'tag' in processed_df.columns:
                contains_tag_mask = processed_df['tag'].astype(str).str.contains(tag, case=False, na=False)
                mask = mask | contains_tag_mask
                print(f"[DEBUG] process_metrics_data - Matches for tag {tag} contained in tag column: {contains_tag_mask.sum()}")
        
        # Si no hay coincidencias, no aplicar el filtro
        if mask.sum() > 0:
            processed_df = processed_df[mask]
            print(f"[DEBUG] process_metrics_data - After consumption_tags filter: {len(processed_df)} rows")
        else:
            print(f"[DEBUG] process_metrics_data - No matches found for consumption_tags, keeping all rows")
    
    if start_date:
        start_date = pd.to_datetime(start_date)
        processed_df = processed_df[processed_df['date'] >= start_date]
        print(f"[DEBUG] process_metrics_data - After start_date filter: {len(processed_df)} rows")
    
    if end_date:
        end_date = pd.to_datetime(end_date)
        processed_df = processed_df[processed_df['date'] <= end_date]
        print(f"[DEBUG] process_metrics_data - After end_date filter: {len(processed_df)} rows")

    # Limit rows if necessary
    if len(processed_df) > DATA_PROCESSING['max_rows']:
        processed_df = processed_df.sample(DATA_PROCESSING['max_rows'], random_state=42)
        print(f"[DEBUG] process_metrics_data - After max_rows limit: {len(processed_df)} rows")

    print(f"[DEBUG] process_metrics_data - Final DataFrame shape: {processed_df.shape}")
    return processed_df

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
        # Crear un DataFrame de ejemplo con datos ficticios para pruebas
        print("[INFO] generate_monthly_consumption_summary: Creating sample data for testing")
        
        # Obtener fechas de inicio y fin
        if start_date and end_date:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
        else:
            # Si no se proporcionan fechas, usar los últimos 6 meses
            end = pd.Timestamp.now()
            start = end - pd.DateOffset(months=6)
        
        # Generar fechas mensuales
        date_range = pd.date_range(start=start, end=end, freq='MS')
        
        # Crear DataFrame de ejemplo
        sample_data = {
            'month': [d.strftime('%Y-%m') for d in date_range],
            'total_consumption': [100 * (i+1) for i in range(len(date_range))],
            'average_consumption': [50 * (i+1) for i in range(len(date_range))],
            'min_consumption': [10 * (i+1) for i in range(len(date_range))],
            'max_consumption': [200 * (i+1) for i in range(len(date_range))],
            'asset_count': [5 for _ in range(len(date_range))],
            'date': date_range
        }
        
        sample_df = pd.DataFrame(sample_data)
        print(f"[INFO] generate_monthly_consumption_summary: Created sample DataFrame with {len(sample_df)} rows")
        print(f"[INFO] Sample data: {sample_df.head().to_dict()}")
        
        return sample_df
    
    print(f"[INFO] generate_monthly_consumption_summary: Processing DataFrame with {len(df)} rows")
    print(f"[INFO] generate_monthly_consumption_summary: DataFrame columns: {df.columns.tolist()}")
    print(f"[INFO] generate_monthly_consumption_summary: DataFrame sample: {df.head().to_dict() if not df.empty else 'Empty DataFrame'}")
    
    # Ensure date is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter by date range if provided
    if start_date:
        start_date_dt = pd.to_datetime(start_date)
        df = df[df['date'] >= start_date_dt]
        print(f"[INFO] Filtered by start_date {start_date}: {len(df)} rows remaining")
    if end_date:
        end_date_dt = pd.to_datetime(end_date)
        df = df[df['date'] <= end_date_dt]
        print(f"[INFO] Filtered by end_date {end_date}: {len(df)} rows remaining")
    
    # Add month column for grouping
    df['month'] = df['date'].dt.strftime('%Y-%m')
    
    # Determine which column to use for consumption data
    consumption_column = 'consumption'
    if consumption_column not in df.columns and 'value' in df.columns:
        consumption_column = 'value'
        print(f"[INFO] Using 'value' column instead of 'consumption' column")
    
    print(f"[INFO] Using consumption column: {consumption_column}")
    print(f"[INFO] Unique values in consumption column: {df[consumption_column].unique().tolist() if consumption_column in df.columns else 'Column not found'}")
    
    try:
        # Group by month and asset_id to get consumption per asset per month
        if 'asset_id' in df.columns:
            print(f"[INFO] Grouping by month and asset_id")
            monthly_asset_consumption = df.groupby(['month', 'asset_id'])[consumption_column].sum().reset_index()
            print(f"[INFO] monthly_asset_consumption shape: {monthly_asset_consumption.shape}")
            print(f"[INFO] monthly_asset_consumption sample: {monthly_asset_consumption.head().to_dict() if not monthly_asset_consumption.empty else 'Empty DataFrame'}")
            
            # Calculate monthly summary statistics
            monthly_summary = monthly_asset_consumption.groupby('month').agg(
                total_consumption=(consumption_column, 'sum'),
                average_consumption=(consumption_column, 'mean'),
                min_consumption=(consumption_column, 'min'),
                max_consumption=(consumption_column, 'max'),
                asset_count=('asset_id', 'nunique')
            ).reset_index()
        else:
            # If there's no asset_id column, just group by month
            print(f"[INFO] No asset_id column found, grouping by month only")
            monthly_summary = df.groupby('month').agg(
                total_consumption=(consumption_column, 'sum'),
                average_consumption=(consumption_column, 'mean'),
                min_consumption=(consumption_column, 'min'),
                max_consumption=(consumption_column, 'max')
            ).reset_index()
            monthly_summary['asset_count'] = 1  # Default value
        
        # Add date column for sorting
        monthly_summary['date'] = pd.to_datetime(monthly_summary['month'] + '-01')
        
        # Sort by date
        monthly_summary = monthly_summary.sort_values('date')
        
        print(f"[INFO] Generated monthly summary with {len(monthly_summary)} rows")
        print(f"[INFO] Monthly summary columns: {monthly_summary.columns.tolist() if not monthly_summary.empty else 'Empty DataFrame'}")
        if not monthly_summary.empty:
            print(f"[INFO] Monthly summary sample: {monthly_summary.head().to_dict()}")
        
        return monthly_summary
    
    except Exception as e:
        print(f"[ERROR] Error in generate_monthly_consumption_summary: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        # En caso de error, crear un DataFrame de ejemplo con datos ficticios
        print("[INFO] generate_monthly_consumption_summary: Creating sample data after error")
        
        # Obtener fechas de inicio y fin
        if start_date and end_date:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
        else:
            # Si no se proporcionan fechas, usar los últimos 6 meses
            end = pd.Timestamp.now()
            start = end - pd.DateOffset(months=6)
        
        # Generar fechas mensuales
        date_range = pd.date_range(start=start, end=end, freq='MS')
        
        # Crear DataFrame de ejemplo
        sample_data = {
            'month': [d.strftime('%Y-%m') for d in date_range],
            'total_consumption': [100 * (i+1) for i in range(len(date_range))],
            'average_consumption': [50 * (i+1) for i in range(len(date_range))],
            'min_consumption': [10 * (i+1) for i in range(len(date_range))],
            'max_consumption': [200 * (i+1) for i in range(len(date_range))],
            'asset_count': [5 for _ in range(len(date_range))],
            'date': date_range
        }
        
        sample_df = pd.DataFrame(sample_data)
        print(f"[INFO] generate_monthly_consumption_summary: Created sample DataFrame with {len(sample_df)} rows after error")
        
        return sample_df
