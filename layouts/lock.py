from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash

# Layout para la página de Lock
layout = html.Div([
    # Stores locales para datos
    dcc.Store(id="lock-filters-store", data={"client_id": "all", "project_id": "all"}),
    
    dbc.Row([
        dbc.Col([
            html.H1("Lock Management", className="mb-4"),
            html.P("Gestiona y monitorea los accesos y cerraduras inteligentes.", className="lead mb-4"),
            
            # Sección de Filtros
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        # Filtro de cliente
                        dbc.Col([
                            html.Label("Cliente"),
                            dcc.Dropdown(
                                id="lock-client-filter",
                                placeholder="Seleccione un cliente",
                                clearable=False,
                                value="all"
                            )
                        ], width=4),
                        
                        # Filtro de proyecto
                        dbc.Col([
                            html.Label("Proyecto"),
                            dcc.Dropdown(
                                id="lock-project-filter",
                                placeholder="Seleccione un proyecto",
                                clearable=False,
                                disabled=True,
                                value="all"
                            )
                        ], width=4),
                        
                        # Botones de acción
                        dbc.Col([
                            html.Div([
                                dbc.Button(
                                    "Aplicar Filtros",
                                    id="lock-apply-filters-button",
                                    color="primary",
                                    className="me-2"
                                ),
                                dbc.Button(
                                    html.I(className="fas fa-sync"), 
                                    id="refresh-locks-button",
                                    color="light",
                                    title="Actualizar datos"
                                ),
                            ], className="d-flex justify-content-end align-items-end", style={"height": "100%"})
                        ], width=4)
                    ])
                ])
            ], className="mb-4"),
            
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
    from utils.api import get_clientes, get_projects
    
    # Callback para cargar clientes
    @app.callback(
        Output("lock-client-filter", "options"),
        [Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def load_lock_clients(token_data):
        try:
            token = token_data.get('token') if token_data else None
            if not token:
                return [{"label": "Todos los clientes", "value": "all"}]
            
            clientes = get_clientes(jwt_token=token)
            client_options = [{"label": "Todos los clientes", "value": "all"}]
            
            for cliente in clientes:
                if isinstance(cliente, dict):
                    nombre = None
                    id_cliente = None
                    
                    for key in ['nombre', 'name', 'client_name']:
                        if key in cliente:
                            nombre = cliente[key]
                            break
                    
                    for key in ['id', 'client_id', 'id_cliente']:
                        if key in cliente:
                            id_cliente = cliente[key]
                            break
                    
                    if nombre and id_cliente is not None:
                        client_options.append({"label": nombre, "value": str(id_cliente)})
            
            return client_options
        except Exception as e:
            return [{"label": "Error al cargar", "value": "all"}]
    
    # Callback para actualizar proyectos según cliente seleccionado
    @app.callback(
        [Output("lock-project-filter", "options"), Output("lock-project-filter", "disabled")],
        [Input("lock-client-filter", "value"), Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def update_lock_project_options(client_id, token_data):
        if client_id == "all":
            return [{"label": "Todos los proyectos", "value": "all"}], True
        
        try:
            token = token_data.get('token') if token_data else None
            if not token:
                return [{"label": "Todos los proyectos", "value": "all"}], False
            
            projects = get_projects(client_id=client_id, jwt_token=token)
            project_options = [{"label": "Todos los proyectos", "value": "all"}]
            
            for project in projects:
                if isinstance(project, dict):
                    nombre = project.get("name")
                    id_proyecto = project.get("id")
                    
                    if nombre and id_proyecto is not None:
                        project_options.append({"label": nombre, "value": id_proyecto})
            
            return project_options, False
        except Exception as e:
            return [{"label": "Error al cargar", "value": "all"}], False
    
    # Callback para aplicar filtros
    @app.callback(
        Output("lock-filters-store", "data"),
        [Input("lock-apply-filters-button", "n_clicks")],
        [State("lock-client-filter", "value"), State("lock-project-filter", "value")],
        prevent_initial_call=True
    )
    def apply_lock_filters(n_clicks, client_id, project_id):
        if n_clicks:
            return {"client_id": client_id or "all", "project_id": project_id or "all"}
        return dash.no_update
    
    # Callback para actualizar el indicador de filtro
    @app.callback(
        Output("lock-filter-indicator", "children"),
        [Input("lock-filters-store", "data")]
    )
    def update_filter_indicator(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        if client_id == "all" and project_id == "all":
            return html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "Mostrando datos globales de todos los clientes y proyectos"
            ], className="alert alert-info")
        
        # Obtener nombre del cliente
        client_name = "Todos los clientes"
        if client_id != "all":
            clientes = get_clientes()
            client_match = next((c for c in clientes if c.get("id") == client_id or c.get("client_id") == client_id), None)
            if client_match:
                client_name = client_match.get("nombre") or client_match.get("name", f"Cliente {client_id}")
        
        # Obtener nombre del proyecto
        project_name = "Todos los proyectos"
        if project_id != "all":
            projects = get_projects(client_id if client_id != "all" else None)
            project_match = next((p for p in projects if p.get("id") == project_id), None)
            if project_match:
                project_name = project_match.get("name", f"Proyecto {project_id}")
        
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
        [Input("lock-filters-store", "data")]
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
            if client_id == "1":
                cerraduras_activas = "15"
                accesos_hoy = "45"
            elif client_id == "2":
                cerraduras_activas = "12"
                accesos_hoy = "38"
                alertas = "1"
                alertas_status = "1 alerta activa"
            elif client_id == "3":
                cerraduras_activas = "8"
                accesos_hoy = "25"
            elif client_id == "4":
                cerraduras_activas = "7"
                accesos_hoy = "20"
        
        # Si hay un proyecto seleccionado
        if project_id != "all":
            # Datos de ejemplo para el proyecto seleccionado
            cerraduras_activas = "6"
            accesos_hoy = "18"
            if project_id in ["3"]:
                alertas = "1"
                alertas_status = "1 alerta activa"
        
        return cerraduras_activas, cerraduras_activas_status, accesos_hoy, accesos_hoy_change, alertas, alertas_status
    
    # Callback para actualizar la tabla de cerraduras
    @app.callback(
        Output("locks-table-container", "children"),
        [Input("lock-filters-store", "data"), Input("refresh-locks-button", "n_clicks")]
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
        [Input("lock-filters-store", "data"), Input("refresh-history-button", "n_clicks")]
    )
    def update_access_history(selection_data, n_clicks):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Datos de ejemplo para el historial
        history_data = [
            {"fecha": "2025-03-04 12:30", "usuario": "Juan Pérez", "cerradura": "Puerta Principal", "tipo": "Acceso", "metodo": "Tarjeta"},
            {"fecha": "2025-03-04 11:45", "usuario": "María García", "cerradura": "Oficina 101", "tipo": "Acceso", "metodo": "Pin"},
            {"fecha": "2025-03-04 10:15", "usuario": "Carlos López", "cerradura": "Sala de Reuniones", "tipo": "Acceso", "metodo": "Tarjeta"},
            {"fecha": "2025-03-04 09:30", "usuario": "Ana Martín", "cerradura": "Oficina 202", "tipo": "Acceso", "metodo": "Pin"},
            {"fecha": "2025-03-03 18:20", "usuario": "Pedro Ruiz", "cerradura": "Almacén", "tipo": "Acceso", "metodo": "Tarjeta"}
        ]
        
        # Filtrar según los filtros seleccionados
        if client_id != "all" or project_id != "all":
            history_data = history_data[:3]  # Simular filtrado
        
        # Crear tabla
        rows = []
        for access in history_data:
            rows.append(html.Tr([
                html.Td(access["fecha"]),
                html.Td(access["usuario"]),
                html.Td(access["cerradura"]),
                html.Td(html.Span(access["tipo"], className="badge bg-success")),
                html.Td(access["metodo"])
            ]))
        
        return html.Table([
            html.Thead([
                html.Tr([
                    html.Th("Fecha/Hora"),
                    html.Th("Usuario"),
                    html.Th("Cerradura"),
                    html.Th("Tipo"),
                    html.Th("Método")
                ])
            ]),
            html.Tbody(rows)
        ], className="table table-striped table-hover")
    
    # Callback para actualizar los gráficos
    @app.callback(
        [Output("lock-graph-1", "figure"), Output("lock-graph-2", "figure")],
        [Input("lock-filters-store", "data")]
    )
    def update_graphs(selection_data):
        # Datos de ejemplo para los gráficos
        import plotly.graph_objs as go
        
        # Gráfico 1: Accesos por hora
        hours = list(range(24))
        accesos = [2, 1, 0, 0, 1, 3, 8, 12, 15, 18, 20, 22, 25, 18, 16, 14, 12, 10, 8, 6, 4, 3, 2, 1]
        
        graph1 = {
            'data': [go.Bar(x=hours, y=accesos, name='Accesos')],
            'layout': go.Layout(
                title='Accesos por Hora',
                xaxis={'title': 'Hora del día'},
                yaxis={'title': 'Número de accesos'},
                showlegend=False
            )
        }
        
        # Gráfico 2: Tipos de acceso
        tipos = ['Tarjeta', 'Pin', 'Biométrico', 'App Móvil']
        valores = [45, 35, 15, 5]
        
        graph2 = {
            'data': [go.Pie(labels=tipos, values=valores)],
            'layout': go.Layout(title='Distribución por Tipo de Acceso')
        }
        
        return graph1, graph2 