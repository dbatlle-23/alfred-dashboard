import dash
from dash import Output, Input, State, callback_context
import json
import pandas as pd
import dash_bootstrap_components as dbc
import numpy as np
from datetime import datetime
import io

from utils.metrics.data_processing import generate_monthly_readings_by_consumption_type, generate_monthly_consumption_summary, process_metrics_data
from components.metrics.tables import create_monthly_readings_by_consumption_type, create_monthly_readings_table, create_monthly_summary_table

def register_table_callbacks(app):
    """Register callbacks for tables."""
    
    @app.callback(
        Output("metrics-monthly-readings-by-consumption-type", "children"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_monthly_readings_by_consumption_type(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        """Update monthly readings table by consumption type."""
        if not json_data or not consumption_tags:
            return create_monthly_readings_by_consumption_type({})
        
        try:
            # Parse JSON data
            data = json.loads(json_data)
            df = pd.DataFrame(data)
            
            print(f"update_monthly_readings_by_consumption_type: Loaded DataFrame with {len(df)} rows")
            
            # Print unique consumption_type values for debugging
            if 'consumption_type' in df.columns:
                unique_types = df['consumption_type'].unique()
                print(f"Unique consumption_type values: {unique_types}")
                
                # Print tag values for debugging
                if 'tag' in df.columns:
                    unique_tags = df['tag'].unique()
                    print(f"Unique tag values: {unique_tags}")
            
            # Filter data
            if asset_id and asset_id != "all":
                df = df[df['asset_id'] == asset_id]
                print(f"Filtered by asset_id {asset_id}: {len(df)} rows remaining")
            
            # Generate tables by consumption type using the original function
            # The function generate_monthly_readings_by_consumption_type will handle the filtering
            tables = generate_monthly_readings_by_consumption_type(df, consumption_tags, start_date, end_date)
            
            # Create tables component
            return create_monthly_readings_by_consumption_type(tables)
            
        except Exception as e:
            print(f"Error updating monthly readings table: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return create_monthly_readings_by_consumption_type({})
    
    @app.callback(
        [Output("metrics-monthly-readings-table", "children"),
         Output("monthly-readings-complete-data", "data")],
        [
            Input("metrics-data-store", "data"),
            Input("metrics-client-filter", "value"),
            Input("metrics-project-filter", "value"),
            Input("metrics-asset-filter", "value"),
            Input("metrics-consumption-tags-filter", "value"),
            Input("metrics-date-range", "start_date"),
            Input("metrics-date-range", "end_date"),
            Input("jwt-token-store", "data")
        ]
    )
    def update_monthly_readings_table(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date, token_data):
        """Update monthly readings table."""
        if not json_data:
            print("No JSON data available")
            return "", None
        
        try:
            # Parse JSON data
            data = json.loads(json_data)
            df = pd.DataFrame(data)
            
            # Verificar si el DataFrame está vacío o no tiene datos
            if df.empty:
                print("El DataFrame está vacío, no hay datos para mostrar")
                return html.Div("No hay datos disponibles para mostrar.", className="alert alert-warning"), None
            
            # Verificar si la columna 'date' existe
            if 'date' not in df.columns:
                print(f"[ERROR] La columna 'date' no existe en el DataFrame. Columnas disponibles: {df.columns.tolist()}")
                return html.Div([
                    html.H5("Error al procesar datos"),
                    html.P("La columna 'date' no existe en los datos. Verifique los archivos CSV de origen."),
                    html.P(f"Columnas disponibles: {', '.join(df.columns.tolist())}")
                ], className="alert alert-danger"), None
            
            # Filter data
            df = process_metrics_data(
                df, 
                client_id=client_id, 
                project_id=project_id,
                asset_id=asset_id,
                consumption_tags=consumption_tags, 
                start_date=start_date, 
                end_date=end_date
            )
            
            # Get JWT token
            token = token_data.get('token') if token_data else None
            
            # Get all assets for the project
            all_project_assets = []
            assets_metadata = {}
            asset_consumption_types = {}
            
            try:
                # Get assets metadata from API
                from utils.api import get_project_assets, get_assets
                
                if project_id and project_id != "all":
                    all_project_assets = get_project_assets(project_id, jwt_token=token)
                else:
                    all_project_assets = get_assets(client_id=client_id, jwt_token=token)
                
                # Create a dictionary with asset_id as key for quick lookup
                for asset in all_project_assets:
                    if isinstance(asset, dict) and "id" in asset:
                        assets_metadata[asset["id"]] = {
                            "block_number": asset.get("block_number", ""),
                            "staircase": asset.get("staircase", ""),
                            "apartment": asset.get("apartment", "")
                        }
                
                print(f"Retrieved metadata for {len(assets_metadata)} assets")
            except Exception as e:
                print(f"Error retrieving asset metadata: {str(e)}")
                import traceback
                print(traceback.format_exc())
            
            # Import consumption tags mapping
            from constants.metrics import CONSUMPTION_TAGS_MAPPING
            
            # Ensure date is datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            
            # Add year_month column
            df['year_month'] = df['date'].dt.strftime('%Y-%m')
            
            # Dictionary to store monthly data by asset
            monthly_data = {}
            
            # Process each asset
            for asset_id, asset_group in df.groupby('asset_id'):
                print(f"Processing asset_id: {asset_id}, group size: {len(asset_group)}")
                
                # Initialize a dictionary to store monthly readings
                asset_monthly_readings = {}
                
                # Get consumption type for this asset
                if 'consumption_type' in asset_group.columns:
                    # Use the most common consumption type for this asset
                    consumption_type = asset_group['consumption_type'].mode().iloc[0] if not asset_group['consumption_type'].empty else ""
                    # Get readable name from mapping
                    readable_consumption_type = CONSUMPTION_TAGS_MAPPING.get(consumption_type, consumption_type)
                    asset_consumption_types[asset_id] = readable_consumption_type
                elif 'tag' in asset_group.columns:
                    # Use the most common tag for this asset
                    tag = asset_group['tag'].mode().iloc[0] if not asset_group['tag'].empty else ""
                    # Get readable name from mapping
                    readable_tag = CONSUMPTION_TAGS_MAPPING.get(tag, tag)
                    asset_consumption_types[asset_id] = readable_tag
                else:
                    asset_consumption_types[asset_id] = ""
                
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
            
            # Get all unique months from the data
            all_months = set()
            for asset_data in monthly_data.values():
                all_months.update(asset_data.index)
            sorted_months = sorted(all_months)
            
            # Create a new DataFrame from the monthly data
            if monthly_data:
                print(f"Creating pivot table from {len(monthly_data)} assets")
                # Convert the dictionary to a DataFrame
                pivot = pd.DataFrame(monthly_data).T
                
                # Sort columns chronologically
                sorted_columns = sorted(pivot.columns)
                pivot = pivot[sorted_columns]
                
                # Reset index and rename
                pivot = pivot.reset_index()
                pivot = pivot.rename(columns={'index': 'Asset'})
                
                # Add asset metadata columns
                pivot['block_number'] = pivot['Asset'].map(lambda x: assets_metadata.get(x, {}).get('block_number', ''))
                pivot['staircase'] = pivot['Asset'].map(lambda x: assets_metadata.get(x, {}).get('staircase', ''))
                pivot['apartment'] = pivot['Asset'].map(lambda x: assets_metadata.get(x, {}).get('apartment', ''))
                
                # Add consumption type column
                pivot['consumption_type'] = pivot['Asset'].map(lambda x: asset_consumption_types.get(x, ''))
                
                # Get list of assets that have data
                assets_with_data = pivot['Asset'].tolist()
                
                # Add assets without data
                missing_assets = []
                for asset in all_project_assets:
                    if isinstance(asset, dict) and "id" in asset:
                        asset_id = asset["id"]
                        if asset_id not in assets_with_data:
                            # Create a row for this asset with "Sin Datos" for all months
                            row = {
                                'Asset': asset_id,
                                'block_number': assets_metadata.get(asset_id, {}).get('block_number', ''),
                                'staircase': assets_metadata.get(asset_id, {}).get('staircase', ''),
                                'apartment': assets_metadata.get(asset_id, {}).get('apartment', ''),
                                'consumption_type': ''  # No consumption type for assets without data
                            }
                            
                            # Add "Sin Datos" for each month column
                            for month in sorted_columns:
                                row[month] = "Sin Datos"
                            
                            missing_assets.append(row)
                
                # Add missing assets to the pivot table
                if missing_assets:
                    missing_df = pd.DataFrame(missing_assets)
                    pivot = pd.concat([pivot, missing_df], ignore_index=True)
                    print(f"Added {len(missing_assets)} assets without data to the table")
                
                # Reorder columns to put metadata after Asset column
                cols = ['Asset', 'consumption_type', 'block_number', 'staircase', 'apartment'] + sorted_columns
                pivot = pivot[cols]
                
                print(f"Final pivot table shape: {pivot.shape}")
                
                # Create table component
                return create_monthly_readings_table(pivot, "Lecturas Mensuales"), pivot.to_dict()
            else:
                # If no assets have data, create a table with all assets but no data
                print("No monthly data found. Creating table with all assets but no data.")
                
                # Create rows for all assets
                rows = []
                for asset in all_project_assets:
                    if isinstance(asset, dict) and "id" in asset:
                        asset_id = asset["id"]
                        row = {
                            'Asset': asset_id,
                            'block_number': assets_metadata.get(asset_id, {}).get('block_number', ''),
                            'staircase': assets_metadata.get(asset_id, {}).get('staircase', ''),
                            'apartment': assets_metadata.get(asset_id, {}).get('apartment', ''),
                            'consumption_type': ''  # No consumption type for assets without data
                        }
                        
                        # If we have date range information, create month columns
                        if start_date and end_date:
                            start = pd.to_datetime(start_date)
                            end = pd.to_datetime(end_date)
                            current = start.replace(day=1)
                            
                            while current <= end:
                                month = current.strftime('%Y-%m')
                                row[month] = "Sin Datos"
                                current = (current + pd.DateOffset(months=1))
                        
                        rows.append(row)
                
                if rows:
                    empty_pivot = pd.DataFrame(rows)
                    
                    # Get all columns except Asset and metadata
                    data_columns = [col for col in empty_pivot.columns if col not in ['Asset', 'consumption_type', 'block_number', 'staircase', 'apartment']]
                    
                    # Reorder columns
                    cols = ['Asset', 'consumption_type', 'block_number', 'staircase', 'apartment'] + sorted(data_columns)
                    empty_pivot = empty_pivot[cols]
                    
                    print(f"Created table with {len(rows)} assets without data")
                    return create_monthly_readings_table(empty_pivot, "Lecturas Mensuales"), None
                else:
                    print("No assets found for the project")
                    return "", None
            
        except Exception as e:
            print(f"Error updating monthly readings table: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return "", None

    @app.callback(
        Output("metrics-monthly-summary-table", "children"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_monthly_summary_table(json_data, client_id, project_id, consumption_tags, start_date, end_date):
        """Update the monthly summary table."""
        print("=====================================================")
        print("DEBUGGING MONTHLY SUMMARY TABLE CALLBACK - FUNCTION CALLED")
        print("=====================================================")
        print(f"[INFO METRICS] update_monthly_summary_table - Starting")
        print(f"[INFO METRICS] update_monthly_summary_table - client_id: {client_id}")
        print(f"[INFO METRICS] update_monthly_summary_table - project_id: {project_id}")
        print(f"[INFO METRICS] update_monthly_summary_table - consumption_tags: {consumption_tags}")
        print(f"[INFO METRICS] update_monthly_summary_table - start_date: {start_date}")
        print(f"[INFO METRICS] update_monthly_summary_table - end_date: {end_date}")
        print(f"[INFO METRICS] update_monthly_summary_table - json_data length: {len(json_data) if json_data else 0}")
        print(f"[INFO METRICS] update_monthly_summary_table - json_data empty?: {json_data == '[]' if json_data else True}")
        
        try:
            # Si no hay datos, mostrar mensaje en lugar de crear datos de ejemplo
            if not json_data or json_data == "[]":
                print(f"[INFO METRICS] update_monthly_summary_table - No data available")
                from components.metrics.tables import create_monthly_summary_table
                return create_monthly_summary_table(None, "No hay datos disponibles")
            
            # Convert JSON to DataFrame
            df = pd.DataFrame(json.loads(json_data))
            print(f"[INFO METRICS] update_monthly_summary_table - Loaded DataFrame with {len(df)} rows")
            print(f"[INFO METRICS] update_monthly_summary_table - DataFrame columns: {df.columns.tolist()}")
            print(f"[INFO METRICS] update_monthly_summary_table - DataFrame sample: {df.head().to_dict() if not df.empty else 'Empty DataFrame'}")
            
            # Verificar si el DataFrame está vacío
            if df.empty:
                print(f"[INFO METRICS] update_monthly_summary_table - DataFrame is empty")
                from components.metrics.tables import create_monthly_summary_table
                return create_monthly_summary_table(None, "No hay datos disponibles")
            
            # Procesar datos según filtros
            try:
                from utils.metrics.data_processing import process_metrics_data
                
                # Convertir fechas a datetime si son strings
                if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                
                # Filtrar datos
                filtered_df = process_metrics_data(
                    df, 
                    client_id=client_id, 
                    project_id=project_id, 
                    consumption_tags=consumption_tags, 
                    start_date=start_date, 
                    end_date=end_date
                )
                
                print(f"[INFO METRICS] update_monthly_summary_table - Filtered DataFrame has {len(filtered_df)} rows")
                print(f"[INFO METRICS] update_monthly_summary_table - Filtered DataFrame columns: {filtered_df.columns.tolist() if not filtered_df.empty else 'Empty DataFrame'}")
                
                # Verificar si el DataFrame filtrado está vacío
                if filtered_df.empty:
                    print(f"[INFO METRICS] update_monthly_summary_table - Filtered DataFrame is empty")
                    from components.metrics.tables import create_monthly_summary_table
                    return create_monthly_summary_table(None, "No hay datos disponibles para los filtros seleccionados")
                
                # Utilizar la función generate_monthly_consumption_summary para calcular el resumen mensual
                try:
                    from utils.metrics.data_processing import generate_monthly_consumption_summary
                    
                    # Generar el resumen mensual utilizando la función mejorada
                    monthly_summary = generate_monthly_consumption_summary(filtered_df, start_date, end_date)
                    
                    print(f"[INFO METRICS] update_monthly_summary_table - Generated monthly summary with {len(monthly_summary)} rows")
                    print(f"[INFO METRICS] update_monthly_summary_table - Monthly summary columns: {monthly_summary.columns.tolist() if not monthly_summary.empty else 'Empty DataFrame'}")
                    print(f"[INFO METRICS] update_monthly_summary_table - Monthly summary sample: {monthly_summary.head().to_dict() if not monthly_summary.empty else 'Empty DataFrame'}")
                    
                    # Verificar si el resumen mensual está vacío
                    if monthly_summary.empty:
                        print(f"[INFO METRICS] update_monthly_summary_table - Monthly summary is empty")
                        from components.metrics.tables import create_monthly_summary_table
                        return create_monthly_summary_table(None, "No se pudo generar el resumen mensual")
                    
                    # Create table
                    from components.metrics.tables import create_monthly_summary_table
                    return create_monthly_summary_table(monthly_summary)
                    
                except Exception as e:
                    print(f"[ERROR METRICS] update_monthly_summary_table - Error generating monthly summary: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    
                    # En caso de error, mostrar mensaje
                    from components.metrics.tables import create_monthly_summary_table
                    return create_monthly_summary_table(None, f"Error al generar el resumen mensual: {str(e)}")
                
            except Exception as e:
                print(f"[ERROR METRICS] update_monthly_summary_table - Error processing data: {str(e)}")
                import traceback
                print(traceback.format_exc())
                
                # En caso de error, mostrar mensaje
                from components.metrics.tables import create_monthly_summary_table
                return create_monthly_summary_table(None, f"Error al procesar los datos: {str(e)}")
            
        except Exception as e:
            print(f"[ERROR METRICS] update_monthly_summary_table: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # En caso de error, mostrar mensaje
            from components.metrics.tables import create_monthly_summary_table
            return create_monthly_summary_table(None, f"Error: {str(e)}")

    # Importaciones necesarias para los callbacks de exportación
    from dash import dcc, html
    
    # Callback para exportar datos de lecturas mensuales
    @app.callback(
        [Output("download-monthly-readings", "data"),
         Output("monthly-readings-error-container", "children"),
         Output("monthly-readings-error-container", "className")],
        [Input("export-monthly-readings-csv-btn", "n_clicks"),
         Input("export-monthly-readings-excel-btn", "n_clicks"),
         Input("export-monthly-readings-pdf-btn", "n_clicks")],
        [State("metrics-data-store", "data"),
         State("metrics-client-filter", "value"),
         State("metrics-project-filter", "value"),
         State("metrics-asset-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("metrics-date-range", "start_date"),
         State("metrics-date-range", "end_date"),
         State("monthly-readings-complete-data", "data"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def export_monthly_readings(csv_clicks, excel_clicks, pdf_clicks, 
                               json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date, complete_data, token_data):
        """Export monthly readings data in different formats."""
        # Determinar qué botón fue clickeado
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
            
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Verificar que realmente se hizo clic en un botón
        if (button_id == "export-monthly-readings-csv-btn" and not csv_clicks) or \
           (button_id == "export-monthly-readings-excel-btn" and not excel_clicks) or \
           (button_id == "export-monthly-readings-pdf-btn" and not pdf_clicks):
            return dash.no_update, dash.no_update, dash.no_update
        
        try:
            # Convertir JSON a DataFrame
            if not json_data or json_data == "[]":
                # Si no hay datos, mostrar un mensaje de error
                error_msg = html.Div([
                    html.I(className="fas fa-exclamation-circle me-2"),
                    "No hay datos disponibles para exportar. Por favor, asegúrese de que hay datos cargados."
                ], className="alert alert-warning")
                return dash.no_update, error_msg, "mb-3 show"
                
            df = pd.DataFrame(json.loads(json_data))
            
            # Procesar datos según filtros
            filtered_df = process_metrics_data(
                df, 
                client_id=client_id, 
                project_id=project_id,
                asset_id=asset_id,
                consumption_tags=consumption_tags, 
                start_date=start_date, 
                end_date=end_date
            )
            
            # Verificar que el DataFrame no esté vacío
            if filtered_df.empty:
                error_msg = html.Div([
                    html.I(className="fas fa-exclamation-circle me-2"),
                    "No hay datos de lecturas para el período seleccionado. Por favor, seleccione otro período."
                ], className="alert alert-warning")
                return dash.no_update, error_msg, "mb-3 show"
            
            # Preparar los datos para exportación - crear una tabla pivotada por mes
            # Asegurarse de que la columna date es datetime
            if 'date' in filtered_df.columns:
                if not pd.api.types.is_datetime64_any_dtype(filtered_df['date']):
                    filtered_df['date'] = pd.to_datetime(filtered_df['date'], errors='coerce')
            
            # Crear una columna de mes
            filtered_df['month'] = filtered_df['date'].dt.strftime('%Y-%m')
            
            # Añadir metadatos de los assets
            try:
                print(f"[INFO METRICS] Iniciando proceso de obtención de metadatos para {len(filtered_df['asset_id'].unique())} assets únicos")
                
                # Inicializar diccionario de metadatos
                asset_metadata = {}
                
                # Imprimir información sobre la estructura de complete_data para depuración
                print(f"[DEBUG METRICS] complete_data type: {type(complete_data)}")
                if complete_data:
                    print(f"[DEBUG METRICS] complete_data keys: {list(complete_data.keys()) if isinstance(complete_data, dict) else 'No es un diccionario'}")
                    if isinstance(complete_data, dict) and 'Asset' in complete_data:
                        print(f"[DEBUG METRICS] complete_data['Asset'] type: {type(complete_data['Asset'])}")
                        print(f"[DEBUG METRICS] complete_data['Asset'] length: {len(complete_data['Asset']) if hasattr(complete_data['Asset'], '__len__') else 'No tiene longitud'}")
                
                # Intentar obtener metadatos desde complete_data si está disponible
                if complete_data and isinstance(complete_data, dict):
                    # Verificar que existe block_number, staircase, apartment en complete_data
                    metadata_keys = ['block_number', 'staircase', 'apartment']
                    if all(key in complete_data for key in metadata_keys):
                        # Crear un diccionario de asset_id -> {metadata} usando el diccionario anidado
                        for idx, asset_id in complete_data.get('Asset', {}).items():
                            if asset_id:  # Asegurarse de que asset_id no es None o vacío
                                asset_metadata[asset_id] = {
                                    'block_number': complete_data.get('block_number', {}).get(idx, 'N/A'),
                                    'staircase': complete_data.get('staircase', {}).get(idx, 'N/A'),
                                    'apartment': complete_data.get('apartment', {}).get(idx, 'N/A')
                                }
                        
                        print(f"[INFO METRICS] Añadiendo metadatos de {len(asset_metadata)} assets desde complete_data")
                        # Imprimir algunos ejemplos para depuración
                        asset_examples = list(asset_metadata.items())[:3]
                        print(f"[DEBUG METRICS] Ejemplos de metadatos: {asset_examples}")
                
                # Si no hay suficientes metadatos desde complete_data, intentar obtener más desde la API
                missing_assets = set(filtered_df['asset_id'].unique()) - set(asset_metadata.keys())
                if missing_assets and len(missing_assets) <= 50:
                    # Obtener el token JWT
                    jwt_token = token_data.get('token') if token_data else None
                    
                    if jwt_token:
                        try:
                            from utils.data_loader import get_asset_metadata
                            print(f"[INFO METRICS] Obteniendo metadatos para {len(missing_assets)} assets faltantes desde la API")
                            for asset_id_val in missing_assets:
                                metadata = get_asset_metadata(asset_id_val, project_id, jwt_token)
                                if metadata:
                                    asset_metadata[asset_id_val] = metadata
                        except Exception as e:
                            print(f"[ERROR METRICS] Error al obtener metadatos adicionales desde la API: {str(e)}")
                
                # Añadir columnas de metadatos al DataFrame
                filtered_df['block_number'] = filtered_df['asset_id'].apply(
                    lambda x: asset_metadata.get(x, {}).get('block_number', 'N/A')
                )
                filtered_df['staircase'] = filtered_df['asset_id'].apply(
                    lambda x: asset_metadata.get(x, {}).get('staircase', 'N/A')
                )
                filtered_df['apartment'] = filtered_df['asset_id'].apply(
                    lambda x: asset_metadata.get(x, {}).get('apartment', 'N/A')
                )
            except Exception as e:
                print(f"[ERROR METRICS] Error general al procesar metadatos: {str(e)}")
                import traceback
                print(traceback.format_exc())
                
                # En caso de error, asegurarse de que las columnas de metadatos existen
                filtered_df['block_number'] = 'N/A'
                filtered_df['staircase'] = 'N/A'
                filtered_df['apartment'] = 'N/A'
            
            # Pivotar la tabla para tener los meses como columnas, incluyendo metadatos en el índice
            index_columns = ['asset_id', 'block_number', 'staircase', 'apartment']
            
            # Verificar que todas las columnas del índice existen en el DataFrame
            for col in index_columns:
                if col not in filtered_df.columns:
                    print(f"[WARNING METRICS] Columna {col} no encontrada en el DataFrame, se añadirá con valores por defecto")
                    filtered_df[col] = 'N/A'
            
            # Crear la tabla pivotada
            pivot = filtered_df.pivot_table(
                index=index_columns,
                columns='month',
                values='consumption',
                aggfunc='sum'
            ).reset_index()
            
            # Información de depuración
            print(f"[INFO METRICS] Tabla pivotada creada con éxito. Dimensiones: {pivot.shape}, Columnas: {pivot.columns.tolist()}")
            # Imprimir un ejemplo de los primeros registros para depuración
            print(f"[DEBUG METRICS] Primeras filas de la tabla pivotada:")
            for i, row in pivot.head(3).iterrows():
                print(f"[DEBUG METRICS] Fila {i}: {dict(row)}")
            
            # Generar nombre de archivo con fecha actual
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lecturas_mensuales_{timestamp}"
            
            # Exportar según el formato seleccionado
            if button_id == "export-monthly-readings-csv-btn":
                try:
                    return dcc.send_data_frame(pivot.to_csv, f"{filename}.csv", index=False), None, "mb-3"
                except Exception as e:
                    print(f"[ERROR METRICS] Error al exportar a CSV: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    error_msg = html.Div([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        f"Error al exportar a CSV: {str(e)}"
                    ], className="alert alert-danger")
                    return dash.no_update, error_msg, "mb-3 show"
            elif button_id == "export-monthly-readings-excel-btn":
                try:
                    # Verificar si openpyxl está instalado
                    try:
                        import openpyxl
                    except ImportError:
                        print("[ERROR METRICS] openpyxl no está instalado")
                        error_msg = html.Div([
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            "Error al exportar a Excel: El módulo openpyxl no está instalado. Por favor, contacte al administrador."
                        ], className="alert alert-danger")
                        return dash.no_update, error_msg, "mb-3 show"
                    
                    return dcc.send_data_frame(pivot.to_excel, f"{filename}.xlsx", index=False), None, "mb-3"
                except Exception as e:
                    print(f"[ERROR METRICS] Error al exportar a Excel: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    error_msg = html.Div([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        f"Error al exportar a Excel: {str(e)}"
                    ], className="alert alert-danger")
                    return dash.no_update, error_msg, "mb-3 show"
            elif button_id == "export-monthly-readings-pdf-btn":
                # Para PDF, necesitamos convertir a HTML primero y luego a PDF
                try:
                    # Verificar si ReportLab está instalado
                    try:
                        from reportlab.lib.pagesizes import letter, landscape
                        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                        from reportlab.lib import colors
                        from reportlab.lib.styles import getSampleStyleSheet
                    except ImportError as e:
                        print(f"[ERROR METRICS] ReportLab no está instalado o hay un problema con la importación: {str(e)}")
                        error_msg = html.Div([
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            "Error al generar PDF: ReportLab no está instalado correctamente. Por favor, contacte al administrador."
                        ], className="alert alert-danger")
                        return dash.no_update, error_msg, "mb-3 show"
                    
                    # Crear un buffer para el PDF
                    buffer = io.BytesIO()
                    
                    # Configurar el documento
                    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
                    elements = []
                    
                    # Añadir título
                    styles = getSampleStyleSheet()
                    elements.append(Paragraph(f"Lecturas Mensuales - {timestamp}", styles['Title']))
                    elements.append(Spacer(1, 12))
                    
                    # Convertir DataFrame a lista para la tabla
                    data = [pivot.columns.tolist()] + pivot.values.tolist()
                    
                    # Crear tabla
                    table = Table(data)
                    
                    # Estilo de la tabla
                    style = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ])
                    table.setStyle(style)
                    
                    # Añadir tabla al documento
                    elements.append(table)
                    
                    try:
                        # Construir PDF
                        doc.build(elements)
                        
                        # Obtener el contenido del buffer
                        buffer.seek(0)
                        
                        return dcc.send_bytes(buffer.getvalue(), f"{filename}.pdf"), None, "mb-3"
                    except Exception as e:
                        print(f"[ERROR METRICS] Error al construir el PDF: {str(e)}")
                        import traceback
                        print(traceback.format_exc())
                        error_msg = html.Div([
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            f"Error al generar PDF: {str(e)}"
                        ], className="alert alert-danger")
                        return dash.no_update, error_msg, "mb-3 show"
                except Exception as e:
                    print(f"[ERROR METRICS] Error general al generar PDF: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    error_msg = html.Div([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        f"Error al generar PDF: {str(e)}"
                    ], className="alert alert-danger")
                    return dash.no_update, error_msg, "mb-3 show"
            
            return dash.no_update, None, "mb-3"
            
        except Exception as e:
            import traceback
            print(f"[ERROR METRICS] export_monthly_readings: {str(e)}")
            print(traceback.format_exc())
            
            error_msg = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error al exportar datos: {str(e)}"
            ], className="alert alert-danger")
            
            return dash.no_update, error_msg, "mb-3 show"
    
    # Callback para mostrar notificaciones de exportación de lecturas mensuales
    @app.callback(
        [Output("monthly-readings-export-notification", "is_open"),
         Output("monthly-readings-export-notification", "children"),
         Output("monthly-readings-export-notification", "header"),
         Output("monthly-readings-export-error-notification", "is_open"),
         Output("monthly-readings-export-error-notification", "children"),
         Output("monthly-readings-export-error-notification", "header")],
        [Input("export-monthly-readings-csv-btn", "n_clicks"),
         Input("export-monthly-readings-excel-btn", "n_clicks"),
         Input("export-monthly-readings-pdf-btn", "n_clicks")],
        [State("metrics-data-store", "data")],
        prevent_initial_call=True
    )
    def show_monthly_readings_export_notification(csv_clicks, excel_clicks, pdf_clicks, json_data):
        """Mostrar notificación cuando se exportan datos de lecturas mensuales."""
        # Determinar qué botón fue clickeado
        ctx = callback_context
        if not ctx.triggered:
            return False, "", "", False, "", ""
            
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Verificar que realmente se hizo clic en un botón
        if (button_id == "export-monthly-readings-csv-btn" and not csv_clicks) or \
           (button_id == "export-monthly-readings-excel-btn" and not excel_clicks) or \
           (button_id == "export-monthly-readings-pdf-btn" and not pdf_clicks):
            return False, "", "", False, "", ""
        
        # Verificar si hay datos para exportar
        if not json_data or json_data == "[]":
            return False, "", "", True, "No hay datos disponibles para exportar. Por favor, asegúrese de que hay datos cargados.", "Error de Exportación"
        
        # Mostrar notificación según el formato seleccionado
        if button_id == "export-monthly-readings-csv-btn":
            return True, "Los datos de lecturas mensuales han sido exportados en formato CSV.", "Exportación CSV", False, "", ""
        elif button_id == "export-monthly-readings-excel-btn":
            return True, "Los datos de lecturas mensuales han sido exportados en formato Excel.", "Exportación Excel", False, "", ""
        elif button_id == "export-monthly-readings-pdf-btn":
            return True, "Los datos de lecturas mensuales han sido exportados en formato PDF.", "Exportación PDF", False, "", ""
        
        return False, "", "", False, "", ""

    # Callback para mostrar detalles de asset al hacer clic en una celda
    @app.callback(
        [Output("show-asset-detail-trigger", "data"),
         Output("asset-detail-modal-title", "children"),
         Output("asset-detail-modal-body", "children")],
        [Input("monthly-readings-table-interactive", "active_cell")],
        [State("monthly-readings-table-interactive", "derived_virtual_data"),
         State("monthly-readings-table-interactive", "derived_virtual_indices"),
         State("monthly-readings-complete-data", "data"),
         State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("jwt-token-store", "data"),
         State("monthly-readings-table-interactive", "page_current"),
         State("monthly-readings-table-interactive", "page_size")]
    )
    def show_asset_detail(active_cell, virtual_data, virtual_indices, complete_data, project_id, consumption_tags, token_data, page_current, page_size):
        """Show asset detail when a cell is clicked."""
        if not active_cell or not virtual_data or not complete_data:
            return None, None, None
        
        # Obtener información de la celda seleccionada
        row_index = active_cell["row"]
        column_id = active_cell["column_id"]
        
        # Logs para depuración de paginación y filtrado
        print(f"[DEBUG] show_asset_detail - Información de paginación: page_current={page_current}, page_size={page_size}")
        print(f"[DEBUG] show_asset_detail - Celda activa: row={row_index}, column={column_id}")
        print(f"[DEBUG] show_asset_detail - ¿Hay índices virtuales? {virtual_indices is not None}")
        if virtual_indices is not None:
            print(f"[DEBUG] show_asset_detail - Longitud de índices virtuales: {len(virtual_indices)}")
            print(f"[DEBUG] show_asset_detail - Primeros 5 índices virtuales (o menos): {virtual_indices[:min(5, len(virtual_indices))]}")
        
        # Ignorar clics en columnas de metadatos
        if column_id in ['Asset', 'block_number', 'staircase', 'apartment', 'consumption_type']:
            return None, None, None
        
        try:
            # Verificar que tenemos datos virtuales y que el índice es válido
            if not virtual_data or row_index >= len(virtual_data):
                print(f"[ERROR] show_asset_detail - Índice de fila inválido: {row_index}, longitud de datos virtuales: {len(virtual_data) if virtual_data else 0}")
                return {"show": True, "error": "Índice de fila inválido"}, "Error", html.Div("Error al obtener datos del asset. Índice de fila inválido.", className="alert alert-danger")
            
            # Obtener la fila seleccionada de los datos virtuales (ya filtrados/paginados)
            selected_row = virtual_data[row_index]
            
            # Verificar que la fila contiene la columna Asset
            if "Asset" not in selected_row:
                print(f"[ERROR] show_asset_detail - La fila seleccionada no contiene la columna 'Asset': {selected_row.keys()}")
                return {"show": True, "error": "Datos de fila inválidos"}, "Error", html.Div("Error al obtener datos del asset. La fila no contiene la columna 'Asset'.", className="alert alert-danger")
            
            # Calcular el índice global considerando la paginación y el filtrado
            global_row_index = row_index
            
            # Primero verificamos si hay filtrado (virtual_indices no es None y tiene elementos)
            if virtual_indices is not None and len(virtual_indices) > 0:
                # Si tenemos índices virtuales (filtrado), necesitamos calcular el índice correcto
                # considerando tanto el filtrado como la paginación
                
                # Si hay paginación, necesitamos ajustar el índice de fila
                if page_current is not None and page_size is not None and page_current > 0:
                    # Calcular el offset de la página actual
                    page_offset = page_current * page_size
                    
                    # SOLUCIÓN CORRECTA: Usar el índice ajustado por paginación para acceder a virtual_indices
                    # Verificar que el índice ajustado no exceda la longitud de virtual_indices
                    adjusted_row_index = row_index + page_offset
                    
                    print(f"[DEBUG] show_asset_detail - Calculando índice ajustado: row_index={row_index}, page_offset={page_offset}, adjusted_row_index={adjusted_row_index}")
                    
                    if adjusted_row_index < len(virtual_indices):
                        # Obtener el índice original usando el índice ajustado
                        original_index = virtual_indices[adjusted_row_index]
                        print(f"[DEBUG] show_asset_detail - Índice original usando índice ajustado: {original_index}")
                        global_row_index = original_index
                    else:
                        print(f"[ERROR] show_asset_detail - Índice ajustado fuera de rango: {adjusted_row_index}, longitud de virtual_indices: {len(virtual_indices)}")
                        # Como fallback, usar el índice de fila sin ajustar si está dentro del rango
                        if row_index < len(virtual_indices):
                            original_index = virtual_indices[row_index]
                            print(f"[DEBUG] show_asset_detail - Usando índice original sin ajustar como fallback: {original_index}")
                            global_row_index = original_index
                else:
                    # Si no hay paginación o estamos en la primera página, simplemente usar el índice de virtual_indices
                    if row_index < len(virtual_indices):
                        original_index = virtual_indices[row_index]
                        print(f"[DEBUG] show_asset_detail - Índice original (sin paginación o primera página): {original_index}")
                        global_row_index = original_index
                    else:
                        print(f"[ERROR] show_asset_detail - Índice de fila fuera de rango en virtual_indices: {row_index}, longitud: {len(virtual_indices)}")
            elif page_current is not None and page_size is not None:
                # Si no hay filtrado pero hay paginación, calcular el índice global
                # La página actual (page_current) comienza en 0, por lo que la página 1 es realmente la segunda página
                global_row_index = (page_current * page_size) + row_index
                print(f"[DEBUG] show_asset_detail - Índice global calculado (paginación sin filtrado): {global_row_index}")
            
            print(f"[DEBUG] show_asset_detail - Índice global final: {global_row_index}")
            
            # Obtener el asset_id y los datos de la fila global
            global_asset_id = None
            global_row_data = {}
            
            if isinstance(complete_data, dict) and 'Asset' in complete_data and isinstance(complete_data['Asset'], dict):
                global_asset_id = complete_data['Asset'].get(str(global_row_index))
                print(f"[DEBUG] show_asset_detail - Asset ID usando índice global ({global_row_index}): {global_asset_id}")
                
                # Obtener todos los datos de la fila global
                for key in complete_data.keys():
                    if isinstance(complete_data[key], dict) and str(global_row_index) in complete_data[key]:
                        global_row_data[key] = complete_data[key][str(global_row_index)]
            
            # Verificar que hemos obtenido un asset_id válido del índice global
            if not global_asset_id:
                print(f"[ERROR] show_asset_detail - No se pudo obtener el asset_id del índice global {global_row_index}")
                
                # Como fallback, usar el asset_id de la fila seleccionada
                asset_id = selected_row["Asset"]
                print(f"[INFO] show_asset_detail - Usando asset_id de la fila seleccionada como fallback: {asset_id}")
                
                # Obtener metadatos del asset de la fila seleccionada
                asset_metadata = {
                    'name': f"Asset {asset_id}",
                    'block_number': selected_row.get('block_number', ''),
                    'staircase': selected_row.get('staircase', ''),
                    'apartment': selected_row.get('apartment', '')
                }
                
                # Imprimir información adicional para depuración
                print(f"[DEBUG] show_asset_detail - Metadatos del asset (fallback): {asset_metadata}")
                print(f"[DEBUG] show_asset_detail - Datos de la fila seleccionada: {selected_row}")
            else:
                # Usar el asset_id y metadatos del índice global
                asset_id = global_asset_id
                
                # Obtener metadatos del asset de los datos globales
                asset_metadata = {
                    'name': f"Asset {asset_id}",
                    'block_number': global_row_data.get('block_number', ''),
                    'staircase': global_row_data.get('staircase', ''),
                    'apartment': global_row_data.get('apartment', '')
                }
                
                print(f"[INFO] show_asset_detail - Usando asset_id del índice global: {asset_id}")
                print(f"[DEBUG] show_asset_detail - Metadatos del asset global: {asset_metadata}")
                
                # Verificar si los metadatos están vacíos y usar los de la fila seleccionada como fallback
                if not asset_metadata.get('block_number') and not asset_metadata.get('staircase') and not asset_metadata.get('apartment'):
                    print(f"[DEBUG] show_asset_detail - Metadatos globales vacíos, usando metadatos de la fila seleccionada como fallback")
                    asset_metadata = {
                        'name': f"Asset {asset_id}",
                        'block_number': selected_row.get('block_number', ''),
                        'staircase': selected_row.get('staircase', ''),
                        'apartment': selected_row.get('apartment', '')
                    }
                    print(f"[DEBUG] show_asset_detail - Metadatos del asset (fallback): {asset_metadata}")
            
            # Usar el mes seleccionado
            selected_month = column_id
            
            # Log para depuración
            print(f"[INFO] show_asset_detail - Mostrando detalles para asset {asset_id}, mes {selected_month}")
            
            # Obtener token JWT
            token = token_data.get('token') if token_data else None
            
            # Cargar datos del CSV para el asset seleccionado
            from utils.data_loader import load_asset_detail_data
            detail_data = load_asset_detail_data(
                project_id=project_id,
                asset_id=asset_id,
                consumption_tags=consumption_tags,
                month=selected_month,
                jwt_token=token
            )
            
            # Título del modal
            modal_title = f"Detalle del Asset: {asset_id} - {selected_month}"
            
            # Crear contenido del modal usando la función del componente
            from components.metrics.asset_detail_modal import create_asset_detail_content
            modal_content = create_asset_detail_content(
                asset_id=asset_id,
                month=selected_month,
                detail_data=detail_data,
                asset_metadata=asset_metadata
            )
            
            # Activar el modal - Asegurarse de que todos los valores son serializables a JSON
            # Incluir project_id en los datos enviados al modal para que esté disponible al actualizar lecturas
            return {
                "show": True, 
                "asset_id": str(asset_id), 
                "month": str(selected_month),
                "project_id": project_id,  # Añadir project_id para que esté disponible en las actualizaciones
                "metadata": asset_metadata,
                "tags": consumption_tags
            }, modal_title, modal_content
        
        except Exception as e:
            print(f"[ERROR] show_asset_detail - Error al cargar detalles: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # En caso de error, mostrar mensaje de error
            error_content = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error al cargar detalles: {str(e)}"
            ], className="alert alert-danger")
            
            # Asegurarse de que todos los valores son serializables a JSON
            return {"show": True, "error": str(e)}, "Error", error_content

    # Callback para monitorear cambios en la tabla (solo para depuración)
    @app.callback(
        Output("monthly-readings-table-debug", "data"),
        [Input("monthly-readings-table-interactive", "page_current"),
         Input("monthly-readings-table-interactive", "page_size"),
         Input("monthly-readings-table-interactive", "filter_query"),
         Input("monthly-readings-table-interactive", "derived_virtual_data"),
         Input("monthly-readings-table-interactive", "derived_virtual_indices")],
        prevent_initial_call=True
    )
    def monitor_table_changes(page_current, page_size, filter_query, virtual_data, virtual_indices):
        """Monitorear cambios en la tabla para depuración."""
        ctx = callback_context
        trigger = ctx.triggered[0]['prop_id'].split('.')[1] if ctx.triggered else 'No trigger'
        
        print(f"[DEBUG] monitor_table_changes - Trigger: {trigger}")
        print(f"[DEBUG] monitor_table_changes - Página actual: {page_current}")
        print(f"[DEBUG] monitor_table_changes - Tamaño de página: {page_size}")
        print(f"[DEBUG] monitor_table_changes - Filtro: {filter_query}")
        print(f"[DEBUG] monitor_table_changes - Datos virtuales: {len(virtual_data) if virtual_data else 0} filas")
        print(f"[DEBUG] monitor_table_changes - Índices virtuales: {len(virtual_indices) if virtual_indices else 0} elementos")
        
        if virtual_indices and len(virtual_indices) > 0:
            print(f"[DEBUG] monitor_table_changes - Primeros 5 índices virtuales: {virtual_indices[:min(5, len(virtual_indices))]}")
            print(f"[DEBUG] monitor_table_changes - Últimos 5 índices virtuales: {virtual_indices[-min(5, len(virtual_indices)):]}")
            
            # Verificar si hay paginación y cómo afecta a los índices virtuales
            if page_current is not None and page_size is not None and page_current > 0:
                print(f"[DEBUG] monitor_table_changes - Estamos en la página {page_current}")
                # Calcular el rango de índices que deberían estar en esta página
                start_idx = page_current * page_size
                end_idx = start_idx + page_size
                print(f"[DEBUG] monitor_table_changes - Rango de índices esperados para esta página: {start_idx} - {end_idx}")
                
                # Verificar si los índices virtuales corresponden a este rango
                if len(virtual_indices) <= page_size:
                    print(f"[DEBUG] monitor_table_changes - Los índices virtuales parecen estar limitados a la página actual")
                    # Verificar los valores de los índices virtuales
                    if len(virtual_indices) > 0:
                        print(f"[DEBUG] monitor_table_changes - Valores de índices virtuales: {virtual_indices}")
                else:
                    print(f"[DEBUG] monitor_table_changes - Los índices virtuales contienen más elementos que el tamaño de la página")
                    # Verificar si los índices virtuales están en el rango esperado
                    indices_in_range = [idx for idx in virtual_indices if start_idx <= idx < end_idx]
                    print(f"[DEBUG] monitor_table_changes - Índices virtuales en el rango esperado: {indices_in_range}")
                    
                    # Simular cómo se calcularía el índice global para diferentes filas en esta página
                    for i in range(min(5, page_size)):
                        adjusted_row_index = i + start_idx
                        if adjusted_row_index < len(virtual_indices):
                            original_index = virtual_indices[adjusted_row_index]
                            print(f"[DEBUG] monitor_table_changes - Simulación: Para fila {i} en página {page_current}, adjusted_row_index={adjusted_row_index}, índice original={original_index}")
        
        # No necesitamos actualizar nada, este callback es solo para depuración
        return dash.no_update
