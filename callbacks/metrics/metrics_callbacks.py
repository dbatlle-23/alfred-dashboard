from dash import Output, Input, State, callback_context, html
import dash
import json
import pandas as pd
from datetime import datetime, timedelta

from utils.metrics.data_processing import process_metrics_data

def register_metrics_callbacks(app):
    """Register callbacks for metrics."""
    
    @app.callback(
        [Output("metrics-total-consumption", "children"),
         Output("metrics-total-consumption-unit", "children"),
         Output("metrics-daily-average", "children"),
         Output("metrics-daily-average-unit", "children"),
         Output("metrics-trend", "children"),
         Output("metrics-trend-period", "children"),
         Output("metrics-trend", "className")],
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_metrics(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        """Update metrics based on selected filters."""
        if not json_data or json_data == "[]":
            return "0", "", "0", "", "0%", "", "h3"
        
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
            
            if filtered_df.empty:
                return "0", "", "0", "", "0%", "", "h3"
            
            # Asegurarse de que la fecha es datetime
            filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            
            # Obtener el mes actual (último mes en los datos)
            current_month = filtered_df['date'].max().strftime('%Y-%m')
            
            # Filtrar datos solo para el mes actual
            current_month_df = filtered_df[filtered_df['date'].dt.strftime('%Y-%m') == current_month]
            
            # Si no hay datos para el mes actual, usar todos los datos
            if current_month_df.empty:
                current_month_df = filtered_df
                current_month = "todos los meses"
            
            # Calcular consumo total del mes para todo el proyecto
            if 'consumption' in current_month_df.columns:
                total_consumption = current_month_df['consumption'].sum()
            elif 'value' in current_month_df.columns:
                total_consumption = current_month_df['value'].sum()
            else:
                total_consumption = 0
            
            # Determinar la unidad
            unit = ""
            if consumption_tags and len(consumption_tags) == 1:
                # Si solo hay un tipo de consumo, usar su unidad
                consumption_type = consumption_tags[0]
                if "WATER" in consumption_type:
                    unit = "m³"
                elif "ENERGY" in consumption_type:
                    unit = "kWh"
                elif "FLOW" in consumption_type:
                    unit = "personas"
            else:
                # Si hay múltiples tipos, usar unidades mixtas
                unit = "unidades"
            
            # Calcular promedio por activo (consumo total dividido por número de activos)
            unique_assets = current_month_df['asset_id'].nunique() if 'asset_id' in current_month_df.columns else 1
            average_per_asset = total_consumption / unique_assets if unique_assets > 0 else 0
            
            # Calcular tendencia (comparación con el mes anterior)
            # Obtener el mes anterior
            if 'date' in filtered_df.columns:
                all_months = sorted(filtered_df['date'].dt.strftime('%Y-%m').unique())
                if len(all_months) > 1 and current_month in all_months:
                    current_month_index = all_months.index(current_month)
                    if current_month_index > 0:
                        previous_month = all_months[current_month_index - 1]
                        previous_month_df = filtered_df[filtered_df['date'].dt.strftime('%Y-%m') == previous_month]
                        
                        # Calcular consumo del mes anterior
                        if 'consumption' in previous_month_df.columns:
                            previous_consumption = previous_month_df['consumption'].sum()
                        elif 'value' in previous_month_df.columns:
                            previous_consumption = previous_month_df['value'].sum()
                        else:
                            previous_consumption = 0
                        
                        # Calcular tendencia
                        if previous_consumption > 0:
                            trend_pct = ((total_consumption - previous_consumption) / previous_consumption) * 100
                        else:
                            trend_pct = 0
                        
                        trend_period = f"vs. {previous_month}"
                    else:
                        trend_pct = 0
                        trend_period = "Sin datos previos"
                else:
                    trend_pct = 0
                    trend_period = "Sin datos previos"
            else:
                trend_pct = 0
                trend_period = "Sin datos de fecha"
            
            # Determinar clase CSS para la tendencia
            trend_class = "h3 text-success" if trend_pct < 0 else "h3 text-danger" if trend_pct > 0 else "h3"
            
            # Formatear valores
            total_formatted = f"{total_consumption:.2f}"
            avg_per_asset_formatted = f"{average_per_asset:.2f}"
            trend_formatted = f"{trend_pct:.1f}%"
            
            return total_formatted, unit, avg_per_asset_formatted, unit, trend_formatted, trend_period, trend_class
            
        except Exception as e:
            print(f"[ERROR METRICS] update_metrics: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return "0", "", "0", "", "0%", "", "h3"
    
    @app.callback(
        Output("metrics-filter-indicator", "children"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-period", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")],
        [State("jwt-token-store", "data")]
    )
    def update_filter_indicator(json_data, client_id, project_id, asset_id, consumption_tags, date_period, start_date, end_date, token_data):
        """Update filter indicator based on selected filters."""
        if not json_data or json_data == "[]":
            return ""
        
        try:
            # Obtener nombres de clientes y proyectos
            from utils.api import get_clientes, get_projects
            
            # Obtener el token JWT
            token = token_data.get('token') if token_data else None
            
            if not token:
                return ""
            
            # Obtener cliente
            client_name = "Cliente seleccionado"
            clientes = get_clientes(jwt_token=token)
            if clientes and isinstance(clientes, list):
                for client in clientes:
                    if isinstance(client, dict) and client.get('id') == client_id:
                        for key in ['nombre', 'name', 'client_name', 'nombre_cliente']:
                            if key in client and client[key]:
                                client_name = client[key]
                                break
            
            # Obtener proyecto
            project_name = "Todos los proyectos"
            if project_id and project_id != "all":
                projects = get_projects(client_id=client_id, jwt_token=token)
                if projects and isinstance(projects, list):
                    for project in projects:
                        if isinstance(project, dict) and project.get('id') == project_id:
                            for key in ['nombre', 'name', 'project_name', 'nombre_proyecto']:
                                if key in project and project[key]:
                                    project_name = project[key]
                                    break
            
            # Obtener activo
            asset_text = "Todos los activos"
            if asset_id and asset_id != "all":
                asset_text = f"Activo: {asset_id}"
            
            # Obtener tipos de consumo
            from constants.metrics import CONSUMPTION_TAGS_MAPPING
            consumption_types = []
            if consumption_tags:
                for tag in consumption_tags:
                    consumption_types.append(CONSUMPTION_TAGS_MAPPING.get(tag, tag))
            
            consumption_text = ", ".join(consumption_types) if consumption_types else "Ninguno"
            
            # Obtener período
            period_text = ""
            if date_period == "last_month":
                period_text = "Último mes"
            elif date_period == "last_3_months":
                period_text = "Últimos 3 meses"
            elif date_period == "last_year":
                period_text = "Último año"
            elif date_period == "custom":
                start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d/%m/%Y") if start_date else ""
                end = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d/%m/%Y") if end_date else ""
                period_text = f"{start} - {end}"
            
            # Crear indicador de filtros
            return html.Div([
                html.Strong("Filtros aplicados: "),
                html.Span(f"Cliente: {client_name} | Proyecto: {project_name} | {asset_text} | Consumos: {consumption_text} | Período: {period_text}")
            ], className="alert alert-info")
            
        except Exception as e:
            print(f"[ERROR METRICS] update_filter_indicator: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return "" 
    
    @app.callback(
        Output("metrics-update-readings-result", "children"),
        [Input("metrics-update-readings-button", "n_clicks")],
        [State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def update_readings(n_clicks, project_id, consumption_tags, token_data):
        """Update readings when the update button is clicked."""
        if not n_clicks:
            return ""
        
        if not project_id or project_id == "all":
            return html.Div([
                html.P("Debe seleccionar un proyecto específico para actualizar las lecturas.", className="text-danger")
            ])
        
        if not consumption_tags or len(consumption_tags) == 0:
            return html.Div([
                html.P("Debe seleccionar al menos un tipo de consumo para actualizar las lecturas.", className="text-danger")
            ])
        
        # Obtener el token JWT si está disponible
        token = None
        if token_data and "token" in token_data:
            token = token_data["token"]
        
        # Llamar a la función para actualizar las lecturas
        from utils.api import get_daily_readings_for_year_multiple_tags_project_parallel
        
        try:
            print(f"[INFO] Actualizando lecturas para proyecto {project_id}, tags {consumption_tags}")
            result = get_daily_readings_for_year_multiple_tags_project_parallel(project_id, consumption_tags, token=token)
            
            if result.get("success", False):
                return html.Div([
                    html.P(result.get("message", "Lecturas actualizadas con éxito"), className="text-success"),
                    html.P(f"Total de assets: {result.get('total_assets', 0)}", className="text-info"),
                    html.P(f"Assets procesados con éxito: {result.get('success_count', 0)}", className="text-info"),
                    html.P(f"Assets con errores: {result.get('error_count', 0)}", className="text-info"),
                    html.Button("Actualizar datos", id="refresh-data-btn", className="btn btn-primary mt-2")
                ])
            else:
                return html.Div([
                    html.P(f"Error: {result.get('message', 'Error desconocido al actualizar lecturas')}", className="text-danger")
                ])
        except Exception as e:
            print(f"[ERROR] Error al actualizar lecturas: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return html.Div([
                html.P(f"Error: {str(e)}", className="text-danger")
            ])
    
    @app.callback(
        Output("metrics-data-store", "data", allow_duplicate=True),
        [Input("refresh-data-btn", "n_clicks")],
        [State("metrics-client-filter", "value"),
         State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def refresh_data_after_update(n_clicks, client_id, project_id, consumption_tags, token_data):
        """Refresh data after updating readings."""
        if not n_clicks:
            return dash.no_update
        
        # Obtener el token JWT si está disponible
        token = None
        if token_data and "token" in token_data:
            token = token_data["token"]
        
        try:
            # Importar la función para cargar datos
            from callbacks.metrics.chart_callbacks import load_data
            
            # Simular un clic en el botón de análisis para recargar los datos
            print(f"[INFO] Recargando datos para cliente {client_id}, proyecto {project_id}, tags {consumption_tags}")
            
            # Llamar directamente a la función load_data
            from utils.data_loader import load_all_csv_data
            
            # Cargar datos desde archivos CSV locales
            df = load_all_csv_data(consumption_tags=consumption_tags, project_id=project_id, jwt_token=token)
            
            if df is None or df.empty:
                print("[ERROR] No se encontraron datos en los archivos CSV")
                return dash.no_update
            
            # Asegurarse de que el DataFrame tiene las columnas necesarias
            required_columns = ['date', 'consumption', 'asset_id', 'consumption_type']
            if not all(col in df.columns for col in required_columns):
                print(f"[ERROR] Faltan columnas requeridas. Columnas disponibles: {df.columns.tolist()}")
                return dash.no_update
            
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
                
                # Convertir a JSON
                json_data = json.dumps(simplified_data)
                
                print(f"[INFO] Se cargaron {len(df)} registros desde archivos CSV")
                return json_data
            except Exception as e:
                print(f"[ERROR] Error al serializar a JSON: {str(e)}")
                import traceback
                print(traceback.format_exc())
                return dash.no_update
            
        except Exception as e:
            print(f"[ERROR] Error al refrescar datos: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return dash.no_update 