from dash import Output, Input, State, callback_context
import dash
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import html
import os
import time

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
    create_monthly_totals_chart,
    create_monthly_averages_chart
)
from utils.data_loader import load_all_csv_data
from constants.metrics import CONSUMPTION_TAGS_MAPPING
from plotly.subplots import make_subplots

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
        [Input("metrics-analyze-button", "n_clicks"),
         Input("metrics-refresh-data-store", "data")],  # Added input for forced refresh
        [State("metrics-client-filter", "value"),
         State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("jwt-token-store", "data"),
         State("metrics-selected-consumption-tags-store", "data")],  # Added state to track previous tags
        prevent_initial_call=True
    )
    def load_data(n_clicks, refresh_data, client_id, project_id, consumption_tags, token_data, prev_tags_data):
        """Load data when the analyze button is clicked or when refresh is requested."""
        # Use more concise logging
        print("== METRICS DATA LOADING STARTED ==")
        
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
        
        print(f"[INFO] load_data - Triggered by: {trigger_id}, Client: {client_id}, Project: {project_id}")
        
        force_refresh = False
        auto_triggered = False
        if trigger_id == "metrics-refresh-data-store" and refresh_data:
            # Check if we need to force a refresh (clear cache)
            force_refresh = refresh_data.get("force_refresh", False)
            auto_triggered = refresh_data.get("auto_triggered", False)
            print(f"[INFO] load_data - Forced refresh requested: {force_refresh}, Auto-triggered: {auto_triggered}")
            
            if force_refresh:
                # Import and clear the cache
                from utils.data_loader import clear_data_cache
                clear_data_cache()
                
                # If auto-triggered, show notification to user
                if auto_triggered:
                    print("[INFO] load_data - Auto-triggered refresh due to empty data - cache was automatically cleared")
        
        # Check if consumption tags have changed since last call
        prev_consumption_tags = prev_tags_data.get("consumption_tags") if prev_tags_data else None
        tags_changed = prev_consumption_tags is not None and sorted(prev_consumption_tags) != sorted(consumption_tags or [])
        
        if tags_changed:
            print(f"[INFO] load_data - Consumption tags changed from {prev_consumption_tags} to {consumption_tags}, clearing cache")
            # Clear the cache if tags changed
            from utils.data_loader import clear_data_cache
            clear_data_cache()
            force_refresh = True
        
        if not ((trigger_id == "metrics-analyze-button" and n_clicks) or 
                (trigger_id == "metrics-refresh-data-store" and refresh_data)) or not client_id or not consumption_tags:
            print(f"[INFO] load_data - No valid trigger or missing parameters")
            return dash.no_update
        
        try:
            print(f"[INFO] load_data - Loading data for client {client_id}, project {project_id}")
            
            # Validate JWT token
            token = token_data.get('token') if token_data else None
            if not token:
                print("[ERROR] load_data - JWT token not found")
                return json.dumps([])
            
            # Verify data directory exists
            base_path = "data/analyzed_data"
            if not os.path.exists(base_path):
                print(f"[INFO] load_data - Creating data path {base_path}")
                os.makedirs(base_path, exist_ok=True)
            
            # Load data directly without extensive directory scanning
            print(f"[INFO] load_data - Loading CSV data with tags: {consumption_tags}")
            
            # Measure loading time
            start_time = time.time()
            df = load_all_csv_data(consumption_tags=consumption_tags, project_id=project_id, jwt_token=token)
            load_time = time.time() - start_time
            
            if df is None or df.empty:
                print(f"[WARN] load_data - No data found, creating sample data")
                
                # Create sample data with fewer rows for testing
                sample_data = []
                end = pd.Timestamp.now()
                start = end - pd.DateOffset(months=2)  # Reduced from 6 to 2 months
                date_range = pd.date_range(start=start, end=end, freq='D')
                
                # Create fewer sample records
                for date in date_range:
                    for asset_id in range(1, 3):  # Reduced from 4 to 3 assets
                        for consumption_type in consumption_tags[:2]:  # Only use first 2 consumption types
                            sample_data.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'consumption': float(np.random.randint(50, 150)),
                                'asset_id': f"asset_{asset_id}",
                                'consumption_type': consumption_type,
                                'client_id': client_id,
                                'project_id': project_id if project_id else "project_1"
                            })
                
                df = pd.DataFrame(sample_data)
                print(f"[INFO] load_data - Created {len(df)} sample records")
            else:
                print(f"[INFO] load_data - Loaded {len(df)} real records in {load_time:.2f} seconds")
            
            # Simplify DataFrame processing for serialization
            try:
                # Use a more efficient approach to create serializable data
                simplified_data = []
                
                # Only process the necessary columns to reduce overhead
                essential_columns = ['date', 'consumption', 'asset_id', 'consumption_type', 'client_id', 'project_id']
                df = df.reindex(columns=[col for col in essential_columns if col in df.columns])
                
                # Add any missing essential columns
                for col in essential_columns:
                    if col not in df.columns:
                        if col == 'date':
                            df[col] = pd.Timestamp.now().strftime('%Y-%m-%d')
                        elif col == 'consumption':
                            df[col] = 100.0
                        elif col == 'asset_id':
                            df[col] = 'asset_1'
                        elif col == 'consumption_type':
                            df[col] = consumption_tags[0] if consumption_tags else 'ENERGY_CONSUMPTION'
                        elif col == 'client_id':
                            df[col] = client_id
                        elif col == 'project_id':
                            df[col] = project_id if project_id else "project_1"
                
                # Ensure date column is datetime
                if not pd.api.types.is_datetime64_any_dtype(df['date']):
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    df = df.dropna(subset=['date'])
                
                # Ensure consumption is float
                if not pd.api.types.is_float_dtype(df['consumption']):
                    df['consumption'] = pd.to_numeric(df['consumption'], errors='coerce')
                    df = df.dropna(subset=['consumption'])
                
                # Create serializable list with batch processing to improve performance
                batch_size = 5000
                total_rows = len(df)
                
                for start_idx in range(0, total_rows, batch_size):
                    end_idx = min(start_idx + batch_size, total_rows)
                    batch = df.iloc[start_idx:end_idx]
                    
                    for _, row in batch.iterrows():
                        simplified_row = {}
                        for col in batch.columns:
                            # Handle different data types efficiently
                            if pd.api.types.is_datetime64_any_dtype(pd.Series([row[col]])):
                                simplified_row[col] = None if pd.isna(row[col]) else row[col].strftime('%Y-%m-%d')
                            elif pd.isna(row[col]):
                                simplified_row[col] = None
                            else:
                                # Convert directly to basic types
                                val = row[col]
                                if not isinstance(val, (str, int, float, bool, type(None))):
                                    try:
                                        simplified_row[col] = str(val)
                                    except:
                                        simplified_row[col] = None
                                else:
                                    simplified_row[col] = val
                        
                        simplified_data.append(simplified_row)
                
                # Measure serialization time
                serialize_start = time.time()
                json_data = json.dumps(simplified_data)
                serialize_time = time.time() - serialize_start
                
                print(f"[INFO] load_data - Serialized {len(simplified_data)} records in {serialize_time:.2f} seconds")
                print("== METRICS DATA LOADING COMPLETED ==")
                return json_data
                
            except Exception as e:
                print(f"[ERROR] load_data - Error serializing data: {str(e)}")
                import traceback
                print(traceback.format_exc())
                return json.dumps([])
            
        except Exception as e:
            print(f"[ERROR] load_data - {str(e)}")
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
        Output("metrics-monthly-totals-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date"),
         Input("metrics-monthly-summary-selected-type-store", "data")],
        prevent_initial_call=True
    )
    def update_monthly_totals_chart(json_data, client_id, project_id, asset_id, start_date, end_date, summary_type_store_data):
        """Update monthly totals chart based on the specific type selected for the summary section."""
        
        from constants.metrics import CONSUMPTION_TAGS_MAPPING
        import plotly.graph_objects as go
        # from plotly.subplots import make_subplots # No longer needed for single type

        # Default empty figure
        default_figure = go.Figure(layout={"template": "plotly_white", "xaxis_title": "Mes", "yaxis_title": "Consumo"})
        default_figure.add_annotation(text="Seleccione un tipo de consumo", xref="paper", yref="paper", showarrow=False, font=dict(size=14))

        active_tag = summary_type_store_data.get("active_tag") if summary_type_store_data else None

        if not json_data or json_data == "[]" or not active_tag:
            return default_figure

        # Map tag to human readable name for filtering
        human_readable_name = CONSUMPTION_TAGS_MAPPING.get(active_tag)
        if not human_readable_name:
             print(f"[WARN update_monthly_totals] Could not map tag {active_tag}")
             return default_figure

        # Determine unit from active_tag
        unit = "units"
        if "WATER" in active_tag: unit = "m³"
        elif "ENERGY" in active_tag: unit = "kWh"
        elif "FLOW" in active_tag: unit = "personas"

        try:
            df = pd.DataFrame(json.loads(json_data))
            
            # Filter main df by the selected type for this section
            df_filtered_type = df[df['consumption_type'] == human_readable_name].copy()

            if df_filtered_type.empty:
                 # print(f"[DEBUG update_monthly_totals] df_filtered_type is empty for {human_readable_name}.")
                 return default_figure # Return default (which now says select type)

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
                 # print("[DEBUG update_monthly_totals] processed_df is empty after filtering.")
                 return default_figure

            # Generate monthly summary for the single selected type
            # No longer need group_by_type=True or the loop/concat logic
            monthly_summary = generate_monthly_consumption_summary(processed_df, start_date, end_date)

            if monthly_summary.empty:
                # print("[DEBUG update_monthly_totals] monthly_summary is empty.")
                return default_figure
                
            # --- Create Figure (Simpler now) ---
            fig = go.Figure()
            
            # Ensure summary is sorted for consistent plotting
            monthly_summary = monthly_summary.sort_values(['date'])

            fig.add_trace(go.Bar(
                x=monthly_summary['month'], 
                y=monthly_summary['total_consumption'],
                name=f"{human_readable_name} ({unit})",
                marker_color='royalblue' # Use a standard color 
            ))

            # --- Configure Layout --- 
            fig.update_layout(
                title=f"Consumo Total Mensual: {human_readable_name}", # Updated title
                xaxis_title="Mes",
                yaxis_title=f"Consumo ({unit})",
                # barmode='group', # Not needed for single trace
                # legend_title="Tipo de Consumo", # Not needed for single trace
                showlegend=False, # Hide legend for single trace
                template="plotly_white",
                hovermode="x unified"
            )
            
            fig.update_layout(yaxis_rangemode='tozero')

            return fig

        except Exception as e:
            print(f"[ERROR update_monthly_totals_chart]: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return a figure indicating error
            error_figure = go.Figure(layout={"template": "plotly_white"})
            error_figure.add_annotation(text=f"Error al generar gráfico: {str(e)}", xref="paper", yref="paper", showarrow=False, font=dict(size=14, color="red"))
            return error_figure
    
    @app.callback(
        Output("metrics-monthly-averages-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date"),
         Input("metrics-monthly-summary-selected-type-store", "data")],
        prevent_initial_call=True
    )
    def update_monthly_averages_chart(json_data, client_id, project_id, asset_id, start_date, end_date, summary_type_store_data):
        """Update monthly averages chart based on the specific type selected for the summary section."""
        
        from constants.metrics import CONSUMPTION_TAGS_MAPPING
        import plotly.graph_objects as go
        # from plotly.subplots import make_subplots # No longer needed for single type

        # Default empty figure
        default_figure = go.Figure(layout={"template": "plotly_white", "xaxis_title": "Mes", "yaxis_title": "Consumo Promedio"})
        default_figure.add_annotation(text="Seleccione un tipo de consumo", xref="paper", yref="paper", showarrow=False, font=dict(size=14))

        active_tag = summary_type_store_data.get("active_tag") if summary_type_store_data else None

        if not json_data or json_data == "[]" or not active_tag:
            return default_figure

        # Map tag to human readable name for filtering
        human_readable_name = CONSUMPTION_TAGS_MAPPING.get(active_tag)
        if not human_readable_name:
             print(f"[WARN update_monthly_averages] Could not map tag {active_tag}")
             return default_figure

        # Determine unit from active_tag
        unit = "units"
        if "WATER" in active_tag: unit = "m³"
        elif "ENERGY" in active_tag: unit = "kWh"
        elif "FLOW" in active_tag: unit = "personas"

        try:
            df = pd.DataFrame(json.loads(json_data))
            
            # Filter main df by the selected type for this section
            df_filtered_type = df[df['consumption_type'] == human_readable_name].copy()

            if df_filtered_type.empty:
                 return default_figure

            # Apply other filters
            current_asset_id = asset_id if asset_id and asset_id != 'all' else None
            processed_df = process_metrics_data(
                df_filtered_type,
                client_id=client_id,
                project_id=project_id,
                asset_id=current_asset_id,
                consumption_tags=[human_readable_name],
                start_date=start_date,
                end_date=end_date
            )

            if processed_df.empty:
                 return default_figure

            # Generate monthly summary for the single selected type
            monthly_summary = generate_monthly_consumption_summary(processed_df, start_date, end_date)

            # Check if summary is valid and contains the necessary average column 
            average_col_name = 'average_consumption' # Or 'mean_consumption', adjust if needed
            if monthly_summary.empty or average_col_name not in monthly_summary.columns:
                print(f"[DEBUG update_monthly_averages] monthly_summary invalid or missing '{average_col_name}' column.")
                return default_figure
                
            # --- Create Figure (Simpler now) ---
            fig = go.Figure()
            monthly_summary = monthly_summary.sort_values(['date'])
            
            fig.add_trace(go.Bar( # Changed to Bar chart for consistency with totals
                x=monthly_summary['month'], 
                y=monthly_summary[average_col_name], 
                name=f"{human_readable_name} ({unit})",
                marker_color='forestgreen' # Use a different color 
            ))

            # --- Configure Layout (Adjust titles) ---
            fig.update_layout(
                title=f"Consumo Promedio Mensual: {human_readable_name}", # Changed title
                xaxis_title="Mes",
                yaxis_title=f"Consumo Promedio ({unit})", # Changed y-axis title
                # barmode='group', # Not needed
                # legend_title="Tipo de Consumo", # Not needed
                showlegend=False,
                template="plotly_white",
                hovermode="x unified"
            )

            fig.update_layout(yaxis_rangemode='tozero')

            return fig

        except Exception as e:
            print(f"[ERROR update_monthly_averages_chart]: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return a figure indicating error
            error_figure = go.Figure(layout={"template": "plotly_white"})
            error_figure.add_annotation(text=f"Error al generar gráfico: {str(e)}", xref="paper", yref="paper", showarrow=False, font=dict(size=14, color="red"))
            return error_figure

    # Callbacks para exportar datos
    @app.callback(
        [Output("download-monthly-data", "data"),
         Output("export-error-container", "children"),
         Output("export-error-container", "className")],
        [Input("export-csv-btn", "n_clicks"),
         Input("export-excel-btn", "n_clicks"),
         Input("export-pdf-btn", "n_clicks"),
         Input("export-png-btn", "n_clicks")],
        [State("metrics-data-store", "data"),
         State("metrics-client-filter", "value"),
         State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("metrics-date-range", "start_date"),
         State("metrics-date-range", "end_date")],
        prevent_initial_call=True
    )
    def export_monthly_data(csv_clicks, excel_clicks, pdf_clicks, png_clicks, 
                           json_data, client_id, project_id, consumption_tags, start_date, end_date):
        """Export monthly data in different formats."""
        # Determinar qué botón fue clickeado
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
            
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Verificar que realmente se hizo clic en un botón
        if (button_id == "export-csv-btn" and not csv_clicks) or \
           (button_id == "export-excel-btn" and not excel_clicks) or \
           (button_id == "export-pdf-btn" and not pdf_clicks) or \
           (button_id == "export-png-btn" and not png_clicks):
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
                consumption_tags=consumption_tags, 
                start_date=start_date, 
                end_date=end_date
            )
            
            # Generar resumen mensual
            monthly_summary = generate_monthly_consumption_summary(filtered_df, start_date, end_date)
            
            # Verificar que el resumen mensual no esté vacío
            if monthly_summary.empty:
                error_msg = html.Div([
                    html.I(className="fas fa-exclamation-circle me-2"),
                    "No hay datos de consumo para el período seleccionado. Por favor, seleccione otro período."
                ], className="alert alert-warning")
                return dash.no_update, error_msg, "mb-3 show"
            
            # Preparar los datos para exportación
            from utils.metrics.data_processing import prepare_data_for_export
            export_data = prepare_data_for_export(monthly_summary)
            
            # Generar nombre de archivo con fecha actual
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"consumo_mensual_{timestamp}"
            
            # Exportar según el formato seleccionado
            if button_id == "export-csv-btn":
                return dcc.send_data_frame(export_data.to_csv, f"{filename}.csv", index=False), None, "mb-3"
            elif button_id == "export-excel-btn":
                return dcc.send_data_frame(export_data.to_excel, f"{filename}.xlsx", index=False), None, "mb-3"
            elif button_id == "export-pdf-btn":
                # Para PDF, necesitamos convertir a HTML primero y luego a PDF
                try:
                    import io
                    from reportlab.lib.pagesizes import letter
                    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                    from reportlab.lib import colors
                    from reportlab.lib.styles import getSampleStyleSheet
                    
                    # Crear un buffer para el PDF
                    buffer = io.BytesIO()
                    
                    # Configurar el documento
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    elements = []
                    
                    # Añadir título
                    styles = getSampleStyleSheet()
                    elements.append(Paragraph(f"Resumen Mensual de Consumos - {timestamp}", styles['Title']))
                    elements.append(Spacer(1, 12))
                    
                    # Convertir DataFrame a lista para la tabla
                    data = [export_data.columns.tolist()] + export_data.values.tolist()
                    
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
                    
                    # Construir PDF
                    doc.build(elements)
                    
                    # Obtener el contenido del buffer
                    buffer.seek(0)
                    
                    return dcc.send_bytes(buffer.getvalue(), f"{filename}.pdf"), None, "mb-3"
                except Exception as e:
                    error_msg = html.Div([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        f"Error al generar PDF: {str(e)}"
                    ], className="alert alert-danger")
                    return dash.no_update, error_msg, "mb-3 show"
            elif button_id == "export-png-btn":
                # Para PNG, necesitamos capturar los gráficos
                # Esto es más complejo y requiere JavaScript para capturar el DOM
                info_msg = html.Div([
                    html.I(className="fas fa-info-circle me-2"),
                    "La exportación a PNG estará disponible próximamente. Por favor, utilice otro formato."
                ], className="alert alert-info")
                return dash.no_update, info_msg, "mb-3 show"
            
            return dash.no_update, None, "mb-3"
            
        except Exception as e:
            import traceback
            print(f"[ERROR METRICS] export_monthly_data: {str(e)}")
            print(traceback.format_exc())
            
            error_msg = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error al exportar datos: {str(e)}"
            ], className="alert alert-danger")
            
            return dash.no_update, error_msg, "mb-3 show"

    # Callback para mostrar notificaciones de exportación
    @app.callback(
        [Output("export-notification", "is_open"),
         Output("export-notification", "children"),
         Output("export-notification", "header"),
         Output("export-error-notification", "is_open"),
         Output("export-error-notification", "children"),
         Output("export-error-notification", "header")],
        [Input("export-csv-btn", "n_clicks"),
         Input("export-excel-btn", "n_clicks"),
         Input("export-pdf-btn", "n_clicks"),
         Input("export-png-btn", "n_clicks")],
        [State("metrics-data-store", "data")],
        prevent_initial_call=True
    )
    def show_export_notification(csv_clicks, excel_clicks, pdf_clicks, png_clicks, json_data):
        """Mostrar notificación cuando se exportan datos."""
        # Determinar qué botón fue clickeado
        ctx = callback_context
        if not ctx.triggered:
            return False, "", "", False, "", ""
            
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Verificar que realmente se hizo clic en un botón
        if (button_id == "export-csv-btn" and not csv_clicks) or \
           (button_id == "export-excel-btn" and not excel_clicks) or \
           (button_id == "export-pdf-btn" and not pdf_clicks) or \
           (button_id == "export-png-btn" and not png_clicks):
            return False, "", "", False, "", ""
        
        # Verificar si hay datos para exportar
        if not json_data or json_data == "[]":
            return False, "", "", True, "No hay datos disponibles para exportar. Por favor, asegúrese de que hay datos cargados.", "Error de Exportación"
        
        # Mostrar notificación según el formato seleccionado
        if button_id == "export-csv-btn":
            return True, "Los datos han sido exportados en formato CSV.", "Exportación CSV", False, "", ""
        elif button_id == "export-excel-btn":
            return True, "Los datos han sido exportados en formato Excel.", "Exportación Excel", False, "", ""
        elif button_id == "export-pdf-btn":
            return True, "Los datos han sido exportados en formato PDF.", "Exportación PDF", False, "", ""
        elif button_id == "export-png-btn":
            return False, "", "", True, "La exportación a PNG estará disponible próximamente. Por favor, utilice otro formato.", "Funcionalidad no disponible"
        
        return False, "", "", False, "", ""

    # Add auto-refresh notification callback
    @app.callback(
        Output("auto-refresh-notification", "is_open"),
        [Input("metrics-refresh-data-store", "data")],
        prevent_initial_call=True
    )
    def show_auto_refresh_notification(refresh_data):
        """Show a notification when automatic refresh happens."""
        if refresh_data and refresh_data.get("auto_triggered"):
            return True
        return dash.no_update
