from dash import html, dcc, no_update
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash
from utils.db_utils import get_common_areas_bookings, get_unique_common_areas
import pandas as pd
from datetime import datetime
from utils.logging import get_logger
import math
import numpy as np
from utils.pdf_export import generate_spaces_report_pdf
import base64

# Configurar logger
logger = get_logger(__name__)

# Layout para la página de Spaces
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Gestión de Reservas de Espacios", className="mb-4"),
            html.P("Gestiona y monitorea las reservas de espacios comunes en tu organización.", className="lead mb-4"),
            
            # Indicador de filtro activo
            html.Div(id="spaces-filter-indicator", className="mb-3"),
            
            # Componentes ocultos para paginación
            dcc.Store(id="page-number", data=1),
            dcc.Store(id="rows-per-page", data=10),
            dcc.Store(id="weekly-occupation-data", data={}),  # Store para datos de ocupación semanal
            dcc.Store(id="spaces-reservations-data", data={}),  # Nuevo Store para datos de espacios por reservas
            
            # Tarjetas de resumen
            dbc.Row([
                # Resumen 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Reservas Totales", className="card-title text-center"),
                            html.H2(id="spaces-total", className="text-center text-primary mb-0"),
                            html.P(id="spaces-total-change", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Resumen 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Ocupación Actual", className="card-title text-center"),
                            html.H2(id="spaces-ocupacion", className="text-center text-primary mb-0"),
                            html.P(id="spaces-ocupacion-detail", className="text-muted text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Resumen 3
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Reservas Hoy", className="card-title text-center"),
                            html.H2(id="spaces-reservas", className="text-center text-primary mb-0"),
                            html.P(id="spaces-reservas-change", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
            ]),
            
            # Sección de filtros
            html.Div([
                html.H5("Filtros y Búsqueda", className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Tipo de Espacio"),
                        dbc.Select(
                                        id="space-type-filter",
                                        options=[
                                            {"label": "Todos", "value": "all"},
                                            {"label": "Sala de Reuniones", "value": "reunion"},
                                {"label": "Oficina", "value": "oficina"},
                                            {"label": "Espacio Común", "value": "comun"},
                                            {"label": "Almacén", "value": "almacen"}
                                        ],
                            value="all"
                                    )
                                ], md=4),
                                dbc.Col([
                        html.Label("Estado de Reserva"),
                        dbc.Select(
                                        id="space-status-filter",
                                        options=[
                                            {"label": "Todos", "value": "all"},
                                            {"label": "Disponible", "value": "disponible"},
                                            {"label": "Ocupado", "value": "ocupado"},
                                            {"label": "Reservado", "value": "reservado"},
                                {"label": "Cancelado", "value": "cancelado"}
                                        ],
                            value="all"
                                    )
                                ], md=4),
                                dbc.Col([
                                    html.Label("Capacidad Mínima"),
                                    dcc.Slider(
                                        id="space-capacity-filter",
                                        min=0,
                                        max=20,
                                        step=1,
                                        value=0,
                            marks={i: str(i) for i in range(0, 21, 5)}
                                    )
                    ], md=4)
                ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Búsqueda"),
                                    dbc.InputGroup([
                                        dbc.Input(id="space-search", placeholder="Buscar por nombre o ID..."),
                                        dbc.Button([html.I(className="fas fa-search")], color="primary")
                        ])
                                ], md=8),
                                dbc.Col([
                                    html.Label("Acciones"),
                        html.Div([
                            dbc.Button([html.I(className="fas fa-filter me-1"), "Aplicar Filtros"], id="apply-space-filters", color="primary", className="me-2"),
                            dbc.Button([html.I(className="fas fa-redo me-1"), "Reiniciar"], id="reset-space-filters", color="secondary", className="me-2"),
                            dbc.Button([html.I(className="fas fa-sync me-1"), "Actualizar"], id="refresh-spaces-button", color="success")
                        ], className="d-flex")
                    ], md=4)
                ], className="mb-4")
            ], className="p-3 bg-light rounded mb-4"),
            
            # Sección de análisis avanzado
            html.Div([
            dbc.Row([
                dbc.Col([
                        html.H5("Análisis Avanzado de Reservas", className="mb-3"),
                        html.P("Visualización de patrones de reserva y ocupación", className="text-muted mb-4")
                    ], md=8),
                    dbc.Col([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Período de Análisis"),
                                dcc.Dropdown(
                                    id="analysis-period",
                                    options=[
                                        {"label": "Última semana", "value": "last_week"},
                                        {"label": "Último mes", "value": "last_month"},
                                        {"label": "Último trimestre", "value": "last_quarter"},
                                        {"label": "Último año", "value": "last_year"},
                                        {"label": "Este año hasta hoy", "value": "this_year"},
                                        {"label": "Todo", "value": "all_time"}
                                    ],
                                    value="last_month",
                                    clearable=False
                                )
                            ], width=6),
                            dbc.Col([
                                html.Button(
                                    [html.I(className="fas fa-file-pdf mr-2"), "Exportar a PDF"],
                                    id="export-spaces-pdf",
                                    className="btn btn-primary mt-4"
                                ),
                                dcc.Download(id="download-spaces-pdf"),
                                html.Div(id="pdf-export-error", className="text-danger mt-2")
                            ], className="d-flex justify-content-end", width=6)
                        ])
                    ], md=4)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Resumen Estadístico"),
                        dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.H4(id="avg-weekly-bookings", className="text-primary mb-0"),
                                            html.P("Reservas semanales (promedio)", className="text-muted small")
                                        ], className="text-center mb-3")
                                    ], md=3),
                                    dbc.Col([
                                        html.Div([
                                            html.H4(id="max-day-occupation", className="text-warning mb-0"),
                                            html.P("Día con mayor ocupación", className="text-muted small")
                                        ], className="text-center mb-3")
                                    ], md=3),
                                    dbc.Col([
                                        html.Div([
                                            html.H4(id="total-bookings-period", className="text-success mb-0"),
                                            html.P("Total de reservas en el período", className="text-muted small")
                                        ], className="text-center mb-3")
                                    ], md=3),
                                    dbc.Col([
                                        html.Div([
                                            html.H4(id="avg-occupation-rate", className="text-info mb-0"),
                                            html.P("Tasa de ocupación media", className="text-muted small")
                                        ], className="text-center mb-3")
                                    ], md=3)
                                ])
                            ])
                        ], className="mb-4")
                    ], md=12)
                ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                            dbc.CardHeader("Reservas por Semana"),
                        dbc.CardBody([
                                dcc.Graph(id="weekly-bookings-chart", className="dash-graph")
                            ])
                        ])
                    ], md=6),
                dbc.Col([
                    dbc.Card([
                            dbc.CardHeader("Ocupación Media por Día"),
                        dbc.CardBody([
                                dcc.Graph(id="daily-occupation-chart", className="dash-graph")
                            ])
                        ])
                    ], md=6)
                ])
            ], className="mb-4"),
            
            # Nueva sección para la tabla de ocupación semanal por día
            html.Div(id="weekly-occupation-table-container", className="mt-4"),
            
            # Nueva sección para la tabla de espacios por reservas
            html.Div(id="spaces-reservations-table-container", className="mt-4"),
            
            # Sección de espacios
            html.Div([
            dbc.Row([
                dbc.Col([
                        html.H5("Reservas de Espacios", className="d-inline-block me-2"),
                        dbc.Badge(id="spaces-count", color="primary", className="me-1")
                    ], width="auto"),
                    dbc.Col([
                        dbc.Button([html.I(className="fas fa-plus me-1"), "Nueva Reserva"], color="success", size="sm", className="float-end")
                    ])
                ], className="mb-3"),
                html.Div(id="spaces-table-container"),
                html.Div(id="pagination-container", className="mt-3")
                ], className="mb-4"),
            
            # Sección de gráficos
            html.Div([
                html.H5("Análisis de Reservas", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(id="spaces-graph-1")
                    ], md=6),
                    dbc.Col([
                        dcc.Graph(id="spaces-graph-2")
                    ], md=6)
                ])
            ], className="mb-4"),
            
            # Sección de calendario
            html.Div([
                html.H5("Calendario de Reservas", className="mb-3"),
                html.Div(id="spaces-calendar-container")
            ])
        ])
    ])
])

# Registrar callbacks para la página de Spaces
def register_callbacks(app):
    # Callback para actualizar el indicador de filtro
    @app.callback(
        Output("spaces-filter-indicator", "children"),
        [Input("selected-client-store", "data")]
    )
    def update_filter_indicator(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        if client_id == "all" and project_id == "all":
            return html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "Mostrando datos globales de todas las reservas de espacios"
            ], className="alert alert-info py-2")
        elif client_id != "all" and project_id == "all":
            return html.Div([
                html.I(className="fas fa-filter me-2"),
                f"Filtrando reservas por cliente: {client_id}"
            ], className="alert alert-primary py-2")
        elif client_id == "all" and project_id != "all":
            return html.Div([
                html.I(className="fas fa-filter me-2"),
                f"Filtrando reservas por proyecto: {project_id}"
            ], className="alert alert-primary py-2")
        else:
            return html.Div([
                html.I(className="fas fa-filter me-2"),
                f"Filtrando reservas por cliente: {client_id} y proyecto: {project_id}"
            ], className="alert alert-primary py-2")
    
    # Callback para actualizar las métricas según el filtro seleccionado
    @app.callback(
        [
            Output("spaces-total", "children"),
            Output("spaces-total-change", "children"),
            Output("spaces-ocupacion", "children"),
            Output("spaces-ocupacion-detail", "children"),
            Output("spaces-reservas", "children"),
            Output("spaces-reservas-change", "children")
        ],
        [Input("selected-client-store", "data")]
    )
    def update_metrics(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Obtener datos de la tabla common_areas_booking_report
        df = get_common_areas_bookings(client_id=client_id, community_uuid=project_id)
        
        # Valores por defecto
        total_bookings = "0"
        bookings_change = "+0% vs. mes anterior"
        ocupacion = "0%"
        ocupacion_detail = "0 espacios ocupados"
        reservas_hoy = "0"
        reservas_change = "+0% vs. semana anterior"
        
        # Si hay datos, calcular métricas
        if df is not None and not df.empty:
            try:
                # 1. Total de reservas (bookings)
                total_bookings = str(len(df))
                
                # 2. Obtener espacios únicos para calcular ocupación
                unique_areas = get_unique_common_areas(client_id, project_id)
                total_spaces = len(unique_areas) if unique_areas is not None else 0
                
                # 3. Calcular ocupación actual (basado en reservas activas)
                now = datetime.now()
                current_date_str = now.strftime('%Y-%m-%d')
                current_time_str = now.strftime('%H:%M:%S')
                
                # Filtrar reservas activas (que están ocurriendo ahora)
                try:
                    # Convertir a datetime para comparación
                    active_bookings = df[df['cancelled_at'].isna()]  # No canceladas
                    
                    # Filtrar por fecha y hora actual
                    current_active = []
                    for _, row in active_bookings.iterrows():
                        start_time = row['start_time']
                        end_time = row['end_time']
                        
                        # Convertir a datetime si son strings
                        if isinstance(start_time, str):
                            if 'T' in start_time:
                                start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
                            elif ' ' in start_time:
                                start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                        
                        if isinstance(end_time, str):
                            if 'T' in end_time:
                                end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
                            elif ' ' in end_time:
                                end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                        
                        # Verificar si la reserva está activa ahora
                        if isinstance(start_time, (datetime, pd.Timestamp)) and isinstance(end_time, (datetime, pd.Timestamp)):
                            if start_time <= now and end_time >= now:
                                current_active.append(row)
                    
                    # Crear DataFrame con las reservas activas
                    active_bookings = pd.DataFrame(current_active) if current_active else pd.DataFrame()
                    
                    # Contar espacios ocupados (espacios únicos con reservas activas)
                    if not active_bookings.empty and total_spaces > 0:
                        occupied_spaces = active_bookings['common_area_id'].nunique()
                        ocupacion_percentage = round((occupied_spaces / total_spaces) * 100) if total_spaces > 0 else 0
                        ocupacion = f"{ocupacion_percentage}%"
                        ocupacion_detail = f"{occupied_spaces} de {total_spaces} espacios ocupados"
                    elif total_spaces > 0:
                        ocupacion = "0%"
                        ocupacion_detail = f"0 de {total_spaces} espacios ocupados"
                except Exception as e:
                    logger.error(f"Error calculando ocupación: {str(e)}")
                
                # 4. Contar reservas de hoy
                try:
                    today_bookings = []
                    for _, row in df.iterrows():
                        start_time = row['start_time']
                        
                        # Extraer la fecha
                        booking_date = None
                        if isinstance(start_time, pd.Timestamp):
                            booking_date = start_time.strftime('%Y-%m-%d')
                        elif isinstance(start_time, str):
                            if 'T' in start_time:
                                booking_date = start_time.split('T')[0]
                            elif ' ' in start_time:
                                booking_date = start_time.split(' ')[0]
                        
                        # Verificar si es hoy
                        if booking_date == current_date_str:
                            today_bookings.append(row)
                    
                    reservas_hoy = str(len(today_bookings))
                except Exception as e:
                    logger.error(f"Error contando reservas de hoy: {str(e)}")
                    reservas_hoy = "0"
                
            except Exception as e:
                logger.error(f"Error calculando métricas de espacios: {str(e)}")
        
        return total_bookings, bookings_change, ocupacion, ocupacion_detail, reservas_hoy, reservas_change
    
    # Callback para actualizar la tabla de espacios
    @app.callback(
        [
        Output("spaces-table-container", "children"),
            Output("pagination-container", "children")
        ],
        [
            Input("selected-client-store", "data"), 
            Input("refresh-spaces-button", "n_clicks"),
            Input("apply-space-filters", "n_clicks"),
            Input("page-number", "data")
        ],
        [
            State("space-type-filter", "value"),
            State("space-status-filter", "value"),
            State("space-capacity-filter", "value"),
            State("space-search", "value"),
            State("rows-per-page", "data")
        ]
    )
    def update_spaces_table(selection_data, refresh_clicks, apply_clicks, page_number, space_type, space_status, space_capacity, space_search, rows_per_page):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Valores por defecto para paginación
        if page_number is None or not isinstance(page_number, int):
            page_number = 1
        if rows_per_page is None or not isinstance(rows_per_page, int):
            rows_per_page = 10
        
        # Obtener datos de la tabla common_areas_booking_report
        df = get_common_areas_bookings(client_id=client_id, community_uuid=project_id)
        
        # Si no hay datos, mostrar mensaje
        if df is None or df.empty:
            return html.Div([
                html.Div("No se encontraron datos de reservas de áreas comunes.", className="alert alert-info"),
                html.P("Posibles razones:"),
                html.Ul([
                    html.Li("No hay reservas registradas para los filtros seleccionados."),
                    html.Li("La conexión a la base de datos no está configurada correctamente."),
                    html.Li("La tabla common_areas_booking_report no existe o está vacía.")
                ])
            ]), html.Div()  # Contenedor de paginación vacío
        
        # Crear tabla de reservas de espacios
        spaces_table = html.Table([
            html.Thead([
                html.Tr([
                    html.Th("ID Reserva"),
                    html.Th("Espacio"),
                    html.Th("Proyecto"),
                    html.Th("Cliente"),
                    html.Th("Estado"),
                    html.Th("Fecha Inicio"),
                    html.Th("Hora Inicio"),
                    html.Th("Hora Fin"),
                    html.Th("Creada"),
                    html.Th("Acciones")
                ])
            ]),
            html.Tbody(id="spaces-table-body")
        ], className="table table-striped table-hover")
        
        # Aplicar filtros adicionales al DataFrame
        filtered_df = df.copy()
        
        # Filtrar por tipo de espacio (si se implementa en el futuro)
        if space_type and space_type != "all" and 'area_type' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['area_type'] == space_type]
        
        # Filtrar por estado (disponible/ocupado basado en si está cancelada o no)
        if space_status and space_status != "all":
            now = datetime.now()
            current_date_str = now.strftime('%Y-%m-%d')
            
            if space_status.lower() == "disponible":
                # Reservas canceladas o que ya pasaron
                filtered_rows = []
                for _, row in filtered_df.iterrows():
                    start_time = row['start_time']
                    end_time = row['end_time']
                    cancelled = pd.notna(row['cancelled_at'])
                    
                    # Convertir a datetime si son strings
                    if isinstance(start_time, str):
                        if 'T' in start_time:
                            start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
                        elif ' ' in start_time:
                            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    
                    if isinstance(end_time, str):
                        if 'T' in end_time:
                            end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
                        elif ' ' in end_time:
                            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                    
                    # Verificar si la reserva está disponible (cancelada o ya pasó)
                    if cancelled or (isinstance(end_time, (datetime, pd.Timestamp)) and end_time < now):
                        filtered_rows.append(row)
                
                filtered_df = pd.DataFrame(filtered_rows) if filtered_rows else pd.DataFrame(columns=filtered_df.columns)
                
            elif space_status.lower() == "reservado":
                # Reservas futuras no canceladas
                filtered_rows = []
                for _, row in filtered_df.iterrows():
                    start_time = row['start_time']
                    cancelled = pd.notna(row['cancelled_at'])
                    
                    # Convertir a datetime si es string
                    if isinstance(start_time, str):
                        if 'T' in start_time:
                            start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
                        elif ' ' in start_time:
                            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    
                    # Verificar si la reserva está reservada (futura y no cancelada)
                    if not cancelled and isinstance(start_time, (datetime, pd.Timestamp)) and start_time > now:
                        filtered_rows.append(row)
                
                filtered_df = pd.DataFrame(filtered_rows) if filtered_rows else pd.DataFrame(columns=filtered_df.columns)
                
            elif space_status.lower() == "ocupado":
                # Reservas actuales no canceladas
                filtered_rows = []
                for _, row in filtered_df.iterrows():
                    start_time = row['start_time']
                    end_time = row['end_time']
                    cancelled = pd.notna(row['cancelled_at'])
                    
                    # Convertir a datetime si son strings
                    if isinstance(start_time, str):
                        if 'T' in start_time:
                            start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
                        elif ' ' in start_time:
                            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    
                    if isinstance(end_time, str):
                        if 'T' in end_time:
                            end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
                        elif ' ' in end_time:
                            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                    
                    # Verificar si la reserva está ocupada (actual y no cancelada)
                    if (not cancelled and 
                        isinstance(start_time, (datetime, pd.Timestamp)) and 
                        isinstance(end_time, (datetime, pd.Timestamp)) and 
                        start_time <= now and end_time >= now):
                        filtered_rows.append(row)
                
                filtered_df = pd.DataFrame(filtered_rows) if filtered_rows else pd.DataFrame(columns=filtered_df.columns)
            
            elif space_status.lower() == "cancelado":
                # Reservas canceladas
                filtered_df = filtered_df[filtered_df['cancelled_at'].notna()]
        
        # Filtrar por búsqueda en nombre de espacio o ID
        if space_search:
            search_term = space_search.lower()
            filtered_df = filtered_df[
                filtered_df['common_area_name'].astype(str).str.lower().str.contains(search_term) | 
                filtered_df['id'].astype(str).str.lower().str.contains(search_term) |
                filtered_df['common_area_id'].astype(str).str.lower().str.contains(search_term)
            ]
        
        # Calcular el número total de filas y páginas
        total_rows = len(filtered_df)
        total_pages = max(1, math.ceil(total_rows / rows_per_page))
        
        # Asegurar que el número de página es válido
        if page_number < 1:
            page_number = 1
        elif page_number > total_pages:
            page_number = total_pages
        
        # Calcular índices de inicio y fin para la página actual
        start_idx = (page_number - 1) * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)
        
        # Obtener solo las filas para la página actual
        if not filtered_df.empty:
            page_df = filtered_df.iloc[start_idx:end_idx].copy()
        else:
            page_df = filtered_df
        
        # Crear filas de la tabla
        rows = []
        for _, row in page_df.iterrows():
            # Extraer datos de la reserva
            booking_id = row.get('id', 'N/A')
            space_name = row.get('common_area_name', 'N/A')
            project_name = row.get('community_id', 'N/A')
            client_name = row.get('client_name', 'N/A')
            
            # Fechas y horas
            start_time = row.get('start_time', 'N/A')
            end_time = row.get('end_time', 'N/A')
            created_at = row.get('created_at', 'N/A')
            cancelled_at = row.get('cancelled_at', None)
            
            # Convertir a datetime si son objetos Timestamp
            if isinstance(start_time, pd.Timestamp):
                start_date = start_time.strftime('%Y-%m-%d')
                start_time_str = start_time.strftime('%H:%M:%S')
            elif isinstance(start_time, str):
                if 'T' in start_time:
                    parts = start_time.split('T')
                    start_date = parts[0]
                    start_time_str = parts[1]
                elif ' ' in start_time:
                    parts = start_time.split(' ')
                    start_date = parts[0]
                    start_time_str = parts[1]
                else:
                    start_date = 'N/A'
                    start_time_str = start_time
            else:
                start_date = 'N/A'
                start_time_str = 'N/A'
                
            if isinstance(end_time, pd.Timestamp):
                end_time_str = end_time.strftime('%H:%M:%S')
            elif isinstance(end_time, str):
                if 'T' in end_time:
                    end_time_str = end_time.split('T')[1]
                elif ' ' in end_time:
                    end_time_str = end_time.split(' ')[1]
                else:
                    end_time_str = end_time
            else:
                end_time_str = 'N/A'
            
            # Determinar el estado de la reserva
            now = datetime.now()
            current_date = now.date()
            current_time = now.time()
            
            # Convertir start_date a objeto date para comparación
            try:
                if start_date != 'N/A':
                    booking_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    booking_date = None
            except:
                booking_date = None
            
            if cancelled_at is not None and pd.notna(cancelled_at):
                status = "Cancelada"
                badge_color = "secondary"
            elif booking_date == current_date:
                # Convertir tiempos a objetos time para comparación
                try:
                    start_time_obj = datetime.strptime(start_time_str, '%H:%M:%S').time()
                    end_time_obj = datetime.strptime(end_time_str, '%H:%M:%S').time() if end_time_str != 'N/A' else None
                    
                    if start_time_obj > current_time:
                        status = "Reservada"
                        badge_color = "warning"
                    elif start_time_obj <= current_time and (end_time_obj is None or end_time_obj >= current_time):
                        status = "Ocupada"
                        badge_color = "danger"
                    else:
                        status = "Disponible"
                        badge_color = "success"
                except:
                    status = "Disponible"
                    badge_color = "success"
            else:
                status = "Disponible"
                badge_color = "success"
            
            # Crear fila de la tabla
            rows.append(html.Tr([
                html.Td(booking_id),
                html.Td(space_name),
                html.Td(project_name),
                html.Td(client_name),
                html.Td(dbc.Badge(status, color=badge_color, className="me-1")),
                html.Td(start_date),
                html.Td(start_time_str),
                html.Td(end_time_str),
                html.Td(created_at.strftime('%Y-%m-%d') if isinstance(created_at, pd.Timestamp) else 
                       created_at.split(' ')[0] if isinstance(created_at, str) and ' ' in created_at else created_at),
                html.Td([
                    html.Button([html.I(className="fas fa-eye")], className="btn btn-sm btn-outline-primary me-1", title="Ver detalles"),
                    html.Button([html.I(className="fas fa-edit")], className="btn btn-sm btn-outline-secondary me-1", title="Editar"),
                    html.Button([html.I(className="fas fa-trash-alt")], className="btn btn-sm btn-outline-danger", title="Eliminar")
                ])
            ]))
        
        # Si no hay filas después de filtrar, mostrar mensaje
        if not rows:
            return html.Div("No se encontraron reservas que coincidan con los filtros seleccionados.", className="alert alert-warning"), html.Div()
        
        # Actualizar el cuerpo de la tabla
        spaces_table.children[1].children = rows
        
        # Crear controles de paginación
        pagination_controls = html.Div([
            html.Div([
                html.Button("<<", id="first-page", className="btn btn-sm btn-outline-primary me-1", title="Primera página", n_clicks=0),
                html.Button("<", id="prev-page", className="btn btn-sm btn-outline-primary me-1", title="Página anterior", n_clicks=0),
                html.Span(f"Página {page_number} de {total_pages}", className="mx-2"),
                html.Button(">", id="next-page", className="btn btn-sm btn-outline-primary me-1", title="Página siguiente", n_clicks=0),
                html.Button(">>", id="last-page", className="btn btn-sm btn-outline-primary me-1", title="Última página", n_clicks=0),
                html.Span("Filas por página:", className="ms-3 me-1"),
                dcc.Dropdown(
                    id="rows-per-page",
                    options=[
                        {"label": "10", "value": 10},
                        {"label": "25", "value": 25},
                        {"label": "50", "value": 50},
                        {"label": "100", "value": 100}
                    ],
                    value=rows_per_page,
                    clearable=False,
                    style={"width": "80px", "display": "inline-block"}
                )
            ], className="d-flex align-items-center justify-content-center mt-3")
        ], id="pagination-controls")
        
        # Crear contenedor con la tabla y contador de resultados
        return html.Div([
            html.Div(f"Mostrando {len(rows)} de {total_rows} reservas de espacios (Página {page_number} de {total_pages})", className="text-muted mb-2"),
            spaces_table
        ]), pagination_controls
    
    # Callback para actualizar los gráficos
    @app.callback(
        [Output("spaces-graph-1", "figure"), Output("spaces-graph-2", "figure")],
        [Input("selected-client-store", "data")]
    )
    def update_graphs(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Obtener datos de la tabla common_areas_booking_report
        df = get_common_areas_bookings(client_id=client_id, community_uuid=project_id)
        
        # Gráfico 1: Distribución de reservas por espacio
        fig1 = {
            "data": [],
            "layout": {
                "title": "Distribución de Reservas por Espacio",
                "showlegend": True,
                "legend": {"orientation": "h", "y": -0.2},
                "margin": {"l": 40, "r": 10, "t": 60, "b": 140}
            }
        }
        
        # Gráfico 2: Reservas por hora del día
        fig2 = {
            "data": [],
            "layout": {
                "title": "Reservas por Hora del Día",
                "xaxis": {"title": "Hora"},
                "yaxis": {"title": "Número de Reservas"},
                "showlegend": True,
                "legend": {"orientation": "h", "y": -0.2},
                "margin": {"l": 40, "r": 10, "t": 60, "b": 140}
            }
        }
        
        # Si hay datos, generar gráficos
        if df is not None and not df.empty:
            try:
                # Gráfico 1: Distribución de reservas por espacio
                if 'common_area_name' in df.columns:
                    # Contar reservas por espacio
                    space_counts = df['common_area_name'].value_counts().head(10)  # Mostrar top 10 espacios
                    
                    fig1["data"] = [{
                        "type": "pie",
                        "labels": space_counts.index.tolist(),
                        "values": space_counts.values.tolist(),
                        "hole": 0.4,
                        "marker": {"colors": ["#4e73df", "#1cc88a", "#36b9cc", "#f6c23e", "#e74a3b", "#5a5c69", "#858796", "#6f42c1", "#20c9a6", "#fd7e14"]}
                    }]
                
                # Gráfico 2: Reservas por hora del día
                if 'start_time' in df.columns:
                    # Extraer la hora de start_time
                    try:
                        # Intentar extraer la hora
                        hours = []
                        for time_val in df['start_time']:
                            if isinstance(time_val, pd.Timestamp):
                                # Si es un Timestamp, extraer la hora directamente
                                hours.append(time_val.hour)
                            elif isinstance(time_val, str):
                                if ' ' in time_val:
                                    # Formato: '2025-05-07 08:30:00'
                                    hour_part = time_val.split(' ')[1].split(':')[0]
                                elif 'T' in time_val:
                                    # Formato: '2025-05-07T08:30:00'
                                    hour_part = time_val.split('T')[1].split(':')[0]
                                else:
                                    hour_part = time_val.split(':')[0]
                                try:
                                    hours.append(int(hour_part))
                                except:
                                    hours.append(None)
                            else:
                                hours.append(None)
                        
                        # Crear Series con las horas
                        hour_series = pd.Series(hours).dropna()
                        
                        # Contar reservas por hora
                        hour_counts = hour_series.value_counts().sort_index()
                        
                        fig2["data"] = [{
                            "type": "bar",
                            "x": hour_counts.index.tolist(),
                            "y": hour_counts.values.tolist(),
                            "marker": {"color": "#4e73df"}
                        }]
                    except Exception as e:
                        logger.error(f"Error procesando horas para el gráfico: {str(e)}")
            except Exception as e:
                logger.error(f"Error generando gráficos de espacios: {str(e)}")
        
        return fig1, fig2
    
    # Callback para actualizar el calendario de reservas
    @app.callback(
        Output("spaces-calendar-container", "children"),
        [Input("selected-client-store", "data")]
    )
    def update_calendar(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Obtener datos de la tabla common_areas_booking_report
        df = get_common_areas_bookings(client_id=client_id, community_uuid=project_id)
        
        # Si no hay datos, mostrar mensaje
        if df is None or df.empty:
            return html.Div("No hay datos de reservas disponibles para mostrar en el calendario.", className="alert alert-info")
        
        # Crear eventos para el calendario
        events = []
        
        try:
            # Filtrar reservas no canceladas
            active_bookings = df[df['cancelled_at'].isna()]
            
            # Procesar cada reserva
            for _, row in active_bookings.iterrows():
                # Obtener fecha y horas
                start_time = row.get('start_time', '')
                end_time = row.get('end_time', '')
                
                # Formatear fechas para el calendario
                start_date = None
                end_date = None
                
                # Procesar start_time
                if isinstance(start_time, pd.Timestamp):
                    # Convertir Timestamp a formato ISO para el calendario
                    start_date = start_time.strftime('%Y-%m-%dT%H:%M:%S')
                elif isinstance(start_time, str):
                    if ' ' in start_time:  # Formato: '2025-05-07 08:30:00'
                        date_part = start_time.split(' ')[0]
                        time_part = start_time.split(' ')[1]
                        start_date = f"{date_part}T{time_part}"
                    elif 'T' in start_time:  # Ya está en formato ISO
                        start_date = start_time
                    else:
                        start_date = start_time
                
                # Procesar end_time
                if isinstance(end_time, pd.Timestamp):
                    # Convertir Timestamp a formato ISO para el calendario
                    end_date = end_time.strftime('%Y-%m-%dT%H:%M:%S')
                elif isinstance(end_time, str):
                    if ' ' in end_time:  # Formato: '2025-05-07 08:30:00'
                        date_part = end_time.split(' ')[0]
                        time_part = end_time.split(' ')[1]
                        end_date = f"{date_part}T{time_part}"
                    elif 'T' in end_time:  # Ya está en formato ISO
                        end_date = end_time
                    else:
                        end_date = end_time
                
                # Obtener nombre del espacio y cliente
                space_name = row.get('common_area_name', "Espacio sin nombre")
                client_name = row.get('client_name', "Cliente desconocido")
                
                # Solo añadir evento si tenemos fechas válidas
                if start_date:
                    # Crear evento
                    event = {
                        "title": f"{space_name} - {client_name}",
                        "start": start_date,
                        "end": end_date if end_date else None,
                        "backgroundColor": "#4e73df",
                        "borderColor": "#3a5ccc"
                    }
                    
                    events.append(event)
        except Exception as e:
            logger.error(f"Error procesando datos para el calendario: {str(e)}")
            return html.Div(f"Error al procesar los datos para el calendario: {str(e)}", className="alert alert-danger")
        
        # Crear el calendario (simulado con una tarjeta)
        calendar = dbc.Card([
            dbc.CardHeader("Calendario de Reservas"),
            dbc.CardBody([
                html.P(f"Se han cargado {len(events)} reservas activas para mostrar en el calendario."),
                html.Div("El calendario se mostraría aquí con los eventos cargados.", className="p-3 bg-light border rounded")
            ])
        ])
        
        return calendar
    
    # Callback para reiniciar los filtros
    @app.callback(
        [
            Output("space-type-filter", "value"),
            Output("space-status-filter", "value"),
            Output("space-capacity-filter", "value"),
            Output("space-search", "value")
        ],
        [Input("reset-space-filters", "n_clicks")],
        prevent_initial_call=True
    )
    def reset_filters(n_clicks):
        return "all", "all", 0, "" 
    
    @app.callback(
        Output("spaces-count", "children"),
        [Input("spaces-table-container", "children")]
    )
    def update_spaces_count(table_container):
        # Si la tabla contiene un mensaje de error o está vacía
        if isinstance(table_container, html.Div) and not any(isinstance(child, html.Table) for child in table_container.children):
            return "0 reservas"
            
        # Si hay una tabla con datos
        if isinstance(table_container, html.Div) and any(isinstance(child, html.Table) for child in table_container.children):
            # Buscar el mensaje que contiene el número de resultados
            for child in table_container.children:
                if isinstance(child, html.Div) and "Mostrando" in child.children:
                    # Extraer el número de la cadena "Mostrando X de Y reservas de espacios"
                    text = child.children
                    import re
                    match = re.search(r'Mostrando \d+ de (\d+)', text)
                    if match:
                        return f"{match.group(1)} reservas"
        
        return "0 reservas"
    
    # Callback unificado para controlar la paginación
    @app.callback(
        Output("page-number", "data", allow_duplicate=True),
        [
            Input("first-page", "n_clicks"),
            Input("prev-page", "n_clicks"),
            Input("next-page", "n_clicks"),
            Input("last-page", "n_clicks"),
            Input("rows-per-page", "value"),
            Input("apply-space-filters", "n_clicks"),
            Input("reset-space-filters", "n_clicks")
        ],
        [State("page-number", "data")],
        prevent_initial_call=True
    )
    def update_pagination(first_clicks, prev_clicks, next_clicks, last_clicks, 
                         rows_per_page, apply_clicks, reset_clicks, 
                         current_page):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Si el trigger es un cambio en filas por página o filtros, resetear a página 1
        if trigger_id in ["rows-per-page", "apply-space-filters", "reset-space-filters"]:
            return 1
        
        # Para botones de navegación, calcular la nueva página
        if trigger_id in ["first-page", "prev-page", "next-page", "last-page"]:
            # Como no tenemos acceso directo al número total de páginas aquí,
            # usamos valores fijos para prev/next y asumimos que la validación
            # completa se hará en update_spaces_table
            if trigger_id == "first-page":
                return 1
            elif trigger_id == "prev-page":
                return max(1, current_page - 1)
            elif trigger_id == "next-page":
                return current_page + 1  # La validación contra max_pages se hará en update_spaces_table
            elif trigger_id == "last-page":
                return 9999  # Un número grande, update_spaces_table lo ajustará al máximo real
        
        return no_update
    
    # Callback para actualizar el almacenamiento de filas por página
    @app.callback(
        Output("rows-per-page", "data", allow_duplicate=True),
        [Input("rows-per-page", "value")],
        prevent_initial_call=True
    )
    def update_rows_per_page(rows_per_page):
        if rows_per_page is None:
            return no_update
        return rows_per_page
    
    # Callback para inicializar los valores de paginación
    @app.callback(
        [
            Output("page-number", "data", allow_duplicate=True), 
            Output("rows-per-page", "data", allow_duplicate=True)
        ],
        [Input("spaces-filter-indicator", "children")],
        prevent_initial_call='initial_duplicate'
    )
    def initialize_pagination(filter_indicator):
        # Este callback se ejecuta al cargar la página y establece los valores iniciales
        return 1, 10
    
    # Callback para generar los gráficos de análisis avanzado
    @app.callback(
        [
            Output("weekly-bookings-chart", "figure"), 
            Output("daily-occupation-chart", "figure"),
            Output("avg-weekly-bookings", "children"),
            Output("max-day-occupation", "children"),
            Output("total-bookings-period", "children"),
            Output("avg-occupation-rate", "children"),
            Output("weekly-occupation-data", "data"),
            Output("spaces-reservations-data", "data")
        ],
        [Input("selected-client-store", "data"), Input("analysis-period", "value")],
        prevent_initial_call=True
    )
    def update_advanced_analytics(selection_data, period):
        # Usar también logging estándar para verificar
        import logging
        std_logger = logging.getLogger("layouts.spaces")
        std_logger.info(f"Iniciando update_advanced_analytics con period={period}")
        std_logger.info(f"Datos de selección recibidos: {selection_data}")
        
        # Valores por defecto para las estadísticas
        avg_weekly = "0"
        max_day = "N/A"
        total_bookings = "0"
        avg_occupation = "0%"
        weekly_occupation_data = {}  # Diccionario para almacenar los datos de ocupación semanal
        spaces_reservations_data = {}  # Nuevo diccionario para almacenar los datos de espacios por reservas
        
        # Inicializar figuras vacías
        weekly_fig = {
            "data": [],
            "layout": {
                "title": "Reservas por Semana",
                "xaxis": {"title": "Semana del Año"},
                "yaxis": {"title": "Número de Reservas"},
                "showlegend": True,
                "legend": {"orientation": "h", "y": -0.2},
                "margin": {"l": 40, "r": 10, "t": 60, "b": 140},
                "height": 400
            }
        }
        
        daily_fig = {
            "data": [],
            "layout": {
                "title": "Ocupación Media por Día",
                "xaxis": {"title": "Porcentaje de Ocupación"},
                "yaxis": {"title": "Día de la Semana"},
                "showlegend": False,
                "margin": {"l": 120, "r": 10, "t": 60, "b": 40},
                "height": 400
            }
        }
        
        try:
            # Obtener datos de la tabla common_areas_booking_report
            client_id = selection_data.get("client_id", "all")
            community_uuid = selection_data.get("project_id", "all")
            
            logger.info(f"Obteniendo datos para client_id={client_id}, community_uuid={community_uuid}")
            df = get_common_areas_bookings(client_id=client_id, community_uuid=community_uuid)
            
            # Verificar si hay datos
            if df is None:
                logger.warning("No se encontraron datos de reservas para el análisis avanzado (df es None)")
                return weekly_fig, daily_fig, avg_weekly, max_day, total_bookings, avg_occupation, weekly_occupation_data, spaces_reservations_data
            elif df.empty:
                logger.warning("No se encontraron datos de reservas para el análisis avanzado (df está vacío)")
                return weekly_fig, daily_fig, avg_weekly, max_day, total_bookings, avg_occupation, weekly_occupation_data, spaces_reservations_data
            else:
                logger.info(f"Datos obtenidos correctamente. Número de filas: {len(df)}")
                logger.info(f"Columnas disponibles: {df.columns.tolist()}")
                logger.info(f"Primeras 5 filas: {df.head(5).to_dict('records')}")
            
            # Convertir la columna de fecha a datetime
            try:
                logger.info(f"Convirtiendo columna start_time a datetime")
                logger.info(f"Tipo de datos de start_time antes de la conversión: {df['start_time'].dtype}")
                logger.info(f"Muestra de valores start_time antes de la conversión: {df['start_time'].head(3).tolist()}")
                
                df['start_time'] = pd.to_datetime(df['start_time'])
                
                logger.info(f"Columna start_time convertida a datetime. Tipo: {df['start_time'].dtype}")
                logger.info(f"Muestra de valores start_time después de la conversión: {df['start_time'].head(3).tolist()}")
            except KeyError as ke:
                logger.error(f"Error: La columna 'start_time' no existe en el DataFrame. Columnas disponibles: {df.columns.tolist()}")
                return weekly_fig, daily_fig, avg_weekly, max_day, total_bookings, avg_occupation, weekly_occupation_data, spaces_reservations_data
            except Exception as e:
                logger.error(f"Error al convertir start_time a datetime: {str(e)}")
                return weekly_fig, daily_fig, avg_weekly, max_day, total_bookings, avg_occupation, weekly_occupation_data, spaces_reservations_data
            
            # Filtrar por período seleccionado
            current_date = pd.Timestamp.now()
            logger.info(f"Filtrando datos por período: {period}")
            logger.info(f"Fecha actual para filtrado: {current_date}")
            
            if period == "last_week":
                start_date = current_date - pd.Timedelta(days=7)
                df_filtered = df[(df['start_time'] >= start_date) & (df['start_time'] <= current_date)]
                period_label = "última semana"
            elif period == "last_month":
                start_date = current_date - pd.Timedelta(days=30)
                df_filtered = df[(df['start_time'] >= start_date) & (df['start_time'] <= current_date)]
                period_label = "último mes"
            elif period == "last_quarter":
                start_date = current_date - pd.Timedelta(days=90)
                df_filtered = df[(df['start_time'] >= start_date) & (df['start_time'] <= current_date)]
                period_label = "último trimestre"
            elif period == "last_year":
                start_date = current_date - pd.Timedelta(days=365)
                df_filtered = df[(df['start_time'] >= start_date) & (df['start_time'] <= current_date)]
                period_label = "último año"
            elif period == "this_year":
                start_date = pd.Timestamp(current_date.year, 1, 1)
                df_filtered = df[(df['start_time'] >= start_date) & (df['start_time'] <= current_date)]
                period_label = "este año hasta hoy"
            else:  # all_time
                # Para "all_time" también limitamos hasta la fecha actual
                df_filtered = df[df['start_time'] <= current_date]
                period_label = "todo el período"
                logger.info("Usando todos los datos disponibles hasta hoy (sin filtro de fecha de inicio)")
            
            if period != "all_time":
                logger.info(f"Filtrando datos desde {start_date} hasta {current_date}")
                logger.info(f"Rango de fechas en los datos: {df['start_time'].min()} a {df['start_time'].max()}")
            
            logger.info(f"Datos filtrados por período: {period}. Registros antes: {len(df)}, después: {len(df_filtered)}")
            
            # Verificar si hay datos después del filtrado
            if df_filtered.empty:
                logger.warning(f"No hay datos disponibles para el período seleccionado: {period}")
                return weekly_fig, daily_fig, avg_weekly, max_day, total_bookings, avg_occupation, weekly_occupation_data, spaces_reservations_data
            
            # Calcular total de reservas en el período
            total_bookings_value = len(df_filtered)
            total_bookings = f"{total_bookings_value:,}".replace(",", ".")
            logger.info(f"Total de reservas en el período: {total_bookings_value}")
            
            # Calcular reservas por semana
            try:
                logger.info("Calculando reservas por semana...")
                df_filtered['week'] = df_filtered['start_time'].dt.isocalendar().week
                df_filtered['year'] = df_filtered['start_time'].dt.isocalendar().year
                
                # Agrupar por semana y contar reservas
                weekly_counts = df_filtered.groupby(['year', 'week']).size().reset_index(name='count')
                weekly_counts['week_label'] = weekly_counts.apply(lambda x: f"{x['year']}-W{x['week']:02d}", axis=1)
                
                # Ordenar por año y semana
                weekly_counts = weekly_counts.sort_values(['year', 'week'])
                
                # Obtener la semana actual para asegurar que no se muestren semanas futuras
                current_week = current_date.isocalendar()[1]
                current_year = current_date.isocalendar()[0]
                
                # Filtrar para mostrar solo hasta la semana actual
                weekly_counts = weekly_counts[
                    ((weekly_counts['year'] < current_year)) | 
                    ((weekly_counts['year'] == current_year) & (weekly_counts['week'] <= current_week))
                ]
                
                logger.info(f"Reservas por semana calculadas. Número de semanas: {len(weekly_counts)}")
                logger.info(f"Datos de reservas por semana: {weekly_counts.to_dict('records')}")
                logger.info(f"Semana actual: {current_year}-W{current_week:02d}")
                
                # Calcular promedio semanal de reservas
                if len(weekly_counts) > 0:
                    avg_weekly_value = weekly_counts['count'].mean()
                    avg_weekly = f"{avg_weekly_value:.1f}".replace(".", ",")
                    logger.info(f"Promedio semanal de reservas: {avg_weekly_value}")
            except Exception as e:
                logger.error(f"Error al calcular reservas por semana: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Crear gráfico de barras para reservas semanales
            try:
                logger.info("Creando gráfico de reservas semanales...")
                weekly_fig["data"] = [{
                    "type": "bar",
                    "x": weekly_counts['week_label'].tolist(),
                    "y": weekly_counts['count'].tolist(),
                    "marker": {"color": "#4e73df"}
                }]
                logger.info("Gráfico de reservas semanales creado correctamente")
            except Exception as e:
                logger.error(f"Error al crear gráfico de reservas semanales: {str(e)}")
            
            # Calcular ocupación por día de la semana
            try:
                logger.info("Calculando ocupación por día de la semana...")
                
                # Extraer el día de la semana de la fecha de inicio de la reserva
                df_filtered['day_of_week'] = df_filtered['start_time'].dt.day_name()
                logger.info(f"Valores únicos de day_of_week: {df_filtered['day_of_week'].unique().tolist()}")
                
                # Mapear nombres de días en inglés a español si es necesario
                day_map = {
                    'Monday': 'Lunes',
                    'Tuesday': 'Martes',
                    'Wednesday': 'Miércoles',
                    'Thursday': 'Jueves',
                    'Friday': 'Viernes',
                    'Saturday': 'Sábado',
                    'Sunday': 'Domingo'
                }
                
                # Verificar si los días están en inglés y convertir si es necesario
                if 'Monday' in df_filtered['day_of_week'].values:
                    logger.info("Convirtiendo nombres de días de inglés a español")
                    df_filtered['day_of_week'] = df_filtered['day_of_week'].map(day_map)
                    logger.info(f"Valores únicos de day_of_week después de la conversión: {df_filtered['day_of_week'].unique().tolist()}")
                
                # Orden correcto de los días de la semana
                day_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                
                # Obtener el número total de espacios únicos disponibles
                unique_areas = get_unique_common_areas(client_id, community_uuid)
                total_spaces = len(unique_areas) if unique_areas is not None else 0
                logger.info(f"Total de espacios únicos disponibles: {total_spaces}")
                
                if total_spaces > 0:
                    # Para cada día de la semana, calcular cuántos espacios únicos están ocupados
                    daily_occupation = []
                    
                    for day in day_order:
                        # Filtrar reservas para este día de la semana
                        day_bookings = df_filtered[df_filtered['day_of_week'] == day]
                        
                        # Contar espacios únicos ocupados en este día
                        occupied_spaces = day_bookings['common_area_id'].nunique() if not day_bookings.empty else 0
                        
                        # Calcular porcentaje de ocupación
                        occupation_percentage = round((occupied_spaces / total_spaces) * 100, 1)
                        
                        daily_occupation.append({
                            'day_of_week': day,
                            'occupied_spaces': occupied_spaces,
                            'percentage': occupation_percentage,
                            'count': len(day_bookings)  # Mantener el conteo de reservas para compatibilidad
                        })
                    
                    # Crear DataFrame con los resultados
                    daily_counts = pd.DataFrame(daily_occupation)
                    logger.info(f"Ocupación por día calculada (nueva metodología): {daily_counts.to_dict('records')}")
                else:
                    # Si no hay espacios, crear un DataFrame vacío con las columnas necesarias
                    daily_counts = pd.DataFrame({
                        'day_of_week': day_order,
                        'occupied_spaces': 0,
                        'percentage': 0,
                        'count': 0
                    })
                
                # Ordenar por día de la semana
                daily_counts['day_order'] = daily_counts['day_of_week'].map({day: i for i, day in enumerate(day_order)})
                daily_counts = daily_counts.sort_values('day_order')
                
                logger.info(f"Ocupación por día calculada (con todos los días): {daily_counts.to_dict('records')}")
                
                # Encontrar el día con mayor ocupación
                if not daily_counts.empty:
                    max_day_row = daily_counts.loc[daily_counts['percentage'].idxmax()]
                    max_day = max_day_row['day_of_week']
                    logger.info(f"Día con mayor ocupación: {max_day} con {max_day_row['percentage']}% de ocupación")
                    
                    # Calcular tasa de ocupación promedio
                    avg_occupation_value = daily_counts['percentage'].mean()
                    avg_occupation = f"{avg_occupation_value:.1f}%".replace(".", ",")
                    logger.info(f"Tasa de ocupación promedio: {avg_occupation_value}%")
                
                # NUEVA SECCIÓN: Calcular ocupación por semana y día
                try:
                    logger.info("Calculando tabla de ocupación por semana y día...")
                    
                    # Añadir columnas de semana y día
                    df_filtered['week'] = df_filtered['start_time'].dt.isocalendar().week
                    df_filtered['year'] = df_filtered['start_time'].dt.isocalendar().year
                    df_filtered['week_label'] = df_filtered.apply(lambda x: f"{x['year']}-W{x['week']:02d}", axis=1)
                    
                    # Crear un DataFrame con todas las combinaciones de semanas y días
                    weeks = sorted(df_filtered['week_label'].unique())
                    
                    # Filtrar para mostrar solo hasta la semana actual
                    current_week = f"{current_date.isocalendar()[0]}-W{current_date.isocalendar()[1]:02d}"
                    weeks = [week for week in weeks if week <= current_week]
                    
                    # Si hay espacios disponibles, calcular la ocupación por semana y día
                    if total_spaces > 0 and weeks:
                        # Crear todas las combinaciones de semanas y días
                        all_combinations = []
                        for week in weeks:
                            for day in day_order:
                                all_combinations.append({'week_label': week, 'day_of_week': day})
                        
                        all_combinations_df = pd.DataFrame(all_combinations)
                        
                        # Para cada combinación de semana y día, calcular la ocupación
                        weekly_daily_occupation = []
                        
                        for week in weeks:
                            week_data = df_filtered[df_filtered['week_label'] == week]
                            
                            for day in day_order:
                                # Filtrar reservas para este día de la semana en esta semana
                                day_bookings = week_data[week_data['day_of_week'] == day]
                                
                                # Contar espacios únicos ocupados en este día de esta semana
                                occupied_spaces = day_bookings['common_area_id'].nunique() if not day_bookings.empty else 0
                                
                                # Calcular porcentaje de ocupación
                                occupation_percentage = round((occupied_spaces / total_spaces) * 100, 1)
                                
                                weekly_daily_occupation.append({
                                    'week_label': week,
                                    'day_of_week': day,
                                    'occupied_spaces': occupied_spaces,
                                    'percentage': occupation_percentage,
                                    'count': len(day_bookings),
                                    'total': total_spaces
                                })
                        
                        # Crear DataFrame con los resultados
                        complete_weekly_daily = pd.DataFrame(weekly_daily_occupation)
                        
                        # Ordenar por semana y día
                        complete_weekly_daily['day_order'] = complete_weekly_daily['day_of_week'].map(
                            {day: i for i, day in enumerate(day_order)}
                        )
                        complete_weekly_daily = complete_weekly_daily.sort_values(['week_label', 'day_order'])
                        
                        # Crear un diccionario pivotado para la tabla
                        pivot_data = {}
                        
                        # Crear una entrada para cada semana
                        for week in weeks:
                            week_data = complete_weekly_daily[complete_weekly_daily['week_label'] == week]
                            pivot_data[week] = {
                                day: round(float(row['percentage']), 1) 
                                for day, row in zip(
                                    week_data['day_of_week'], 
                                    week_data.to_dict('records')
                                )
                            }
                        
                        # Guardar los datos para la tabla
                        weekly_occupation_data = {
                            'weeks': weeks,
                            'days': day_order,
                            'data': pivot_data
                        }
                        
                        logger.info(f"Tabla de ocupación por semana y día calculada con {len(weeks)} semanas")
                    else:
                        # Si no hay espacios o semanas, crear un diccionario vacío
                        weekly_occupation_data = {'weeks': [], 'days': day_order, 'data': {}}
                        logger.info("No hay espacios disponibles o semanas para calcular la ocupación semanal")
                    
                except Exception as e:
                    logger.error(f"Error al calcular tabla de ocupación por semana y día: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    weekly_occupation_data = {'weeks': [], 'days': day_order, 'data': {}}
                
            except Exception as e:
                logger.error(f"Error al calcular ocupación por día: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Crear gráfico de barras horizontales para ocupación diaria
            try:
                logger.info("Creando gráfico de ocupación diaria...")
                daily_fig["data"] = [{
                    "type": "bar",
                    "y": daily_counts['day_of_week'].tolist(),
                    "x": daily_counts['percentage'].tolist(),
                    "orientation": 'h',
                    "marker": {"color": "#1cc88a"},
                    "text": [f"{p}% ({o} de {total_spaces} espacios)" for p, o in zip(daily_counts['percentage'], daily_counts['occupied_spaces'])],
                    "textposition": "auto",
                    "hoverinfo": "text"
                }]
                
                # Actualizar el layout para mostrar que es ocupación de espacios
                daily_fig["layout"]["title"] = "Ocupación de Espacios por Día"
                daily_fig["layout"]["xaxis"]["title"] = "Porcentaje de Espacios Ocupados"
                
                logger.info("Gráfico de ocupación diaria creado correctamente")
            except Exception as e:
                logger.error(f"Error al crear gráfico de ocupación diaria: {str(e)}")
            
            logger.info(f"Análisis avanzado completado con éxito. Período: {period_label}, Total reservas: {total_bookings_value}")
            
            # NUEVA SECCIÓN: Calcular reservas por espacio y día de la semana
            try:
                logger.info("Calculando tabla de reservas por espacio y día de la semana...")
                
                # Verificar si tenemos la columna common_area_name
                if 'common_area_name' not in df_filtered.columns or 'common_area_id' not in df_filtered.columns:
                    logger.error(f"Columnas necesarias no encontradas. Columnas disponibles: {df_filtered.columns.tolist()}")
                    spaces_reservations_data = {'spaces': [], 'days': day_order, 'data': {}}
                else:
                    # Agrupar por espacio y contar reservas totales
                    space_counts = df_filtered.groupby(['common_area_id', 'common_area_name']).size().reset_index(name='total_reservations')
                    
                    # Ordenar por número de reservas (descendente)
                    space_counts = space_counts.sort_values('total_reservations', ascending=False)
                    
                    # Obtener lista de espacios ordenados
                    spaces = space_counts[['common_area_id', 'common_area_name', 'total_reservations']].to_dict('records')
                    
                    # Calcular reservas por espacio y día de la semana
                    space_day_data = {}
                    
                    for space in spaces:
                        space_id = space['common_area_id']
                        space_name = space['common_area_name']
                        
                        # Filtrar reservas para este espacio
                        space_bookings = df_filtered[df_filtered['common_area_id'] == space_id]
                        
                        # Inicializar conteo por día
                        day_counts = {day: 0 for day in day_order}
                        
                        # Contar reservas por día para este espacio
                        if not space_bookings.empty:
                            day_distribution = space_bookings.groupby('day_of_week').size().to_dict()
                            
                            # Actualizar conteos
                            for day, count in day_distribution.items():
                                if day in day_counts:
                                    day_counts[day] = count
                        
                        # Guardar datos para este espacio
                        space_day_data[space_id] = {
                            'name': space_name,
                            'total': space['total_reservations'],
                            'days': day_counts
                        }
                    
                    # Guardar los datos para la tabla
                    spaces_reservations_data = {
                        'spaces': spaces,
                        'days': day_order,
                        'data': space_day_data
                    }
                    
                    logger.info(f"Tabla de reservas por espacio calculada con {len(spaces)} espacios")
            except Exception as e:
                logger.error(f"Error al calcular tabla de reservas por espacio: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                spaces_reservations_data = {'spaces': [], 'days': day_order, 'data': {}}
        
        except Exception as e:
            logger.error(f"Error general en update_advanced_analytics: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return weekly_fig, daily_fig, avg_weekly, max_day, total_bookings, avg_occupation, weekly_occupation_data, spaces_reservations_data 

    # Callback para exportar el análisis a PDF
    @app.callback(
        [
            Output("download-spaces-pdf", "data"),
            Output("pdf-export-error", "children")
        ],
        [Input("export-spaces-pdf", "n_clicks")],
        [
            State("selected-client-store", "data"),
            State("analysis-period", "value"),
            State("weekly-bookings-chart", "figure"),
            State("daily-occupation-chart", "figure"),
            State("avg-weekly-bookings", "children"),
            State("max-day-occupation", "children"),
            State("total-bookings-period", "children"),
            State("avg-occupation-rate", "children"),
            State("weekly-occupation-data", "data"),
            State("spaces-reservations-data", "data")
        ],
        prevent_initial_call=True
    )
    def export_spaces_to_pdf(n_clicks, client_data, period, weekly_fig, daily_fig, avg_weekly, max_day, total_bookings, avg_occupation, weekly_occupation_data, spaces_reservations_data):
        """
        Exporta el análisis de espacios a un archivo PDF.
        """
        if n_clicks is None:
            return dash.no_update, dash.no_update
        
        try:
            # Logging para depuración
            logger.info(f"Exportando a PDF con período: {period}")
            logger.info(f"Tipo de weekly_fig: {type(weekly_fig)}")
            logger.info(f"Tipo de daily_fig: {type(daily_fig)}")
            
            if isinstance(weekly_fig, dict):
                logger.info(f"weekly_fig es un diccionario con claves: {list(weekly_fig.keys())}")
            if isinstance(daily_fig, dict):
                logger.info(f"daily_fig es un diccionario con claves: {list(daily_fig.keys())}")
            
            # Obtener información del cliente
            client_id = client_data.get("client_id", "all")
            project_id = client_data.get("project_id", "all")
            
            # Obtener el nombre real del cliente a partir del ID
            client_name = "Todos los clientes"
            community_name = "Todas las comunidades"
            
            if client_id != "all":
                try:
                    from utils.api import get_clientes
                    clientes = get_clientes()
                    logger.info(f"Clientes obtenidos: {len(clientes) if isinstance(clientes, list) else 'No es una lista'}")
                    client_match = next((c for c in clientes if str(c.get("id", "")) == str(client_id)), None)
                    if client_match:
                        logger.info(f"Cliente encontrado: {client_match}")
                        # Intentar obtener el nombre con diferentes claves posibles
                        for key in ['nombre', 'name', 'client_name', 'nombre_cliente', 'client']:
                            if key in client_match and client_match[key]:
                                client_name = client_match[key]
                                logger.info(f"Nombre del cliente obtenido con clave '{key}': {client_name}")
                                break
                    else:
                        logger.warning(f"No se encontró cliente con ID: {client_id}")
                except Exception as e:
                    logger.error(f"Error al obtener el nombre del cliente: {str(e)}")
            
            if project_id != "all":
                try:
                    from utils.api import get_projects
                    projects = get_projects(client_id)
                    logger.info(f"Proyectos obtenidos: {len(projects) if isinstance(projects, list) else 'No es una lista'}")
                    project_match = next((p for p in projects if str(p.get("id", "")) == str(project_id)), None)
                    if project_match:
                        logger.info(f"Proyecto encontrado: {project_match}")
                        # Intentar obtener el nombre con diferentes claves posibles
                        for key in ['nombre', 'name', 'project_name', 'nombre_proyecto', 'project']:
                            if key in project_match and project_match[key]:
                                community_name = project_match[key]
                                logger.info(f"Nombre de la comunidad obtenido con clave '{key}': {community_name}")
                                break
                    else:
                        logger.warning(f"No se encontró proyecto con ID: {project_id}")
                except Exception as e:
                    logger.error(f"Error al obtener el nombre de la comunidad: {str(e)}")
            
            logger.info(f"Nombre final del cliente: {client_name}")
            logger.info(f"Nombre final de la comunidad: {community_name}")
            
            # Mapear el valor del período a una etiqueta legible
            period_labels = {
                "last_week": "Última semana",
                "last_month": "Último mes",
                "last_quarter": "Último trimestre",
                "last_year": "Último año",
                "this_year": "Este año hasta hoy",
                "all_time": "Todo el período"
            }
            period_label = period_labels.get(period, "Período seleccionado")
            
            # Generar el PDF
            pdf_content = generate_spaces_report_pdf(
                client_name=client_name,
                community_name=community_name,
                period_label=period_label,
                weekly_bookings_fig=weekly_fig,
                daily_occupation_fig=daily_fig,
                avg_weekly_bookings=avg_weekly,
                max_day_occupation=max_day,
                total_bookings_period=total_bookings,
                avg_occupation_rate=avg_occupation,
                weekly_occupation_data=weekly_occupation_data,
                spaces_reservations_data=spaces_reservations_data
            )
            
            if pdf_content:
                logger.info("PDF generado correctamente")
                # Convertir el contenido del PDF (bytes) a base64 para que sea JSON serializable
                encoded_content = base64.b64encode(pdf_content).decode('utf-8')
                
                return {
                    'content': encoded_content,
                    'filename': f"alfred_spaces_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    'type': 'application/pdf',
                    'base64': True
                }, ""
            else:
                logger.error("Error: PDF content is None")
                return dash.no_update, html.Div("Error al generar el PDF. Por favor, inténtelo de nuevo.", className="alert alert-danger")
        
        except Exception as e:
            logger.error(f"Error al exportar a PDF: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return dash.no_update, html.Div(f"Error al generar el PDF: {str(e)}", className="alert alert-danger")

    # Callback para generar la tabla de ocupación semanal por día
    @app.callback(
        Output("weekly-occupation-table-container", "children"),
        [Input("weekly-occupation-data", "data")],
        prevent_initial_call=True
    )
    def update_weekly_occupation_table(weekly_occupation_data):
        """
        Genera una tabla HTML con los datos de ocupación semanal por día.
        """
        if not weekly_occupation_data or not weekly_occupation_data.get('weeks') or not weekly_occupation_data.get('days'):
            return html.Div()
        
        # Obtener datos
        weeks = weekly_occupation_data.get('weeks', [])
        days = weekly_occupation_data.get('days', [])
        data = weekly_occupation_data.get('data', {})
        
        if not weeks:
            return html.Div()
        
        # Crear la tabla
        table_header = [
            html.Thead(html.Tr(
                [html.Th("Semana", className="text-center")] + 
                [html.Th(day, className="text-center") for day in days]
            ), className="table-primary")
        ]
        
        table_rows = []
        for week in weeks:
            week_values = data.get(week, {})
            row_cells = [html.Td(week, className="fw-bold")]
            
            for day in days:
                value = week_values.get(day, 0)
                # Formatear el valor como porcentaje
                formatted_value = f"{value:.1f}%".replace(".", ",")
                
                # Aplicar clases de color según el valor
                cell_class = ""
                if value > 75:
                    cell_class = "bg-danger text-white"
                elif value > 50:
                    cell_class = "bg-warning"
                elif value > 25:
                    cell_class = "bg-info text-white"
                elif value > 0:
                    cell_class = "bg-success text-white"
                
                row_cells.append(html.Td(formatted_value, className=f"text-center {cell_class}"))
            
            table_rows.append(html.Tr(row_cells))
        
        table_body = [html.Tbody(table_rows)]
        
        # Crear el contenedor de la tabla con título y descripción
        return html.Div([
            dbc.Card([
                dbc.CardHeader("Ocupación Semanal por Día (%)"),
                dbc.CardBody([
                    html.P(
                        "Esta tabla muestra el porcentaje de ocupación para cada día de la semana, desglosado por semanas. "
                        "Los valores representan el porcentaje de reservas realizadas en cada día respecto al total de reservas "
                        "de la semana correspondiente.",
                        className="text-muted mb-3"
                    ),
                    dbc.Table(
                        table_header + table_body,
                        bordered=True,
                        hover=True,
                        responsive=True,
                        striped=True,
                        className="mb-2"
                    ),
                    html.Small(
                        "Nota: Los colores indican el nivel de ocupación: >75% (rojo), >50% (amarillo), >25% (azul), >0% (verde).",
                        className="text-muted"
                    )
                ])
            ])
        ]) 

    # Nuevo callback para generar la tabla de espacios por reservas
    @app.callback(
        Output("spaces-reservations-table-container", "children"),
        [Input("spaces-reservations-data", "data")],
        prevent_initial_call=True
    )
    def update_spaces_reservations_table(spaces_reservations_data):
        """
        Genera una tabla HTML que muestra los espacios ordenados por número de reservas,
        con columnas para el total y el desglose por día de la semana.
        """
        logger.info("Generando tabla de espacios por reservas...")
        
        # Verificar si hay datos
        if not spaces_reservations_data or 'spaces' not in spaces_reservations_data or not spaces_reservations_data['spaces']:
            return html.Div("No hay datos disponibles para generar la tabla de espacios por reservas.", className="alert alert-info")
        
        # Obtener datos
        spaces = spaces_reservations_data.get('spaces', [])
        days = spaces_reservations_data.get('days', [])
        data = spaces_reservations_data.get('data', {})
        
        if not spaces or not days or not data:
            return html.Div("Datos insuficientes para generar la tabla de espacios por reservas.", className="alert alert-info")
        
        # Crear encabezado de la tabla
        header_row = [html.Th("Espacio"), html.Th("Total")]
        for day in days:
            header_row.append(html.Th(day))
        
        # Crear filas de datos
        table_rows = []
        for space in spaces:
            space_id = space['common_area_id']
            space_data = data.get(space_id, {})
            
            if not space_data:
                continue
                
            # Crear fila para este espacio
            row_cells = [
                html.Td(space_data.get('name', 'Desconocido')),
                html.Td(space_data.get('total', 0), className="text-center font-weight-bold")
            ]
            
            # Añadir celdas para cada día
            day_counts = space_data.get('days', {})
            for day in days:
                count = day_counts.get(day, 0)
                
                # Aplicar clases según el valor
                cell_class = "text-center "
                if count > 10:
                    cell_class += "table-danger"
                elif count > 5:
                    cell_class += "table-warning"
                elif count > 0:
                    cell_class += "table-info"
                
                row_cells.append(html.Td(count, className=cell_class))
            
            # Añadir fila a la tabla
            table_rows.append(html.Tr(row_cells))
        
        # Construir la tabla completa
        table = dbc.Table(
            [html.Thead(html.Tr(header_row)), html.Tbody(table_rows)],
            bordered=True,
            hover=True,
            responsive=True,
            striped=True,
            className="mt-3"
        )
        
        # Crear tarjeta con la tabla
        card = dbc.Card([
            dbc.CardHeader([
                html.H5("Espacios por Número de Reservas", className="mb-0")
            ]),
            dbc.CardBody([
                html.P("Esta tabla muestra los espacios ordenados por el número total de reservas, con el desglose por día de la semana.", className="card-text"),
                table,
                html.Small([
                    html.I(className="fas fa-info-circle me-1"),
                    "Los colores indican el nivel de uso: ",
                    html.Span("Alto (>10)", className="badge bg-danger me-1"),
                    html.Span("Medio (>5)", className="badge bg-warning me-1"),
                    html.Span("Bajo (>0)", className="badge bg-info me-1")
                ], className="text-muted mt-2 d-block")
            ])
        ])
        
        return card