from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash

# Layout para la página de Lock
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Lock Management", className="mb-4"),
            html.P("Gestiona y monitorea los accesos y cerraduras inteligentes.", className="lead mb-4"),
            
            # Indicador de filtro activo
            html.Div(id="lock-filter-indicator", className="mb-3"),
            
            # Tarjetas de estado
            dbc.Row([
                # Estado 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Cerraduras Activas", className="card-title text-center"),
                            html.H2(id="lock-cerraduras-activas", className="text-center text-primary mb-0"),
                            html.P(id="lock-cerraduras-activas-status", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Estado 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Accesos Hoy", className="card-title text-center"),
                            html.H2(id="lock-accesos-hoy", className="text-center text-primary mb-0"),
                            html.P(id="lock-accesos-hoy-change", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Estado 3
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Alertas", className="card-title text-center"),
                            html.H2(id="lock-alertas", className="text-center text-success mb-0"),
                            html.P(id="lock-alertas-status", className="text-muted text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
            ]),
            
            # Lista de cerraduras
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Cerraduras", className="mb-0 d-inline"),
                            dbc.Button(
                                [html.I(className="fas fa-sync-alt")],
                                color="link",
                                className="float-end",
                                id="refresh-locks-button"
                            )
                        ]),
                        dbc.CardBody([
                            html.Div(id="locks-table-container")
                        ])
                    ], className="shadow-sm")
                ], className="mb-4"),
            ]),
            
            # Gráficos
            dbc.Row([
                # Gráfico 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Accesos por Hora"),
                        dbc.CardBody([
                            dcc.Graph(id="lock-graph-1")
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
                
                # Gráfico 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Tipos de Acceso"),
                        dbc.CardBody([
                            dcc.Graph(id="lock-graph-2")
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
            ]),
            
            # Historial de accesos
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Historial de Accesos", className="mb-0 d-inline"),
                            dbc.Button(
                                [html.I(className="fas fa-sync-alt")],
                                color="link",
                                className="float-end",
                                id="refresh-history-button"
                            )
                        ]),
                        dbc.CardBody([
                            html.Div(id="access-history-container")
                        ])
                    ], className="shadow-sm")
                ], className="mb-4"),
            ]),
        ])
    ])
])

# Registrar callbacks para la página de Lock
def register_callbacks(app):
    # Callback para actualizar el indicador de filtro
    @app.callback(
        Output("lock-filter-indicator", "children"),
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
            Output("lock-cerraduras-activas", "children"),
            Output("lock-cerraduras-activas-status", "children"),
            Output("lock-accesos-hoy", "children"),
            Output("lock-accesos-hoy-change", "children"),
            Output("lock-alertas", "children"),
            Output("lock-alertas-status", "children")
        ],
        [Input("selected-client-store", "data")]
    )
    def update_metrics(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Valores por defecto (todos los clientes/proyectos)
        cerraduras_activas = "42"
        cerraduras_activas_status = "100% en línea"
        accesos_hoy = "128"
        accesos_hoy_change = "↑ 12% vs. ayer"
        alertas = "0"
        alertas_status = "Sin alertas activas"
        
        # Si hay un cliente seleccionado
        if client_id != "all":
            # Datos de ejemplo para el cliente seleccionado
            if client_id == 1:
                cerraduras_activas = "15"
                accesos_hoy = "45"
            elif client_id == 2:
                cerraduras_activas = "12"
                accesos_hoy = "38"
                alertas = "1"
                alertas_status = "1 alerta activa"
            elif client_id == 3:
                cerraduras_activas = "8"
                accesos_hoy = "25"
            elif client_id == 4:
                cerraduras_activas = "7"
                accesos_hoy = "20"
        
        # Si hay un proyecto seleccionado
        if project_id != "all":
            # Datos de ejemplo para el proyecto seleccionado
            if project_id == 1:
                cerraduras_activas = "8"
                accesos_hoy = "25"
            elif project_id == 2:
                cerraduras_activas = "7"
                accesos_hoy = "20"
            elif project_id == 3:
                cerraduras_activas = "6"
                accesos_hoy = "18"
                alertas = "1"
                alertas_status = "1 alerta activa"
            elif project_id == 4:
                cerraduras_activas = "6"
                accesos_hoy = "20"
            elif project_id == 5:
                cerraduras_activas = "8"
                accesos_hoy = "25"
            elif project_id == 6:
                cerraduras_activas = "7"
                accesos_hoy = "20"
        
        return cerraduras_activas, cerraduras_activas_status, accesos_hoy, accesos_hoy_change, alertas, alertas_status
    
    # Callback para actualizar la tabla de cerraduras
    @app.callback(
        Output("locks-table-container", "children"),
        [Input("selected-client-store", "data"), Input("refresh-locks-button", "n_clicks")]
    )
    def update_locks_table(selection_data, n_clicks):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Crear tabla de cerraduras
        locks_table = html.Table([
            html.Thead([
                html.Tr([
                    html.Th("ID"),
                    html.Th("Nombre"),
                    html.Th("Ubicación"),
                    html.Th("Estado"),
                    html.Th("Batería"),
                    html.Th("Último Acceso"),
                    html.Th("Acciones")
                ])
            ]),
            html.Tbody(id="locks-table-body")
        ], className="table table-striped table-hover")
        
        # Datos de ejemplo para la tabla
        locks_data = [
            {"id": "L001", "nombre": "Puerta Principal", "ubicacion": "Entrada", "estado": "Online", "bateria": "95%", "ultimo_acceso": "2025-03-04 12:30"},
            {"id": "L002", "nombre": "Oficina 101", "ubicacion": "Piso 1", "estado": "Online", "bateria": "87%", "ultimo_acceso": "2025-03-04 11:45"},
            {"id": "L003", "nombre": "Sala de Reuniones", "ubicacion": "Piso 2", "estado": "Online", "bateria": "92%", "ultimo_acceso": "2025-03-04 10:15"},
            {"id": "L004", "nombre": "Almacén", "ubicacion": "Sótano", "estado": "Online", "bateria": "78%", "ultimo_acceso": "2025-03-03 18:20"},
            {"id": "L005", "nombre": "Oficina 202", "ubicacion": "Piso 2", "estado": "Online", "bateria": "85%", "ultimo_acceso": "2025-03-04 09:30"},
        ]
        
        # Filtrar datos según cliente/proyecto
        if client_id != "all" or project_id != "all":
            # En un caso real, filtrarías los datos según el cliente/proyecto
            # Por ahora, simplemente reducimos la lista para simular el filtrado
            locks_data = locks_data[:3] if client_id != "all" else locks_data
            locks_data = locks_data[:2] if project_id != "all" else locks_data
        
        # Crear filas de la tabla
        rows = []
        for lock in locks_data:
            row = html.Tr([
                html.Td(lock["id"]),
                html.Td(lock["nombre"]),
                html.Td(lock["ubicacion"]),
                html.Td(html.Span("Online", className="badge bg-success") if lock["estado"] == "Online" else html.Span("Offline", className="badge bg-danger")),
                html.Td([
                    dbc.Progress(value=int(lock["bateria"].replace("%", "")), color="success" if int(lock["bateria"].replace("%", "")) > 80 else "warning", className="mb-0")
                ]),
                html.Td(lock["ultimo_acceso"]),
                html.Td([
                    dbc.ButtonGroup([
                        dbc.Button([html.I(className="fas fa-eye")], color="primary", size="sm", className="me-1"),
                        dbc.Button([html.I(className="fas fa-lock-open")], color="success", size="sm", className="me-1"),
                        dbc.Button([html.I(className="fas fa-cog")], color="secondary", size="sm")
                    ], size="sm")
                ])
            ])
            rows.append(row)
        
        # Actualizar el cuerpo de la tabla
        locks_table.children[1].children = rows
        
        return locks_table
    
    # Callback para actualizar el historial de accesos
    @app.callback(
        Output("access-history-container", "children"),
        [Input("selected-client-store", "data"), Input("refresh-history-button", "n_clicks")]
    )
    def update_access_history(selection_data, n_clicks):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Crear tabla de historial de accesos
        history_table = html.Table([
            html.Thead([
                html.Tr([
                    html.Th("ID"),
                    html.Th("Usuario"),
                    html.Th("Cerradura"),
                    html.Th("Fecha/Hora"),
                    html.Th("Tipo"),
                    html.Th("Estado"),
                    html.Th("Detalles")
                ])
            ]),
            html.Tbody(id="history-table-body")
        ], className="table table-striped table-hover")
        
        # Datos de ejemplo para la tabla
        history_data = [
            {"id": "A001", "usuario": "usuario1@example.com", "cerradura": "Puerta Principal", "fecha": "2025-03-04 12:30", "tipo": "App", "estado": "Exitoso"},
            {"id": "A002", "usuario": "usuario2@example.com", "cerradura": "Oficina 101", "fecha": "2025-03-04 12:25", "tipo": "Tarjeta", "estado": "Exitoso"},
            {"id": "A003", "usuario": "usuario3@example.com", "cerradura": "Sala de Reuniones", "fecha": "2025-03-04 12:15", "tipo": "App", "estado": "Fallido"},
            {"id": "A004", "usuario": "usuario4@example.com", "cerradura": "Almacén", "fecha": "2025-03-04 12:10", "tipo": "PIN", "estado": "Exitoso"},
            {"id": "A005", "usuario": "usuario5@example.com", "cerradura": "Oficina 202", "fecha": "2025-03-04 12:05", "tipo": "App", "estado": "Exitoso"},
        ]
        
        # Filtrar datos según cliente/proyecto
        if client_id != "all" or project_id != "all":
            # En un caso real, filtrarías los datos según el cliente/proyecto
            # Por ahora, simplemente reducimos la lista para simular el filtrado
            history_data = history_data[:3] if client_id != "all" else history_data
            history_data = history_data[:2] if project_id != "all" else history_data
        
        # Crear filas de la tabla
        rows = []
        for access in history_data:
            row = html.Tr([
                html.Td(access["id"]),
                html.Td(access["usuario"]),
                html.Td(access["cerradura"]),
                html.Td(access["fecha"]),
                html.Td(html.Span(access["tipo"], className="badge bg-info")),
                html.Td(html.Span("Exitoso", className="badge bg-success") if access["estado"] == "Exitoso" else html.Span("Fallido", className="badge bg-danger")),
                html.Td([
                    dbc.Button([html.I(className="fas fa-info-circle")], color="link", size="sm")
                ])
            ])
            rows.append(row)
        
        # Actualizar el cuerpo de la tabla
        history_table.children[1].children = rows
        
        return history_table
    
    # Callback para actualizar los gráficos
    @app.callback(
        [Output("lock-graph-1", "figure"), Output("lock-graph-2", "figure")],
        [Input("selected-client-store", "data")]
    )
    def update_graphs(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Gráfico 1: Accesos por Hora
        figure1 = {
            'data': [
                {'x': ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00'], 
                 'y': [5, 12, 18, 15, 22, 10, 14, 16, 19, 23, 17, 8], 
                 'type': 'bar', 
                 'name': 'Accesos'}
            ],
            'layout': {
                'title': f'Accesos por Hora {"Global" if client_id == "all" else "por Cliente" if project_id == "all" else "por Proyecto"}',
                'height': 300,
                'margin': {'l': 40, 'r': 10, 't': 40, 'b': 30}
            }
        }
        
        # Gráfico 2: Tipos de Acceso
        figure2 = {
            'data': [
                {'labels': ['App', 'Tarjeta', 'PIN', 'Biométrico'], 
                 'values': [45, 30, 15, 10], 
                 'type': 'pie', 
                 'name': 'Tipos de Acceso'}
            ],
            'layout': {
                'title': f'Tipos de Acceso {"Global" if client_id == "all" else "por Cliente" if project_id == "all" else "por Proyecto"}',
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
                trace['y'] = [int(val * multiplier) for val in trace['y']]
            
            # Ajustar gráfico 2
            if client_id != "all":
                figure2['data'][0]['values'] = [50, 25, 15, 10]
            if project_id != "all":
                figure2['data'][0]['values'] = [60, 20, 15, 5]
        
        return figure1, figure2 