from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash

# Layout para la página de Spaces
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Spaces Management", className="mb-4"),
            html.P("Gestiona y monitorea los espacios inteligentes de tu organización.", className="lead mb-4"),
            
            # Indicador de filtro activo
            html.Div(id="spaces-filter-indicator", className="mb-3"),
            
            # Tarjetas de resumen
            dbc.Row([
                # Resumen 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Espacios Totales", className="card-title text-center"),
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
            
            # Filtros y búsqueda
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Filtros y Búsqueda"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Tipo de Espacio"),
                                    dcc.Dropdown(
                                        id="space-type-filter",
                                        options=[
                                            {"label": "Todos", "value": "all"},
                                            {"label": "Oficina", "value": "oficina"},
                                            {"label": "Sala de Reuniones", "value": "reunion"},
                                            {"label": "Espacio Común", "value": "comun"},
                                            {"label": "Almacén", "value": "almacen"}
                                        ],
                                        value="all",
                                        clearable=False,
                                        className="mb-3"
                                    )
                                ], md=4),
                                dbc.Col([
                                    html.Label("Estado"),
                                    dcc.Dropdown(
                                        id="space-status-filter",
                                        options=[
                                            {"label": "Todos", "value": "all"},
                                            {"label": "Disponible", "value": "disponible"},
                                            {"label": "Ocupado", "value": "ocupado"},
                                            {"label": "Reservado", "value": "reservado"},
                                            {"label": "Mantenimiento", "value": "mantenimiento"}
                                        ],
                                        value="all",
                                        clearable=False,
                                        className="mb-3"
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
                                        marks={i: str(i) for i in range(0, 21, 5)},
                                        className="mb-3"
                                    )
                                ], md=4),
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Búsqueda"),
                                    dbc.InputGroup([
                                        dbc.Input(id="space-search", placeholder="Buscar por nombre o ID..."),
                                        dbc.Button([html.I(className="fas fa-search")], color="primary")
                                    ], className="mb-3")
                                ], md=8),
                                dbc.Col([
                                    html.Label("Acciones"),
                                    dbc.Button([html.I(className="fas fa-filter me-2"), "Aplicar Filtros"], color="primary", className="me-2", id="apply-space-filters"),
                                    dbc.Button([html.I(className="fas fa-sync-alt me-2"), "Reiniciar"], color="secondary", id="reset-space-filters")
                                ], md=4, className="d-flex align-items-end")
                            ])
                        ])
                    ], className="shadow-sm")
                ], className="mb-4"),
            ]),
            
            # Lista de espacios
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Espacios", className="mb-0 d-inline"),
                            dbc.Button(
                                [html.I(className="fas fa-sync-alt")],
                                color="link",
                                className="float-end",
                                id="refresh-spaces-button"
                            )
                        ]),
                        dbc.CardBody([
                            html.Div(id="spaces-table-container")
                        ])
                    ], className="shadow-sm")
                ], className="mb-4"),
            ]),
            
            # Gráficos
            dbc.Row([
                # Gráfico 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Ocupación por Tipo de Espacio"),
                        dbc.CardBody([
                            dcc.Graph(id="spaces-graph-1")
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
                
                # Gráfico 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Reservas por Día"),
                        dbc.CardBody([
                            dcc.Graph(id="spaces-graph-2")
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
            ]),
            
            # Calendario de reservas
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Calendario de Reservas"),
                        dbc.CardBody([
                            html.Div(id="spaces-calendar-container", style={"height": "400px"})
                        ])
                    ], className="shadow-sm")
                ], className="mb-4"),
            ]),
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
                "Mostrando datos globales de todos los clientes y proyectos"
            ], className="alert alert-info")
        
        from utils.api import get_clientes, get_projects
        
        # Obtener nombre del cliente
        client_name = "Todos los clientes"
        if client_id != "all":
            clientes = get_clientes()
            client_match = next((c for c in clientes if c["id"] == client_id), None)
            if client_match:
                client_name = client_match["nombre"]
        
        # Obtener nombre del proyecto
        project_name = "Todos los proyectos"
        if project_id != "all":
            projects = get_projects(client_id if client_id != "all" else None)
            project_match = next((p for p in projects if p["id"] == project_id), None)
            if project_match:
                project_name = project_match["nombre"]
        
        if project_id == "all":
            return html.Div([
                html.I(className="fas fa-filter me-2"),
                f"Filtrando datos para: {client_name}"
            ], className="alert alert-primary")
        else:
            return html.Div([
                html.I(className="fas fa-filter me-2"),
                f"Filtrando datos para: {client_name} / {project_name}"
            ], className="alert alert-primary")
    
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
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Valores por defecto (todos los clientes/proyectos)
        espacios_total = "24"
        espacios_total_change = "3 nuevos este mes"
        ocupacion = "68%"
        ocupacion_detail = "16 espacios ocupados"
        reservas = "12"
        reservas_change = "↑ 20% vs. ayer"
        
        # Si hay un cliente seleccionado
        if client_id != "all":
            # Datos de ejemplo para el cliente seleccionado
            if client_id == 1:
                espacios_total = "10"
                ocupacion = "70%"
                ocupacion_detail = "7 espacios ocupados"
                reservas = "5"
            elif client_id == 2:
                espacios_total = "8"
                ocupacion = "75%"
                ocupacion_detail = "6 espacios ocupados"
                reservas = "4"
            elif client_id == 3:
                espacios_total = "6"
                ocupacion = "50%"
                ocupacion_detail = "3 espacios ocupados"
                reservas = "2"
            elif client_id == 4:
                espacios_total = "4"
                ocupacion = "25%"
                ocupacion_detail = "1 espacio ocupado"
                reservas = "1"
        
        # Si hay un proyecto seleccionado
        if project_id != "all":
            # Datos de ejemplo para el proyecto seleccionado
            if project_id == 1:
                espacios_total = "5"
                ocupacion = "80%"
                ocupacion_detail = "4 espacios ocupados"
                reservas = "3"
            elif project_id == 2:
                espacios_total = "5"
                ocupacion = "60%"
                ocupacion_detail = "3 espacios ocupados"
                reservas = "2"
            elif project_id == 3:
                espacios_total = "4"
                ocupacion = "75%"
                ocupacion_detail = "3 espacios ocupados"
                reservas = "2"
            elif project_id == 4:
                espacios_total = "4"
                ocupacion = "50%"
                ocupacion_detail = "2 espacios ocupados"
                reservas = "2"
            elif project_id == 5:
                espacios_total = "6"
                ocupacion = "50%"
                ocupacion_detail = "3 espacios ocupados"
                reservas = "2"
            elif project_id == 6:
                espacios_total = "4"
                ocupacion = "25%"
                ocupacion_detail = "1 espacio ocupado"
                reservas = "1"
        
        return espacios_total, espacios_total_change, ocupacion, ocupacion_detail, reservas, reservas_change
    
    # Callback para actualizar la tabla de espacios
    @app.callback(
        Output("spaces-table-container", "children"),
        [
            Input("selected-client-store", "data"), 
            Input("refresh-spaces-button", "n_clicks"),
            Input("apply-space-filters", "n_clicks")
        ],
        [
            State("space-type-filter", "value"),
            State("space-status-filter", "value"),
            State("space-capacity-filter", "value"),
            State("space-search", "value")
        ]
    )
    def update_spaces_table(selection_data, refresh_clicks, apply_clicks, space_type, space_status, space_capacity, space_search):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Crear tabla de espacios
        spaces_table = html.Table([
            html.Thead([
                html.Tr([
                    html.Th("ID"),
                    html.Th("Nombre"),
                    html.Th("Tipo"),
                    html.Th("Capacidad"),
                    html.Th("Estado"),
                    html.Th("Próxima Reserva"),
                    html.Th("Acciones")
                ])
            ]),
            html.Tbody(id="spaces-table-body")
        ], className="table table-striped table-hover")
        
        # Datos de ejemplo para la tabla
        spaces_data = [
            {"id": "S001", "nombre": "Sala Principal", "tipo": "reunion", "capacidad": 12, "estado": "disponible", "proxima_reserva": "2025-03-04 15:00"},
            {"id": "S002", "nombre": "Oficina 101", "tipo": "oficina", "capacidad": 4, "estado": "ocupado", "proxima_reserva": "N/A"},
            {"id": "S003", "nombre": "Sala de Conferencias", "tipo": "reunion", "capacidad": 20, "estado": "reservado", "proxima_reserva": "2025-03-04 14:00"},
            {"id": "S004", "nombre": "Espacio Común", "tipo": "comun", "capacidad": 15, "estado": "disponible", "proxima_reserva": "2025-03-05 10:00"},
            {"id": "S005", "nombre": "Almacén 1", "tipo": "almacen", "capacidad": 2, "estado": "mantenimiento", "proxima_reserva": "N/A"},
            {"id": "S006", "nombre": "Oficina 102", "tipo": "oficina", "capacidad": 3, "estado": "disponible", "proxima_reserva": "2025-03-04 16:30"},
            {"id": "S007", "nombre": "Sala de Reuniones 2", "tipo": "reunion", "capacidad": 8, "estado": "ocupado", "proxima_reserva": "N/A"},
        ]
        
        # Filtrar datos según cliente/proyecto
        if client_id != "all" or project_id != "all":
            # En un caso real, filtrarías los datos según el cliente/proyecto
            # Por ahora, simplemente reducimos la lista para simular el filtrado
            spaces_data = spaces_data[:5] if client_id != "all" else spaces_data
            spaces_data = spaces_data[:3] if project_id != "all" else spaces_data
        
        # Aplicar filtros adicionales
        filtered_data = spaces_data
        
        # Filtrar por tipo de espacio
        if space_type and space_type != "all":
            filtered_data = [s for s in filtered_data if s["tipo"] == space_type]
        
        # Filtrar por estado
        if space_status and space_status != "all":
            filtered_data = [s for s in filtered_data if s["estado"] == space_status]
        
        # Filtrar por capacidad mínima
        if space_capacity and space_capacity > 0:
            filtered_data = [s for s in filtered_data if s["capacidad"] >= space_capacity]
        
        # Filtrar por búsqueda
        if space_search:
            search_term = space_search.lower()
            filtered_data = [s for s in filtered_data if search_term in s["nombre"].lower() or search_term in s["id"].lower()]
        
        # Crear filas de la tabla
        rows = []
        for space in filtered_data:
            # Determinar el color del badge según el estado
            badge_color = {
                "disponible": "success",
                "ocupado": "danger",
                "reservado": "warning",
                "mantenimiento": "secondary"
            }.get(space["estado"], "primary")
            
            # Formatear el estado para mostrar
            estado_display = {
                "disponible": "Disponible",
                "ocupado": "Ocupado",
                "reservado": "Reservado",
                "mantenimiento": "Mantenimiento"
            }.get(space["estado"], space["estado"].capitalize())
            
            # Formatear el tipo para mostrar
            tipo_display = {
                "oficina": "Oficina",
                "reunion": "Sala de Reuniones",
                "comun": "Espacio Común",
                "almacen": "Almacén"
            }.get(space["tipo"], space["tipo"].capitalize())
            
            row = html.Tr([
                html.Td(space["id"]),
                html.Td(space["nombre"]),
                html.Td(tipo_display),
                html.Td(f"{space['capacidad']} personas"),
                html.Td(html.Span(estado_display, className=f"badge bg-{badge_color}")),
                html.Td(space["proxima_reserva"]),
                html.Td([
                    dbc.ButtonGroup([
                        dbc.Button([html.I(className="fas fa-eye")], color="primary", size="sm", className="me-1"),
                        dbc.Button([html.I(className="fas fa-calendar-plus")], color="success", size="sm", className="me-1"),
                        dbc.Button([html.I(className="fas fa-cog")], color="secondary", size="sm")
                    ], size="sm")
                ])
            ])
            rows.append(row)
        
        # Actualizar el cuerpo de la tabla
        spaces_table.children[1].children = rows
        
        return spaces_table
    
    # Callback para actualizar los gráficos
    @app.callback(
        [Output("spaces-graph-1", "figure"), Output("spaces-graph-2", "figure")],
        [Input("selected-client-store", "data")]
    )
    def update_graphs(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Gráfico 1: Ocupación por Tipo de Espacio
        figure1 = {
            'data': [
                {'x': ['Oficinas', 'Salas de Reuniones', 'Espacios Comunes', 'Almacenes'], 
                 'y': [75, 60, 40, 20], 
                 'type': 'bar', 
                 'name': 'Ocupación (%)'}
            ],
            'layout': {
                'title': f'Ocupación por Tipo de Espacio {"Global" if client_id == "all" else "por Cliente" if project_id == "all" else "por Proyecto"}',
                'height': 300,
                'margin': {'l': 40, 'r': 10, 't': 40, 'b': 30}
            }
        }
        
        # Gráfico 2: Reservas por Día
        figure2 = {
            'data': [
                {'x': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'], 
                 'y': [15, 18, 20, 17, 12, 5, 3], 
                 'type': 'scatter', 
                 'name': 'Reservas'}
            ],
            'layout': {
                'title': f'Reservas por Día {"Global" if client_id == "all" else "por Cliente" if project_id == "all" else "por Proyecto"}',
                'height': 300,
                'margin': {'l': 40, 'r': 10, 't': 40, 'b': 30}
            }
        }
        
        # Modificar datos según el filtro seleccionado
        if client_id != "all" or project_id != "all":
            # Ajustar los datos de ejemplo para mostrar diferencias
            multiplier = 0.8 if client_id != "all" else 1
            multiplier = 0.6 if project_id != "all" else multiplier
            
            # Ajustar gráfico 1
            for trace in figure1['data']:
                trace['y'] = [val * multiplier for val in trace['y']]
            
            # Ajustar gráfico 2
            for trace in figure2['data']:
                trace['y'] = [int(val * multiplier) for val in trace['y']]
        
        return figure1, figure2
    
    # Callback para actualizar el calendario de reservas
    @app.callback(
        Output("spaces-calendar-container", "children"),
        [Input("selected-client-store", "data")]
    )
    def update_calendar(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, mostramos un mensaje de placeholder
        
        # Mensaje de placeholder para el calendario
        calendar_placeholder = html.Div([
            html.P([
                html.I(className="fas fa-calendar-alt me-2"),
                f"Calendario de reservas {'' if client_id == 'all' else 'para el cliente seleccionado'} {'' if project_id == 'all' else 'y proyecto seleccionado'}."
            ], className="text-center mt-5"),
            html.P([
                "En un entorno real, aquí se mostraría un calendario interactivo con las reservas programadas."
            ], className="text-center text-muted"),
            html.Div([
                dbc.Button([html.I(className="fas fa-plus me-2"), "Nueva Reserva"], color="primary", className="me-2"),
                dbc.Button([html.I(className="fas fa-calendar-week me-2"), "Ver Agenda"], color="secondary")
            ], className="text-center mt-3")
        ])
        
        return calendar_placeholder
    
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