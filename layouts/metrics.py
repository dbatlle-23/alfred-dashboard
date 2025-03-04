from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash

# Layout para la página de Metrics
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Metrics", className="mb-4"),
            html.P("Visualiza y analiza métricas importantes de tu sistema.", className="lead mb-4"),
            
            # Indicador de filtro activo
            html.Div(id="metrics-filter-indicator", className="mb-3"),
            
            # Tarjetas de métricas
            dbc.Row([
                # Métrica 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Total Usuarios", className="card-title text-center"),
                            html.H2(id="metrics-total-usuarios", className="text-center text-primary mb-0"),
                            html.P(id="metrics-total-usuarios-change", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Métrica 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Espacios Activos", className="card-title text-center"),
                            html.H2(id="metrics-espacios-activos", className="text-center text-primary mb-0"),
                            html.P(id="metrics-espacios-activos-change", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Métrica 3
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Accesos", className="card-title text-center"),
                            html.H2(id="metrics-accesos", className="text-center text-primary mb-0"),
                            html.P(id="metrics-accesos-change", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
            ]),
            
            # Gráficos
            dbc.Row([
                # Gráfico 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Consumo Energético"),
                        dbc.CardBody([
                            dcc.Graph(id="metrics-graph-1")
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
                
                # Gráfico 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Ocupación de Espacios"),
                        dbc.CardBody([
                            dcc.Graph(id="metrics-graph-2")
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
            ]),
            
            # Gráfico 3 (ancho completo)
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Tendencias de Consumo"),
                        dbc.CardBody([
                            dcc.Graph(id="metrics-graph-3")
                        ])
                    ], className="shadow-sm")
                ], className="mb-4"),
            ]),
        ])
    ])
])

# Registrar callbacks para la página de Metrics
def register_callbacks(app):
    # Callback para actualizar el indicador de filtro
    @app.callback(
        Output("metrics-filter-indicator", "children"),
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
            Output("metrics-total-usuarios", "children"),
            Output("metrics-total-usuarios-change", "children"),
            Output("metrics-espacios-activos", "children"),
            Output("metrics-espacios-activos-change", "children"),
            Output("metrics-accesos", "children"),
            Output("metrics-accesos-change", "children")
        ],
        [Input("selected-client-store", "data")]
    )
    def update_metrics(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Valores por defecto (todos los clientes/proyectos)
        total_usuarios = "1,234"
        total_usuarios_change = "↑ 12% desde el mes pasado"
        espacios_activos = "567"
        espacios_activos_change = "↑ 8% desde el mes pasado"
        accesos = "9,876"
        accesos_change = "↑ 15% desde el mes pasado"
        
        # Si hay un cliente seleccionado
        if client_id != "all":
            # Datos de ejemplo para el cliente seleccionado
            if client_id == 1:
                total_usuarios = "432"
                espacios_activos = "210"
                accesos = "3,456"
            elif client_id == 2:
                total_usuarios = "321"
                espacios_activos = "180"
                accesos = "2,789"
            elif client_id == 3:
                total_usuarios = "256"
                espacios_activos = "120"
                accesos = "1,987"
            elif client_id == 4:
                total_usuarios = "225"
                espacios_activos = "57"
                accesos = "1,644"
        
        # Si hay un proyecto seleccionado
        if project_id != "all":
            # Datos de ejemplo para el proyecto seleccionado
            if project_id == 1:
                total_usuarios = "210"
                espacios_activos = "120"
                accesos = "1,800"
            elif project_id == 2:
                total_usuarios = "222"
                espacios_activos = "90"
                accesos = "1,656"
            elif project_id == 3:
                total_usuarios = "180"
                espacios_activos = "100"
                accesos = "1,400"
            elif project_id == 4:
                total_usuarios = "141"
                espacios_activos = "80"
                accesos = "1,389"
            elif project_id == 5:
                total_usuarios = "156"
                espacios_activos = "70"
                accesos = "1,200"
            elif project_id == 6:
                total_usuarios = "125"
                espacios_activos = "57"
                accesos = "1,044"
        
        return total_usuarios, total_usuarios_change, espacios_activos, espacios_activos_change, accesos, accesos_change
    
    # Callback para actualizar los gráficos según el filtro seleccionado
    @app.callback(
        [
            Output("metrics-graph-1", "figure"),
            Output("metrics-graph-2", "figure"),
            Output("metrics-graph-3", "figure")
        ],
        [Input("selected-client-store", "data")]
    )
    def update_graphs(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Aquí implementarías la lógica real para obtener datos según los filtros
        # Por ahora, usamos datos de ejemplo
        
        # Gráfico 1: Consumo Energético
        figure1 = {
            'data': [
                {'x': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'], 'y': [100, 120, 90, 80, 110, 105], 'type': 'bar', 'name': 'Electricidad'},
                {'x': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'], 'y': [50, 60, 45, 40, 55, 52], 'type': 'bar', 'name': 'Agua'}
            ],
            'layout': {
                'title': f'Consumo Energético {"Global" if client_id == "all" else "por Cliente" if project_id == "all" else "por Proyecto"}',
                'barmode': 'group'
            }
        }
        
        # Gráfico 2: Ocupación de Espacios
        figure2 = {
            'data': [
                {'labels': ['Ocupados', 'Disponibles'], 'values': [65, 35], 'type': 'pie', 'name': 'Ocupación'}
            ],
            'layout': {
                'title': f'Ocupación de Espacios {"Global" if client_id == "all" else "por Cliente" if project_id == "all" else "por Proyecto"}'
            }
        }
        
        # Gráfico 3: Tendencias de Consumo
        figure3 = {
            'data': [
                {'x': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'], 'y': [100, 110, 120, 115, 130, 125], 'type': 'scatter', 'name': '2023'},
                {'x': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'], 'y': [90, 95, 100, 105, 110, 115], 'type': 'scatter', 'name': '2022'}
            ],
            'layout': {
                'title': f'Tendencias de Consumo {"Global" if client_id == "all" else "por Cliente" if project_id == "all" else "por Proyecto"}'
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
            figure2['data'][0]['values'] = [75, 25] if project_id != "all" else [70, 30] if client_id != "all" else [65, 35]
            
            # Ajustar gráfico 3
            for trace in figure3['data']:
                trace['y'] = [val * multiplier for val in trace['y']]
        
        return figure1, figure2, figure3 