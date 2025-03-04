from dash import html
import dash_bootstrap_components as dbc

# Layout para la página de inicio
layout = html.Div([
    html.H2("Dashboard Alfred", className="mb-4"),
    
    dbc.Card([
        dbc.CardBody([
            html.H5("Bienvenido al Dashboard de Alfred", className="card-title"),
            html.P(
                "Esta aplicación te permite explorar y gestionar la base de datos de Alfred. "
                "Utiliza el menú lateral para navegar entre las diferentes secciones.",
                className="card-text"
            ),
            html.Div([
                html.P("Para comenzar, puedes:", className="mt-3"),
                html.Ul([
                    html.Li([
                        "Configurar la conexión a la base de datos en ",
                        html.A("Configuración DB", href="/db-config")
                    ]),
                    html.Li([
                        "Explorar las tablas y datos en ",
                        html.A("Explorador BD", href="/database-explorer")
                    ]),
                    html.Li([
                        "Exportar datos específicos en ",
                        html.A("Exportar Datos", href="/data-export")
                    ]),
                ])
            ])
        ])
    ])
])
