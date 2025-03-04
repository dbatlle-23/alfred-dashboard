from dash import html, dcc, no_update
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash
from utils.db_utils import get_common_areas_bookings, get_unique_common_areas
import pandas as pd
from datetime import datetime
from utils.logging import get_logger
import math

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
        prevent_initial_call=False
    )
    def initialize_pagination(filter_indicator):
        # Este callback se ejecuta al cargar la página y establece los valores iniciales
        return 1, 10 