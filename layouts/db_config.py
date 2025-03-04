from dash import html, dcc
import dash_bootstrap_components as dbc

# Layout para la página de configuración de base de datos
layout = html.Div([
    html.H2("Configuración de Base de Datos", className="mb-4"),
    
    dbc.Card([
        dbc.CardBody([
            html.H5("Parámetros de Conexión", className="card-title"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Host:", className="form-label"),
                    dbc.Input(id="db-host-input", type="text", placeholder="localhost"),
                ], width=6),
                dbc.Col([
                    html.Label("Puerto:", className="form-label"),
                    dbc.Input(id="db-port-input", type="text", placeholder="5432"),
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Base de Datos:", className="form-label"),
                    dbc.Input(id="db-name-input", type="text", placeholder="nombre_db"),
                ], width=12),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Usuario:", className="form-label"),
                    dbc.Input(id="db-user-input", type="text", placeholder="usuario"),
                ], width=6),
                dbc.Col([
                    html.Label("Contraseña:", className="form-label"),
                    dbc.Input(id="db-password-input", type="password", placeholder="contraseña"),
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("SSL Mode:", className="form-label"),
                    dcc.Dropdown(
                        id="db-sslmode-dropdown",
                        options=[
                            {"label": "Prefer", "value": "prefer"},
                            {"label": "Require", "value": "require"},
                            {"label": "Disable", "value": "disable"},
                        ],
                        value="prefer",
                    ),
                ], width=12),
            ], className="mb-3"),
            
            dbc.Button("Guardar Configuración", id="save-db-config-btn", color="primary"),
            html.Div([
                html.Br(),
                dbc.Alert(id="db-config-status", color="", is_open=False, className="mt-3"),
            ]),
        ]),
    ]),
])
