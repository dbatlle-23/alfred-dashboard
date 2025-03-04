from dash import html, dcc
import dash_bootstrap_components as dbc

# Layout para la página de Spaces
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Spaces Management", className="mb-4"),
            html.P("Gestiona y monitorea los espacios inteligentes de tu organización.", className="lead mb-4"),
            
            # Tarjetas de resumen
            dbc.Row([
                # Resumen 1
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Espacios Totales", className="card-title text-center"),
                            html.H2("24", className="text-center text-primary mb-0"),
                            html.P("3 nuevos este mes", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Resumen 2
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Ocupación Actual", className="card-title text-center"),
                            html.H2("68%", className="text-center text-primary mb-0"),
                            html.P("16 espacios ocupados", className="text-muted text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Resumen 3
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Reservas Hoy", className="card-title text-center"),
                            html.H2("12", className="text-center text-primary mb-0"),
                            html.P("↑ 20% vs. ayer", className="text-success text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
            ]),
            
            # Filtros y búsqueda
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Buscar espacio"),
                                    dbc.Input(type="text", placeholder="Nombre o ID del espacio", className="mb-2")
                                ], md=4),
                                dbc.Col([
                                    html.Label("Tipo"),
                                    dbc.Select(
                                        options=[
                                            {"label": "Todos", "value": "all"},
                                            {"label": "Oficina", "value": "office"},
                                            {"label": "Sala de Reuniones", "value": "meeting"},
                                            {"label": "Área Común", "value": "common"},
                                            {"label": "Almacén", "value": "storage"}
                                        ],
                                        value="all",
                                        className="mb-2"
                                    )
                                ], md=3),
                                dbc.Col([
                                    html.Label("Estado"),
                                    dbc.Select(
                                        options=[
                                            {"label": "Todos", "value": "all"},
                                            {"label": "Disponible", "value": "available"},
                                            {"label": "Ocupado", "value": "occupied"},
                                            {"label": "Reservado", "value": "reserved"},
                                            {"label": "Mantenimiento", "value": "maintenance"}
                                        ],
                                        value="all",
                                        className="mb-2"
                                    )
                                ], md=3),
                                dbc.Col([
                                    html.Label("\u00A0"), # Espacio en blanco para alinear
                                    dbc.Button("Buscar", color="primary", className="w-100")
                                ], md=2)
                            ])
                        ])
                    ], className="shadow-sm")
                ], className="mb-4")
            ]),
            
            # Lista de espacios
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("Espacios", className="d-inline-block mb-0"),
                            dbc.Button("Añadir Espacio", color="primary", size="sm", className="float-end")
                        ]),
                        dbc.CardBody([
                            html.Div([
                                html.Table([
                                    html.Thead([
                                        html.Tr([
                                            html.Th("ID"),
                                            html.Th("Nombre"),
                                            html.Th("Tipo"),
                                            html.Th("Capacidad"),
                                            html.Th("Estado"),
                                            html.Th("Ocupantes"),
                                            html.Th("Acciones")
                                        ])
                                    ]),
                                    html.Tbody([
                                        html.Tr([
                                            html.Td("SPACE-001"),
                                            html.Td("Sala de Juntas Principal"),
                                            html.Td("Sala de Reuniones"),
                                            html.Td("12 personas"),
                                            html.Td(html.Span("Ocupado", className="badge bg-danger")),
                                            html.Td("8/12"),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-eye"), color="primary", size="sm", className="me-1", id="view-1"),
                                                    dbc.Button(html.I(className="fas fa-calendar"), color="success", size="sm", className="me-1", id="reserve-1"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-space-1")
                                                ])
                                            ])
                                        ]),
                                        html.Tr([
                                            html.Td("SPACE-002"),
                                            html.Td("Oficina Ejecutiva"),
                                            html.Td("Oficina"),
                                            html.Td("3 personas"),
                                            html.Td(html.Span("Disponible", className="badge bg-success")),
                                            html.Td("0/3"),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-eye"), color="primary", size="sm", className="me-1", id="view-2"),
                                                    dbc.Button(html.I(className="fas fa-calendar"), color="success", size="sm", className="me-1", id="reserve-2"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-space-2")
                                                ])
                                            ])
                                        ]),
                                        html.Tr([
                                            html.Td("SPACE-003"),
                                            html.Td("Área de Descanso"),
                                            html.Td("Área Común"),
                                            html.Td("20 personas"),
                                            html.Td(html.Span("Ocupado", className="badge bg-danger")),
                                            html.Td("12/20"),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-eye"), color="primary", size="sm", className="me-1", id="view-3"),
                                                    dbc.Button(html.I(className="fas fa-calendar"), color="success", size="sm", className="me-1", id="reserve-3"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-space-3")
                                                ])
                                            ])
                                        ]),
                                        html.Tr([
                                            html.Td("SPACE-004"),
                                            html.Td("Sala de Conferencias"),
                                            html.Td("Sala de Reuniones"),
                                            html.Td("30 personas"),
                                            html.Td(html.Span("Reservado", className="badge bg-warning")),
                                            html.Td("0/30"),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-eye"), color="primary", size="sm", className="me-1", id="view-4"),
                                                    dbc.Button(html.I(className="fas fa-calendar"), color="success", size="sm", className="me-1", id="reserve-4"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-space-4")
                                                ])
                                            ])
                                        ]),
                                        html.Tr([
                                            html.Td("SPACE-005"),
                                            html.Td("Almacén Principal"),
                                            html.Td("Almacén"),
                                            html.Td("5 personas"),
                                            html.Td(html.Span("Mantenimiento", className="badge bg-secondary")),
                                            html.Td("0/5"),
                                            html.Td([
                                                dbc.ButtonGroup([
                                                    dbc.Button(html.I(className="fas fa-eye"), color="primary", size="sm", className="me-1", id="view-5"),
                                                    dbc.Button(html.I(className="fas fa-calendar"), color="success", size="sm", className="me-1", id="reserve-5"),
                                                    dbc.Button(html.I(className="fas fa-cog"), color="secondary", size="sm", id="config-space-5")
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
            
            # Calendario de reservas
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Calendario de Reservas"),
                        dbc.CardBody([
                            html.Div([
                                # Aquí iría un componente de calendario real
                                # Por ahora, mostramos un placeholder
                                html.Div([
                                    html.H5("Marzo 2025", className="text-center mb-3"),
                                    html.Table([
                                        html.Thead([
                                            html.Tr([
                                                html.Th("Lun"),
                                                html.Th("Mar"),
                                                html.Th("Mié"),
                                                html.Th("Jue"),
                                                html.Th("Vie"),
                                                html.Th("Sáb"),
                                                html.Th("Dom")
                                            ])
                                        ]),
                                        html.Tbody([
                                            html.Tr([
                                                html.Td(""),
                                                html.Td(""),
                                                html.Td(""),
                                                html.Td(""),
                                                html.Td(""),
                                                html.Td("1"),
                                                html.Td("2")
                                            ]),
                                            html.Tr([
                                                html.Td("3"),
                                                html.Td("4", className="bg-primary text-white"),
                                                html.Td("5"),
                                                html.Td("6"),
                                                html.Td("7"),
                                                html.Td("8"),
                                                html.Td("9")
                                            ]),
                                            html.Tr([
                                                html.Td("10"),
                                                html.Td("11"),
                                                html.Td("12"),
                                                html.Td("13"),
                                                html.Td("14"),
                                                html.Td("15"),
                                                html.Td("16")
                                            ]),
                                            html.Tr([
                                                html.Td("17"),
                                                html.Td("18"),
                                                html.Td("19"),
                                                html.Td("20"),
                                                html.Td("21"),
                                                html.Td("22"),
                                                html.Td("23")
                                            ]),
                                            html.Tr([
                                                html.Td("24"),
                                                html.Td("25"),
                                                html.Td("26"),
                                                html.Td("27"),
                                                html.Td("28"),
                                                html.Td("29"),
                                                html.Td("30")
                                            ]),
                                            html.Tr([
                                                html.Td("31"),
                                                html.Td(""),
                                                html.Td(""),
                                                html.Td(""),
                                                html.Td(""),
                                                html.Td(""),
                                                html.Td("")
                                            ])
                                        ])
                                    ], className="table table-bordered text-center")
                                ], className="calendar-container")
                            ])
                        ])
                    ], className="shadow-sm")
                ], className="mb-4")
            ])
        ])
    ])
]) 