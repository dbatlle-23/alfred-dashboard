from dash import Output, Input, State, callback_context, html
import dash
import json
import pandas as pd
from datetime import datetime, timedelta
import locale
import dash_bootstrap_components as dbc

from utils.metrics.data_processing import process_metrics_data

def register_metrics_callbacks(app):
    """Register callbacks for metrics."""
    
    @app.callback(
        [Output("metrics-total-period-consumption", "children"),
         Output("metrics-total-period-consumption-unit", "children"),
         Output("metrics-monthly-average", "children"),
         Output("metrics-monthly-average-unit", "children"),
         Output("metrics-trend", "children"),
         Output("metrics-trend-period", "children"),
         Output("metrics-trend", "className"),
         Output("metrics-last-month-consumption", "children"),
         Output("metrics-last-month-name", "children"),
         Output("metrics-last-month-consumption-unit", "children"),
         Output("metrics-max-month-consumption", "children"),
         Output("metrics-max-month-name", "children"),
         Output("metrics-max-month-consumption-unit", "children"),
         Output("metrics-min-month-consumption", "children"),
         Output("metrics-min-month-name", "children"),
         Output("metrics-min-month-consumption-unit", "children")],
        [Input("metrics-data-store", "data"),
         Input("metrics-kpi-selected-type-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")],
        [State("jwt-token-store", "data")]
    )
    def update_metrics(json_data, kpi_type_store_data, client_id, project_id, asset_id, start_date, end_date, token_data):
        """Update metrics based on the single selected KPI type."""
        
        # Default empty values
        default_return = "0", "", "0", "", "0%", "", "h3", "0", "Sin datos", "", "0", "Sin datos", "", "0", "Sin datos", ""
        
        from constants.metrics import CONSUMPTION_TAGS_MAPPING

        active_tag = kpi_type_store_data.get("active_tag") if kpi_type_store_data else None
        
        if not json_data or json_data == "[]" or not active_tag:
            return default_return
        
        # --- NUEVO: Mapear el tag interno al nombre legible ---
        human_readable_name = CONSUMPTION_TAGS_MAPPING.get(active_tag)

        if not human_readable_name:
            print(f"[ERROR update_metrics] Could not map active_tag '{active_tag}' to a human-readable name.")
            return default_return # Si no se puede mapear, algo va mal
        # --- FIN NUEVO ---
        
        try:
            # Convertir JSON a DataFrame
            df = pd.DataFrame(json.loads(json_data))
            
            # 1. Filter using the HUMAN-READABLE NAME
            df_filtered_by_tag = df[df['consumption_type'] == human_readable_name].copy()
            
            if df_filtered_by_tag.empty:
                return default_return
            
            # 2. Process this TAG-SPECIFIC data further using other filters
            processed_df = process_metrics_data(
                df_filtered_by_tag,
                client_id=client_id,
                project_id=project_id,
                asset_id=asset_id,
                consumption_tags=[human_readable_name],
                start_date=start_date,
                end_date=end_date
            )
            
            if processed_df.empty:
                return default_return
            
            # 3. Determine Unit (Based only on active_tag - this part was correct)
            unit = ""
            # Use active_tag (internal name) for reliable unit determination
            if "WATER" in active_tag: 
                unit = "m³"
            elif "ENERGY" in active_tag:
                unit = "kWh"
            elif "FLOW" in active_tag:  # Assuming FLOW relates to people count
                 unit = "personas"
            else:
                # Fallback or default unit if needed
                unit = "units"
            
            # 4. Generate Monthly Summary ONLY from the fully processed data for the ACTIVE TAG
            from utils.metrics.data_processing import generate_monthly_consumption_summary
            # Pass processed_df which contains only data for the active tag AND other filters
            monthly_summary = generate_monthly_consumption_summary(processed_df, start_date, end_date)
            
            if monthly_summary.empty:
                return default_return
            
            # --- All subsequent calculations ONLY use monthly_summary ---
            # This summary was derived ONLY from data matching the active_tag
            
            monthly_summary = monthly_summary.sort_values('date')
            
            # 1. Consumo total del periodo
            total_period_consumption = monthly_summary['total_consumption'].sum()
            
            # 2. Promedio mensual
            monthly_average = monthly_summary['total_consumption'].mean()
            
            # 3. Último mes (mes más reciente en los datos)
            last_month_row = monthly_summary.iloc[-1]
            last_month = last_month_row['month']
            last_month_consumption = last_month_row['total_consumption']
            
            # 4. Máximo mensual
            max_month_idx = monthly_summary['total_consumption'].idxmax()
            max_month_row = monthly_summary.loc[max_month_idx]
            max_month = max_month_row['month']
            max_month_consumption = max_month_row['total_consumption']
            
            # 5. Mínimo mensual (excluyendo valores cero o negativos)
            positive_consumption = monthly_summary[monthly_summary['total_consumption'] > 0]
            if not positive_consumption.empty:
                min_month_idx = positive_consumption['total_consumption'].idxmin()
                min_month_row = monthly_summary.loc[min_month_idx]
            else:  # Handle case where all consumption is zero or negative
                min_month_idx = monthly_summary['total_consumption'].idxmin()
                min_month_row = monthly_summary.loc[min_month_idx]
            
            min_month = min_month_row['month']
            min_month_consumption = min_month_row['total_consumption']
            
            # 6. Calcular tendencia (comparación con el mes anterior)
            trend_pct = 0
            trend_period = "Sin datos previos"
            
            if len(monthly_summary) > 1:
                previous_month_row = monthly_summary.iloc[-2]
                previous_month = previous_month_row['month']
                previous_consumption = previous_month_row['total_consumption']
                
                try:
                    # Ensure numeric types for calculation
                    current = float(last_month_consumption)
                    previous = float(previous_consumption)
                    
                    if previous != 0:
                        # Use abs(previous) in denominator to handle potential negative values correctly
                        trend_pct = ((current - previous) / abs(previous)) * 100
                    elif current > 0:  # If previous is 0 and current is positive, trend is infinite positive
                        trend_pct = float('inf')
                    else:  # If previous is 0 and current is 0 or negative, trend is 0
                        trend_pct = 0
                except (ValueError, TypeError) as e:
                    print(f"Error calculating trend percentage: {str(e)}")
                    trend_pct = 0  # Default to 0 on error
                
                trend_period = f"vs. {previous_month}"
            
            # Determinar clase CSS para la tendencia (handle potential infinite trend)
            if trend_pct == float('inf'):
                trend_class = "h3 text-danger"  # Infinite increase is bad in consumption
                trend_formatted = "+∞%"
            elif trend_pct < 0:
                trend_class = "h3 text-success"  # Negative trend (reduction) is good
                trend_formatted = f"{trend_pct:.1f}%"
            elif trend_pct > 0:
                trend_class = "h3 text-danger"  # Positive trend is bad
                trend_formatted = f"+{trend_pct:.1f}%"
            else:
                trend_class = "h3"  # No change
                trend_formatted = "0.0%"
            
            # Formatear valores para mostrar
            total_period_formatted = f"{total_period_consumption:.2f}"
            monthly_average_formatted = f"{monthly_average:.2f}"
            last_month_formatted = f"{last_month_consumption:.2f}"
            max_month_formatted = f"{max_month_consumption:.2f}"
            min_month_formatted = f"{min_month_consumption:.2f}"
            
            # Formatear nombres de meses para mostrar
            # Intentar establecer el locale a español
            try:
                locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
            except:
                try:
                    locale.setlocale(locale.LC_TIME, 'es_ES')
                except:
                    try:
                        locale.setlocale(locale.LC_TIME, 'es')
                    except:
                        pass  # Si no se puede establecer el locale, se usará el predeterminado
            
            def format_month_name(month_str):
                try:
                    date = datetime.strptime(month_str, '%Y-%m')
                    month_name = date.strftime('%B %Y')
                    # Capitalizar primera letra
                    return month_name.capitalize()
                except:
                    return month_str
            
            last_month_name = format_month_name(last_month)
            max_month_name = format_month_name(max_month)
            min_month_name = format_month_name(min_month)
            
            return (
                total_period_formatted, unit,
                monthly_average_formatted, unit,
                trend_formatted, trend_period, trend_class,
                last_month_formatted, last_month_name, unit,
                max_month_formatted, max_month_name, unit,
                min_month_formatted, min_month_name, unit
            )
            
        except Exception as e:
            print(f"[ERROR METRICS] update_metrics: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return default_return
    
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
         State("metrics-date-period", "value"),
         State("metrics-date-range", "start_date"),
         State("metrics-date-range", "end_date"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def update_readings(n_clicks, project_id, consumption_tags, date_period, start_date, end_date, token_data):
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
        
        # Llamar a la función para actualizar las lecturas solo para el período seleccionado
        from utils.api import get_daily_readings_for_period_multiple_tags_project_parallel
        
        try:
            print(f"[INFO] Actualizando lecturas para proyecto {project_id}, tags {consumption_tags}, período: {start_date} a {end_date}")
            result = get_daily_readings_for_period_multiple_tags_project_parallel(
                project_id, 
                consumption_tags, 
                start_date, 
                end_date, 
                token=token
            )
            
            if result.get("success", False):
                # Formatear los meses procesados para su mejor visualización
                months_processed = result.get('months_processed', [])
                months_display = ", ".join(months_processed) if months_processed else "Ninguno"
                
                return dbc.Card([
                    dbc.CardHeader(html.H5([html.I(className="fas fa-check-circle me-2 text-success"), "Lecturas actualizadas con éxito"])),
                    dbc.CardBody([
                        html.P(result.get("message", "Lecturas actualizadas con éxito"), className="lead"),
                        dbc.Row([
                            dbc.Col([
                                html.Strong("Total de tareas:"),
                                html.Span(f" {result.get('total_tasks', 0)}", className="ms-2")
                            ], width=6),
                            dbc.Col([
                                html.Strong("Tareas exitosas:"),
                                html.Span(f" {result.get('success_count', 0)}", className="ms-2 text-success")
                            ], width=6)
                        ], className="mb-2"),
                        dbc.Row([
                            dbc.Col([
                                html.Strong("Tareas con errores:"),
                                html.Span(f" {result.get('error_count', 0)}", className="ms-2 text-danger")
                            ], width=6),
                            dbc.Col([
                                html.Strong("Meses procesados:"),
                                html.Span(f" {months_display}", className="ms-2")
                            ], width=6)
                        ], className="mb-3"),
                        dbc.Button([
                            html.I(className="fas fa-sync-alt me-2"),
                            "Actualizar visualización"
                        ], id="refresh-data-btn", color="primary", className="mt-2")
                    ])
                ], className="mb-4 shadow-sm border-success")
            else:
                return dbc.Card([
                    dbc.CardHeader(html.H5([html.I(className="fas fa-exclamation-circle me-2 text-danger"), "Error al actualizar lecturas"])),
                    dbc.CardBody([
                        html.P(result.get("message", "Error desconocido al actualizar lecturas"), className="lead text-danger"),
                        html.P("Por favor, verifique los parámetros e intente nuevamente.")
                    ])
                ], className="mb-4 shadow-sm border-danger")
        except Exception as e:
            print(f"[ERROR] Error al actualizar lecturas: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-exclamation-triangle me-2 text-danger"), "Error inesperado"])),
                dbc.CardBody([
                    html.P(f"Error: {str(e)}", className="lead text-danger"),
                    html.P("Por favor, contacte al administrador del sistema.")
                ])
            ], className="mb-4 shadow-sm border-danger")
    
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
                # Convertir a JSON
                try:
                    # Crear una lista de diccionarios simplificada
                    simplified_data = []
                    for _, row in df.iterrows():
                        simplified_row = {}
                        for col in df.columns:
                            # Manejar diferentes tipos de datos
                            if pd.api.types.is_datetime64_any_dtype(pd.Series([row[col]])):
                                # Verificar si el valor es NaT antes de aplicar strftime
                                if pd.isna(row[col]) or pd.isnull(row[col]):
                                    simplified_row[col] = None
                                else:
                                    simplified_row[col] = row[col].strftime('%Y-%m-%d')
                            elif hasattr(row[col], 'to_timestamp'):  # Para objetos Period
                                try:
                                    simplified_row[col] = row[col].to_timestamp().strftime('%Y-%m-%d')
                                except:
                                    # Si hay error al convertir el período, usar None
                                    simplified_row[col] = None
                            elif pd.isna(row[col]):
                                simplified_row[col] = None
                            else:
                                simplified_row[col] = row[col]
                        simplified_data.append(simplified_row)
                    
                    # Convertir a JSON
                    try:
                        json_data = json.dumps(simplified_data)
                        
                        print(f"[INFO] Se cargaron {len(df)} registros desde archivos CSV")
                        return json_data
                    except TypeError as e:
                        # Capturar error de tipos no serializables
                        print(f"[ERROR] Error de tipo al serializar a JSON: {str(e)}")
                        
                        # Intentar una segunda pasada con conversión más estricta
                        try:
                            # Convertir todos los valores problemáticos a str o None
                            for i, item in enumerate(simplified_data):
                                for key, value in list(item.items()):
                                    if not (isinstance(value, (str, int, float, bool, type(None)))):
                                        try:
                                            simplified_data[i][key] = str(value)
                                        except:
                                            simplified_data[i][key] = None
                            
                            json_data = json.dumps(simplified_data)
                            print(f"[INFO] Datos serializados a JSON en segunda pasada, {len(simplified_data)} registros")
                            return json_data
                        except Exception as e2:
                            print(f"[ERROR] Error en segunda pasada al serializar a JSON: {str(e2)}")
                            import traceback
                            print(traceback.format_exc())
                            return dash.no_update
                except Exception as e:
                    print(f"[ERROR] Error al crear lista simplificada: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    return dash.no_update
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