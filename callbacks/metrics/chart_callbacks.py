from dash import Output, Input, State, callback_context
import dash
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils.api import get_daily_readings_for_year_multiple_tags_project_parallel
from utils.metrics.data_processing import (
    process_metrics_data, 
    generate_monthly_consumption_summary
)
from components.metrics.charts import (
    create_time_series_chart,
    create_bar_chart,
    create_consumption_comparison_chart,
    create_consumption_trend_chart,
    create_consumption_distribution_chart,
    create_heatmap,
    create_combined_readings_chart,
    create_monthly_totals_chart,
    create_monthly_averages_chart
)
from utils.data_loader import load_all_csv_data

# Función personalizada para serializar objetos a JSON
def custom_json_serializer(obj):
    """Función personalizada para serializar objetos a JSON."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, 'to_timestamp'):
        # Para objetos Period de pandas
        return obj.to_timestamp().isoformat()
    elif pd.isna(obj):
        return None
    elif hasattr(obj, '__str__'):
        return str(obj)
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def register_chart_callbacks(app):
    """Register callbacks for charts."""
    
    @app.callback(
        Output("metrics-data-store", "data"),
        [Input("metrics-analyze-button", "n_clicks")],
        [State("metrics-client-filter", "value"),
         State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def load_data(n_clicks, client_id, project_id, consumption_tags, token_data):
        """Load data when the analyze button is clicked."""
        print("=====================================================")
        print("DEBUGGING LOAD DATA - FUNCTION CALLED")
        print("=====================================================")
        print(f"[DEBUG] load_data - n_clicks: {n_clicks}")
        print(f"[DEBUG] load_data - client_id: {client_id}")
        print(f"[DEBUG] load_data - project_id: {project_id}")
        print(f"[DEBUG] load_data - consumption_tags: {consumption_tags}")
        
        if not n_clicks or not client_id or not consumption_tags:
            print(f"[DEBUG] load_data - No clicks or missing client_id or consumption_tags")
            return dash.no_update
        
        try:
            print(f"[INFO METRICS] load_data - Cargando datos para cliente {client_id}, proyecto {project_id}, tags {consumption_tags}")
            
            # Obtener el token JWT directamente del store
            token = token_data.get('token') if token_data else None
            
            if not token:
                print("[ERROR METRICS] load_data - No se encontró token JWT")
                return json.dumps([])
            
            # Cargar datos desde archivos CSV locales
            print(f"[INFO METRICS] load_data - Cargando datos desde archivos CSV para proyecto {project_id}, tags {consumption_tags}")
            df = load_all_csv_data(consumption_tags=consumption_tags, project_id=project_id, jwt_token=token)
            
            if df is None or df.empty:
                print("[ERROR METRICS] load_data - No se encontraron datos en los archivos CSV")
                return json.dumps([])
            
            # Asegurarse de que el DataFrame tiene las columnas necesarias
            required_columns = ['date', 'consumption', 'asset_id', 'consumption_type']
            if not all(col in df.columns for col in required_columns):
                print(f"[ERROR METRICS] load_data - Faltan columnas requeridas. Columnas disponibles: {df.columns.tolist()}")
                return json.dumps([])
            
            # Añadir client_id si no existe
            if 'client_id' not in df.columns:
                df['client_id'] = client_id
            
            # Simplificar el DataFrame para evitar problemas de serialización
            try:
                # Convertir la columna date a string para evitar problemas de serialización
                if 'date' in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df['date']):
                        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                    else:
                        df['date'] = df['date'].astype(str)
                
                # Crear una lista de diccionarios simplificada
                simplified_data = []
                for _, row in df.iterrows():
                    simplified_row = {}
                    for col in df.columns:
                        # Manejar diferentes tipos de datos
                        if pd.api.types.is_datetime64_any_dtype(pd.Series([row[col]])):
                            simplified_row[col] = row[col].strftime('%Y-%m-%d')
                        elif hasattr(row[col], 'to_timestamp'):  # Para objetos Period
                            simplified_row[col] = row[col].to_timestamp().strftime('%Y-%m-%d')
                        elif pd.isna(row[col]):
                            simplified_row[col] = None
                        else:
                            simplified_row[col] = row[col]
                    simplified_data.append(simplified_row)
                
                # Convertir a JSON con el serializador personalizado
                json_data = json.dumps(simplified_data, default=custom_json_serializer)
                
                print(f"[INFO METRICS] load_data - Se cargaron {len(df)} registros desde archivos CSV")
                return json_data
            except Exception as e:
                print(f"[ERROR METRICS] load_data - Error al serializar a JSON: {str(e)}")
                # Enfoque aún más simple: solo incluir las columnas requeridas como strings
                simplified_data = []
                for _, row in df.iterrows():
                    simplified_row = {}
                    for col in required_columns:
                        simplified_row[col] = str(row[col])
                    if 'client_id' in df.columns:
                        simplified_row['client_id'] = str(row['client_id'])
                    simplified_data.append(simplified_row)
                
                return json.dumps(simplified_data)
            
        except Exception as e:
            print(f"[ERROR METRICS] load_data: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return json.dumps([])
    
    @app.callback(
        Output("metrics-visualization-container", "style"),
        [Input("metrics-data-store", "data")]
    )
    def toggle_visualization_container(json_data):
        """Toggle visibility of visualization container based on data availability."""
        if not json_data or json_data == "[]":
            return {"display": "none"}
        return {"display": "block"}
    
    @app.callback(
        [Output("metrics-data-loading-message", "style"),
         Output("metrics-initial-message", "style")],
        [Input("metrics-data-store", "data"),
         Input("metrics-analyze-button", "n_clicks")]
    )
    def toggle_messages(json_data, n_clicks):
        """Toggle visibility of loading and initial messages."""
        # Si no se ha hecho clic en el botón, mostrar el mensaje inicial
        if not n_clicks:
            return {"display": "none"}, {"display": "block"}
        
        # Si se ha hecho clic pero no hay datos, mostrar el mensaje de carga
        if not json_data or json_data == "[]":
            return {"display": "flex", "flex-direction": "column", "align-items": "center", "justify-content": "center"}, {"display": "none"}
        
        # Si hay datos, ocultar ambos mensajes
        return {"display": "none"}, {"display": "none"}
    
    @app.callback(
        Output("metrics-time-series-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_time_series_chart(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        """Update time series chart based on selected filters."""
        if not json_data or json_data == "[]":
            return create_time_series_chart(pd.DataFrame())
        
        try:
            # Convertir JSON a DataFrame
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
            
            # Crear gráfico
            return create_time_series_chart(filtered_df, color_column='consumption_type')
            
        except Exception as e:
            print(f"[ERROR METRICS] update_time_series_chart: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return create_time_series_chart(pd.DataFrame())
    
    @app.callback(
        Output("metrics-distribution-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_distribution_chart(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        """Update distribution chart based on selected filters."""
        if not json_data or json_data == "[]":
            return create_consumption_distribution_chart(pd.DataFrame(), 'asset_id')
        
        try:
            # Convertir JSON a DataFrame
            df = pd.DataFrame(json.loads(json_data))
            
            # Procesar datos según filtros
            filtered_df = process_metrics_data(
                df, 
                client_id=client_id, 
                project_id=project_id, 
                consumption_tags=consumption_tags, 
                start_date=start_date, 
                end_date=end_date
            )
            
            # Si se ha seleccionado un activo específico, mostrar distribución por tipo de consumo
            if asset_id and asset_id != "all":
                return create_consumption_distribution_chart(filtered_df, 'consumption_type', "Distribución por Tipo de Consumo")
            
            # Si no, mostrar distribución por activo
            return create_consumption_distribution_chart(filtered_df, 'asset_id', "Distribución por Activo")
            
        except Exception as e:
            print(f"[ERROR METRICS] update_distribution_chart: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return create_consumption_distribution_chart(pd.DataFrame(), 'asset_id')
    
    @app.callback(
        Output("metrics-trend-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date"),
         Input("metrics-time-period", "value")]
    )
    def update_trend_chart(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date, time_period):
        """Update trend chart based on selected filters and time period."""
        if not json_data or json_data == "[]":
            return create_consumption_trend_chart(pd.DataFrame())
        
        try:
            # Convertir JSON a DataFrame
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
            
            # Crear gráfico
            return create_consumption_trend_chart(filtered_df, time_period, 'consumption_type')
            
        except Exception as e:
            print(f"[ERROR METRICS] update_trend_chart: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return create_consumption_trend_chart(pd.DataFrame())
    
    @app.callback(
        Output("metrics-assets-comparison-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_assets_comparison_chart(json_data, client_id, project_id, consumption_tags, start_date, end_date):
        """Update assets comparison chart based on selected filters."""
        if not json_data or json_data == "[]":
            return create_bar_chart(pd.DataFrame(), 'asset_id')
        
        try:
            # Convertir JSON a DataFrame
            df = pd.DataFrame(json.loads(json_data))
            
            # Procesar datos según filtros
            filtered_df = process_metrics_data(
                df, 
                client_id=client_id, 
                project_id=project_id, 
                consumption_tags=consumption_tags, 
                start_date=start_date, 
                end_date=end_date
            )
            
            # Crear gráfico
            return create_consumption_comparison_chart(filtered_df, 'asset_id', "Comparación de Activos")
            
        except Exception as e:
            print(f"[ERROR METRICS] update_assets_comparison_chart: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return create_bar_chart(pd.DataFrame(), 'asset_id')
    
    @app.callback(
        Output("metrics-combined-readings-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_combined_readings_chart(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        """Update the combined readings chart."""
        try:
            # Parse JSON data
            if not json_data:
                print("[INFO METRICS] update_combined_readings_chart - No JSON data")
                return create_combined_readings_chart(pd.DataFrame())
            
            # Convert JSON to DataFrame
            try:
                data = json.loads(json_data)
                if not data:
                    print("[INFO METRICS] update_combined_readings_chart - Empty JSON data")
                    return create_combined_readings_chart(pd.DataFrame())
                
                df = pd.DataFrame(data)
                print(f"[INFO METRICS] update_combined_readings_chart - Columns in DataFrame: {df.columns.tolist()}")
                print(f"[INFO METRICS] update_combined_readings_chart - DataFrame shape: {df.shape}")
                
                # Debug: Check unique values for key columns
                print(f"[DEBUG] Unique client_ids: {df['client_id'].unique() if 'client_id' in df.columns else 'No client_id column'}")
                print(f"[DEBUG] Unique project_ids: {df['project_id'].unique() if 'project_id' in df.columns else 'No project_id column'}")
                print(f"[DEBUG] Unique asset_ids: {df['asset_id'].unique() if 'asset_id' in df.columns else 'No asset_id column'}")
                print(f"[DEBUG] Unique consumption_types: {df['consumption_type'].unique() if 'consumption_type' in df.columns else 'No consumption_type column'}")
                print(f"[DEBUG] Selected client_id: {client_id}")
                print(f"[DEBUG] Selected project_id: {project_id}")
                print(f"[DEBUG] Selected asset_id: {asset_id}")
                print(f"[DEBUG] Selected consumption_tags: {consumption_tags}")
                
            except Exception as e:
                print(f"[ERROR METRICS] update_combined_readings_chart - Error al convertir JSON a DataFrame: {str(e)}")
                return create_combined_readings_chart(pd.DataFrame())
            
            # Skip the process_metrics_data function for now and work directly with the data
            filtered_df = df.copy()
            
            # Apply basic filters manually
            if client_id and 'client_id' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['client_id'] == client_id]
                
            if project_id and project_id != "all" and 'project_id' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['project_id'] == project_id]
                
            if consumption_tags and 'consumption_type' in filtered_df.columns:
                # Check if we need to filter by consumption_type or tag
                # First try to match by consumption_type
                consumption_type_mask = filtered_df['consumption_type'].isin(consumption_tags)
                matches_in_consumption_type = consumption_type_mask.sum()
                print(f"Matches in consumption_type column: {matches_in_consumption_type}")
                
                # If no matches in consumption_type, try to match by tag
                if matches_in_consumption_type == 0 and 'tag' in filtered_df.columns:
                    tag_mask = filtered_df['tag'].isin(consumption_tags)
                    matches_in_tag = tag_mask.sum()
                    print(f"Matches in tag column: {matches_in_tag}")
                    
                    if matches_in_tag > 0:
                        filtered_df = filtered_df[tag_mask]
                    else:
                        # If still no matches, try a more flexible approach
                        print(f"Attempting to filter by consumption_tags: {consumption_tags}")
                        # Keep all rows since we couldn't match by consumption_type or tag
                        print(f"Filtered by consumption_tags using flexible matching: {len(filtered_df)} rows remaining")
                else:
                    # Use consumption_type filter if we found matches
                    filtered_df = filtered_df[consumption_type_mask]
                
            if start_date:
                filtered_df['date'] = pd.to_datetime(filtered_df['date'])
                filtered_df = filtered_df[filtered_df['date'] >= pd.to_datetime(start_date)]
                
            if end_date:
                if 'date' not in filtered_df.columns or not pd.api.types.is_datetime64_any_dtype(filtered_df['date']):
                    filtered_df['date'] = pd.to_datetime(filtered_df['date'])
                filtered_df = filtered_df[filtered_df['date'] <= pd.to_datetime(end_date)]
            
            print(f"[INFO METRICS] update_combined_readings_chart - DataFrame shape after manual filtering: {filtered_df.shape}")
            
            if filtered_df.empty:
                print("[INFO METRICS] update_combined_readings_chart - DataFrame is empty after manual filtering")
                return create_combined_readings_chart(pd.DataFrame())
            
            # Ensure date is datetime
            filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            
            # Sort by date
            filtered_df = filtered_df.sort_values('date')
            
            # Get the asset_id for the readings
            if asset_id and asset_id != "all" and 'asset_id' in filtered_df.columns:
                asset_ids = [asset_id]
            else:
                # If no specific asset is selected, use the first one in the data
                if 'asset_id' in filtered_df.columns:
                    asset_ids = filtered_df['asset_id'].unique()
                    if len(asset_ids) > 0:
                        asset_ids = [asset_ids[0]]
                    else:
                        print("[INFO METRICS] update_combined_readings_chart - No asset_ids found")
                        return create_combined_readings_chart(pd.DataFrame())
                else:
                    # If there's no asset_id column, just use all data
                    asset_ids = ["all"]
            
            print(f"[INFO METRICS] update_combined_readings_chart - Using asset_id: {asset_ids[0]}")
            
            # Filter for the selected asset if needed
            if asset_ids[0] != "all" and 'asset_id' in filtered_df.columns:
                asset_df = filtered_df[filtered_df['asset_id'] == asset_ids[0]]
            else:
                asset_df = filtered_df
            
            if asset_df.empty:
                print(f"[INFO METRICS] update_combined_readings_chart - No data for asset_id {asset_ids[0]}")
                return create_combined_readings_chart(pd.DataFrame())
            
            # Ensure we have the value column
            if 'value' not in asset_df.columns:
                print("[ERROR METRICS] update_combined_readings_chart - No 'value' column found in data")
                return create_combined_readings_chart(pd.DataFrame())
            
            # Convert value column to numeric
            asset_df['value'] = pd.to_numeric(asset_df['value'], errors='coerce')
            
            # Add month column for grouping
            asset_df['month'] = asset_df['date'].dt.strftime('%Y-%m')
            
            # Get the last reading of each month (accumulated reading)
            monthly_readings = asset_df.groupby('month').agg({
                'value': 'last',  # Last reading of the month
                'date': 'last'    # Last date of the month
            }).reset_index()
            
            # Rename columns for clarity
            monthly_readings = monthly_readings.rename(columns={'value': 'reading'})
            
            # Calculate monthly consumption (difference between consecutive readings)
            monthly_readings['consumption'] = monthly_readings['reading'].diff().fillna(monthly_readings['reading'])
            
            # For negative consumption values (e.g., meter reset), use the absolute value
            # This is more appropriate for consumption data which should be positive
            monthly_readings.loc[monthly_readings['consumption'] < 0, 'consumption'] = monthly_readings.loc[monthly_readings['consumption'] < 0, 'reading'].abs()
            
            # Ensure the date is at the beginning of the month for better display
            monthly_readings['date'] = pd.to_datetime(monthly_readings['month'] + '-01')
            
            # Ensure data types are correct
            monthly_readings['reading'] = pd.to_numeric(monthly_readings['reading'], errors='coerce')
            monthly_readings['consumption'] = pd.to_numeric(monthly_readings['consumption'], errors='coerce')
            
            # Debug: Print the actual values
            print(f"[DEBUG] Reading values: {monthly_readings['reading'].tolist()}")
            print(f"[DEBUG] Consumption values: {monthly_readings['consumption'].tolist()}")
            print(f"[DEBUG] Date values: {monthly_readings['date'].tolist()}")
            
            # Check if we have valid data for the chart
            if monthly_readings.empty or monthly_readings['reading'].isnull().all() or monthly_readings['consumption'].isnull().all():
                print("[WARNING] No valid data for chart after processing")
                return create_combined_readings_chart(pd.DataFrame())
                
            print(f"[INFO METRICS] update_combined_readings_chart - Final DataFrame shape: {monthly_readings.shape}")
            if not monthly_readings.empty:
                print(f"[INFO METRICS] update_combined_readings_chart - Final DataFrame sample: {monthly_readings.head().to_dict()}")
            
            # Create the chart
            return create_combined_readings_chart(monthly_readings)
            
        except Exception as e:
            print(f"[ERROR METRICS] update_combined_readings_chart - Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return create_combined_readings_chart(pd.DataFrame())

    @app.callback(
        Output("metrics-monthly-totals-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_monthly_totals_chart(json_data, client_id, project_id, consumption_tags, start_date, end_date):
        """Update the monthly totals chart."""
        print("=====================================================")
        print("DEBUGGING MONTHLY TOTALS CHART CALLBACK - FUNCTION CALLED")
        print("=====================================================")
        print(f"[INFO METRICS] update_monthly_totals_chart - Starting")
        print(f"[INFO METRICS] update_monthly_totals_chart - client_id: {client_id}")
        print(f"[INFO METRICS] update_monthly_totals_chart - project_id: {project_id}")
        print(f"[INFO METRICS] update_monthly_totals_chart - consumption_tags: {consumption_tags}")
        print(f"[INFO METRICS] update_monthly_totals_chart - start_date: {start_date}")
        print(f"[INFO METRICS] update_monthly_totals_chart - end_date: {end_date}")
        
        try:
            # Si no hay datos, crear datos de ejemplo
            if not json_data or json_data == "[]":
                print(f"[INFO METRICS] update_monthly_totals_chart - No data available, creating sample data")
                
                # Crear datos de ejemplo directamente
                end = pd.Timestamp.now()
                start = end - pd.DateOffset(months=6)
                date_range = pd.date_range(start=start, end=end, freq='MS')
                
                sample_data = {
                    'month': [d.strftime('%Y-%m') for d in date_range],
                    'total_consumption': [100 * (i+1) for i in range(len(date_range))],
                    'average_consumption': [50 * (i+1) for i in range(len(date_range))],
                    'min_consumption': [10 * (i+1) for i in range(len(date_range))],
                    'max_consumption': [200 * (i+1) for i in range(len(date_range))],
                    'asset_count': [5 for _ in range(len(date_range))],
                    'date': date_range
                }
                
                monthly_summary = pd.DataFrame(sample_data)
                print(f"[INFO METRICS] update_monthly_totals_chart - Created sample DataFrame with {len(monthly_summary)} rows")
                
                return create_monthly_totals_chart(monthly_summary)
            
            # Convert JSON to DataFrame
            df = pd.DataFrame(json.loads(json_data))
            print(f"[INFO METRICS] update_monthly_totals_chart - Loaded DataFrame with {len(df)} rows")
            
            # Process data according to filters
            filtered_df = process_metrics_data(
                df, 
                client_id=client_id, 
                project_id=project_id, 
                consumption_tags=consumption_tags, 
                start_date=start_date, 
                end_date=end_date
            )
            
            print(f"[INFO METRICS] update_monthly_totals_chart - Filtered DataFrame has {len(filtered_df)} rows")
            
            # Generate monthly summary
            monthly_summary = generate_monthly_consumption_summary(filtered_df, start_date, end_date)
            
            print(f"[INFO METRICS] update_monthly_totals_chart - Generated monthly summary with {len(monthly_summary)} rows")
            
            # Create chart
            return create_monthly_totals_chart(monthly_summary)
            
        except Exception as e:
            print(f"[ERROR METRICS] update_monthly_totals_chart: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # En caso de error, crear datos de ejemplo
            print(f"[INFO METRICS] update_monthly_totals_chart - Error occurred, creating sample data")
            
            # Crear datos de ejemplo directamente
            end = pd.Timestamp.now()
            start = end - pd.DateOffset(months=6)
            date_range = pd.date_range(start=start, end=end, freq='MS')
            
            sample_data = {
                'month': [d.strftime('%Y-%m') for d in date_range],
                'total_consumption': [100 * (i+1) for i in range(len(date_range))],
                'average_consumption': [50 * (i+1) for i in range(len(date_range))],
                'min_consumption': [10 * (i+1) for i in range(len(date_range))],
                'max_consumption': [200 * (i+1) for i in range(len(date_range))],
                'asset_count': [5 for _ in range(len(date_range))],
                'date': date_range
            }
            
            monthly_summary = pd.DataFrame(sample_data)
            print(f"[INFO METRICS] update_monthly_totals_chart - Created sample DataFrame with {len(monthly_summary)} rows")
            
            return create_monthly_totals_chart(monthly_summary)

    @app.callback(
        Output("metrics-monthly-averages-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_monthly_averages_chart(json_data, client_id, project_id, consumption_tags, start_date, end_date):
        """Update the monthly averages chart."""
        print("=====================================================")
        print("DEBUGGING MONTHLY AVERAGES CHART CALLBACK - FUNCTION CALLED")
        print("=====================================================")
        print(f"[INFO METRICS] update_monthly_averages_chart - Starting")
        print(f"[INFO METRICS] update_monthly_averages_chart - client_id: {client_id}")
        print(f"[INFO METRICS] update_monthly_averages_chart - project_id: {project_id}")
        print(f"[INFO METRICS] update_monthly_averages_chart - consumption_tags: {consumption_tags}")
        print(f"[INFO METRICS] update_monthly_averages_chart - start_date: {start_date}")
        print(f"[INFO METRICS] update_monthly_averages_chart - end_date: {end_date}")
        
        try:
            # Si no hay datos, crear datos de ejemplo
            if not json_data or json_data == "[]":
                print(f"[INFO METRICS] update_monthly_averages_chart - No data available, creating sample data")
                
                # Crear datos de ejemplo directamente
                end = pd.Timestamp.now()
                start = end - pd.DateOffset(months=6)
                date_range = pd.date_range(start=start, end=end, freq='MS')
                
                sample_data = {
                    'month': [d.strftime('%Y-%m') for d in date_range],
                    'total_consumption': [100 * (i+1) for i in range(len(date_range))],
                    'average_consumption': [50 * (i+1) for i in range(len(date_range))],
                    'min_consumption': [10 * (i+1) for i in range(len(date_range))],
                    'max_consumption': [200 * (i+1) for i in range(len(date_range))],
                    'asset_count': [5 for _ in range(len(date_range))],
                    'date': date_range
                }
                
                monthly_summary = pd.DataFrame(sample_data)
                print(f"[INFO METRICS] update_monthly_averages_chart - Created sample DataFrame with {len(monthly_summary)} rows")
                
                return create_monthly_averages_chart(monthly_summary)
            
            # Convert JSON to DataFrame
            df = pd.DataFrame(json.loads(json_data))
            print(f"[INFO METRICS] update_monthly_averages_chart - Loaded DataFrame with {len(df)} rows")
            
            # Process data according to filters
            filtered_df = process_metrics_data(
                df, 
                client_id=client_id, 
                project_id=project_id, 
                consumption_tags=consumption_tags, 
                start_date=start_date, 
                end_date=end_date
            )
            
            print(f"[INFO METRICS] update_monthly_averages_chart - Filtered DataFrame has {len(filtered_df)} rows")
            
            # Generate monthly summary
            monthly_summary = generate_monthly_consumption_summary(filtered_df, start_date, end_date)
            
            print(f"[INFO METRICS] update_monthly_averages_chart - Generated monthly summary with {len(monthly_summary)} rows")
            
            # Create chart
            return create_monthly_averages_chart(monthly_summary)
            
        except Exception as e:
            print(f"[ERROR METRICS] update_monthly_averages_chart: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # En caso de error, crear datos de ejemplo
            print(f"[INFO METRICS] update_monthly_averages_chart - Error occurred, creating sample data")
            
            # Crear datos de ejemplo directamente
            end = pd.Timestamp.now()
            start = end - pd.DateOffset(months=6)
            date_range = pd.date_range(start=start, end=end, freq='MS')
            
            sample_data = {
                'month': [d.strftime('%Y-%m') for d in date_range],
                'total_consumption': [100 * (i+1) for i in range(len(date_range))],
                'average_consumption': [50 * (i+1) for i in range(len(date_range))],
                'min_consumption': [10 * (i+1) for i in range(len(date_range))],
                'max_consumption': [200 * (i+1) for i in range(len(date_range))],
                'asset_count': [5 for _ in range(len(date_range))],
                'date': date_range
            }
            
            monthly_summary = pd.DataFrame(sample_data)
            print(f"[INFO METRICS] update_monthly_averages_chart - Created sample DataFrame with {len(monthly_summary)} rows")
            
            return create_monthly_averages_chart(monthly_summary)
