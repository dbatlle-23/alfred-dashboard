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
        from utils.logging import get_logger
        logger = get_logger(__name__)
        
        if not json_data:
            logger.warning("No JSON data available for monthly readings table")
            return "", None
        
        try:
            logger.info("Starting update of monthly readings table")
            
            # Parse JSON data
            data = json.loads(json_data)
            df = pd.DataFrame(data)
            
            logger.debug(f"Parsed DataFrame with shape: {df.shape if not df.empty else 'Empty DataFrame'}")
            
            # Check if DataFrame is empty
            if df.empty:
                logger.warning("DataFrame is empty, no data to display")
                from dash import html
                return html.Div("No hay datos disponibles para mostrar.", className="alert alert-warning"), None
            
            # Check if 'date' column exists
            if 'date' not in df.columns:
                logger.error(f"'date' column does not exist in DataFrame. Available columns: {df.columns.tolist()}")
                from dash import html
                return html.Div([
                    html.H5("Error al procesar datos"),
                    html.P("La columna 'date' no existe en los datos. Verifique los archivos CSV de origen."),
                    html.P(f"Columnas disponibles: {', '.join(df.columns.tolist())}")
                ], className="alert alert-danger"), None
            
            logger.debug(f"Processing data with filter - client: {client_id}, project: {project_id}, asset: {asset_id}, tags: {consumption_tags}")
            
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
            
            logger.debug(f"DataFrame after filtering has {len(df)} rows")
            if df.empty:
                logger.warning("DataFrame after filtering is empty")
                
                # Attempt to clear caches and notify the user
                try:
                    from utils.data_loader import clear_all_caches
                    clear_all_caches()
                    logger.info("Automatically cleared caches due to no data found with current filters")
                    
                    from dash import html
                    return html.Div([
                        html.I(className="fas fa-exclamation-circle me-2"),
                        "No hay datos disponibles para los filtros seleccionados.",
                        html.Br(),
                        html.Small("Se ha limpiado la caché automáticamente. Por favor, intente visualizar los datos nuevamente.")
                    ], className="alert alert-warning"), None
                except Exception as e:
                    logger.error(f"Error clearing caches: {str(e)}")
                    
                    # Default message if cache clearing fails
                    from dash import html
                    return html.Div("No hay datos disponibles para los filtros seleccionados.", className="alert alert-warning"), None
            
            logger.debug("Getting sample of filtered DataFrame")
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"Sample data:\n{df.head(3)}")
            
            # Log consumption type information for debugging
            if 'consumption_type' in df.columns:
                logger.debug(f"Unique consumption_types: {df['consumption_type'].unique().tolist()}")
            elif 'tag' in df.columns:
                logger.debug(f"Unique tags: {df['tag'].unique().tolist()}")
            else:
                logger.warning("No consumption_type or tag column found in data")
            
            # Get JWT token
            token = token_data.get('token') if token_data else None
            
            # Get all assets for the project
            all_project_assets = []
            assets_metadata = {}
            
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
                
                logger.debug(f"Retrieved metadata for {len(assets_metadata)} assets")
            except Exception as e:
                logger.error(f"Error retrieving asset metadata: {str(e)}", exc_info=True)
            
            # Import consumption tags mapping
            from constants.metrics import CONSUMPTION_TAGS_MAPPING
            
            # Ensure date is datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            
            # Add year_month column
            df['year_month'] = df['date'].dt.strftime('%Y-%m')
            
            # Dictionary to store monthly data by asset and consumption type
            monthly_data = {}
            
            # Determine consumption type column
            consumption_type_column = 'consumption_type' if 'consumption_type' in df.columns else 'tag'
            
            # Process data by asset AND consumption type
            logger.debug(f"Using consumption type column: {consumption_type_column}")
            
            if consumption_type_column in df.columns:
                # Group by both asset_id and consumption_type
                asset_consumption_groups = df.groupby(['asset_id', consumption_type_column])
                logger.debug(f"Number of asset-consumption groups: {len(asset_consumption_groups)}")
                
                # Print some sample groups for debugging
                group_count = 0
                for (asset_id, consumption_type), group in asset_consumption_groups:
                    if group_count < 3:  # Limit to first 3 groups to avoid log clutter
                        logger.debug(f"Sample group {group_count+1}:")
                        logger.debug(f"  Asset ID: {asset_id}, Consumption Type: {consumption_type}")
                        logger.debug(f"  Group shape: {group.shape}")
                        logger.debug(f"  Group year_month values: {group['year_month'].unique().tolist()}")
                    group_count += 1
                
                for (asset_id, consumption_type), group in asset_consumption_groups:
                    logger.debug(f"Processing asset_id: {asset_id}, consumption_type: {consumption_type}, group size: {len(group)}")
                    
                    # Initialize a dictionary to store monthly readings for this asset-consumption type pair
                    asset_consumption_monthly_readings = {}
                    
                    # Get readable consumption type name
                    readable_consumption_type = CONSUMPTION_TAGS_MAPPING.get(consumption_type, consumption_type)
                    
                    # Process each month for this asset and consumption type
                    for month, month_group in group.groupby('year_month'):
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
                            asset_consumption_monthly_readings[month] = last_reading
                            
                            logger.debug(f"Month {month}, Asset {asset_id}, Type {readable_consumption_type}: First reading = {first_reading}, Last reading = {last_reading}, Monthly consumption = {monthly_consumption}")
                        except Exception as e:
                            logger.error(f"Error processing month {month} for asset {asset_id}, consumption type {readable_consumption_type}: {str(e)}")
                            import traceback
                            logger.debug(traceback.format_exc())
                    
                    if asset_consumption_monthly_readings:
                        # Use composite key for asset and consumption type
                        monthly_data[(asset_id, readable_consumption_type)] = pd.Series(asset_consumption_monthly_readings)
            else:
                logger.warning("No consumption type column found in the data. Available columns: {df.columns.tolist()}")
                # Default process by asset only if no consumption type column exists
                for asset_id, asset_group in df.groupby('asset_id'):
                    logger.debug(f"Processing asset_id: {asset_id}, group size: {len(asset_group)}")
                    
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
                            asset_monthly_readings[month] = last_reading
                            
                            logger.debug(f"Month {month}, Asset {asset_id}: First reading = {first_reading}, Last reading = {last_reading}, Monthly consumption = {monthly_consumption}")
                        except Exception as e:
                            logger.error(f"Error processing month {month} for asset {asset_id}: {str(e)}")
                            import traceback
                            logger.debug(traceback.format_exc())
                    
                    if asset_monthly_readings:
                        monthly_data[(asset_id, "Unknown")] = pd.Series(asset_monthly_readings)
            
            # Get all unique months from the data
            all_months = set()
            for asset_data in monthly_data.values():
                all_months.update(asset_data.index)
            sorted_months = sorted(all_months)
            
            logger.debug(f"Monthly data keys count: {len(monthly_data)}")
            logger.debug(f"Unique months: {sorted_months}")
            
            # Create a new DataFrame from the monthly data with ONE ROW PER ASSET
            # This is the key change - we'll combine consumption types for each asset
            if monthly_data:
                logger.debug(f"Creating pivot table with one row per asset, combining consumption types")
                
                # Get all unique assets
                all_assets = set(asset_id for (asset_id, _) in monthly_data.keys())
                
                # Get all unique consumption types
                all_consumption_types = set(consumption_type for (_, consumption_type) in monthly_data.keys())
                
                # Create rows for the pivot table - one row per asset
                rows = []
                for asset_id in all_assets:
                    # Initialize row with asset metadata
                    row = {
                        'Asset': asset_id,
                        'block_number': assets_metadata.get(asset_id, {}).get('block_number', ''),
                        'staircase': assets_metadata.get(asset_id, {}).get('staircase', ''),
                        'apartment': assets_metadata.get(asset_id, {}).get('apartment', '')
                    }
                    
                    # For each month, add columns for each consumption type
                    for month in sorted_months:
                        for consumption_type in all_consumption_types:
                            # Create a column name that includes both month and consumption type
                            column_name = f"{month} ({consumption_type})"
                            
                            # Try to get the reading for this asset, month and consumption type
                            if (asset_id, consumption_type) in monthly_data and month in monthly_data[(asset_id, consumption_type)]:
                                row[column_name] = monthly_data[(asset_id, consumption_type)][month]
                            else:
                                row[column_name] = "Sin Datos"
                    
                    rows.append(row)
                
                logger.debug(f"Created {len(rows)} rows for pivot table")
                if len(rows) > 0:
                    logger.debug(f"Sample row: {rows[0]}")
                
                # Create pivot table from rows
                pivot = pd.DataFrame(rows)
                logger.debug(f"Created pivot table with shape: {pivot.shape}")
                logger.debug(f"Pivot table columns: {pivot.columns.tolist()}")
                
                # Get list of assets that have data
                assets_with_data = all_assets
                
                # Add assets without data
                missing_assets = []
                for asset in all_project_assets:
                    if isinstance(asset, dict) and "id" in asset:
                        asset_id = asset["id"]
                        if asset_id not in assets_with_data:
                            # Create a row for this asset with "Sin Datos" for all months/consumption types
                            row = {
                                'Asset': asset_id,
                                'block_number': assets_metadata.get(asset_id, {}).get('block_number', ''),
                                'staircase': assets_metadata.get(asset_id, {}).get('staircase', ''),
                                'apartment': assets_metadata.get(asset_id, {}).get('apartment', '')
                            }
                            
                            # For each month, add columns for each consumption type
                            for month in sorted_months:
                                for consumption_type in all_consumption_types:
                                    column_name = f"{month} ({consumption_type})"
                                    row[column_name] = "Sin Datos"
                            
                            missing_assets.append(row)
                
                # Add missing assets to the pivot table
                if missing_assets:
                    logger.debug(f"Adding {len(missing_assets)} assets without data")
                    missing_df = pd.DataFrame(missing_assets)
                    pivot = pd.concat([pivot, missing_df], ignore_index=True)
                    logger.debug(f"Added {len(missing_assets)} assets without data to the table")
                    logger.debug(f"Pivot table shape after adding missing assets: {pivot.shape}")
                
                # Reorder columns to put metadata after Asset column
                metadata_cols = ['Asset', 'block_number', 'staircase', 'apartment']
                data_cols = [col for col in pivot.columns if col not in metadata_cols]
                # Sort data columns to keep them organized by month and consumption type
                data_cols.sort()
                cols = metadata_cols + data_cols
                # Only keep columns that exist in the pivot table
                existing_cols = [col for col in cols if col in pivot.columns]
                pivot = pivot[existing_cols]
                
                # Sort by Asset for better readability
                pivot = pivot.sort_values(['Asset']).reset_index(drop=True)
                
                logger.debug(f"Final pivot table shape: {pivot.shape}")
                logger.debug(f"Final pivot table columns: {pivot.columns.tolist()}")
                
                # Check if the pivot table is valid
                if pivot.empty:
                    logger.error("Final pivot table is empty")
                    from dash import html
                    return html.Div("No fue posible crear la tabla de lecturas mensuales.", className="alert alert-warning"), None
                
                # Create table component
                from dash import html
                table_component = create_monthly_readings_table(pivot, "Lecturas Mensuales")
                
                logger.debug(f"Table component created, returning results")
                return table_component, pivot.to_dict()
            else:
                # If no assets have data, create a table with all assets but no data
                logger.debug("No monthly data found. Creating table with all assets but no data.")
                
                # Create rows for all assets
                rows = []
                for asset in all_project_assets:
                    if isinstance(asset, dict) and "id" in asset:
                        asset_id = asset["id"]
                        row = {
                            'Asset': asset_id,
                            'block_number': assets_metadata.get(asset_id, {}).get('block_number', ''),
                            'staircase': assets_metadata.get(asset_id, {}).get('staircase', ''),
                            'apartment': assets_metadata.get(asset_id, {}).get('apartment', '')
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
                    logger.debug(f"Created {len(rows)} rows for empty assets")
                    empty_pivot = pd.DataFrame(rows)
                    
                    # Get all columns except Asset and metadata
                    data_columns = [col for col in empty_pivot.columns if col not in ['Asset', 'block_number', 'staircase', 'apartment']]
                    
                    # Reorder columns
                    cols = ['Asset', 'block_number', 'staircase', 'apartment'] + sorted(data_columns)
                    empty_pivot = empty_pivot[cols]
                    
                    logger.debug(f"Created table with {len(rows)} assets without data")
                    from dash import html
                    return create_monthly_readings_table(empty_pivot, "Lecturas Mensuales"), None
                else:
                    logger.debug("No assets found for the project")
                    from dash import html
                    return html.Div("No se encontraron activos para el proyecto.", className="alert alert-warning"), None
            
        except Exception as e:
            logger.error(f"Error updating monthly readings table: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            from dash import html
            return html.Div(f"Error al procesar datos: {str(e)}", className="alert alert-danger"), None

    @app.callback(
        Output("metrics-monthly-summary-table", "children"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date"),
         Input("metrics-monthly-summary-selected-type-store", "data")],
        prevent_initial_call=True
    )
    def update_monthly_summary_table(json_data, client_id, project_id, asset_id, start_date, end_date, summary_type_store_data):
        """Update monthly summary table based on the specific type selected for the summary section."""

        from constants.metrics import CONSUMPTION_TAGS_MAPPING
        from utils.logging import get_logger 
        logger = get_logger(__name__)

        default_table = dbc.Alert("Seleccione un tipo de consumo para ver el resumen mensual.", color="info")

        active_tag = summary_type_store_data.get("active_tag") if summary_type_store_data else None

        if not json_data or json_data == "[]" or not active_tag:
            return default_table

        # Map tag to human readable name for filtering
        human_readable_name = CONSUMPTION_TAGS_MAPPING.get(active_tag)
        if not human_readable_name:
             logger.warning(f"[update_monthly_summary_table] Could not map tag {active_tag}")
             return default_table

        try:
            df = pd.DataFrame(json.loads(json_data))
            
            # --- Filter data for the selected type --- 
            df_filtered_type = df[df['consumption_type'] == human_readable_name].copy()

            if df_filtered_type.empty:
                 logger.debug(f"[update_monthly_summary_table] df_filtered_type is empty for {human_readable_name}.")
                 return default_table

            # Apply other filters
            current_asset_id = asset_id if asset_id and asset_id != 'all' else None
            processed_df = process_metrics_data(
                df_filtered_type,
                client_id=client_id,
                project_id=project_id,
                asset_id=current_asset_id,
                consumption_tags=[human_readable_name], # Pass the specific type
                start_date=start_date,
                end_date=end_date
            )

            if processed_df.empty:
                 logger.debug("[update_monthly_summary_table] processed_df is empty.")
                 return default_table

            # --- Generate monthly summary for the single selected type --- 
            monthly_summary = generate_monthly_consumption_summary(processed_df, start_date, end_date)

            if monthly_summary.empty:
                logger.debug("[update_monthly_summary_table] monthly_summary is empty.")
                return default_table

            # --- Remove Pivot Logic --- 
            # The monthly_summary DataFrame should now be directly usable by the table component
            # Ensure it has the expected columns (e.g., month, total_consumption, average_consumption)
            # logger.debug(f"Monthly summary columns: {monthly_summary.columns.tolist()}")
            # logger.debug(f"Monthly summary head:\n{monthly_summary.head()}")
            
            # --- Create Table Component --- 
            # Pass the non-pivoted summary dataframe 
            # Make sure create_monthly_summary_table can handle this format
            return create_monthly_summary_table(monthly_summary)

        except Exception as e:
            logger.error(f"[ERROR update_monthly_summary_table]: {str(e)}", exc_info=True)
            return dbc.Alert(f"Ocurrió un error al generar la tabla de resumen mensual: {str(e)}", color="danger")

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
        from utils.logging import get_logger
        logger = get_logger(__name__)
        
        if not active_cell or not virtual_data or not complete_data:
            return None, None, None
        
        # Obtener información de la celda seleccionada
        row_index = active_cell["row"]
        column_id = active_cell["column_id"]
        
        # Log basic cell info for debugging
        logger.debug(f"Asset detail requested for cell at row={row_index}, column={column_id}")
        
        # Ignorar clics en columnas de metadatos
        if column_id in ['Asset', 'block_number', 'staircase', 'apartment']:
            return None, None, None
        
        try:
            # Verificar que tenemos datos virtuales y que el índice es válido
            if not virtual_data or row_index >= len(virtual_data):
                logger.error(f"Invalid row index: {row_index}, virtual data length: {len(virtual_data) if virtual_data else 0}")
                from dash import html
                return {"show": True, "error": "Índice de fila inválido"}, "Error", html.Div("Error al obtener datos del asset. Índice de fila inválido.", className="alert alert-danger")
            
            # Obtener la fila seleccionada de los datos virtuales (ya filtrados/paginados)
            selected_row = virtual_data[row_index]
            
            # Verificar que la fila contiene la columna Asset
            if "Asset" not in selected_row:
                logger.error(f"Selected row does not contain 'Asset' column. Available columns: {list(selected_row.keys())}")
                from dash import html
                return {"show": True, "error": "Datos de fila inválidos"}, "Error", html.Div("Error al obtener datos del asset. La fila no contiene la columna 'Asset'.", className="alert alert-danger")
            
            # Calcular el índice global considerando la paginación y el filtrado
            global_row_index = row_index
            
            # Calculate global row index taking into account pagination and filtering
            if virtual_indices is not None and len(virtual_indices) > 0:
                if page_current is not None and page_size is not None and page_current > 0:
                    # Pagination adjustment
                    adjusted_row_index = row_index + (page_current * page_size)
                    
                    if adjusted_row_index < len(virtual_indices):
                        global_row_index = virtual_indices[adjusted_row_index]
                    elif row_index < len(virtual_indices):
                        global_row_index = virtual_indices[row_index]
                elif row_index < len(virtual_indices):
                    global_row_index = virtual_indices[row_index]
            elif page_current is not None and page_size is not None:
                global_row_index = (page_current * page_size) + row_index
            
            logger.debug(f"Calculated global row index: {global_row_index}")
            
            # Obtener el asset_id y los datos de la fila global
            global_asset_id = None
            global_row_data = {}
            
            if isinstance(complete_data, dict) and 'Asset' in complete_data and isinstance(complete_data['Asset'], dict):
                global_asset_id = complete_data['Asset'].get(str(global_row_index))
                
                # Obtener todos los datos de la fila global
                for key in complete_data.keys():
                    if isinstance(complete_data[key], dict) and str(global_row_index) in complete_data[key]:
                        global_row_data[key] = complete_data[key][str(global_row_index)]
            
            # Prepare asset data - use global data if available, otherwise fall back to selected row
            if not global_asset_id:
                logger.info(f"Using asset ID from selected row as fallback")
                asset_id = selected_row["Asset"]
                asset_metadata = {
                    'name': f"Asset {asset_id}",
                    'block_number': selected_row.get('block_number', ''),
                    'staircase': selected_row.get('staircase', ''),
                    'apartment': selected_row.get('apartment', '')
                }
            else:
                asset_id = global_asset_id
                asset_metadata = {
                    'name': f"Asset {asset_id}",
                    'block_number': global_row_data.get('block_number', ''),
                    'staircase': global_row_data.get('staircase', ''),
                    'apartment': global_row_data.get('apartment', '')
                }
                
                # Fall back to selected row metadata if global metadata is empty
                if not asset_metadata.get('block_number') and not asset_metadata.get('staircase') and not asset_metadata.get('apartment'):
                    logger.debug("Global metadata empty, using metadata from selected row")
                    asset_metadata = {
                        'name': f"Asset {asset_id}",
                        'block_number': selected_row.get('block_number', ''),
                        'staircase': selected_row.get('staircase', ''),
                        'apartment': selected_row.get('apartment', '')
                    }
            
            # Parse column ID to extract month and consumption type
            import re
            column_match = re.match(r'(\d{4}-\d{2}) \((.*?)\)', column_id)
            
            if column_match:
                selected_month = column_match.group(1)  # Month (YYYY-MM)
                selected_consumption_type = column_match.group(2)  # Consumption type
                logger.debug(f"Parsed column: month={selected_month}, consumption_type={selected_consumption_type}")
            else:
                # Fallback for backward compatibility
                selected_month = column_id
                selected_consumption_type = None
                logger.warning(f"Could not parse column ID format: {column_id}, using as month directly")
            
            # Get JWT token
            token = token_data.get('token') if token_data else None
            
            # Filter consumption tags if we have a specific consumption type
            filtered_consumption_tags = consumption_tags
            if selected_consumption_type and consumption_tags:
                try:
                    from constants.metrics import CONSUMPTION_TAGS_MAPPING
                    
                    # Find tags that match the selected consumption type
                    matching_tags = []
                    for tag in consumption_tags:
                        tag_name = tag.get('tag_name', tag) if isinstance(tag, dict) else tag
                        tag_display = CONSUMPTION_TAGS_MAPPING.get(tag_name, tag_name)
                        
                        if tag_display == selected_consumption_type:
                            matching_tags.append(tag)
                    
                    if matching_tags:
                        filtered_consumption_tags = matching_tags
                        logger.info(f"Filtered to {len(matching_tags)} tags matching '{selected_consumption_type}'")
                    else:
                        logger.warning(f"No matching tags found for type '{selected_consumption_type}'")
                except Exception as e:
                    logger.error(f"Error filtering tags: {str(e)}")
                    filtered_consumption_tags = consumption_tags
            
            # Load data for the selected asset, month and consumption type
            from utils.data_loader import load_asset_detail_data
            detail_data = load_asset_detail_data(
                project_id=project_id,
                asset_id=asset_id,
                consumption_tags=filtered_consumption_tags,
                month=selected_month,
                jwt_token=token
            )
            
            # Prepare modal title
            if selected_consumption_type:
                modal_title = f"Detalle del Asset: {asset_id} - {selected_month} - {selected_consumption_type}"
            else:
                modal_title = f"Detalle del Asset: {asset_id} - {selected_month}"
            
            # Create modal content
            from components.metrics.asset_detail_modal import create_asset_detail_content
            modal_content = create_asset_detail_content(
                asset_id=asset_id,
                month=selected_month,
                detail_data=detail_data,
                asset_metadata=asset_metadata
            )
            
            logger.info(f"Showing asset detail for asset={asset_id}, month={selected_month}, type={selected_consumption_type or 'all'}")
            
            # Return data for modal
            return {
                "show": True, 
                "asset_id": str(asset_id), 
                "month": str(selected_month),
                "consumption_type": selected_consumption_type,
                "project_id": project_id,
                "metadata": asset_metadata,
                "tags": filtered_consumption_tags
            }, modal_title, modal_content
        
        except Exception as e:
            logger.error(f"Error loading asset details: {str(e)}", exc_info=True)
            
            # Show error message
            from dash import html
            error_content = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error al cargar detalles: {str(e)}"
            ], className="alert alert-danger")
            
            return {"show": True, "error": str(e)}, "Error", error_content

    # Callback for monitoring table changes (for debugging purposes)
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
        """Monitor table changes for debugging purposes."""
        from utils.logging import get_logger
        logger = get_logger(__name__)
        
        ctx = callback_context
        trigger = ctx.triggered[0]['prop_id'].split('.')[1] if ctx.triggered else 'No trigger'
        
        # Only log details at DEBUG level to avoid cluttering logs
        if logger.isEnabledFor(10):  # DEBUG level
            logger.debug(f"Table change triggered by: {trigger}")
            logger.debug(f"Page: {page_current}, Size: {page_size}, Filter: {filter_query}")
            logger.debug(f"Virtual data: {len(virtual_data) if virtual_data else 0} rows")
            logger.debug(f"Virtual indices: {len(virtual_indices) if virtual_indices else 0} indices")
            
            # Log a sample of indices for detailed debugging if needed
            if virtual_indices and len(virtual_indices) > 0:
                logger.debug(f"First 5 indices: {virtual_indices[:min(5, len(virtual_indices))]}")
                logger.debug(f"Last 5 indices: {virtual_indices[-min(5, len(virtual_indices)):]}")
        
        # This callback is for monitoring only, no update needed
        return dash.no_update
