from dash import html, dcc
import dash_bootstrap_components as dbc

# Layout para la página de Metrics
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Metrics", className="mb-4"),
            html.P("Visualiza y analiza métricas importantes de tu sistema.", className="lead mb-4"),
            
            # Tarjetas de métricas
            dbc.Row([
                # Métrica 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Total Usuarios", className="card-title text-center"),
                            html.H2("1,234", className="text-center text-primary mb-0"),
                            html.P("↑ 12% desde el mes pasado", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Métrica 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Espacios Activos", className="card-title text-center"),
                            html.H2("567", className="text-center text-primary mb-0"),
                            html.P("↑ 8% desde el mes pasado", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Métrica 3
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Accesos", className="card-title text-center"),
                            html.H2("9,876", className="text-center text-primary mb-0"),
                            html.P("↑ 15% desde el mes pasado", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
            ]),
            
            # Gráficos
            dbc.Row([
                # Gráfico 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Usuarios por Día"),
                        dbc.CardBody([
                            dcc.Graph(
                                figure={
                                    'data': [
                                        {'x': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'], 
                                         'y': [120, 150, 170, 180, 190, 110, 100], 
                                         'type': 'bar', 
                                         'name': 'Usuarios'}
                                    ],
                                    'layout': {
                                        'title': 'Actividad Diaria',
                                        'height': 300,
                                        'margin': {'l': 40, 'r': 10, 't': 40, 'b': 30}
                                    }
                                }
                            )
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
                
                # Gráfico 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Distribución de Accesos"),
                        dbc.CardBody([
                            dcc.Graph(
                                figure={
                                    'data': [
                                        {'labels': ['App', 'Web', 'API'], 
                                         'values': [45, 35, 20], 
                                         'type': 'pie', 
                                         'name': 'Accesos'}
                                    ],
                                    'layout': {
                                        'title': 'Tipo de Acceso',
                                        'height': 300,
                                        'margin': {'l': 40, 'r': 10, 't': 40, 'b': 30}
                                    }
                                }
                            )
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
            ]),
            
            # Tabla de datos recientes
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Actividad Reciente"),
                        dbc.CardBody([
                            html.Div([
                                html.Table([
                                    html.Thead([
                                        html.Tr([
                                            html.Th("Usuario"),
                                            html.Th("Acción"),
                                            html.Th("Fecha"),
                                            html.Th("Estado")
                                        ])
                                    ]),
                                    html.Tbody([
                                        html.Tr([
                                            html.Td("usuario1@example.com"),
                                            html.Td("Login"),
                                            html.Td("2025-03-04 12:30"),
                                            html.Td(html.Span("Exitoso", className="badge bg-success"))
                                        ]),
                                        html.Tr([
                                            html.Td("usuario2@example.com"),
                                            html.Td("Acceso a Espacio"),
                                            html.Td("2025-03-04 12:25"),
                                            html.Td(html.Span("Exitoso", className="badge bg-success"))
                                        ]),
                                        html.Tr([
                                            html.Td("usuario3@example.com"),
                                            html.Td("Login"),
                                            html.Td("2025-03-04 12:15"),
                                            html.Td(html.Span("Fallido", className="badge bg-danger"))
                                        ]),
                                        html.Tr([
                                            html.Td("usuario4@example.com"),
                                            html.Td("Acceso a Espacio"),
                                            html.Td("2025-03-04 12:10"),
                                            html.Td(html.Span("Exitoso", className="badge bg-success"))
                                        ]),
                                    ])
                                ], className="table table-striped table-hover")
                            ], style={"overflowX": "auto"})
                        ])
                    ], className="shadow-sm")
                ], className="mb-4")
            ])
        ])
    ])
]) 