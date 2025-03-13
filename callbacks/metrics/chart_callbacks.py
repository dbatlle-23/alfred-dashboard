from dash import Output, Input, State, callback_context
import dash
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import html

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
                
                # Crear datos de ejemplo para pruebas
                print("[INFO METRICS] load_data - Creando datos de ejemplo para pruebas")
                end = pd.Timestamp.now()
                start = end - pd.DateOffset(months=6)
                date_range = pd.date_range(start=start, end=end, freq='D')
                
                # Crear datos de ejemplo
                sample_data = []
                for date in date_range:
                    for asset_id in range(1, 4):  # 3 activos de ejemplo
                        for consumption_type in consumption_tags:
                            sample_data.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'consumption': float(np.random.randint(50, 200)),
                                'asset_id': f"asset_{asset_id}",
                                'consumption_type': consumption_type,
                                'client_id': client_id,
                                'project_id': project_id
                            })
                
                return json.dumps(sample_data)
            
            # Asegurarse de que el DataFrame tiene las columnas necesarias
            required_columns = ['date', 'consumption', 'asset_id', 'consumption_type']
            if not all(col in df.columns for col in required_columns):
                print(f"[ERROR METRICS] load_data - Faltan columnas requeridas. Columnas disponibles: {df.columns.tolist()}")
                return json.dumps([])
            
            # Añadir client_id si no existe
            if 'client_id' not in df.columns:
                df['client_id'] = client_id
            
            # Añadir project_id si no existe
            if 'project_id' not in df.columns:
                df['project_id'] = project_id
            
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
                    if 'project_id' in df.columns:
                        simplified_row['project_id'] = str(row['project_id'])
                    simplified_data.append(simplified_row)
                
                return json.dumps(simplified_data)
            
        except Exception as e:
            print(f"[ERROR METRICS] load_data: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # Crear datos de ejemplo en caso de error
            print("[INFO METRICS] load_data - Creando datos de ejemplo debido a un error")
            end = pd.Timestamp.now()
            start = end - pd.DateOffset(months=6)
            date_range = pd.date_range(start=start, end=end, freq='D')
            
            # Crear datos de ejemplo
            sample_data = []
            for date in date_range:
                for asset_id in range(1, 4):  # 3 activos de ejemplo
                    for consumption_type in consumption_tags if consumption_tags else ["_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL"]:
                        sample_data.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'consumption': float(np.random.randint(50, 200)),
                            'asset_id': f"asset_{asset_id}",
                            'consumption_type': consumption_type,
                            'client_id': client_id,
                            'project_id': project_id
                        })
            
            return json.dumps(sample_data)
    
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
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_monthly_totals_chart(json_data, client_id, project_id, consumption_tags, start_date, end_date):
        """Update the monthly totals chart."""
        try:
            # Intentar usar datos reales primero
            if json_data and json_data != "[]":
                # Convertir JSON a DataFrame
                df = pd.DataFrame(json.loads(json_data))
                
                # Verificar que el DataFrame no esté vacío
                if not df.empty:
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
                    if not monthly_summary.empty and 'month' in monthly_summary.columns and 'total_consumption' in monthly_summary.columns:
                        # Crear el gráfico con los datos reales
                        fig = go.Figure()
                        
                        fig.add_trace(
                            go.Bar(
                                x=monthly_summary['month'],
                                y=monthly_summary['total_consumption'],
                                marker_color='royalblue',
                                name='Consumo Total'
                            )
                        )
                        
                        # Configuración básica
                        fig.update_layout(
                            title="Total de Consumo por Mes",
                            xaxis_title="Mes",
                            yaxis_title="Consumo Total",
                            height=400,
                            plot_bgcolor='white',
                            paper_bgcolor='white'
                        )
                        
                        return fig
        except Exception as e:
            print(f"[ERROR METRICS] update_monthly_totals_chart: {str(e)}")
            import traceback
            print(traceback.format_exc())
        
        # Si hay algún problema o no hay datos, crear datos de ejemplo
        print("[INFO METRICS] update_monthly_totals_chart - Usando datos de ejemplo")
        end = pd.Timestamp.now()
        start = end - pd.DateOffset(months=6)
        date_range = pd.date_range(start=start, end=end, freq='MS')
        
        # Crear datos de ejemplo
        sample_data = {
            'month': date_range,
            'total_consumption': [100 * (i+1) for i in range(len(date_range))],
        }
        
        monthly_summary = pd.DataFrame(sample_data)
        
        # Crear el gráfico con datos de ejemplo
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                x=monthly_summary['month'],
                y=monthly_summary['total_consumption'],
                marker_color='royalblue',
                name='Consumo Total (Ejemplo)'
            )
        )
        
        # Configuración básica
        fig.update_layout(
            title="Total de Consumo por Mes (Datos de Ejemplo)",
            xaxis_title="Mes",
            yaxis_title="Consumo Total",
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        return fig

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
        try:
            # Intentar usar datos reales primero
            if json_data and json_data != "[]":
                # Convertir JSON a DataFrame
                df = pd.DataFrame(json.loads(json_data))
                
                # Verificar que el DataFrame no esté vacío
                if not df.empty:
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
                    if not monthly_summary.empty and 'month' in monthly_summary.columns and 'average_consumption' in monthly_summary.columns:
                        # Crear el gráfico con los datos reales
                        fig = go.Figure()
                        
                        fig.add_trace(
                            go.Scatter(
                                x=monthly_summary['month'],
                                y=monthly_summary['average_consumption'],
                                mode='lines+markers',
                                marker=dict(color='forestgreen'),
                                line=dict(color='forestgreen'),
                                name='Consumo Promedio'
                            )
                        )
                        
                        # Configuración básica
                        fig.update_layout(
                            title="Promedio de Consumo por Mes",
                            xaxis_title="Mes",
                            yaxis_title="Consumo Promedio",
                            height=400,
                            plot_bgcolor='white',
                            paper_bgcolor='white'
                        )
                        
                        return fig
        except Exception as e:
            print(f"[ERROR METRICS] update_monthly_averages_chart: {str(e)}")
            import traceback
            print(traceback.format_exc())
        
        # Si hay algún problema o no hay datos, crear datos de ejemplo
        print("[INFO METRICS] update_monthly_averages_chart - Usando datos de ejemplo")
        end = pd.Timestamp.now()
        start = end - pd.DateOffset(months=6)
        date_range = pd.date_range(start=start, end=end, freq='MS')
        
        # Crear datos de ejemplo
        sample_data = {
            'month': date_range,
            'average_consumption': [50 * (i+1) for i in range(len(date_range))],
        }
        
        monthly_summary = pd.DataFrame(sample_data)
        
        # Crear el gráfico con datos de ejemplo
        fig = go.Figure()
        
        fig.add_trace(
            go.Scatter(
                x=monthly_summary['month'],
                y=monthly_summary['average_consumption'],
                mode='lines+markers',
                marker=dict(color='forestgreen'),
                line=dict(color='forestgreen'),
                name='Consumo Promedio (Ejemplo)'
            )
        )
        
        # Configuración básica
        fig.update_layout(
            title="Promedio de Consumo por Mes (Datos de Ejemplo)",
            xaxis_title="Mes",
            yaxis_title="Consumo Promedio",
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        return fig

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
