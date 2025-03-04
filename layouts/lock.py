from dash import html, dcc
import dash_bootstrap_components as dbc

# Layout para la página de Lock
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Lock Management", className="mb-4"),
            html.P("Gestiona y monitorea los accesos y cerraduras inteligentes.", className="lead mb-4"),
            
            # Tarjetas de estado
            dbc.Row([
                # Estado 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Cerraduras Activas", className="card-title text-center"),
                            html.H2("42", className="text-center text-primary mb-0"),
                            html.P("100% en línea", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Estado 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Accesos Hoy", className="card-title text-center"),
                            html.H2("128", className="text-center text-primary mb-0"),
                            html.P("↑ 12% vs. ayer", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Estado 3
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Alertas", className="card-title text-center"),
                            html.H2("0", className="text-center text-success mb-0"),
                            html.P("Sin alertas activas", className="text-muted text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
            ]),
            
            # Lista de cerraduras
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("Cerraduras", className="d-inline-block mb-0"),
                            dbc.Button("Añadir Cerradura", color="primary", size="sm", className="float-end")
                        ]),
                        dbc.CardBody([
                            html.Div([
                                html.Table([
                                    html.Thead([
                                        html.Tr([
                                            html.Th("ID"),
                                            html.Th("Ubicación"),
                                            html.Th("Estado"),
                                            html.Th("Último Acceso"),
                                            html.Th("Batería"),
                                            html.Th("Acciones")
                                        ])
                                    ]),
                                    html.Tbody([
                                        html.Tr([
                                            html.Td("LOCK-001"),
                                            html.Td("Entrada Principal"),
                                            html.Td(html.Span("Cerrado", className="badge bg-success")),
                                            html.Td("2025-03-04 12:30"),
                                            html.Td([
                                                dbc.Progress(value=85, color="success", style={"height": "10px"}),
                                                html.Small("85%", className="text-muted")
                                            ]),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-lock"), color="primary", size="sm", className="me-1", id="lock-1"),
                                                    dbc.Button(html.I(className="fas fa-unlock"), color="success", size="sm", className="me-1", id="unlock-1"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-1")
                                                ])
                                            ])
                                        ]),
                                        html.Tr([
                                            html.Td("LOCK-002"),
                                            html.Td("Oficina 101"),
                                            html.Td(html.Span("Abierto", className="badge bg-warning")),
                                            html.Td("2025-03-04 12:15"),
                                            html.Td([
                                                dbc.Progress(value=72, color="success", style={"height": "10px"}),
                                                html.Small("72%", className="text-muted")
                                            ]),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-lock"), color="primary", size="sm", className="me-1", id="lock-2"),
                                                    dbc.Button(html.I(className="fas fa-unlock"), color="success", size="sm", className="me-1", id="unlock-2"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-2")
                                                ])
                                            ])
                                        ]),
                                        html.Tr([
                                            html.Td("LOCK-003"),
                                            html.Td("Sala de Reuniones"),
                                            html.Td(html.Span("Cerrado", className="badge bg-success")),
                                            html.Td("2025-03-04 11:45"),
                                            html.Td([
                                                dbc.Progress(value=45, color="warning", style={"height": "10px"}),
                                                html.Small("45%", className="text-muted")
                                            ]),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-lock"), color="primary", size="sm", className="me-1", id="lock-3"),
                                                    dbc.Button(html.I(className="fas fa-unlock"), color="success", size="sm", className="me-1", id="unlock-3"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-3")
                                                ])
                                            ])
                                        ]),
                                        html.Tr([
                                            html.Td("LOCK-004"),
                                            html.Td("Almacén"),
                                            html.Td(html.Span("Cerrado", className="badge bg-success")),
                                            html.Td("2025-03-04 10:30"),
                                            html.Td([
                                                dbc.Progress(value=15, color="danger", style={"height": "10px"}),
                                                html.Small("15%", className="text-muted")
                                            ]),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-lock"), color="primary", size="sm", className="me-1", id="lock-4"),
                                                    dbc.Button(html.I(className="fas fa-unlock"), color="success", size="sm", className="me-1", id="unlock-4"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-4")
                                                ])
                                            ])
                                        ]),
                                    ])
                                ], className="table table-striped table-hover")
                            ], style={"overflowX": "auto"})
                        ])
                    ], className="shadow-sm")
                ], className="mb-4")
            ]),
            
            # Historial de accesos
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Historial de Accesos Recientes"),
                        dbc.CardBody([
                            html.Div([
                                html.Table([
                                    html.Thead([
                                        html.Tr([
                                            html.Th("Fecha/Hora"),
                                            html.Th("Usuario"),
                                            html.Th("Cerradura"),
                                            html.Th("Acción"),
                                            html.Th("Método"),
                                            html.Th("Estado")
                                        ])
                                    ]),
                                    html.Tbody([
                                        html.Tr([
                                            html.Td("2025-03-04 12:30"),
                                            html.Td("usuario1@example.com"),
                                            html.Td("Entrada Principal"),
                                            html.Td("Desbloqueo"),
                                            html.Td("App Móvil"),
                                            html.Td(html.Span("Exitoso", className="badge bg-success"))
                                        ]),
                                        html.Tr([
                                            html.Td("2025-03-04 12:15"),
                                            html.Td("usuario2@example.com"),
                                            html.Td("Oficina 101"),
                                            html.Td("Desbloqueo"),
                                            html.Td("Tarjeta NFC"),
                                            html.Td(html.Span("Exitoso", className="badge bg-success"))
                                        ]),
                                        html.Tr([
                                            html.Td("2025-03-04 11:45"),
                                            html.Td("usuario3@example.com"),
                                            html.Td("Sala de Reuniones"),
                                            html.Td("Bloqueo"),
                                            html.Td("App Móvil"),
                                            html.Td(html.Span("Exitoso", className="badge bg-success"))
                                        ]),
                                        html.Tr([
                                            html.Td("2025-03-04 11:30"),
                                            html.Td("usuario4@example.com"),
                                            html.Td("Almacén"),
                                            html.Td("Desbloqueo"),
                                            html.Td("Código PIN"),
                                            html.Td(html.Span("Fallido", className="badge bg-danger"))
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